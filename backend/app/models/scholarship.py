from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

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
    last_verified_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="scholarship_recommendations")
    scholarship = relationship("Scholarship", back_populates="recommendations")

