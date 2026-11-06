from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, utc_now
from backend.app.models.user import User, UserRole, StudentProfile
from backend.app.models.scholarship import Scholarship
from backend.app.schemas.scholarship import (
    StudentScholarshipProfileCreate,
    ScholarshipProfileUpdateRequest,
    ScholarshipResponse,
    RecommendationResponse,
)
from backend.app.schemas.scholarship_announcement import (
    ScholarshipAnnouncementCreate,
    ScholarshipAnnouncementUpdate,
    ScholarshipAnnouncementResponse,
    StageScheduleUpdate,
    StageScheduleResponse,
    ApplicationProgressResponse,
    CoordinatorPermissionRequest,
    CoordinatorSummaryResponse,
    ScholarshipModuleStats,
)
from backend.app.auth.dependencies import (
    get_current_user,
    require_student,
    require_admin,
    require_scholarship_publisher,
)
from backend.app.services.scholarship_service import ScholarshipService
from backend.app.services.scholarship_announcement_service import ScholarshipAnnouncementService

router = APIRouter(prefix="/api/scholarships", tags=["Scholarships & Announcements"])

@router.get("", response_model=List[ScholarshipResponse])
def get_all_scholarships(db: Session = Depends(get_db)):
    """Returns all active scholarships available to NIE students."""
    return db.query(Scholarship).filter(Scholarship.is_active == True).order_by(Scholarship.application_deadline.asc()).all()

@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_my_recommendations(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """
    Evaluates logged-in student's academic and financial profile against all genuine scholarships.
    Ranks them into Eligible, Potentially Eligible, and Not Eligible with full criteria breakdown.
    """
    if not current_user.student_profile:
        raise HTTPException(
            status_code=400,
            detail="Student profile not configured. Please complete your academic details first.",
        )
    return ScholarshipService.get_recommendations_for_student(db, current_user.student_profile.id)

@router.get("/profile", response_model=dict)
def get_user_scholarship_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves current user scholarship or coordinator profile."""
    if current_user.student_profile:
        sp = current_user.student_profile
        return {
            "role": "student",
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone or sp.student_phone_number or "",
            "course": sp.course or "B.E.",
            "branch": sp.branch or "Computer Science & Engineering",
            "year": sp.year or 3,
            "semester": sp.semester or 6,
            "cgpa": sp.cgpa if sp.cgpa is not None else 8.5,
            "annual_income": sp.annual_income if sp.annual_income is not None else 250000,
            "category": sp.category or "General",
            "state_of_domicile": sp.state_of_domicile or "Karnataka",
            "disability_status": bool(sp.disability_status),
        }
    else:
        dept_name = current_user.department.name if current_user.department else "Scholarship & Financial Aid Cell"
        return {
            "role": current_user.role,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone or "",
            "department_id": current_user.department_id,
            "department_name": dept_name,
            "can_publish_scholarships": current_user.can_publish_scholarships,
        }

@router.post("/profile", response_model=dict)
def update_user_scholarship_profile(
    payload: ScholarshipProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates student academic/financial profile or coordinator institutional profile."""
    if current_user.student_profile or current_user.role == UserRole.STUDENT:
        profile = current_user.student_profile
        if not profile:
            profile = StudentProfile(user_id=current_user.id, usn=current_user.username, hashed_dob="")
            db.add(profile)

        if payload.course is not None:
            profile.course = payload.course
        if payload.branch is not None:
            profile.branch = payload.branch
        if payload.semester is not None:
            profile.semester = payload.semester
        if payload.year is not None:
            profile.year = payload.year
        if payload.cgpa is not None:
            profile.cgpa = payload.cgpa
        if payload.annual_income is not None:
            profile.annual_income = payload.annual_income
        if payload.category is not None:
            profile.category = payload.category
        if payload.state_of_domicile is not None:
            profile.state_of_domicile = payload.state_of_domicile
        if payload.disability_status is not None:
            profile.disability_status = payload.disability_status
        if payload.existing_scholarships is not None:
            profile.existing_scholarships = payload.existing_scholarships

        if payload.full_name:
            current_user.full_name = payload.full_name.strip()
        if payload.phone:
            current_user.phone = payload.phone.strip()
            profile.student_phone_number = payload.phone.strip()

        db.commit()
        db.refresh(profile)
        return {"message": "Student academic and financial profile updated successfully."}
    else:
        # Coordinator / Admin user profile update
        if payload.full_name:
            current_user.full_name = payload.full_name.strip()
        if payload.phone is not None:
            current_user.phone = payload.phone.strip()
        if payload.department_id:
            current_user.department_id = payload.department_id

        db.commit()
        db.refresh(current_user)
        return {"message": "Coordinator profile details updated successfully."}

@router.post("", response_model=ScholarshipResponse)
def add_scholarship(
    sch: ScholarshipResponse,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin endpoint to add or update scholarship records."""
    new_sch = Scholarship(
        name=sch.name,
        provider=sch.provider,
        description=sch.description,
        eligible_categories=sch.eligible_categories,
        min_cgpa=sch.min_cgpa,
        max_family_income=sch.max_family_income,
        eligible_courses=sch.eligible_courses,
        eligible_branches=sch.eligible_branches,
        eligible_genders=sch.eligible_genders,
        eligible_domiciles=sch.eligible_domiciles,
        disability_required=sch.disability_required,
        financial_benefits=sch.financial_benefits,
        required_documents=sch.required_documents,
        application_open_date=sch.application_open_date,
        application_deadline=sch.application_deadline,
        official_url=sch.official_url,
        last_verified_date=utc_now(),
        is_active=True,
    )
    db.add(new_sch)
    db.commit()
    db.refresh(new_sch)
    return new_sch

# =========================================================================
# LIVE SCHOLARSHIP ANNOUNCEMENTS & TIMELINES (PART A, B, C, D)
# =========================================================================

@router.get("/announcements", response_model=List[ScholarshipAnnouncementResponse])
def get_announcements(
    token_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns scholarship announcements.
    Students receive only published announcements.
    Authorized coordinators and Super Admins receive all announcements (published, draft, withdrawn).
    """
    can_view_all = False
    if token_user:
        can_view_all = (
            token_user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOLARSHIP_COORDINATOR]
            or getattr(token_user, "can_publish_scholarships", False) is True
        )
    return ScholarshipAnnouncementService.get_announcements(db, only_published=not can_view_all)

@router.post("/announcements", response_model=ScholarshipAnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: ScholarshipAnnouncementCreate,
    current_user: User = Depends(require_scholarship_publisher),
    db: Session = Depends(get_db),
):
    """
    Authorized scholarship coordinators or Super Admins publish scholarship announcements.
    Includes verification dates, times, locations, and seal/signature instructions.
    Triggers student notifications without duplicates.
    """
    return ScholarshipAnnouncementService.create_announcement(db, payload, current_user)

@router.put("/announcements/{announcement_id}", response_model=ScholarshipAnnouncementResponse)
def update_announcement(
    announcement_id: int,
    payload: ScholarshipAnnouncementUpdate,
    current_user: User = Depends(require_scholarship_publisher),
    db: Session = Depends(get_db),
):
    """
    Authorized scholarship coordinators edit announcements, update deadlines, or reschedule appointments.
    """
    try:
        return ScholarshipAnnouncementService.update_announcement(db, announcement_id, payload, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/announcements/{announcement_id}/withdraw", response_model=ScholarshipAnnouncementResponse)
def withdraw_announcement(
    announcement_id: int,
    current_user: User = Depends(require_scholarship_publisher),
    db: Session = Depends(get_db),
):
    """
    Authorized scholarship coordinators or Super Admin withdraws an announcement.
    """
    try:
        return ScholarshipAnnouncementService.withdraw_announcement(db, announcement_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/my-applications", response_model=List[ApplicationProgressResponse])
def get_my_applications(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """
    Returns logged-in student's scholarship application progress and stage schedules.
    Provides clear timeline tracking from submission through verification, seal & signature, and approval.
    """
    return ScholarshipAnnouncementService.get_student_applications(db, current_user.id)

@router.post("/stages/{stage_id}", response_model=StageScheduleResponse)
def update_stage_schedule(
    stage_id: int,
    payload: StageScheduleUpdate,
    current_user: User = Depends(require_scholarship_publisher),
    db: Session = Depends(get_db),
):
    """
    Scholarship coordinator updates a specific application stage:
    Schedule processing dates, time windows (e.g. 10:30 AM – 1:30 PM), office room, required physical documents, and seal/signature clearances.
    """
    try:
        return ScholarshipAnnouncementService.update_stage_schedule(db, stage_id, payload, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/coordinators", response_model=List[CoordinatorSummaryResponse])
def get_coordinators(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Super Admin Portal: List all potential and active scholarship coordinators,
    their publishing permissions, and activity audit counts.
    """
    return ScholarshipAnnouncementService.get_coordinators(db)

@router.post("/coordinators/permissions", response_model=CoordinatorSummaryResponse)
def set_coordinator_permission(
    payload: CoordinatorPermissionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Super Admin Portal: Grant or revoke scholarship update publishing permissions.
    Enforces Principle of Least Privilege.
    """
    try:
        return ScholarshipAnnouncementService.set_coordinator_permission(
            db, payload.user_id, payload.can_publish_scholarships, current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/stats", response_model=ScholarshipModuleStats)
def get_scholarship_stats(db: Session = Depends(get_db)):
    """
    Returns overall statistics for the Scholarship Notification & Approval Tracking Module.
    """
    return ScholarshipAnnouncementService.get_module_stats(db)
