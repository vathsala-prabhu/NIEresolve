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

class UnifiedLoginRequest(BaseModel):
    username_or_email: Optional[str] = Field(None, description="Email, username, USN, or Faculty ID")
    username: Optional[str] = Field(None, description="Username or email or USN")
    email: Optional[str] = Field(None, description="Email address")
    usn: Optional[str] = Field(None, description="University Seat Number")
    password: str = Field(..., min_length=1, description="Account password")

    model_config = ConfigDict(extra="ignore")

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, description="Full Name of the user")
    email: str = Field(..., min_length=5, max_length=150, description="Email address")
    username: Optional[str] = Field(None, max_length=100, description="Unique username (optional)")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    role: Optional[str] = Field("student", description="Role: student, faculty, etc.")
    usn: Optional[str] = Field(None, description="University Seat Number for student (e.g. 4NI22CS101)")
    department_id: Optional[int] = Field(None, description="Department ID")
    branch: Optional[str] = Field(None, description="Academic Branch / Department")
    phone: Optional[str] = Field(None, description="Contact phone number")
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD or DD-MM-YYYY format")
    parent_phone: Optional[str] = Field(None, description="Parent/Guardian mobile number")
    identifier: Optional[str] = Field(None, description="Identifier alias for USN or Faculty ID")

    model_config = ConfigDict(extra="ignore")

class UserRegisterResponse(BaseModel):
    message: str
    user_id: int
    email: str
    username: str
    full_name: str
    role: str
    identifier: Optional[str] = None
    access_token: Optional[str] = None
    token_type: str = "bearer"
    department_name: Optional[str] = None


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
