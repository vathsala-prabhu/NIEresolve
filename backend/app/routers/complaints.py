from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.database import get_db, utc_now
from backend.app.models.user import User, UserRole, Department
from backend.app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTier,
    ComplaintPriority,
    ComplaintEvidence,
    ComplaintTimeline,
    ComplaintCampus,
    ComplaintCategory,
    ComplaintVote,
    InternalComplaintMessage,
)
from backend.app.schemas.complaint import (
    ComplaintCreate,
    ComplaintListResponse,
    ComplaintDetailResponse,
    ComplaintStatusUpdateRequest,
    PriorityOverrideRequest,
    DuplicateCheckRequest,
    DuplicateMatchItem,
    DuplicateMergeRequest,
    EscalationPauseRequest,
    StudentConfirmResolutionRequest,
    InternalMessageCreate,
    InternalMessageResponse,
    ComplaintCommunityItemResponse,
    CategorySummaryResponse,
    GrievanceGroupResponse,
)
from backend.app.auth.dependencies import (
    get_current_user,
    require_complainant,
    require_any_officer,
    require_admin,
)
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.issue_grouping_service import group_complaints_by_issue
from backend.app.ml.duplicate_detector import duplicate_detector

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

def _resolve_complaint(db: Session, complaint_id_or_ref: Any) -> Optional[Complaint]:
    """Helper to resolve a complaint by either numeric database ID or institutional grievance ID string."""
    if complaint_id_or_ref is None:
        return None
    cid_str = str(complaint_id_or_ref).strip()
    if cid_str.isdigit():
        return db.query(Complaint).filter(Complaint.id == int(cid_str)).first()
    return db.query(Complaint).filter(Complaint.grievance_id == cid_str).first()

def format_complaint_list_item(comp: Complaint, current_user: User) -> dict:
    """Helper to format complaint item with appropriate role privacy masks."""
    is_privileged = current_user.role in [
        UserRole.DEPT_OFFICER,
        UserRole.GRIEVANCE_CELL,
        UserRole.PRINCIPAL,
        UserRole.SUPER_ADMIN,
    ]
    is_owner = comp.complainant_id == current_user.id

    complainant_name = "Confidential Reporter"
    complainant_identifier = None
    if is_owner or not comp.is_anonymous or current_user.role == UserRole.SUPER_ADMIN:
        complainant_name = comp.complainant.full_name
        if comp.complainant.student_profile:
            complainant_identifier = comp.complainant.student_profile.usn
        elif comp.complainant.faculty_profile:
            complainant_identifier = comp.complainant.faculty_profile.faculty_id

    now = utc_now()
    days_pending = (now - comp.submission_date).days
    has_upvoted = any(v.user_id == current_user.id for v in comp.votes) if hasattr(comp, 'votes') and comp.votes else False

    master_gid = None
    if comp.master_complaint_id:
        if getattr(comp, "master_complaint", None):
            master_gid = comp.master_complaint.grievance_id

    return {
        "id": comp.id,
        "grievance_id": comp.grievance_id,
        "title": comp.title,
        "category": comp.category,
        "campus": comp.campus or ComplaintCampus.NORTH_CAMPUS,
        "department_id": comp.department_id,
        "department_name": comp.department.name if comp.department else "General",
        "department_code": comp.department.code if comp.department else "GEN",
        "complainant_name": complainant_name,
        "complainant_identifier": complainant_identifier,
        "complainant_role": comp.complainant.role,
        "is_anonymous": comp.is_anonymous,
        "status": comp.status,
        "current_tier": comp.current_tier,
        "predicted_priority": comp.predicted_priority,
        "final_priority": comp.final_priority,
        "is_safety_critical": comp.is_safety_critical,
        "is_duplicate": comp.is_duplicate,
        "master_complaint_grievance_id": master_gid,
        "affected_students_count": comp.affected_students_count,
        "upvote_count": comp.upvote_count or 0,
        "has_upvoted": has_upvoted,
        "is_confidential_evidence": bool(comp.is_confidential_evidence),
        "submission_date": comp.submission_date,
        "expected_deadline": comp.expected_deadline,
        "days_pending": days_pending,
        "resolved_at": comp.resolved_at,
        "confirmation_deadline": comp.confirmation_deadline,
        "resolution_date": comp.resolution_date,
        "student_confirmed": comp.student_confirmed,
        "is_auto_confirmed": bool(comp.is_auto_confirmed),
        "reopen_count": comp.reopen_count or 0,
        "reopen_reason": comp.reopen_reason,
    }

# ----------------------------------------------------------------------
# STATIC ROUTES (MUST BE DEFINED BEFORE PARAMETERIZED /{complaint_id})
# ----------------------------------------------------------------------

@router.post("", response_model=dict)
def submit_complaint(
    payload: ComplaintCreate,
    current_user: User = Depends(require_complainant),
    db: Session = Depends(get_db),
):
    """
    Submits a new grievance.
    Captures title, description, category, department, location, and geo-coordinates.
    Executes ML priority prediction and checks for duplicates.
    """
    result = ComplaintService.create_complaint(
        db=db,
        complainant=current_user,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        campus=payload.campus,
        department_id=payload.department_id,
        location_name=payload.location_name,
        is_confidential_evidence=payload.is_confidential_evidence,
        is_anonymous=False, # Anonymous submission is disabled
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        exception_reason=payload.exception_reason,
    )
    complaint = result["complaint"]
    return {
        "message": "Complaint submitted successfully.",
        "grievance_id": complaint.grievance_id,
        "complaint_id": complaint.id,
        "predicted_priority": complaint.predicted_priority,
        "final_priority": complaint.final_priority,
        "potential_duplicates_count": len(result["potential_duplicates"]),
        "potential_duplicates": result["potential_duplicates"],
        "is_duplicate": complaint.is_duplicate,
        "master_complaint_id": complaint.master_complaint_id,
    }

@router.get("", response_model=List[ComplaintListResponse])
def get_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    campus_filter: Optional[str] = Query(None, alias="campus"),
    tier_filter: Optional[str] = Query(None, alias="tier"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    department_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns complaints filtered strictly by role:
    - Student: Their submitted complaints.
    - Faculty: Their submitted complaints.
    - Tier 1 (Dept Officer): Complaints assigned to their department.
    - Tier 2 (Grievance Cell): All escalated Tier 2 complaints + institutional pending cases.
    - Tier 3 (Principal): Tier 2 & Tier 3 escalations + Critical/High cases institution-wide.
    - Super Admin: All complaints.
    - Scholarship Coordinator: Restricted with 403 Forbidden.
    """
    if current_user.role == UserRole.SCHOLARSHIP_COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scholarship coordinators are restricted from grievance redressal complaints.",
        )

    query = db.query(Complaint)

    # Scoping by Role
    if current_user.role in [UserRole.STUDENT, UserRole.FACULTY]:
        query = query.filter(Complaint.complainant_id == current_user.id)
    elif current_user.role == UserRole.DEPT_OFFICER:
        if current_user.department_id:
            query = query.filter(Complaint.department_id == current_user.department_id)
    elif current_user.role == UserRole.GRIEVANCE_CELL:
        pass
    elif current_user.role == UserRole.PRINCIPAL:
        pass

    # Optional Filters
    if isinstance(status_filter, str) and status_filter.strip():
        query = query.filter(Complaint.status == status_filter.strip())
    if isinstance(category_filter, str) and category_filter.strip():
        query = query.filter(Complaint.category == category_filter.strip())
    if isinstance(campus_filter, str) and campus_filter.strip():
        query = query.filter(Complaint.campus == campus_filter.strip())
    if isinstance(tier_filter, str) and tier_filter.strip():
        query = query.filter(Complaint.current_tier == tier_filter.strip())
    if isinstance(priority_filter, str) and priority_filter.strip():
        query = query.filter(Complaint.final_priority == priority_filter.strip())
    if isinstance(department_id, int):
        query = query.filter(Complaint.department_id == department_id)

    complaints = query.order_by(Complaint.submission_date.desc()).all()
    return [format_complaint_list_item(c, current_user) for c in complaints]

@router.get("/grouped", response_model=List[GrievanceGroupResponse])
def get_grouped_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    campus_filter: Optional[str] = Query(None, alias="campus"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    tier_filter: Optional[str] = Query(None, alias="tier"),
    department_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns complaints organized into normalized smart issue groups
    (e.g. Water Cooler Issues, Washroom Issues, Classroom Infrastructure, Electrical Issues, etc.).
    Preserves all individual complaint records, grievance IDs, dates, and ownership.
    """
    if current_user.role == UserRole.SCHOLARSHIP_COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scholarship coordinators are restricted from grievance redressal complaints.",
        )

    query = db.query(Complaint)
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Complaint.complainant_id == current_user.id)
    elif current_user.role == UserRole.FACULTY:
        query = query.filter(Complaint.complainant_id == current_user.id)
    elif current_user.role == UserRole.DEPT_OFFICER:
        if current_user.department_id:
            query = query.filter(Complaint.department_id == current_user.department_id)
    elif current_user.role == UserRole.GRIEVANCE_CELL:
        query = query.filter(Complaint.current_tier.in_([ComplaintTier.TIER_2, ComplaintTier.TIER_3]))
    elif current_user.role == UserRole.PRINCIPAL:
        query = query.filter(
            or_(
                Complaint.current_tier == ComplaintTier.TIER_3,
                Complaint.final_priority.in_([ComplaintPriority.CRITICAL, ComplaintPriority.HIGH]),
            )
        )

    if isinstance(status_filter, str) and status_filter.strip():
        query = query.filter(Complaint.status == status_filter.strip())
    if isinstance(category_filter, str) and category_filter.strip():
        query = query.filter(Complaint.category == category_filter.strip())
    if isinstance(campus_filter, str) and campus_filter.strip():
        query = query.filter(Complaint.campus == campus_filter.strip())
    if isinstance(priority_filter, str) and priority_filter.strip():
        query = query.filter(Complaint.final_priority == priority_filter.strip())
    if isinstance(tier_filter, str) and tier_filter.strip():
        query = query.filter(Complaint.current_tier == tier_filter.strip())
    if isinstance(department_id, int):
        query = query.filter(Complaint.department_id == department_id)

    complaints = query.order_by(Complaint.submission_date.desc()).all()
    grouped_data = group_complaints_by_issue(complaints)

    results = []
    for g in grouped_data:
        formatted_items = [format_complaint_list_item(c, current_user) for c in g["complaints"]]
        results.append(GrievanceGroupResponse(
            group_id=g["group_id"],
            group_name=g["group_name"],
            category=g["category"],
            icon=g["icon"],
            total_count=g["total_count"],
            pending_count=g["pending_count"],
            resolved_count=g["resolved_count"],
            complaints=formatted_items,
        ))
    return results

@router.get("/community", response_model=List[ComplaintCommunityItemResponse])
def get_community_complaints(
    category: Optional[str] = Query(None),
    campus: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("most_supported", description="most_supported or recent"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Browse existing community grievances by category, campus, and keyword.
    Supports students and faculty in viewing shared issues and upvoting existing complaints.
    Protects complainant identity and confidential evidence.
    """
    if current_user.role == UserRole.SCHOLARSHIP_COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scholarship coordinators are restricted from grievance redressal complaints.",
        )

    query = db.query(Complaint).filter(Complaint.is_duplicate == False)

    if category and category != "All":
        query = query.filter(Complaint.category == category)
    if campus and campus != "All":
        query = query.filter(Complaint.campus == campus)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter((Complaint.title.ilike(search_term)) | (Complaint.description.ilike(search_term)))

    if sort_by == "most_supported":
        query = query.order_by(Complaint.upvote_count.desc(), Complaint.submission_date.desc())
    else:
        query = query.order_by(Complaint.submission_date.desc())

    complaints = query.limit(100).all()

    # Preload user's votes for fast lookup
    user_voted_ids = set(
        v.complaint_id for v in db.query(ComplaintVote.complaint_id).filter(ComplaintVote.user_id == current_user.id).all()
    )

    now = utc_now()
    results = []
    for c in complaints:
        days_pending = (now - c.submission_date).days
        results.append(ComplaintCommunityItemResponse(
            id=c.id,
            grievance_id=c.grievance_id,
            title=c.title,
            category=c.category,
            campus=c.campus or ComplaintCampus.NORTH_CAMPUS,
            location_name=c.location_name,
            description=c.description,
            status=c.status,
            final_priority=c.final_priority,
            is_safety_critical=c.is_safety_critical,
            upvote_count=c.upvote_count or 0,
            has_upvoted=c.id in user_voted_ids,
            affected_students_count=c.affected_students_count or 1,
            submission_date=c.submission_date,
            days_pending=days_pending,
        ))
    return results

@router.get("/categories/summary", response_model=List[CategorySummaryResponse])
def get_categories_summary(
    campus: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated complaint statistics for each of the 14 defined institutional categories.
    """
    if current_user.role == UserRole.SCHOLARSHIP_COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scholarship coordinators are restricted from grievance redressal complaints.",
        )

    summaries = []
    for cat in ComplaintCategory.ALL:
        query = db.query(Complaint).filter(Complaint.category == cat, Complaint.is_duplicate == False)
        if campus and campus != "All":
            query = query.filter(Complaint.campus == campus)

        all_cat_complaints = query.all()
        total = len(all_cat_complaints)
        pending = sum(1 for c in all_cat_complaints if c.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CONFIRMED_RESOLVED, ComplaintStatus.AUTO_CONFIRMED_RESOLVED, ComplaintStatus.CLOSED])
        resolved = total - pending
        north_count = sum(1 for c in all_cat_complaints if c.campus == ComplaintCampus.NORTH_CAMPUS)
        south_count = sum(1 for c in all_cat_complaints if c.campus == ComplaintCampus.SOUTH_CAMPUS)

        summaries.append(CategorySummaryResponse(
            category=cat,
            total_complaints=total,
            pending_complaints=pending,
            resolved_complaints=resolved,
            north_campus_count=north_count,
            south_campus_count=south_count,
        ))
    return summaries

@router.post("/check-duplicate", response_model=List[DuplicateMatchItem])
def check_duplicate(payload: DuplicateCheckRequest, db: Session = Depends(get_db)):
    """Pre-submission check: compares complaint draft with active unresolved complaints."""
    active_complaints = (
        db.query(Complaint)
        .filter(
            Complaint.status.notin_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]),
            Complaint.is_duplicate == False,
        )
        .all()
    )
    matches = duplicate_detector.find_potential_duplicates(
        payload.title,
        payload.description,
        payload.category,
        payload.department_id,
        active_complaints,
    )
    return [
        DuplicateMatchItem(
            complaint_id=m["complaint_id"],
            grievance_id=m["grievance_id"],
            title=m["title"],
            category=m["category"],
            similarity_score=m["similarity_score"],
            status=m["status"],
            created_at=m["submission_date"],
        )
        for m in matches
    ]

@router.post("/merge", response_model=dict)
def merge_complaints(
    payload: DuplicateMergeRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Merges a duplicate complaint into a master complaint with recorded reason and notification."""
    master = ComplaintService.merge_complaints(
        db=db,
        actor=current_user,
        master_complaint_id=payload.master_complaint_id,
        duplicate_complaint_id=payload.duplicate_complaint_id,
        reason=payload.reason,
    )
    return {
        "message": f"Successfully merged into master complaint {master.grievance_id}.",
        "master_grievance_id": master.grievance_id,
        "affected_students_count": master.affected_students_count,
    }

# ----------------------------------------------------------------------
# PARAMETERIZED ROUTES (/{complaint_id}) - ACCEPTS INTEGER OR GRIEVANCE ID
# ----------------------------------------------------------------------

@router.get("/{complaint_id}", response_model=ComplaintDetailResponse)
def get_complaint_details(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns complete grievance details including timeline, evidence, location and duplicates."""
    if current_user.role == UserRole.SCHOLARSHIP_COORDINATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scholarship coordinators are restricted from grievance redressal complaints.",
        )

    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Complaint '{complaint_id}' not found")

    # Authorization Check
    is_owner = comp.complainant_id == current_user.id
    is_officer = current_user.role in [
        UserRole.DEPT_OFFICER,
        UserRole.GRIEVANCE_CELL,
        UserRole.PRINCIPAL,
        UserRole.SUPER_ADMIN,
    ]
    if not is_owner and not is_officer:
        raise HTTPException(status_code=403, detail="Access denied to this grievance.")

    base_data = format_complaint_list_item(comp, current_user)

    # Master grievance ID if merged
    master_gid = None
    if comp.master_complaint_id:
        master = db.query(Complaint).filter(Complaint.id == comp.master_complaint_id).first()
        if master:
            master_gid = master.grievance_id

    # Evidence items
    evidence_res = []
    for ev in comp.evidence_items:
        # Hide confidential evidence from other students
        if ev.is_confidential and not is_officer and not is_owner:
            continue
        evidence_res.append({
            "id": ev.id,
            "file_url": ev.file_url,
            "file_name": ev.file_name,
            "file_type": ev.file_type,
            "file_size_bytes": ev.file_size_bytes,
            "verification_status": ev.verification_status,
            "officer_remarks": ev.officer_remarks,
            "verified_at": ev.verified_at,
            "is_confidential": ev.is_confidential,
            "created_at": ev.created_at,
        })

    # Location data
    loc_res = None
    if comp.location_data:
        loc_res = {
            "latitude": comp.location_data.latitude,
            "longitude": comp.location_data.longitude,
            "accuracy_meters": comp.location_data.accuracy_meters,
            "captured_at": comp.location_data.captured_at,
            "is_exception_granted": comp.location_data.is_exception_granted,
            "exception_reason": comp.location_data.exception_reason,
        }

    # Timeline entries
    timeline_res = []
    for t in comp.timeline_entries:
        actor_name = t.actor.full_name if t.actor else "Automated System"
        timeline_res.append({
            "id": t.id,
            "action": t.action,
            "actor_name": actor_name,
            "remarks": t.remarks,
            "from_status": t.from_status,
            "to_status": t.to_status,
            "timestamp": t.timestamp,
        })

    # Duplicates list
    duplicates_list = [format_complaint_list_item(dup, current_user) for dup in comp.duplicates]
    assigned_to_name = comp.assigned_to.full_name if comp.assigned_to else None

    return ComplaintDetailResponse(
        **base_data,
        description=comp.description,
        location_name=comp.location_name,
        assigned_to_name=assigned_to_name,
        priority_override_reason=comp.priority_override_reason,
        priority_confidence=comp.priority_confidence,
        priority_explanation=comp.priority_explanation,
        duplicate_similarity_score=comp.duplicate_similarity_score,
        is_escalation_paused=comp.is_escalation_paused,
        escalation_pause_reason=comp.escalation_pause_reason,
        resolution_remarks=comp.resolution_remarks,
        resolution_evidence_url=comp.resolution_evidence_url,
        student_confirmation_remarks=comp.student_confirmation_remarks,
        evidence_items=evidence_res,
        location_data=loc_res,
        timeline_entries=timeline_res,
        duplicates_list=duplicates_list,
    )

@router.post("/{complaint_id}/override-priority", response_model=dict)
def override_priority(
    complaint_id: str,
    payload: PriorityOverrideRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Allows authorized officers to override the ML-predicted priority with a recorded explanation."""
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    updated = ComplaintService.override_priority(
        db=db,
        actor=current_user,
        complaint_id=comp.id,
        new_priority=payload.new_priority,
        reason=payload.reason,
    )
    return {
        "message": "Priority successfully overridden.",
        "grievance_id": updated.grievance_id,
        "final_priority": updated.final_priority,
    }

@router.post("/{complaint_id}/status", response_model=dict)
def update_status(
    complaint_id: str,
    payload: ComplaintStatusUpdateRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Transitions complaint status (assigned, under_investigation, action_taken, resolved, closed)."""
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    updated = ComplaintService.update_status(
        db=db,
        actor=current_user,
        complaint_id=comp.id,
        new_status=payload.status,
        remarks=payload.remarks,
        assigned_to_id=payload.assigned_to_id,
        resolution_evidence_url=payload.resolution_evidence_url,
    )
    return {
        "message": f"Status updated to {updated.status}.",
        "grievance_id": updated.grievance_id,
        "status": updated.status,
    }

@router.post("/{complaint_id}/pause-escalation", response_model=dict)
def pause_escalation(
    complaint_id: str,
    payload: EscalationPauseRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Allows administrators to pause or resume a 15-day escalation deadline with a recorded reason."""
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    updated = EscalationService.toggle_deadline_pause(
        db=db,
        actor=current_user,
        complaint_id=comp.id,
        paused=payload.paused,
        reason=payload.reason,
    )
    return {
        "message": f"Escalation {'paused' if updated.is_escalation_paused else 'resumed'}.",
        "grievance_id": updated.grievance_id,
        "is_escalation_paused": updated.is_escalation_paused,
    }

@router.post("/{complaint_id}/confirm-resolution", response_model=dict)
def confirm_resolution(
    complaint_id: str,
    payload: StudentConfirmResolutionRequest,
    current_user: User = Depends(require_complainant),
    db: Session = Depends(get_db),
):
    """
    Allows student/faculty complainant to confirm resolution satisfaction or reopen with remarks.
    If confirmed=True -> 'confirmed_resolved'.
    If confirmed=False -> 'reopened', resets 5-day timer, notifies officer, and dispatches SMS.
    """
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    updated = ComplaintService.confirm_resolution(
        db=db,
        complaint_id=comp.id,
        student=current_user,
        confirmed=payload.confirmed,
        remarks=payload.remarks,
    )
    return {
        "message": f"Confirmation recorded. Status is now {updated.status}.",
        "grievance_id": updated.grievance_id,
        "status": updated.status,
        "student_confirmed": updated.student_confirmed,
        "is_auto_confirmed": updated.is_auto_confirmed,
    }

@router.post("/{complaint_id}/upvote", response_model=dict)
def upvote_complaint(
    complaint_id: str,
    current_user: User = Depends(require_complainant),
    db: Session = Depends(get_db),
):
    """
    Registers a community support vote ('I am facing this issue too').
    Enforces 1 vote per user; dynamically adjusts ML priority if thresholds are reached.
    """
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return ComplaintService.upvote_complaint(db, comp.id, current_user)

@router.delete("/{complaint_id}/upvote", response_model=dict)
def remove_upvote(
    complaint_id: str,
    current_user: User = Depends(require_complainant),
    db: Session = Depends(get_db),
):
    """Removes a previously cast community support vote."""
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return ComplaintService.remove_upvote(db, comp.id, current_user)

@router.get("/{complaint_id}/internal-messages", response_model=List[InternalMessageResponse])
def get_internal_messages(
    complaint_id: str,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """
    Internal Discussion Stream strictly accessible to authorized administrative tiers:
    Tier 1 (Dept Officer), Tier 2 (Grievance Cell), Tier 3 (Principal), Super Admin.
    Students and faculty receive 403 Forbidden.
    """
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    messages = ComplaintService.get_internal_messages(db, comp.id, current_user)
    results = []
    for m in messages:
        sender_dept = m.sender.department.name if m.sender.department else None
        results.append(InternalMessageResponse(
            id=m.id,
            complaint_id=m.complaint_id,
            sender_id=m.sender_id,
            sender_name=m.sender.full_name,
            author_name=m.sender.full_name,
            sender_role=m.sender.role,
            author_role=m.sender.role,
            sender_designation=m.sender.role.replace("_", " ").title(),
            sender_department=sender_dept,
            message=m.message,
            attachment_url=m.attachment_url,
            attachment_name=m.attachment_name,
            created_at=m.created_at,
        ))
    return results

@router.post("/{complaint_id}/internal-messages", response_model=InternalMessageResponse)
def post_internal_message(
    complaint_id: str,
    payload: InternalMessageCreate,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """
    Posts an internal communication note or remark for this grievance.
    Strictly restricted to authorized administrative tiers.
    """
    comp = _resolve_complaint(db, complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

    msg = ComplaintService.post_internal_message(
        db=db,
        complaint_id=comp.id,
        officer=current_user,
        message=payload.message,
        attachment_url=payload.attachment_url,
        attachment_name=payload.attachment_name,
    )
    sender_dept = msg.sender.department.name if msg.sender.department else None
    return InternalMessageResponse(
        id=msg.id,
        complaint_id=msg.complaint_id,
        sender_id=msg.sender_id,
        sender_name=msg.sender.full_name,
        author_name=msg.sender.full_name,
        sender_role=msg.sender.role,
        author_role=msg.sender.role,
        sender_designation=msg.sender.role.replace("_", " ").title(),
        sender_department=sender_dept,
        message=msg.message,
        attachment_url=msg.attachment_url,
        attachment_name=msg.attachment_name,
        created_at=msg.created_at,
    )
