from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.models.user import User, UserRole, Department, StudentProfile, FacultyProfile
from backend.app.models.audit import AuditLog
from backend.app.models.complaint import ComplaintCategory, SmsLog
from backend.app.auth.dependencies import require_admin
from backend.app.auth.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["Super Admin Operations"])

class UserCreateAdmin(BaseModel):
    email: str
    username: str
    full_name: str
    password: str
    role: str
    department_id: Optional[int] = None
    identifier: Optional[str] = None # USN or Faculty ID
    dob: Optional[str] = None

class DepartmentCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    grievance_officer_id: Optional[int] = None

@router.get("/users")
def list_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Lists all registered institutional users with their role and profiles."""
    users = db.query(User).all()
    out = []
    for u in users:
        ident = None
        if u.student_profile:
            ident = u.student_profile.usn
        elif u.faculty_profile:
            ident = u.faculty_profile.faculty_id
        out.append({
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "department_id": u.department_id,
            "department_name": u.department.name if u.department else None,
            "identifier": ident,
            "is_active": u.is_active,
            "created_at": u.created_at,
        })
    return out

@router.post("/users")
def create_user(payload: UserCreateAdmin, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin provisioning for new students, faculty, or officers."""
    existing = db.query(User).filter((User.email == payload.email) | (User.username == payload.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email or username already exists.")

    h_pass = hash_password(payload.password)
    new_user = User(
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=h_pass,
        role=payload.role,
        department_id=payload.department_id,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    # Create associated profile if applicable
    if payload.role == UserRole.STUDENT and payload.identifier and payload.dob:
        sp = StudentProfile(
            user_id=new_user.id,
            usn=payload.identifier.upper(),
            hashed_dob=hash_password(payload.dob),
            branch="Engineering",
        )
        db.add(sp)
    elif payload.role == UserRole.FACULTY and payload.identifier and payload.dob:
        fp = FacultyProfile(
            user_id=new_user.id,
            faculty_id=payload.identifier.upper(),
            hashed_dob=hash_password(payload.dob),
            department_name="Engineering",
        )
        db.add(fp)

    db.add(AuditLog(
        actor_id=current_user.id,
        action="CREATE_USER",
        entity_type="user",
        entity_id=str(new_user.id),
        details=f"Created user {new_user.username} with role {new_user.role}",
    ))

    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully.", "user_id": new_user.id}

@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    """Lists all academic and institutional departments."""
    depts = db.query(Department).all()
    return [
        {
            "id": d.id,
            "code": d.code,
            "name": d.name,
            "description": d.description,
            "grievance_officer_id": d.grievance_officer_id,
            "grievance_officer_name": (
                db.query(User).filter(User.id == d.grievance_officer_id).first().full_name
                if d.grievance_officer_id
                else "Unassigned"
            ),
        }
        for d in depts
    ]

@router.post("/departments")
def create_department(payload: DepartmentCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin endpoint to create an institutional department."""
    dept = Department(
        code=payload.code.upper(),
        name=payload.name,
        description=payload.description,
        grievance_officer_id=payload.grievance_officer_id,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"message": "Department created.", "department_id": dept.id}

@router.get("/audit-logs")
def get_audit_logs(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Returns system-wide audit activity logs."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return [
        {
            "id": l.id,
            "actor_name": l.actor.full_name if l.actor else "System",
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details,
            "created_at": l.created_at,
        }
        for l in logs
    ]

@router.get("/categories")
def get_categories():
    """Returns official list of 14 institutional grievance categories."""
    return ComplaintCategory.ALL

@router.get("/sms-logs")
def get_sms_logs(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Returns audit history of all outgoing SMS notifications."""
    logs = db.query(SmsLog).order_by(SmsLog.created_at.desc()).limit(100).all()
    return [
        {
            "id": l.id,
            "recipient_phone": l.recipient_phone,
            "complaint_id": l.complaint_id,
            "message": l.message,
            "event_type": l.event_type,
            "provider": l.provider,
            "status": l.status,
            "error_message": l.error_message,
            "created_at": l.created_at,
        }
        for l in logs
    ]

