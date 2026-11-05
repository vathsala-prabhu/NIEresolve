from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class StudentScholarshipProfileCreate(BaseModel):
    course: str = "B.Tech"
    branch: str = Field(..., description="e.g. Computer Science and Engineering")
    semester: int = Field(..., ge=1, le=8)
    year: int = Field(..., ge=1, le=4)
    cgpa: float = Field(..., ge=0.0, le=10.0)
    annual_income: float = Field(..., ge=0.0, description="Annual family income in INR")
    category: str = Field(..., description="General, OBC, SC, ST, Cat-1, 2A, 2B, 3A, 3B")
    state_of_domicile: str = "Karnataka"
    disability_status: bool = False
    existing_scholarships: Optional[str] = None

class ScholarshipResponse(BaseModel):
    id: int
    name: str
    provider: str
    description: str
    eligible_categories: str
    min_cgpa: float
    max_family_income: float
    eligible_courses: str
    eligible_branches: str
    eligible_genders: str
    eligible_domiciles: str
    disability_required: bool
    financial_benefits: str
    required_documents: str
    application_open_date: Optional[datetime] = None
    application_deadline: datetime
    official_url: str
    last_verified_date: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class RecommendationResponse(BaseModel):
    scholarship: ScholarshipResponse
    status: str # "Eligible", "Potentially Eligible", "Not Eligible"
    match_score: float # Percentage
    match_reasons: List[str]
    missing_criteria: List[str]
    deadline_days_left: int

