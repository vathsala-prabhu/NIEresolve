from typing import Optional
from pydantic import BaseModel, Field

class StudentLoginRequest(BaseModel):
    usn: str = Field(..., description="University Seat Number (e.g. 4NI21CS045)")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD or DD-MM-YYYY format")

class FacultyLoginRequest(BaseModel):
    faculty_id: str = Field(..., description="Faculty Employee ID (e.g. NIE-FAC-102)")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD or DD-MM-YYYY format")

class AdminLoginRequest(BaseModel):
    username_or_email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str
    email: str
    identifier: Optional[str] = None # USN or Faculty ID if applicable
    department_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    identifier: Optional[str] = None # USN or Faculty ID
    
    class Config:
        from_attributes = True

