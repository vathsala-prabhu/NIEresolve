import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, utc_now
from backend.app.models.user import User, UserRole, StudentProfile, FacultyProfile, Department
from backend.app.schemas.auth import (
    StudentLoginRequest,
    StudentPasswordSetupRequest,
    StudentPasswordResetRequest,
    FacultyLoginRequest,
    AdminLoginRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.auth.security import (
    verify_password,
    hash_password,
    create_access_token,
    normalize_dob,
)
from backend.app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Rate limiter tracking for brute-force protection (Max 5 attempts per 10 minutes)
LOGIN_RATE_LIMIT = 5
RATE_LIMIT_WINDOW_SECONDS = 600
failed_attempts_tracker: Dict[str, List[float]] = {}

GENERIC_STUDENT_AUTH_ERROR = "Authentication failed. Please verify your USN, Full Name, Date of Birth, and Guardian mobile details."

def check_rate_limit(key: str):
    now = time.time()
    attempts = failed_attempts_tracker.get(key, [])
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]
    failed_attempts_tracker[key] = attempts
    if len(attempts) >= LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 10 minutes before retrying.",
        )

def record_failed_attempt(key: str):
    now = time.time()
    attempts = failed_attempts_tracker.get(key, [])
    attempts.append(now)
    failed_attempts_tracker[key] = attempts

def _verify_student_identity_factors(student: StudentProfile, full_name: Optional[str], dob: Optional[str], parent_phone_last4: Optional[str]) -> bool:
    """Helper to verify student 4-factor identity."""
    if not full_name or not dob or not parent_phone_last4:
        return False
    user = student.user
    if not user:
        return False

    stored_name = (user.full_name or "").strip().lower()
    provided_name = full_name.strip().lower()
    if stored_name != provided_name and provided_name not in stored_name:
        return False

    clean_dob = normalize_dob(dob)
    if not verify_password(clean_dob, student.hashed_dob):
        return False

    parent_phone = (student.parent_phone_number or "").strip()
    provided_last4 = parent_phone_last4.strip()
    if not parent_phone or len(parent_phone) < 4 or not parent_phone.endswith(provided_last4):
        return False

    return True

@router.post("/student-login", response_model=TokenResponse)
def student_login(payload: StudentLoginRequest, db: Session = Depends(get_db)):
    """
    Student authentication supporting:
    1. USN + Personal Password (fast, secure daily login)
    2. Multi-factor fallback: USN + Full Name + DOB + Parent Phone Last 4
    """
    clean_usn = payload.usn.strip().upper()
    check_rate_limit(clean_usn)

    student = db.query(StudentProfile).filter(StudentProfile.usn == clean_usn).first()
    if not student or not student.user:
        record_failed_attempt(clean_usn)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student record not found for the provided USN.",
        )

    user = student.user
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student account is deactivated.")

    authenticated = False

    # Path A: Password-based authentication
    if payload.password and payload.password.strip():
        if verify_password(payload.password, user.hashed_password):
            authenticated = True
        else:
            # Check if 4-factor details were also provided for fallback
            if payload.full_name and payload.dob and payload.parent_phone_last4:
                authenticated = _verify_student_identity_factors(
                    student, payload.full_name, payload.dob, payload.parent_phone_last4
                )
            if not authenticated:
                record_failed_attempt(clean_usn)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid USN or password. If you have not created your password yet, click 'First-Time Password Setup'.",
                )
    # Path B: 4-factor multi-factor identity verification
    elif payload.full_name and payload.dob and payload.parent_phone_last4:
        authenticated = _verify_student_identity_factors(
            student, payload.full_name, payload.dob, payload.parent_phone_last4
        )
        if not authenticated:
            record_failed_attempt(clean_usn)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_STUDENT_AUTH_ERROR)
    else:
        record_failed_attempt(clean_usn)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide your USN and Password, or complete all 4 verification fields.",
        )

    # Successful login: reset failed counter
    failed_attempts_tracker.pop(clean_usn, None)

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name,
        "usn": student.usn,
    })

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        identifier=student.usn,
        department_name=student.branch,
    )

@router.post("/student-setup-password", response_model=dict)
def student_setup_password(payload: StudentPasswordSetupRequest, db: Session = Depends(get_db)):
    """
    First-time student password creation:
    Verifies student 4-factor institutional identity before setting personal password.
    """
    clean_usn = payload.usn.strip().upper()
    check_rate_limit(clean_usn)

    student = db.query(StudentProfile).filter(StudentProfile.usn == clean_usn).first()
    if not student or not student.user:
        record_failed_attempt(clean_usn)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_STUDENT_AUTH_ERROR)

    if not _verify_student_identity_factors(student, payload.full_name, payload.dob, payload.parent_phone_last4):
        record_failed_attempt(clean_usn)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_STUDENT_AUTH_ERROR)

    user = student.user
    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    failed_attempts_tracker.pop(clean_usn, None)
    return {
        "message": "Password created successfully! You can now log in using your USN and password.",
        "usn": student.usn,
    }

@router.post("/student-reset-password", response_model=dict)
def student_reset_password(payload: StudentPasswordResetRequest, db: Session = Depends(get_db)):
    """
    Student password reset:
    Verifies student 4-factor institutional identity before updating personal password.
    """
    clean_usn = payload.usn.strip().upper()
    check_rate_limit(clean_usn)

    student = db.query(StudentProfile).filter(StudentProfile.usn == clean_usn).first()
    if not student or not student.user:
        record_failed_attempt(clean_usn)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_STUDENT_AUTH_ERROR)

    if not _verify_student_identity_factors(student, payload.full_name, payload.dob, payload.parent_phone_last4):
        record_failed_attempt(clean_usn)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_STUDENT_AUTH_ERROR)

    user = student.user
    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    failed_attempts_tracker.pop(clean_usn, None)
    return {
        "message": "Password reset successfully! You can now log in with your new password.",
        "usn": student.usn,
    }

@router.post("/faculty-login", response_model=TokenResponse)
def faculty_login(payload: FacultyLoginRequest, db: Session = Depends(get_db)):
    """
    Faculty authentication using Faculty ID and Date of Birth.
    Validates Faculty ID against registered faculty database.
    """
    clean_fac_id = payload.faculty_id.strip().upper()
    faculty = db.query(FacultyProfile).filter(FacultyProfile.faculty_id == clean_fac_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faculty record not found for the provided Faculty ID.",
        )

    clean_dob = normalize_dob(payload.dob)
    if not verify_password(clean_dob, faculty.hashed_dob):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Date of Birth. Please provide your registered date of birth.",
        )

    user = faculty.user
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty account is deactivated.")

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name,
        "faculty_id": faculty.faculty_id,
    })

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        identifier=faculty.faculty_id,
        department_name=faculty.department_name,
    )

@router.post("/admin-login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Administrative Login for Department Officers (Tier 1), Grievance Cell (Tier 2),
    Principal / Higher Authority (Tier 3), Scholarship Coordinators, and Super Admins.
    """
    ident = payload.username_or_email.strip().lower()
    user = (
        db.query(User)
        .filter((User.email.ilike(ident)) | (User.username.ilike(ident)))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name,
    })

    dept_name = user.department.name if user.department else None

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        identifier=user.username,
        department_name=dept_name,
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns currently authenticated user profile."""
    identifier = None
    if current_user.student_profile:
        identifier = current_user.student_profile.usn
    elif current_user.faculty_profile:
        identifier = current_user.faculty_profile.faculty_id

    dept_name = current_user.department.name if current_user.department else None

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        department_id=current_user.department_id,
        department_name=dept_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        identifier=identifier,
        can_publish_scholarships=bool(
            getattr(current_user, "can_publish_scholarships", False)
            or current_user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOLARSHIP_COORDINATOR]
        ),
    )
