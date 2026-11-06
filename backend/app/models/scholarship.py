from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now

class Scholarship(Base):
    __tablename__ = "scholarships"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    provider = Column(String(150), nullable=False) # e.g. "Government of Karnataka", "AICTE", "Central Government"
    description = Column(Text, nullable=False)
    
    # Eligibility Criteria
    eligible_categories = Column(String(255), default="All") # e.g. "SC, ST, OBC, Cat-1" or "All"
    min_cgpa = Column(Float, default=0.0)
    max_family_income = Column(Float, default=500000.0) # In INR per annum
    eligible_courses = Column(String(255), default="B.Tech, M.Tech")
    eligible_branches = Column(String(255), default="All") # "All" or "CSE, ISE, ECE, EEE, MECH, CIVIL"
    eligible_genders = Column(String(50), default="All") # "All", "Female", "Transgender"
    eligible_domiciles = Column(String(100), default="Karnataka") # "Karnataka" or "All-India"
    disability_required = Column(Boolean, default=False)
    
    # Details & Deadlines
    financial_benefits = Column(Text, nullable=False) # e.g. "₹50,000 per annum + tuition fee waiver"
    required_documents = Column(Text, nullable=False) # Income Certificate, Caste Certificate, Marksheets, Fee Receipt
    application_open_date = Column(DateTime, nullable=True)
    application_deadline = Column(DateTime, nullable=False)
    official_url = Column(String(500), nullable=False)
    last_verified_date = Column(DateTime, default=utc_now)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    recommendations = relationship("ScholarshipRecommendation", back_populates="scholarship", cascade="all, delete-orphan")

class ScholarshipRecommendation(Base):
    __tablename__ = "scholarship_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    scholarship_id = Column(Integer, ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="Eligible", index=True) # Eligible, Potentially Eligible, Not Eligible
    match_score = Column(Float, default=100.0) # 0 to 100%
    match_reasons = Column(Text, nullable=True) # JSON or formatted string
    missing_criteria = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("StudentProfile", back_populates="scholarship_recommendations")
    scholarship = relationship("Scholarship", back_populates="recommendations")


class ScholarshipAnnouncement(Base):
    __tablename__ = "scholarship_announcements"

    id = Column(Integer, primary_key=True, index=True)
    scholarship_name = Column(String(200), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    eligibility_criteria = Column(Text, nullable=False)
    application_start_date = Column(DateTime, nullable=True)
    application_deadline = Column(DateTime, nullable=True)
    links_and_documents = Column(Text, nullable=True) # URLs, reference portal links
    
    # Scheduled Event / Verification / Appointment details
    event_date = Column(DateTime, nullable=True)
    event_time_window = Column(String(100), nullable=True) # e.g. "10:30 AM – 1:30 PM"
    event_location = Column(String(200), nullable=True) # e.g. "Scholarship Section, Room 104, Administrative Block"
    required_documents = Column(Text, nullable=True) # Documents students must bring
    responsible_authority = Column(String(150), nullable=True) # e.g. "Dr. Ramesh K, Nodal Officer"
    seal_signature_instructions = Column(Text, nullable=True) # Instructions for seal & signature

    status = Column(String(50), default="published", index=True) # "draft", "published", "withdrawn"
    is_urgent = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    author = relationship("User", foreign_keys=[author_id])


class ScholarshipApplication(Base):
    __tablename__ = "scholarship_applications"

    id = Column(Integer, primary_key=True, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarships.id", ondelete="SET NULL"), nullable=True)
    scholarship_name = Column(String(200), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_number = Column(String(100), unique=True, index=True, nullable=False)
    current_stage = Column(String(100), default="Application Submitted")
    status = Column(String(50), default="in_progress", index=True) # "submitted", "in_progress", "approved", "rejected"
    submitted_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    student = relationship("User", foreign_keys=[student_id])
    stages = relationship("ScholarshipStageSchedule", back_populates="application", cascade="all, delete-orphan", order_by="ScholarshipStageSchedule.stage_order")


class ScholarshipStageSchedule(Base):
    __tablename__ = "scholarship_stage_schedules"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("scholarship_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(String(150), nullable=False)
    stage_order = Column(Integer, default=1)
    status = Column(String(50), default="pending", index=True) # "pending", "in_progress", "completed", "rejected"
    expected_date = Column(DateTime, nullable=True)
    expected_time_window = Column(String(100), nullable=True)
    location_or_office = Column(String(200), nullable=True)
    required_documents = Column(Text, nullable=True)
    responsible_authority = Column(String(150), nullable=True)
    seal_signature_instructions = Column(Text, nullable=True)
    officer_remarks = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    application = relationship("ScholarshipApplication", back_populates="stages")


