from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    category: str
    department_id: int
    location_name: Optional[str] = None
    is_anonymous: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    exception_reason: Optional[str] = None # Reason if location could not be provided

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

    class Config:
        from_attributes = True

class TimelineResponse(BaseModel):
    id: int
    action: str
    actor_name: Optional[str] = None
    remarks: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class ComplaintLocationResponse(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    captured_at: Optional[datetime] = None
    is_exception_granted: bool = False
    exception_reason: Optional[str] = None

    class Config:
        from_attributes = True

class ComplaintListResponse(BaseModel):
    id: int
    grievance_id: str
    title: str
    category: str
    department_id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    complainant_name: Optional[str] = None # Masked if anonymous
    complainant_identifier: Optional[str] = None
    complainant_role: Optional[str] = None
    is_anonymous: bool
    status: str
    current_tier: str
    predicted_priority: str
    final_priority: str
    is_safety_critical: bool
    is_duplicate: bool
    affected_students_count: int
    submission_date: datetime
    expected_deadline: Optional[datetime] = None
    days_pending: int
    resolution_date: Optional[datetime] = None
    student_confirmed: Optional[bool] = None

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

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

