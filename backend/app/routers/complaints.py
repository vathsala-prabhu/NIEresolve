from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
)
from backend.app.auth.dependencies import (
    get_current_user,
    require_complainant,
    require_any_officer,
    require_admin,
)
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.escalation_service import EscalationService
from backend.app.ml.duplicate_detector import duplicate_detector

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

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

    return {
        "id": comp.id,
        "grievance_id": comp.grievance_id,
        "title": comp.title,
        "category": comp.category,
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
        "affected_students_count": comp.affected_students_count,
        "submission_date": comp.submission_date,
        "expected_deadline": comp.expected_deadline,
        "days_pending": days_pending,
        "resolution_date": comp.resolution_date,
        "student_confirmed": comp.student_confirmed,
    }

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
        department_id=payload.department_id,
        location_name=payload.location_name,
        is_anonymous=payload.is_anonymous,
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
    }

@router.get("", response_model=List[ComplaintListResponse])
def get_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
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
    """
    query = db.query(Complaint)

    # Scoping by Role
    if current_user.role in [UserRole.STUDENT, UserRole.FACULTY]:
        query = query.filter(Complaint.complainant_id == current_user.id)
    elif current_user.role == UserRole.DEPT_OFFICER:
        if current_user.department_id:
            query = query.filter(Complaint.department_id == current_user.department_id)
    elif current_user.role == UserRole.GRIEVANCE_CELL:
        # Grievance Cell oversees Tier 2 + all escalated/unresolved institutional complaints
        pass
    elif current_user.role == UserRole.PRINCIPAL:
        # Principal reviews Tier 3, Tier 2 escalations, and Critical priorities
        pass

    # Optional Filters
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    if category_filter:
        query = query.filter(Complaint.category == category_filter)
    if tier_filter:
        query = query.filter(Complaint.current_tier == tier_filter)
    if priority_filter:
        query = query.filter(Complaint.final_priority == priority_filter)
    if department_id:
        query = query.filter(Complaint.department_id == department_id)

    complaints = query.order_by(Complaint.submission_date.desc()).all()
    return [format_complaint_list_item(c, current_user) for c in complaints]

@router.get("/{complaint_id}", response_model=ComplaintDetailResponse)
def get_complaint_details(
    complaint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns complete grievance details including timeline, evidence, location and duplicates."""
    comp = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")

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
        master_complaint_grievance_id=master_gid,
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

@router.post("/{complaint_id}/override-priority", response_model=dict)
def override_priority(
    complaint_id: int,
    payload: PriorityOverrideRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Allows authorized officers to override the ML-predicted priority with a recorded explanation."""
    comp = ComplaintService.override_priority(
        db=db,
        actor=current_user,
        complaint_id=complaint_id,
        new_priority=payload.new_priority,
        reason=payload.reason,
    )
    return {
        "message": "Priority successfully overridden.",
        "grievance_id": comp.grievance_id,
        "final_priority": comp.final_priority,
    }

@router.post("/{complaint_id}/status", response_model=dict)
def update_status(
    complaint_id: int,
    payload: ComplaintStatusUpdateRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Transitions complaint status (assigned, under_investigation, action_taken, resolved, closed)."""
    comp = ComplaintService.update_status(
        db=db,
        actor=current_user,
        complaint_id=complaint_id,
        new_status=payload.status,
        remarks=payload.remarks,
        assigned_to_id=payload.assigned_to_id,
        resolution_evidence_url=payload.resolution_evidence_url,
    )
    return {
        "message": f"Status updated to {comp.status}.",
        "grievance_id": comp.grievance_id,
        "status": comp.status,
    }

@router.post("/{complaint_id}/pause-escalation", response_model=dict)
def pause_escalation(
    complaint_id: int,
    payload: EscalationPauseRequest,
    current_user: User = Depends(require_any_officer),
    db: Session = Depends(get_db),
):
    """Allows administrators to pause or resume a 15-day escalation deadline with a recorded reason."""
    comp = EscalationService.toggle_deadline_pause(
        db=db,
        actor=current_user,
        complaint_id=complaint_id,
        paused=payload.paused,
        reason=payload.reason,
    )
    return {
        "message": f"Escalation {'paused' if comp.is_escalation_paused else 'resumed'}.",
        "grievance_id": comp.grievance_id,
        "is_escalation_paused": comp.is_escalation_paused,
    }

@router.post("/{complaint_id}/confirm-resolution", response_model=dict)
def confirm_resolution(
    complaint_id: int,
    payload: StudentConfirmResolutionRequest,
    current_user: User = Depends(require_complainant),
    db: Session = Depends(get_db),
):
    """Allows student/faculty complainant to confirm resolution satisfaction or reopen with remarks."""
    comp = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if comp.complainant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the original complainant can confirm resolution.")

    now = utc_now()
    comp.student_confirmed = payload.confirmed
    comp.student_confirmation_remarks = payload.remarks
    comp.student_confirmed_at = now

    if payload.confirmed:
        comp.status = ComplaintStatus.CLOSED
        action_name = "Resolution Confirmed by Complainant"
        remarks_text = payload.remarks or "Complainant confirmed issue is resolved. Complaint closed."
    else:
        comp.status = ComplaintStatus.REOPENED
        action_name = "Resolution Rejected - Complaint Reopened"
        remarks_text = f"Complainant unsatisfied: {payload.remarks or 'Reopened for further investigation.'}"

    db.add(ComplaintTimeline(
        complaint_id=comp.id,
        action=action_name,
        actor_id=current_user.id,
        remarks=remarks_text,
        from_status=ComplaintStatus.RESOLVED,
        to_status=comp.status,
        timestamp=now,
    ))

    db.commit()
    return {
        "message": f"Confirmation recorded. Status is now {comp.status}.",
        "grievance_id": comp.grievance_id,
        "status": comp.status,
    }

