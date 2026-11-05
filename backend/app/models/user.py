from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, Enum
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now

class UserRole:
    STUDENT = "student"
    FACULTY = "faculty"
    DEPT_OFFICER = "dept_officer"       # Tier 1
    GRIEVANCE_CELL = "grievance_cell"   # Tier 2
    PRINCIPAL = "principal"             # Tier 3 / Higher Authority
    SUPER_ADMIN = "super_admin"

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    grievance_officer_id = Column(Integer, ForeignKey("users.id", name="fk_dept_officer", use_alter=True), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    users = relationship("User", back_populates="department", foreign_keys="User.department_id")
    complaints = relationship("Complaint", back_populates="department")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, index=True)  # UserRole enum value
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    department = relationship("Department", back_populates="users", foreign_keys=[department_id])
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    faculty_profile = relationship("FacultyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    usn = Column(String(20), unique=True, index=True, nullable=False)
    hashed_dob = Column(String(255), nullable=False) # Hashed DOB for secure verification
    dob_raw_display = Column(String(50), nullable=True) # Kept encrypted/internal only if necessary, DOB is not returned in responses
    course = Column(String(50), default="B.Tech")
    branch = Column(String(100), nullable=False) # E.g. Computer Science & Engineering
    semester = Column(Integer, default=6)
    year = Column(Integer, default=3)
    section = Column(String(10), default="A")
    cgpa = Column(Float, default=8.5)
    category = Column(String(50), default="General") # General, OBC, SC, ST, Cat-1, 2A, 2B, 3A, 3B
    annual_income = Column(Float, default=250000.0)
    state_of_domicile = Column(String(100), default="Karnataka")
    disability_status = Column(Boolean, default=False)
    existing_scholarships = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="student_profile")
    scholarship_recommendations = relationship("ScholarshipRecommendation", back_populates="student", cascade="all, delete-orphan")

class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    faculty_id = Column(String(50), unique=True, index=True, nullable=False) # E.g. NIE-FAC-102
    hashed_dob = Column(String(255), nullable=False)
    department_name = Column(String(100), nullable=False)
    designation = Column(String(100), default="Assistant Professor")
    qualification = Column(String(100), default="Ph.D")
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="faculty_profile")

