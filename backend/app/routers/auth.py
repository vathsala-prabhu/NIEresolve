from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole, StudentProfile, FacultyProfile, Department
from backend.app.schemas.auth import (
    StudentLoginRequest,
    FacultyLoginRequest,
    AdminLoginRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.auth.security import (
    verify_password,
    create_access_token,
    normalize_dob,
)
from backend.app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/student-login", response_model=TokenResponse)
def student_login(payload: StudentLoginRequest, db: Session = Depends(get_db)):
    """
    Student authentication using University Seat Number (USN) and Date of Birth (DOB).
    Validates USN against registered student database. DOB is hashed and never exposed.
    """
    clean_usn = payload.usn.strip().upper()
    student = db.query(StudentProfile).filter(StudentProfile.usn == clean_usn).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student record not found for the provided USN.",
        )

    clean_dob = normalize_dob(payload.dob)
    if not verify_password(clean_dob, student.hashed_dob):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Date of Birth. Please provide your registered date of birth.",
        )

    user = student.user
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student account is deactivated.")

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
    Principal / Higher Authority (Tier 3), and Super Admins.
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
    )

