from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.auth.security import decode_access_token
from backend.app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency to retrieve currently authenticated user from Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session has expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found.",
        )
    return user

def require_roles(allowed_roles: List[str]):
    """Factory dependency to enforce role-based access control."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role in {allowed_roles}, your role is '{current_user.role}'.",
            )
        return current_user
    return role_checker

# Common role guards
require_student = require_roles([UserRole.STUDENT])
require_faculty = require_roles([UserRole.FACULTY])
require_complainant = require_roles([UserRole.STUDENT, UserRole.FACULTY]) # Both can raise complaints
require_dept_officer = require_roles([UserRole.DEPT_OFFICER, UserRole.SUPER_ADMIN])
require_grievance_cell = require_roles([UserRole.GRIEVANCE_CELL, UserRole.SUPER_ADMIN])
require_principal = require_roles([UserRole.PRINCIPAL, UserRole.SUPER_ADMIN])
require_admin = require_roles([UserRole.SUPER_ADMIN])
require_any_officer = require_roles([
    UserRole.DEPT_OFFICER,
    UserRole.GRIEVANCE_CELL,
    UserRole.PRINCIPAL,
    UserRole.SUPER_ADMIN,
])

