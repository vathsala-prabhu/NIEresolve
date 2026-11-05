from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole, StudentProfile
from backend.app.models.scholarship import Scholarship
from backend.app.schemas.scholarship import (
    StudentScholarshipProfileCreate,
    ScholarshipResponse,
    RecommendationResponse,
)
from backend.app.auth.dependencies import get_current_user, require_student, require_admin
from backend.app.services.scholarship_service import ScholarshipService

router = APIRouter(prefix="/api/scholarships", tags=["Scholarship Recommendation System"])

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

@router.post("/profile", response_model=dict)
def update_student_profile(
    payload: StudentScholarshipProfileCreate,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Updates student profile fields used for scholarship eligibility calculations."""
    profile = current_user.student_profile
    if not profile:
        profile = StudentProfile(user_id=current_user.id, usn=current_user.username, hashed_dob="")
        db.add(profile)

    profile.course = payload.course
    profile.branch = payload.branch
    profile.semester = payload.semester
    profile.year = payload.year
    profile.cgpa = payload.cgpa
    profile.annual_income = payload.annual_income
    profile.category = payload.category
    profile.state_of_domicile = payload.state_of_domicile
    profile.disability_status = payload.disability_status
    profile.existing_scholarships = payload.existing_scholarships

    db.commit()
    db.refresh(profile)

    return {"message": "Student academic and financial profile updated successfully."}

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
        last_verified_date=datetime.utcnow(),
        is_active=True,
    )
    db.add(new_sch)
    db.commit()
    db.refresh(new_sch)
    return new_sch

