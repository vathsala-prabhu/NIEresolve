from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ScholarshipAnnouncementCreate(BaseModel):
    scholarship_name: str = Field(..., description="Name of the scholarship, e.g. SSP Post-Matric Karnataka")
    title: str = Field(..., description="Announcement title, e.g. Physical Seal & Verification Schedule")
    description: str = Field(..., description="Detailed announcement body and guidelines")
    eligibility_criteria: str = Field(..., description="Academic, domicile, or income eligibility criteria")
    application_start_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    links_and_documents: Optional[str] = None
    event_date: Optional[datetime] = None
    event_time_window: Optional[str] = Field(None, description="e.g. 10:30 AM – 1:30 PM")
    event_location: Optional[str] = Field(None, description="e.g. Scholarship Section, Room 104, Administrative Block")
    required_documents: Optional[str] = Field(None, description="Documents students must bring")
    responsible_authority: Optional[str] = Field(None, description="Responsible officer/coordinator name")
    seal_signature_instructions: Optional[str] = Field(None, description="Specific seal & signature instructions")
    is_urgent: bool = False
    status: str = Field("published", description="published, draft, or withdrawn")

class ScholarshipAnnouncementUpdate(BaseModel):
    scholarship_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    application_start_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    links_and_documents: Optional[str] = None
    event_date: Optional[datetime] = None
    event_time_window: Optional[str] = None
    event_location: Optional[str] = None
    required_documents: Optional[str] = None
    responsible_authority: Optional[str] = None
    seal_signature_instructions: Optional[str] = None
    is_urgent: Optional[bool] = None
    status: Optional[str] = None

class ScholarshipAnnouncementResponse(BaseModel):
    id: int
    scholarship_name: str
    title: str
    description: str
    eligibility_criteria: str
    application_start_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    links_and_documents: Optional[str] = None
    event_date: Optional[datetime] = None
    event_time_window: Optional[str] = None
    event_location: Optional[str] = None
    required_documents: Optional[str] = None
    responsible_authority: Optional[str] = None
    seal_signature_instructions: Optional[str] = None
    status: str
    is_urgent: bool
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StageScheduleUpdate(BaseModel):
    status: Optional[str] = Field(None, description="pending, in_progress, completed, rejected")
    expected_date: Optional[datetime] = None
    expected_time_window: Optional[str] = None
    location_or_office: Optional[str] = None
    required_documents: Optional[str] = None
    responsible_authority: Optional[str] = None
    seal_signature_instructions: Optional[str] = None
    officer_remarks: Optional[str] = None

class StageScheduleResponse(BaseModel):
    id: int
    stage_name: str
    stage_order: int
    status: str
    expected_date: Optional[datetime] = None
    expected_time_window: Optional[str] = None
    location_or_office: Optional[str] = None
    required_documents: Optional[str] = None
    responsible_authority: Optional[str] = None
    seal_signature_instructions: Optional[str] = None
    officer_remarks: Optional[str] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApplicationProgressResponse(BaseModel):
    id: int
    scholarship_id: Optional[int] = None
    scholarship_name: str
    student_id: int
    application_number: str
    current_stage: str
    status: str
    submitted_at: datetime
    updated_at: datetime
    stages: List[StageScheduleResponse] = []

    model_config = ConfigDict(from_attributes=True)

class CoordinatorPermissionRequest(BaseModel):
    user_id: int
    can_publish_scholarships: bool

class CoordinatorSummaryResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    can_publish_scholarships: bool
    announcements_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class ScholarshipModuleStats(BaseModel):
    total_scholarships: int
    published_announcements: int
    active_applications: int
    upcoming_appointments: int

