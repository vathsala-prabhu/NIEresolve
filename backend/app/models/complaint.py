from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from backend.app.database import Base, utc_now

class ComplaintStatus:
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    ASSIGNED = "assigned"
    UNDER_INVESTIGATION = "under_investigation"
    ACTION_TAKEN = "action_taken"
    RESOLVED_AWAITING_CONFIRMATION = "resolved_awaiting_confirmation"
    CONFIRMED_RESOLVED = "confirmed_resolved"
    AUTO_CONFIRMED_RESOLVED = "auto_confirmed_resolved"
    RESOLVED = "resolved" # Standard resolved state
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

class ComplaintCampus:
    NORTH_CAMPUS = "North Campus"
    SOUTH_CAMPUS = "South Campus"
    ALL = [NORTH_CAMPUS, SOUTH_CAMPUS]

class ComplaintCategory:
    PLACEMENT = "Placement and Career Services"
    INFRASTRUCTURE = "Infrastructure and Maintenance"
    HOSTEL = "Hostel and Accommodation"
    TRANSPORTATION = "Transportation"
    ACADEMIC = "Academic and Curriculum"
    EXAMINATION = "Examination and Results"
    FACULTY = "Faculty-related Issues"
    LIBRARY = "Library"
    LABORATORY = "Laboratory"
    SCHOLARSHIP = "Scholarship and Financial Aid"
    FEES = "Fees and Administration"
    CAMPUS_SAFETY = "Campus Safety"
    IT_NETWORK = "IT and Network Issues"
    OTHER = "Other"

    # Legacy mappings / aliases
    FACULTY_GRIEVANCES = "Faculty-related Grievances"
    INFRASTRUCTURE_FACILITIES = "Infrastructure and Facilities"
    HOSTEL_ISSUES = "Hostel Issues"
    ACADEMIC_ISSUES = "Academic Issues"
    LAB_EQUIPMENT = "Laboratory Equipment"
    HARASSMENT = "Harassment and Misconduct"

    ALL = [
        PLACEMENT,
        INFRASTRUCTURE,
        HOSTEL,
        TRANSPORTATION,
        ACADEMIC,
        EXAMINATION,
        FACULTY,
        LIBRARY,
        LABORATORY,
        SCHOLARSHIP,
        FEES,
        CAMPUS_SAFETY,
        IT_NETWORK,
        OTHER,
    ]

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
    campus = Column(String(50), nullable=False, default=ComplaintCampus.NORTH_CAMPUS, index=True) # "North Campus" or "South Campus"
    location_name = Column(String(200), nullable=True) # e.g. "MB 01" or "Department Block Room 204"
    
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
    
    # Community Support & Upvoting
    upvote_count = Column(Integer, default=0, index=True) # Number of additional users facing this issue
    is_confidential_evidence = Column(Boolean, default=False) # Restricted to authorized officers only

    # Duplicate Detection & Merging
    is_duplicate = Column(Boolean, default=False)
    master_complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    duplicate_similarity_score = Column(Float, default=0.0)
    duplicate_flag_reason = Column(Text, nullable=True)
    affected_students_count = Column(Integer, default=1)
    
    # Dates & Escalation Tracking
    submission_date = Column(DateTime, default=utc_now, nullable=False)
    expected_deadline = Column(DateTime, nullable=True)
    tier1_entered_at = Column(DateTime, default=utc_now)
    tier2_entered_at = Column(DateTime, nullable=True)
    tier3_entered_at = Column(DateTime, nullable=True)
    is_escalation_paused = Column(Boolean, default=False)
    escalation_pause_reason = Column(Text, nullable=True)
    
    # Resolution & Student Confirmation (5-Day Auto-Confirm Workflow)
    resolved_at = Column(DateTime, nullable=True) # Timestamp when officer marked as resolved
    confirmation_deadline = Column(DateTime, nullable=True) # resolved_at + 5 calendar days
    resolution_date = Column(DateTime, nullable=True)
    resolution_remarks = Column(Text, nullable=True)
    resolution_evidence_url = Column(String(500), nullable=True)
    student_confirmed = Column(Boolean, nullable=True) # None=pending, True=satisfied, False=reopened
    student_confirmation_remarks = Column(Text, nullable=True)
    student_confirmed_at = Column(DateTime, nullable=True)
    is_auto_confirmed = Column(Boolean, default=False) # True if confirmed via 5-day timeout
    reopen_count = Column(Integer, default=0)
    reopen_reason = Column(Text, nullable=True)
    reopened_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    department = relationship("Department", back_populates="complaints")
    complainant = relationship("User", foreign_keys=[complainant_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    evidence_items = relationship("ComplaintEvidence", back_populates="complaint", cascade="all, delete-orphan")
    location_data = relationship("ComplaintLocation", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    timeline_entries = relationship("ComplaintTimeline", back_populates="complaint", order_by="ComplaintTimeline.timestamp.asc()", cascade="all, delete-orphan")
    escalation_logs = relationship("EscalationLog", back_populates="complaint", cascade="all, delete-orphan")
    duplicates = relationship("Complaint", backref=backref("master_complaint", remote_side=[id]))
    votes = relationship("ComplaintVote", back_populates="complaint", cascade="all, delete-orphan")
    internal_messages = relationship("InternalComplaintMessage", back_populates="complaint", cascade="all, delete-orphan", order_by="InternalComplaintMessage.created_at.asc()")

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
    created_at = Column(DateTime, default=utc_now)

    complaint = relationship("Complaint", back_populates="evidence_items")
    verified_by = relationship("User", foreign_keys=[verified_by_id])

class ComplaintLocation(Base):
    __tablename__ = "complaint_locations"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), unique=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy_meters = Column(Float, nullable=True)
    captured_at = Column(DateTime, default=utc_now)
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
    timestamp = Column(DateTime, default=utc_now)

    complaint = relationship("Complaint", back_populates="timeline_entries")
    actor = relationship("User", foreign_keys=[actor_id])

class ComplaintVote(Base):
    """
    Tracks community supporters ("I am facing this issue too").
    Guarantees 1 vote per user per complaint with unique constraint.
    """
    __tablename__ = "complaint_votes"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (UniqueConstraint("complaint_id", "user_id", name="uq_complaint_user_vote"),)

    complaint = relationship("Complaint", back_populates="votes")
    user = relationship("User", foreign_keys=[user_id])

class InternalComplaintMessage(Base):
    """
    Secure internal communication channel strictly between authorized tiers:
    Tier 1 (Dept Officer), Tier 2 (Grievance Cell), Tier 3 (Principal), Super Admin.
    Complainants and other students can NEVER view internal messages.
    """
    __tablename__ = "internal_complaint_messages"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    complaint = relationship("Complaint", back_populates="internal_messages")
    sender = relationship("User", foreign_keys=[sender_id])

class SmsLog(Base):
    """
    Audit log of all SMS notifications dispatched to students and faculty.
    Tracks phone number, template event, status, provider, and error logs.
    """
    __tablename__ = "sms_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient_phone = Column(String(20), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    message = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=False, index=True) # "complaint_registered", "complaint_resolved", "complaint_escalated", "complaint_reopened"
    provider = Column(String(50), default="test_logger") # "twilio", "msg91", "test_logger"
    status = Column(String(50), default="sent", index=True) # "sent", "delivered", "failed", "logged_test_mode"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    complaint = relationship("Complaint", foreign_keys=[complaint_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
