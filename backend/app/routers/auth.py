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
    UnifiedLoginRequest,
    UserRegisterRequest,
    UserRegisterResponse,
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

@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Public registration endpoint for new students, faculty, or institutional members.
    Validates user credentials, checks for duplicates, hashes password securely,
    saves record in SQLite database, and returns JWT access token.
    """
    clean_email = payload.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format.")

    # Determine unique username and USN
    clean_username = (payload.username or "").strip().lower()
    clean_usn = (payload.usn or payload.identifier or "").strip().upper()

    assigned_role = (payload.role or "student").strip().lower()
    valid_roles = [
        UserRole.STUDENT,
        UserRole.FACULTY,
        UserRole.DEPT_OFFICER,
        UserRole.GRIEVANCE_CELL,
        UserRole.PRINCIPAL,
        UserRole.SUPER_ADMIN,
        UserRole.SCHOLARSHIP_COORDINATOR,
    ]
    if assigned_role not in valid_roles:
        assigned_role = UserRole.STUDENT

    if not clean_username:
        if assigned_role == UserRole.STUDENT and clean_usn:
            clean_username = clean_usn.lower()
        elif assigned_role == UserRole.FACULTY and payload.identifier:
            clean_username = payload.identifier.strip().lower()
        else:
            clean_username = clean_email.split("@")[0].lower()

    # Password validation
    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )

    # Check duplicate email
    existing_by_email = db.query(User).filter(User.email.ilike(clean_email)).first()
    if existing_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{clean_email}' already exists. Please sign in instead.",
        )

    # Check duplicate username
    existing_by_username = db.query(User).filter(User.username.ilike(clean_username)).first()
    if existing_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with username '{clean_username}' already exists. Please choose a different username.",
        )

    # Department resolution
    dept_id = payload.department_id
    dept_name = (payload.branch or "").strip()
    if dept_id:
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if dept and not dept_name:
            dept_name = dept.name
    elif dept_name:
        dept = db.query(Department).filter(
            (Department.name.ilike(f"%{dept_name}%")) | (Department.code.ilike(f"%{dept_name}%"))
        ).first()
        if dept:
            dept_id = dept.id
            dept_name = dept.name
        else:
            dept_name = "Computer Science & Engineering"
    else:
        dept_name = "Computer Science & Engineering"

    # Check student USN uniqueness
    if assigned_role == UserRole.STUDENT:
        if not clean_usn:
            clean_usn = clean_username.upper()
        existing_student = db.query(StudentProfile).filter(StudentProfile.usn.ilike(clean_usn)).first()
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A student profile with USN '{clean_usn}' already exists. Please sign in or use password setup.",
            )

    # Check faculty ID uniqueness
    if assigned_role == UserRole.FACULTY:
        fac_id = (payload.identifier or clean_username).upper()
        existing_faculty = db.query(FacultyProfile).filter(FacultyProfile.faculty_id.ilike(fac_id)).first()
        if existing_faculty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A faculty profile with ID '{fac_id}' already exists.",
            )

    # Hash password securely
    hashed = hash_password(payload.password)

    # Create User
    new_user = User(
        email=clean_email,
        username=clean_username,
        full_name=payload.full_name.strip(),
        hashed_password=hashed,
        role=assigned_role,
        department_id=dept_id,
        phone=payload.phone.strip() if payload.phone else None,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    # Associated profiles
    identifier_val = clean_username
    if assigned_role == UserRole.STUDENT:
        identifier_val = clean_usn
        clean_dob = normalize_dob(payload.dob) if payload.dob else "2003-01-01"
        branch_final = dept_name or "Computer Science & Engineering"
        parent_phone_val = (payload.parent_phone or payload.phone or "9876543210").strip()
        sp = StudentProfile(
            user_id=new_user.id,
            usn=clean_usn,
            hashed_dob=hash_password(clean_dob),
            dob_raw_display=payload.dob if payload.dob else None,
            course="B.Tech",
            branch=branch_final,
            semester=4,
            year=2,
            section="A",
            cgpa=8.0,
            category="General",
            annual_income=250000.0,
            state_of_domicile="Karnataka",
            student_phone_number=payload.phone.strip() if payload.phone else None,
            parent_phone_number=parent_phone_val,
            parent_name="Parent of " + new_user.full_name,
            parent_relation="Father",
        )
        db.add(sp)
    elif assigned_role == UserRole.FACULTY:
        fac_id = (payload.identifier or clean_username).upper()
        identifier_val = fac_id
        clean_dob = normalize_dob(payload.dob) if payload.dob else "1985-01-01"
        fp = FacultyProfile(
            user_id=new_user.id,
            faculty_id=fac_id,
            hashed_dob=hash_password(clean_dob),
            department_name=dept_name or "Engineering",
            designation="Assistant Professor",
            qualification="Ph.D",
        )
        db.add(fp)

    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "sub": str(new_user.id),
        "role": new_user.role,
        "username": new_user.username,
        "full_name": new_user.full_name,
        "usn": identifier_val if new_user.role == UserRole.STUDENT else None,
    })

    return UserRegisterResponse(
        message="Registration successful! Your account is active.",
        user_id=new_user.id,
        email=new_user.email,
        username=new_user.username,
        full_name=new_user.full_name,
        role=new_user.role,
        identifier=identifier_val,
        access_token=token,
        token_type="bearer",
        department_name=dept_name,
    )

@router.post("/login", response_model=TokenResponse)
def unified_login(payload: UnifiedLoginRequest, db: Session = Depends(get_db)):
    """
    Unified login endpoint accepting email, username, USN, or Faculty ID along with password.
    Routes and authenticates any registered student, faculty, officer, or administrator.
    """
    ident = (payload.username_or_email or payload.username or payload.email or payload.usn or "").strip()
    if not ident:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide an email, username, USN, or Faculty ID.",
        )

    # 1. Direct User lookup by email or username
    user = (
        db.query(User)
        .filter((User.email.ilike(ident)) | (User.username.ilike(ident)))
        .first()
    )

    # 2. If not found, lookup by Student USN
    if not user:
        student = db.query(StudentProfile).filter(StudentProfile.usn.ilike(ident)).first()
        if student and student.user:
            user = student.user

    # 3. If not found, lookup by Faculty ID
    if not user:
        faculty = db.query(FacultyProfile).filter(FacultyProfile.faculty_id.ilike(ident)).first()
        if faculty and faculty.user:
            user = faculty.user

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your identifier and password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact campus administrator.",
        )

    identifier = user.username
    dept_name = user.department.name if user.department else None
    if user.student_profile:
        identifier = user.student_profile.usn
        dept_name = user.student_profile.branch or dept_name
    elif user.faculty_profile:
        identifier = user.faculty_profile.faculty_id
        dept_name = user.faculty_profile.department_name or dept_name

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name,
        "usn": identifier if user.role == UserRole.STUDENT else None,
    })

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        identifier=identifier,
        department_name=dept_name,
    )

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
        alt_user = db.query(User).filter(
            (User.email.ilike(payload.usn.strip())) | (User.username.ilike(payload.usn.strip()))
        ).first()
        if alt_user and alt_user.student_profile and alt_user.student_profile.user:
            student = alt_user.student_profile

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
        student = db.query(StudentProfile).filter(StudentProfile.usn.ilike(ident)).first()
        if student and student.user:
            user = student.user
    if not user:
        faculty = db.query(FacultyProfile).filter(FacultyProfile.faculty_id.ilike(ident)).first()
        if faculty and faculty.user:
            user = faculty.user

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

    identifier = user.username
    if user.student_profile:
        identifier = user.student_profile.usn
    elif user.faculty_profile:
        identifier = user.faculty_profile.faculty_id

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name,
        "usn": identifier if user.role == UserRole.STUDENT else None,
    })

    dept_name = user.department.name if user.department else None
    if user.student_profile and user.student_profile.branch:
        dept_name = user.student_profile.branch
    elif user.faculty_profile and user.faculty_profile.department_name:
        dept_name = user.faculty_profile.department_name

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        identifier=identifier,
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
