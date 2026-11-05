from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship, backref
from backend.app.database import Base

class ComplaintStatus:
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    ASSIGNED = "assigned"
    UNDER_INVESTIGATION = "under_investigation"
    ACTION_TAKEN = "action_taken"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"

class ComplaintTier:
    TIER_1 = "tier_1" # Department Level
    TIER_2 = "tier_2" # Grievance Redressal Cell
    TIER_3 = "tier_3" # Principal / Higher Authority

class ComplaintPriority:
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class ComplaintCategory:
    INFRASTRUCTURE = "Infrastructure and Facilities"
    HOSTEL = "Hostel Issues"
    TRANSPORTATION = "Transportation"
    ACADEMIC = "Academic Issues"
    EXAMINATION = "Examination and Results"
    FACULTY = "Faculty-related Grievances"
    SCHOLARSHIPS = "Scholarships and Financial Aid"
    FEES = "Fees and Administration"
    LIBRARY = "Library"
    LAB = "Laboratory Equipment"
    SAFETY = "Campus Safety"
    HARASSMENT = "Harassment and Misconduct"
    OTHER = "Other"

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    grievance_id = Column(String(50), unique=True, index=True, nullable=False) # e.g. NIE-2026-0001
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    complainant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_anonymous = Column(Boolean, default=False)
    location_name = Column(String(200), nullable=True) # e.g. "Main Mechanical Workshop Room 102"
    
    # Workflow & Lifecycle
    status = Column(String(50), default=ComplaintStatus.SUBMITTED, index=True)
    current_tier = Column(String(50), default=ComplaintTier.TIER_1, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # ML Priority Prediction & Safety Override
    predicted_priority = Column(String(50), default=ComplaintPriority.MEDIUM)
    final_priority = Column(String(50), default=ComplaintPriority.MEDIUM, index=True)
    priority_override_reason = Column(Text, nullable=True)
    priority_confidence = Column(Float, default=0.0)
    priority_explanation = Column(Text, nullable=True) # Top keywords / reasons
    is_safety_critical = Column(Boolean, default=False)
    
    # Duplicate Detection & Merging
    is_duplicate = Column(Boolean, default=False)
    master_complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    duplicate_similarity_score = Column(Float, default=0.0)
    duplicate_flag_reason = Column(Text, nullable=True)
    affected_students_count = Column(Integer, default=1)
    
    # Dates & Escalation Tracking
    submission_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_deadline = Column(DateTime, nullable=True)
    tier1_entered_at = Column(DateTime, default=datetime.utcnow)
    tier2_entered_at = Column(DateTime, nullable=True)
    tier3_entered_at = Column(DateTime, nullable=True)
    is_escalation_paused = Column(Boolean, default=False)
    escalation_pause_reason = Column(Text, nullable=True)
    
    # Resolution & Student Confirmation
    resolution_date = Column(DateTime, nullable=True)
    resolution_remarks = Column(Text, nullable=True)
    resolution_evidence_url = Column(String(500), nullable=True)
    student_confirmed = Column(Boolean, nullable=True) # None=pending, True=satisfied, False=reopened
    student_confirmation_remarks = Column(Text, nullable=True)
    student_confirmed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="complaints")
    complainant = relationship("User", foreign_keys=[complainant_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    evidence_items = relationship("ComplaintEvidence", back_populates="complaint", cascade="all, delete-orphan")
    location_data = relationship("ComplaintLocation", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    timeline_entries = relationship("ComplaintTimeline", back_populates="complaint", order_by="ComplaintTimeline.timestamp.asc()", cascade="all, delete-orphan")
    escalation_logs = relationship("EscalationLog", back_populates="complaint", cascade="all, delete-orphan")
    duplicates = relationship("Complaint", backref=backref("master_complaint", remote_side=[id]))

class ComplaintEvidence(Base):
    __tablename__ = "complaint_evidence"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=True) # image/png, image/jpeg, application/pdf
    file_size_bytes = Column(Integer, default=0)
    
    # Verification
    verification_status = Column(String(50), default="pending_verification", index=True) # pending_verification, verified, rejected, requires_additional_evidence
    officer_remarks = Column(Text, nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    is_confidential = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="evidence_items")
    verified_by = relationship("User", foreign_keys=[verified_by_id])

class ComplaintLocation(Base):
    __tablename__ = "complaint_locations"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), unique=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy_meters = Column(Float, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)
    is_exception_granted = Column(Boolean, default=False)
    exception_reason = Column(String(255), nullable=True)

    complaint = relationship("Complaint", back_populates="location_data")

class ComplaintTimeline(Base):
    __tablename__ = "complaint_timeline"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(100), nullable=False) # e.g. "Complaint Submitted", "Evidence Verified", "Assigned to Officer", "Status Changed to Under Investigation", "Auto-Escalated to Tier 2", "Resolved", "Confirmed by Student"
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remarks = Column(Text, nullable=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="timeline_entries")
    actor = relationship("User", foreign_keys=[actor_id])
