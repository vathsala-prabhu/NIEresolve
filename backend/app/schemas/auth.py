from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class StudentLoginRequest(BaseModel):
    usn: str = Field(..., description="University Seat Number (e.g. 4NI21CS045)")
    password: Optional[str] = Field(None, description="Personal password created by student")
    full_name: Optional[str] = Field(None, description="Full Name as registered in institutional records")
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or DD-MM-YYYY format")
    parent_phone_last4: Optional[str] = Field(None, description="Last 4 digits of parent/guardian mobile number")

class StudentPasswordSetupRequest(BaseModel):
    usn: str = Field(..., description="University Seat Number (e.g. 4NI21CS045)")
    full_name: str = Field(..., description="Full Name as registered in institutional records")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD or DD-MM-YYYY format")
    parent_phone_last4: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of parent/guardian mobile number")
    new_password: str = Field(..., min_length=6, description="New secret personal password (min 6 characters)")

class StudentPasswordResetRequest(BaseModel):
    usn: str = Field(..., description="University Seat Number (e.g. 4NI21CS045)")
    full_name: str = Field(..., description="Full Name as registered in institutional records")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD or DD-MM-YYYY format")
    parent_phone_last4: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of parent/guardian mobile number")
    new_password: str = Field(..., min_length=6, description="New secret personal password (min 6 characters)")

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
    can_publish_scholarships: bool = False
    
    model_config = ConfigDict(from_attributes=True)
