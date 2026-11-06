from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    category: str
    description: str = Field(..., min_length=10)
    campus: str = Field("North Campus", description="Mandatory: North Campus or South Campus")
    location_name: Optional[str] = Field(None, description="Building, Block, Room No, etc.")
    department_id: Optional[int] = Field(None, description="Optional: specific department ID if known")
    is_confidential_evidence: bool = Field(False, description="Treat evidence as restricted to authorized officers")
    is_anonymous: bool = False # Deprecated: anonymous submission is disabled; strictly False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    exception_reason: Optional[str] = None

class EvidenceResponse(BaseModel):
    id: int
    file_url: str
    file_name: str
    file_type: Optional[str] = None
    file_size_bytes: int
    verification_status: str
    officer_remarks: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_confidential: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TimelineResponse(BaseModel):
    id: int
    action: str
    actor_name: Optional[str] = None
    remarks: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ComplaintLocationResponse(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    captured_at: Optional[datetime] = None
    is_exception_granted: bool = False
    exception_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ComplaintListResponse(BaseModel):
    id: int
    grievance_id: str
    title: str
    category: str
    campus: str = "North Campus"
    issue_type: Optional[str] = None
    issue_icon: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    complainant_name: Optional[str] = None
    complainant_identifier: Optional[str] = None
    complainant_role: Optional[str] = None
    is_anonymous: bool = False
    status: str
    current_tier: str
    predicted_priority: str
    final_priority: str
    is_safety_critical: bool
    is_duplicate: bool
    master_complaint_grievance_id: Optional[str] = None
    affected_students_count: int
    upvote_count: int = 0
    has_upvoted: bool = False
    is_confidential_evidence: bool = False
    submission_date: datetime
    expected_deadline: Optional[datetime] = None
    days_pending: int
    resolved_at: Optional[datetime] = None
    confirmation_deadline: Optional[datetime] = None
    resolution_date: Optional[datetime] = None
    student_confirmed: Optional[bool] = None
    is_auto_confirmed: bool = False
    reopen_count: int = 0
    reopen_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ComplaintDetailResponse(ComplaintListResponse):
    description: str
    location_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    priority_override_reason: Optional[str] = None
    priority_confidence: float = 0.0
    priority_explanation: Optional[str] = None
    duplicate_similarity_score: float = 0.0
    master_complaint_grievance_id: Optional[str] = None
    is_escalation_paused: bool = False
    escalation_pause_reason: Optional[str] = None
    resolution_remarks: Optional[str] = None
    resolution_evidence_url: Optional[str] = None
    student_confirmation_remarks: Optional[str] = None
    evidence_items: List[EvidenceResponse] = []
    location_data: Optional[ComplaintLocationResponse] = None
    timeline_entries: List[TimelineResponse] = []
    duplicates_list: List[ComplaintListResponse] = []

    model_config = ConfigDict(from_attributes=True)

class InternalMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Internal message content between tiers")
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None

class InternalMessageResponse(BaseModel):
    id: int
    complaint_id: int
    sender_id: int
    sender_name: str
    author_name: Optional[str] = None
    sender_role: str
    author_role: Optional[str] = None
    sender_designation: Optional[str] = None
    sender_department: Optional[str] = None
    message: str
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ComplaintCommunityItemResponse(BaseModel):
    id: int
    grievance_id: str
    title: str
    category: str
    campus: str
    location_name: Optional[str] = None
    description: str
    status: str
    final_priority: str
    is_safety_critical: bool
    upvote_count: int
    has_upvoted: bool
    affected_students_count: int
    submission_date: datetime
    days_pending: int

    model_config = ConfigDict(from_attributes=True)

class CategorySummaryResponse(BaseModel):
    category: str
    total_complaints: int
    pending_complaints: int
    resolved_complaints: int
    north_campus_count: int
    south_campus_count: int

class GrievanceGroupResponse(BaseModel):
    group_id: str
    group_name: str
    category: str
    icon: str
    total_count: int
    pending_count: int
    resolved_count: int
    complaints: List[ComplaintListResponse] = []

    model_config = ConfigDict(from_attributes=True)

class EvidenceVerifyRequest(BaseModel):
    evidence_id: int
    status: str = Field(..., description="verified, rejected, or requires_additional_evidence")
    officer_remarks: Optional[str] = None

class PriorityOverrideRequest(BaseModel):
    new_priority: str = Field(..., description="Critical, High, Medium, or Low")
    reason: str = Field(..., min_length=5, description="Mandatory reason for priority change")

class DuplicateCheckRequest(BaseModel):
    title: str
    description: str
    category: str
    department_id: int

class DuplicateMatchItem(BaseModel):
    complaint_id: int
    grievance_id: str
    title: str
    category: str
    similarity_score: float
    status: str
    created_at: datetime

class DuplicateMergeRequest(BaseModel):
    master_complaint_id: int
    duplicate_complaint_id: int
    reason: str

class ComplaintStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="assigned, under_investigation, action_taken, resolved, closed")
    remarks: Optional[str] = None
    assigned_to_id: Optional[int] = None
    resolution_evidence_url: Optional[str] = None

class EscalationPauseRequest(BaseModel):
    paused: bool
    reason: str = Field(..., min_length=5)

class StudentConfirmResolutionRequest(BaseModel):
    confirmed: bool = Field(..., description="True if issue resolved, False to reopen")
    remarks: Optional[str] = None

