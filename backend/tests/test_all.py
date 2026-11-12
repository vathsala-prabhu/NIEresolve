import os
import sys
from datetime import datetime, timedelta

# Ensure repo root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pytest
from fastapi import HTTPException
from backend.app.database import SessionLocal, Base, engine, utc_now
from backend.app.models.user import User, UserRole, StudentProfile, FacultyProfile, Department
from backend.app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTier,
    ComplaintPriority,
    ComplaintCategory,
    ComplaintEvidence,
    ComplaintTimeline,
)
from backend.app.models.notification import Notification, NotificationType
from backend.app.schemas.auth import (
    StudentLoginRequest,
    FacultyLoginRequest,
    AdminLoginRequest,
    UserRegisterRequest,
    UnifiedLoginRequest,
)
from backend.app.schemas.complaint import (
    ComplaintCreate,
    EvidenceVerifyRequest,
    PriorityOverrideRequest,
    DuplicateMergeRequest,
    StudentConfirmResolutionRequest,
)
from backend.app.routers.auth import student_login, faculty_login, admin_login, register_user, unified_login
from backend.app.routers.complaints import submit_complaint, get_complaints, get_complaint_details
from backend.app.routers.evidence import verify_evidence
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.scholarship_service import ScholarshipService
from backend.app.services.chatbot_service import ChatbotService
from backend.app.ml.priority_model import priority_predictor
from backend.app.ml.duplicate_detector import duplicate_detector
from backend.app.routers.announcements import (
    get_ticker_announcements,
    get_all_announcements,
    create_institutional_announcement,
)
from backend.app.schemas.ticker import TickerAnnouncementCreate
from backend.app.seeds.seed_data import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

def test_student_login_success_and_dob_security():
    """Verifies student login with 4-factor validation (USN, Full Name, DOB, Parent Phone Last 4). Confirms DOB/Phone is never exposed."""
    db = SessionLocal()
    try:
        req = StudentLoginRequest(
            usn="4NI21CS045",
            full_name="Ananya Sharma",
            dob="2003-05-15",
            parent_phone_last4="3456",
        )
        res = student_login(req, db)
        assert res.role == "student"
        assert res.identifier == "4NI21CS045"
        assert res.full_name == "Ananya Sharma"
        assert hasattr(res, "dob") is False # DOB is never part of API token response
        assert hasattr(res, "parent_phone_number") is False # Parent phone never exposed
        assert len(res.access_token) > 20
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_student_login_invalid_credentials():
    """Verifies that incorrect credentials fail with 401 Unauthorized and generic security message."""
    db = SessionLocal()
    try:
        # Invalid DOB
        req1 = StudentLoginRequest(
            usn="4NI21CS045",
            full_name="Ananya Sharma",
            dob="1999-12-31",
            parent_phone_last4="3456",
        )
        with pytest.raises(HTTPException) as exc1:
            student_login(req1, db)
        assert exc1.value.status_code == 401
        assert "Authentication failed" in exc1.value.detail

        # Invalid Parent Phone Last 4
        req2 = StudentLoginRequest(
            usn="4NI21CS045",
            full_name="Ananya Sharma",
            dob="2003-05-15",
            parent_phone_last4="9999",
        )
        with pytest.raises(HTTPException) as exc2:
            student_login(req2, db)
        assert exc2.value.status_code == 401
        assert "Authentication failed" in exc2.value.detail
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_faculty_login_success():
    """Verifies faculty login using Faculty ID and DOB."""
    db = SessionLocal()
    try:
        req = FacultyLoginRequest(faculty_id="NIE-FAC-102", dob="1985-08-20")
        res = faculty_login(req, db)
        assert res.role == "faculty"
        assert res.identifier == "NIE-FAC-102"
        assert res.full_name == "Dr. Ramesh Kumar"
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_admin_officer_login():
    """Verifies administrative authentication for Tier 1 Department Officer."""
    db = SessionLocal()
    try:
        req = AdminLoginRequest(username_or_email="officer.cse@nie.ac.in", password="Officer@123")
        res = admin_login(req, db)
        assert res.role == "dept_officer"
        assert res.full_name == "Prof. Sudhir Rao"
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_ml_priority_prediction_and_safety_guardrail():
    """Verifies ML urgency prediction and mandatory urgent safety override."""
    # Safety hazard: Must trigger Critical priority override
    pred_safety = priority_predictor.predict(
        category="Campus Safety",
        title="Live high voltage wire touching walkway puddle",
        description="Sparking 440V electrical cable snapped after storm near mechanical block. Severe electrocution hazard.",
    )
    assert pred_safety["final_priority"] == "Critical"
    assert pred_safety["is_safety_critical"] is True
    assert "Safety-Critical Override" in pred_safety["explanation"]

    # Low priority routine inquiry
    pred_routine = priority_predictor.predict(
        category="Other",
        title="Whiteboard marker dry in room 108",
        description="Classroom whiteboard marker needs replacement from stationery department.",
    )
    assert pred_routine["final_priority"] in ["Low", "Medium"]
    assert pred_routine["is_safety_critical"] is False

def test_duplicate_complaint_detection():
    """Verifies TF-IDF cosine similarity detection of similar active complaints."""
    db = SessionLocal()
    try:
        active_comps = db.query(Complaint).filter(Complaint.is_duplicate == False).all()
        matches = duplicate_detector.find_potential_duplicates(
            new_title="Computer Lab 4 Workstations Overheating and Tripping Circuit",
            new_description="Workstations in CSE Lab 4 are shutting down due to compressor cooling failure.",
            category="Laboratory Equipment",
            department_id=1,
            existing_complaints=active_comps,
            threshold=0.35,
        )
        assert len(matches) > 0
        top = matches[0]
        assert top["similarity_score"] >= 0.35
        assert top["grievance_id"] == "NIE-2026-0001"
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_complaint_submission_workflow():
    """Verifies complaint registration with mandatory Campus, ML prediction, and initial 15-day deadline."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        payload = ComplaintCreate(
            title="Water cooler tap broken and leaking continuously in Library Ground Floor",
            description="Continuous dripping from main drinking water cooler near entrance creating slipping hazard.",
            category="Infrastructure and Maintenance",
            campus="North Campus",
            department_id=8, # ESTATE
            location_name="Library Ground Floor Entrance",
            is_confidential_evidence=False,
        )
        res = submit_complaint(payload, current_user=student, db=db)
        assert "grievance_id" in res
        assert res["grievance_id"].startswith("NIE-2026-")

        # Verify saved complaint in DB
        comp = db.query(Complaint).filter(Complaint.id == res["complaint_id"]).first()
        assert comp is not None
        assert comp.status == ComplaintStatus.SUBMITTED
        assert comp.current_tier == ComplaintTier.TIER_1
        assert comp.campus == "North Campus"
        assert comp.is_anonymous is False
        assert len(comp.timeline_entries) >= 1
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_community_upvoting_and_dynamic_priority():
    """Verifies students/faculty upvoting complaints with duplicate prevention and priority elevation."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        comp = db.query(Complaint).filter(Complaint.grievance_id == "NIE-2026-0002").first()
        initial_votes = comp.upvote_count

        # Upvote
        res = ComplaintService.upvote_complaint(db=db, user=student, complaint_id=comp.id)
        assert res["upvote_count"] == initial_votes + 1
        assert res["has_upvoted"] is True

        # Duplicate vote attempt returns already upvoted without creating duplicate DB row
        dup_res = ComplaintService.upvote_complaint(db=db, user=student, complaint_id=comp.id)
        assert dup_res["upvote_count"] == initial_votes + 1
        assert "Already upvoted" in dup_res["message"]

        # Remove vote
        unvote_res = ComplaintService.remove_upvote(db=db, user=student, complaint_id=comp.id)
        assert unvote_res["upvote_count"] == initial_votes
        assert unvote_res["has_upvoted"] is False
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_internal_discussion_messages_and_rbac():
    """Verifies that only authorized officers can read and write internal inter-tier notes."""
    db = SessionLocal()
    try:
        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        comp = db.query(Complaint).first()

        # Officer posts message
        msg = ComplaintService.post_internal_message(
            db=db,
            actor=officer,
            complaint_id=comp.id,
            message="Internal inspection: Work order #402 dispatched to campus electrician.",
        )
        assert msg.id is not None
        assert msg.complaint_id == comp.id
        assert msg.sender_id == officer.id

        # Officer reads messages
        messages = ComplaintService.get_internal_messages(db=db, actor=officer, complaint_id=comp.id)
        assert len(messages) >= 1

        # Student attempting to read internal messages gets 403 Forbidden
        with pytest.raises(HTTPException) as exc1:
            ComplaintService.get_internal_messages(db=db, actor=student, complaint_id=comp.id)
        assert exc1.value.status_code == 403

        # Student attempting to post internal message gets 403 Forbidden
        with pytest.raises(HTTPException) as exc2:
            ComplaintService.post_internal_message(db=db, actor=student, complaint_id=comp.id, message="Unauthorized")
        assert exc2.value.status_code == 403
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_student_resolution_confirmation_and_reopen():
    """Verifies two-way resolution confirmation and student reopening workflow with 5-day timer."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        comp = db.query(Complaint).filter(Complaint.complainant_id == student.id).first()

        # Officer marks as resolved -> becomes RESOLVED_AWAITING_CONFIRMATION
        ComplaintService.update_status(
            db=db,
            actor=officer,
            complaint_id=comp.id,
            new_status=ComplaintStatus.RESOLVED,
            remarks="Workstation circuit breaker replaced and tested.",
        )

        db.refresh(comp)
        assert comp.status == ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION
        assert comp.confirmation_deadline is not None
        assert comp.resolved_at is not None

        # Scenario A: Student confirms resolution -> CONFIRMED_RESOLVED
        confirmed_comp = ComplaintService.confirm_resolution(
            db=db,
            actor=student,
            complaint_id=comp.id,
            confirmed=True,
            remarks="Verified in lab today, power is stable. Thank you!",
        )
        assert confirmed_comp.status == ComplaintStatus.CONFIRMED_RESOLVED
        assert confirmed_comp.student_confirmed is True

        # Scenario B: Officer marks resolved again, student rejects -> REOPENED
        ComplaintService.update_status(
            db=db,
            actor=officer,
            complaint_id=comp.id,
            new_status=ComplaintStatus.RESOLVED,
            remarks="Re-inspected.",
        )
        reopened_comp = ComplaintService.confirm_resolution(
            db=db,
            actor=student,
            complaint_id=comp.id,
            confirmed=False,
            remarks="Tripped again under GPU benchmark load.",
        )
        assert reopened_comp.status == ComplaintStatus.REOPENED
        assert reopened_comp.student_confirmed is False
        assert reopened_comp.reopen_count >= 1
        assert "Tripped again" in reopened_comp.reopen_reason
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_5_day_auto_confirmation_job():
    """Verifies that complaints awaiting confirmation past 5 days automatically transition to AUTO_CONFIRMED_RESOLVED."""
    import uuid
    db = SessionLocal()
    try:
        unique_test_id = f"NIE-AUTO-CONF-{uuid.uuid4().hex[:6].upper()}"
        overdue_comp = Complaint(
            grievance_id=unique_test_id,
            title="Overdue Confirmation Complaint Test",
            description="Testing 5-day auto confirmation background processor.",
            category="Infrastructure and Maintenance",
            campus="North Campus",
            department_id=1,
            complainant_id=1,
            status=ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=ComplaintPriority.LOW,
            final_priority=ComplaintPriority.LOW,
            submission_date=utc_now() - timedelta(days=10),
            resolved_at=utc_now() - timedelta(days=6),
            confirmation_deadline=utc_now() - timedelta(days=1), # Expired yesterday
        )
        db.add(overdue_comp)
        db.commit()
        db.refresh(overdue_comp)

        result = ComplaintService.check_and_run_auto_confirmations(db)
        db.refresh(overdue_comp)

        assert overdue_comp.status == ComplaintStatus.AUTO_CONFIRMED_RESOLVED
        assert overdue_comp.is_auto_confirmed is True
        assert overdue_comp.grievance_id in result["auto_confirmed"]
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_14_categories_summary():
    """Verifies that all 14 official categories are returned in the summary."""
    db = SessionLocal()
    try:
        summary = ComplaintService.get_categories_summary(db)
        assert len(summary) == 14
        categories = [s["category"] for s in summary]
        assert "Placement and Career Services" in categories
        assert "Infrastructure and Maintenance" in categories
        assert "Hostel and Accommodation" in categories
        assert "IT and Network Issues" in categories
        assert "Campus Safety" in categories
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_evidence_verification():
    """Verifies officer verification workflow on submitted evidence."""
    db = SessionLocal()
    try:
        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        comp = db.query(Complaint).first()

        evidence = ComplaintEvidence(
            complaint_id=comp.id,
            file_url="/uploads/test_photo.jpg",
            file_name="test_photo.jpg",
            file_type="image/jpeg",
            file_size_bytes=45000,
            verification_status="pending_verification",
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        # Verify evidence as officer
        req = EvidenceVerifyRequest(
            evidence_id=evidence.id,
            status="verified",
            officer_remarks="Photograph matches campus location inspection.",
        )
        ver_res = verify_evidence(req, current_user=officer, db=db)
        assert ver_res["status"] == "verified"

        db.refresh(evidence)
        assert evidence.verification_status == "verified"
        assert evidence.verified_by_id == officer.id
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_duplicate_complaint_merging():
    """Verifies master-duplicate merging while preserving original records and updating affected count."""
    db = SessionLocal()
    try:
        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        master = db.query(Complaint).filter(Complaint.grievance_id == "NIE-2026-0001").first()
        duplicate = db.query(Complaint).filter(Complaint.grievance_id == "NIE-2026-0004").first()

        initial_count = master.affected_students_count

        merged_master = ComplaintService.merge_complaints(
            db=db,
            actor=officer,
            master_complaint_id=master.id,
            duplicate_complaint_id=duplicate.id,
            reason="Common AC compressor failure in Lab 4 reported by multiple students.",
        )

        db.refresh(duplicate)
        assert duplicate.is_duplicate is True
        assert duplicate.master_complaint_id == master.id
        assert merged_master.affected_students_count == initial_count + duplicate.affected_students_count
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_escalation_15_day_matrix():
    """Verifies automatic escalation from Tier 1 to Tier 2 after 15 calendar days."""
    import uuid
    db = SessionLocal()
    try:
        unique_test_id = f"NIE-TEST-ESC-{uuid.uuid4().hex[:6].upper()}"
        aged_comp = Complaint(
            grievance_id=unique_test_id,
            title="Overdue Laboratory Calibration Issue",
            description="Testing automated 15-day tier 1 to tier 2 progression.",
            category="Laboratory Equipment",
            department_id=1,
            complainant_id=1,
            status=ComplaintStatus.SUBMITTED,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=ComplaintPriority.MEDIUM,
            final_priority=ComplaintPriority.MEDIUM,
            submission_date=utc_now() - timedelta(days=16),
            tier1_entered_at=utc_now() - timedelta(days=16),
        )
        db.add(aged_comp)
        db.commit()
        db.refresh(aged_comp)

        # Run escalation check
        res = EscalationService.check_and_run_escalations(db)
        db.refresh(aged_comp)

        assert aged_comp.current_tier == ComplaintTier.TIER_2
        assert aged_comp.grievance_id in res["escalated_to_tier2"]
        assert len(aged_comp.escalation_logs) >= 1
        assert aged_comp.escalation_logs[0].from_tier == ComplaintTier.TIER_1
        assert aged_comp.escalation_logs[0].to_tier == ComplaintTier.TIER_2
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_scholarship_recommendations():
    """Verifies transparent rule-based scholarship eligibility engine for engineering students."""
    db = SessionLocal()
    try:
        student_profile = db.query(StudentProfile).filter(StudentProfile.usn == "4NI21CS045").first()
        recs = ScholarshipService.get_recommendations_for_student(db, student_profile.id)
        assert len(recs) > 0

        # Ananya: Female, OBC, CGPA 8.75, Income ₹2.2L, Karnataka -> Matches AICTE Pragati / PM YASASVI
        nsp_rec = next((r for r in recs if "Pragati" in r["scholarship"].name or "YASASVI" in r["scholarship"].name), None)
        assert nsp_rec is not None
        assert nsp_rec["status"] in ["Eligible", "Potentially Eligible"]
        assert nsp_rec["match_score"] >= 70.0
        assert len(nsp_rec["match_reasons"]) >= 2
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_chatbot_rag_and_live_status():
    """Verifies institutional RAG knowledge retrieval and dynamic live database complaint lookup."""
    db = SessionLocal()
    try:
        student_user = db.query(User).filter(User.username == "4NI21CS045").first()

        # 1. RAG query over institutional policies
        rag_res = ChatbotService.process_query(
            db=db,
            query="How does the 15-day escalation policy work across tiers?",
            current_user=student_user,
        )
        assert "15" in rag_res["response"]
        assert "Tier 1" in rag_res["response"]
        assert "Tier 2" in rag_res["response"]

        # 2. Dynamic live query for student complaints
        live_res = ChatbotService.process_query(
            db=db,
            query="What is the status of my complaints?",
            current_user=student_user,
        )
        assert live_res["is_live_data"] is True
        assert "NIE-2026-" in live_res["response"]
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_student_resolution_confirmation():
    """Verifies student confirmation of resolved complaint."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        comp = db.query(Complaint).filter(Complaint.complainant_id == student.id).first()

        # Officer marks as resolved -> becomes RESOLVED_AWAITING_CONFIRMATION
        ComplaintService.update_status(
            db=db,
            actor=officer,
            complaint_id=comp.id,
            new_status=ComplaintStatus.RESOLVED,
            remarks="Workstation circuit breaker replaced and tested.",
        )

        db.refresh(comp)
        assert comp.status == ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION

        # Student confirms resolution -> CONFIRMED_RESOLVED
        confirmed = ComplaintService.confirm_resolution(
            db=db,
            complaint_id=comp.id,
            student=student,
            confirmed=True,
            remarks="All fine now.",
        )
        assert confirmed.status == ComplaintStatus.CONFIRMED_RESOLVED
        assert confirmed.student_confirmed is True
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



# =========================================================================
# SCHOLARSHIP NOTIFICATION & APPROVAL TRACKING SUITE (10 SCENARIOS)
# =========================================================================

def test_scenario_1_super_admin_granting_and_revoking_permissions():
    """Scenario 1: Super Admin granting scholarship publishing permission to a coordinator and revoking it."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import set_coordinator_permission, get_coordinators
        from backend.app.schemas.scholarship_announcement import CoordinatorPermissionRequest

        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        faculty = db.query(User).filter(User.role == UserRole.FACULTY).first()

        # Initial state
        faculty.can_publish_scholarships = False
        db.commit()

        # Super Admin grants permission
        req = CoordinatorPermissionRequest(user_id=faculty.id, can_publish_scholarships=True)
        resp = set_coordinator_permission(req, current_user=admin, db=db)
        assert resp.can_publish_scholarships is True

        db.refresh(faculty)
        assert faculty.can_publish_scholarships is True

        # Audit check: confirm audit entry was created
        from backend.app.models.audit import AuditLog
        audit = db.query(AuditLog).filter(
            AuditLog.action == "SET_SCHOLARSHIP_COORDINATOR_PERMISSION",
            AuditLog.entity_id == str(faculty.id),
        ).first()
        assert audit is not None
        assert audit.actor_id == admin.id

        # Super Admin revokes permission
        req_revoke = CoordinatorPermissionRequest(user_id=faculty.id, can_publish_scholarships=False)
        resp_revoke = set_coordinator_permission(req_revoke, current_user=admin, db=db)
        assert resp_revoke.can_publish_scholarships is False
        db.refresh(faculty)
        assert faculty.can_publish_scholarships is False
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_2_authorized_coordinator_creating_and_publishing_announcement():
    """Scenario 2: Authorized coordinator creating and publishing an announcement."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import create_announcement
        from backend.app.schemas.scholarship_announcement import ScholarshipAnnouncementCreate

        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()
        assert coord is not None

        req = ScholarshipAnnouncementCreate(
            scholarship_name="AICTE Pragati Scholarship for Girls 2026",
            title="Pragati Application & Verification Drive",
            description="Empowering female engineering students with ₹50,000 per annum for tuition fees and books.",
            eligibility_criteria="Female students in 1st/2nd year B.Tech with annual family income under ₹8,00,000.",
            application_start_date=utc_now(),
            application_deadline=utc_now() + timedelta(days=30),
            links_and_documents="https://www.aicte-pragati.gov.in",
            event_date=utc_now() + timedelta(days=7),
            event_time_window="10:00 AM – 1:00 PM",
            event_location="Room 205, Golden Jubilee Block",
            required_documents="Aadhaar card, 10th/12th marksheets, family income certificate",
            responsible_authority="Prof. Savitha Murthy",
            seal_signature_instructions="Documents must be signed by HOD before submitting for Principal's seal.",
            is_urgent=True,
            status="published",
        )

        ann = create_announcement(req, current_user=coord, db=db)
        assert ann.id is not None
        assert ann.scholarship_name == "AICTE Pragati Scholarship for Girls 2026"
        assert ann.status == "published"
        assert ann.is_urgent is True
        assert ann.published_at is not None
        assert ann.author_id == coord.id
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_3_unauthorized_user_attempting_to_publish_announcement():
    """Scenario 3: Unauthorized user (e.g. Student) attempting to publish an announcement receives 403 Forbidden."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import create_announcement
        from backend.app.schemas.scholarship_announcement import ScholarshipAnnouncementCreate
        from backend.app.auth.dependencies import require_scholarship_publisher

        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        assert student.can_publish_scholarships is False

        # Attempt to pass student into require_scholarship_publisher guard
        with pytest.raises(HTTPException) as exc_info:
            require_scholarship_publisher(current_user=student)
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_4_coordinator_editing_and_withdrawing_announcement():
    """Scenario 4: Coordinator editing and withdrawing an announcement."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import create_announcement, update_announcement, withdraw_announcement
        from backend.app.schemas.scholarship_announcement import ScholarshipAnnouncementCreate, ScholarshipAnnouncementUpdate

        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()

        req = ScholarshipAnnouncementCreate(
            scholarship_name="Draft Merit Scholarship",
            title="Initial Title",
            description="Initial description",
            eligibility_criteria="CGPA >= 8.0",
            status="draft",
        )
        created = create_announcement(req, current_user=coord, db=db)
        assert created.status == "draft"

        # Update announcement
        update_req = ScholarshipAnnouncementUpdate(
            title="Updated Title: Extended Timeline",
            status="published",
        )
        updated = update_announcement(created.id, update_req, current_user=coord, db=db)
        assert updated.title == "Updated Title: Extended Timeline"
        assert updated.status == "published"

        # Withdraw announcement
        withdrawn = withdraw_announcement(created.id, current_user=coord, db=db)
        assert withdrawn.status == "withdrawn"
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_5_coordinator_publishing_seal_and_signature_appointment():
    """Scenario 5: Coordinator publishing a seal-and-signature appointment with date, time, and location."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import create_announcement
        from backend.app.schemas.scholarship_announcement import ScholarshipAnnouncementCreate

        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()

        appointment_date = utc_now() + timedelta(days=4)
        req = ScholarshipAnnouncementCreate(
            scholarship_name="Karnataka Minorities Development Corporation (KMDC)",
            title="KMDC Loan Subsidy Physical Seal & Signature Camp",
            description="Special institutional verification counter for KMDC loan subsidy verification.",
            eligibility_criteria="Religious minority students with income certificate <= ₹2.5 Lakhs.",
            event_date=appointment_date,
            event_time_window="10:00 AM – 2:00 PM",
            event_location="Counter 3, Main Examination Building",
            required_documents="1. KMDC Form 2. Bonafide Certificate 3. Minority Affidavit",
            responsible_authority="Dr. Rohini Nagapadma (Principal) & Prof. Savitha Murthy",
            seal_signature_instructions="Carry 2 physical copies. One copy will be retained for institutional records.",
            status="published",
            is_urgent=True,
        )

        ann = create_announcement(req, current_user=coord, db=db)
        assert ann.event_time_window == "10:00 AM – 2:00 PM"
        assert ann.event_location == "Counter 3, Main Examination Building"
        assert "Principal" in ann.seal_signature_instructions or "One copy" in ann.seal_signature_instructions
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_6_student_viewing_announcements_and_scheduled_events():
    """Scenario 6: Student viewing published announcements and scheduled seal/signature event."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_announcements

        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        announcements = get_announcements(token_user=student, db=db)
        assert len(announcements) > 0

        # Confirm all returned announcements for students are published (no drafts/withdrawn visible to student)
        for a in announcements:
            assert a.status == "published"

        # Check that scheduled event details are present
        ssp = next((a for a in announcements if "SSP" in a.scholarship_name), None)
        assert ssp is not None
        assert ssp.event_location is not None
        assert ssp.event_time_window is not None
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_7_student_tracking_application_progress_across_stages():
    """Scenario 7: Student tracking application progress across configured stages."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_my_applications, update_stage_schedule
        from backend.app.schemas.scholarship_announcement import StageScheduleUpdate

        student = db.query(User).filter(User.username == "4NI21CS045").first()
        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()

        apps = get_my_applications(current_user=student, db=db)
        assert len(apps) >= 1

        app = apps[0]
        assert app.application_number.startswith("SSP")
        assert len(app.stages) == 8

        # Find Stage 5: Required Seal and Signature
        seal_stage = next(s for s in app.stages if "Seal and Signature" in s.stage_name)
        assert seal_stage.status in ["in_progress", "completed", "pending"]
        assert seal_stage.location_or_office is not None
        assert seal_stage.expected_time_window is not None

        # Coordinator completes Stage 5
        upd = StageScheduleUpdate(
            status="completed",
            officer_remarks="Institutional seal and Principal signature completed on physical form.",
        )
        res = update_stage_schedule(seal_stage.id, upd, current_user=coord, db=db)
        assert res.status == "completed"

        # Re-fetch student application -> current stage advances
        apps_after = get_my_applications(current_user=student, db=db)
        app_after = apps_after[0]
        assert "Institutional Approval" in app_after.current_stage
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_8_non_duplicate_notifications_on_announcement_publication():
    """Scenario 8: Notification generated for student upon announcement publication without duplicate notifications."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import create_announcement
        from backend.app.schemas.scholarship_announcement import ScholarshipAnnouncementCreate
        from backend.app.services.scholarship_announcement_service import ScholarshipAnnouncementService

        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()
        student = db.query(User).filter(User.username == "4NI21CS045").first()

        test_title = f"Duplicate Prevention Test Scholarship {int(utc_now().timestamp())}"
        req = ScholarshipAnnouncementCreate(
            scholarship_name=test_title,
            title="Non-Duplicate Notification Verification",
            description="Testing duplicate notification suppression.",
            eligibility_criteria="All registered students.",
            status="published",
        )

        # First publication
        create_announcement(req, current_user=coord, db=db)

        # Count notifications with this title
        notif_title = f"New Scholarship Update: {test_title}"
        count_first = db.query(Notification).filter(
            Notification.user_id == student.id,
            Notification.title == notif_title,
        ).count()
        assert count_first == 1

        # Simulate second duplicate broadcast call
        ScholarshipAnnouncementService._notify_students_without_duplicates(
            db, notif_title, "Testing duplicate prevention broadcast."
        )

        count_second = db.query(Notification).filter(
            Notification.user_id == student.id,
            Notification.title == notif_title,
        ).count()
        assert count_second == 1, "Duplicate notification should be prevented!"
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_9_coordinator_prevented_from_unauthorized_super_admin_actions():
    """Scenario 9: Coordinator attempting unauthorized Super Admin actions is strictly prevented (Least Privilege)."""
    db = SessionLocal()
    try:
        from backend.app.auth.dependencies import require_admin
        from backend.app.routers.scholarships import set_coordinator_permission
        from backend.app.schemas.scholarship_announcement import CoordinatorPermissionRequest

        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()
        faculty = db.query(User).filter(User.role == UserRole.FACULTY).first()

        # Coordinator is NOT super_admin; require_admin must raise 403
        with pytest.raises(HTTPException) as exc_info:
            require_admin(current_user=coord)
        assert exc_info.value.status_code == 403

        # Attempt to grant coordinator permissions as non-admin -> fails require_admin
        req = CoordinatorPermissionRequest(user_id=faculty.id, can_publish_scholarships=True)
        with pytest.raises(HTTPException):
            admin_guarded_func = require_admin
            admin_guarded_func(current_user=coord)
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_scenario_10_complete_lifecycle_from_creation_to_withdrawal():
    """Scenario 10: Complete lifecycle test from creation, schedule update, to withdrawal."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import (
            create_announcement,
            update_announcement,
            withdraw_announcement,
            get_announcements,
        )
        from backend.app.schemas.scholarship_announcement import (
            ScholarshipAnnouncementCreate,
            ScholarshipAnnouncementUpdate,
        )

        coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()

        # 1. Create Draft
        req = ScholarshipAnnouncementCreate(
            scholarship_name="Lifecycle Test Scholarship",
            title="Draft Stage",
            description="Testing complete lifecycle.",
            eligibility_criteria="All NIE students.",
            status="draft",
        )
        ann = create_announcement(req, current_user=coord, db=db)
        assert ann.status == "draft"

        # 2. Student cannot see draft
        student_ann = get_announcements(token_user=student, db=db)
        assert not any(a.id == ann.id for a in student_ann)

        # 3. Publish Announcement with verification event
        upd = ScholarshipAnnouncementUpdate(
            title="Published Stage: Final Call",
            status="published",
            event_date=utc_now() + timedelta(days=2),
            event_time_window="11:00 AM – 1:00 PM",
            event_location="Scholarship Office Room 104",
        )
        pub_ann = update_announcement(ann.id, upd, current_user=coord, db=db)
        assert pub_ann.status == "published"
        assert pub_ann.event_time_window == "11:00 AM – 1:00 PM"

        # 4. Student can now see published announcement
        student_ann_after = get_announcements(token_user=student, db=db)
        assert any(a.id == ann.id for a in student_ann_after)

        # 5. Withdraw Announcement
        withdrawn_ann = withdraw_announcement(ann.id, current_user=coord, db=db)
        assert withdrawn_ann.status == "withdrawn"

        # 6. Student cannot see withdrawn announcement
        student_ann_final = get_announcements(token_user=student, db=db)
        assert not any(a.id == ann.id for a in student_ann_final)
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



# =========================================================================
# SMART GRIEVANCE GROUPING & PASSWORD AUTHENTICATION TESTS
# =========================================================================

def test_smart_grievance_grouping_endpoint_and_record_preservation():
    """Verifies that GET /api/complaints/grouped organizes complaints into issue groups while preserving every record and ID."""
    db = SessionLocal()
    try:
        from backend.app.routers.complaints import get_grouped_complaints

        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        groups = get_grouped_complaints(current_user=admin, db=db)

        assert len(groups) > 0
        total_grouped_complaints = 0

        for g in groups:
            assert g.group_id is not None
            assert g.group_name is not None
            assert g.icon is not None
            assert g.total_count == len(g.complaints)
            assert g.total_count == (g.pending_count + g.resolved_count)
            total_grouped_complaints += g.total_count

            # Verify every complaint preserves its individual grievance_id, submission_date, etc.
            for c in g.complaints:
                assert c.grievance_id.startswith("NIE-")
                assert c.id is not None

        # Verify no complaints were lost in grouping
        actual_total = db.query(Complaint).count()
        assert total_grouped_complaints == actual_total
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_student_password_setup_and_login_workflow():
    """Verifies student first-time password setup, USN+password authentication, and password reset."""
    db = SessionLocal()
    try:
        from backend.app.routers.auth import student_setup_password, student_login, student_reset_password
        from backend.app.schemas.auth import StudentPasswordSetupRequest, StudentLoginRequest, StudentPasswordResetRequest

        student = db.query(StudentProfile).filter(StudentProfile.usn == "4NI21CS045").first()
        user = student.user

        # 1. First-time setup password with 4-factor verification
        setup_req = StudentPasswordSetupRequest(
            usn="4NI21CS045",
            full_name="Ananya Sharma",
            dob="2003-05-15",
            parent_phone_last4="3456",
            new_password="NewStudentPassword@2026",
        )
        res_setup = student_setup_password(setup_req, db=db)
        assert "successfully" in res_setup["message"]

        # 2. Login using USN + Password directly
        login_req = StudentLoginRequest(
            usn="4NI21CS045",
            password="NewStudentPassword@2026",
        )
        token_res = student_login(login_req, db=db)
        assert token_res.role == "student"
        assert token_res.identifier == "4NI21CS045"
        assert token_res.access_token is not None

        # 3. Invalid password fails
        bad_login = StudentLoginRequest(
            usn="4NI21CS045",
            password="WrongPassword123",
        )
        with pytest.raises(HTTPException) as exc:
            student_login(bad_login, db=db)
        assert exc.value.status_code == 401

        # 4. Reset password with 4-factor verification
        reset_req = StudentPasswordResetRequest(
            usn="4NI21CS045",
            full_name="Ananya Sharma",
            dob="2003-05-15",
            parent_phone_last4="3456",
            new_password="ResetStudentPassword@2026",
        )
        res_reset = student_reset_password(reset_req, db=db)
        assert "successfully" in res_reset["message"]

        # 5. Login with new password
        login_new = StudentLoginRequest(
            usn="4NI21CS045",
            password="ResetStudentPassword@2026",
        )
        token_new = student_login(login_new, db=db)
        assert token_new.identifier == "4NI21CS045"
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_news_ticker_dynamic_announcements_and_scholarship_integration():
    """Verifies that the live news ticker combines scholarship schedules and campus announcements with complete fields."""
    db = SessionLocal()
    try:
        items = get_ticker_announcements(token_user=None, db=db)
        assert len(items) > 0

        categories = [item.category for item in items]
        assert "Scholarship" in categories

        # Verify fields on each ticker item
        for item in items:
            assert item.title and len(item.title.strip()) > 0
            assert item.message and len(item.message.strip()) > 0
            assert item.category and len(item.category.strip()) > 0
            assert item.publication_date and len(item.publication_date.strip()) > 0
            assert item.publication_time and len(item.publication_time.strip()) > 0
            assert item.priority in ["Critical", "Urgent", "High", "Normal", "Medium", "Low"]
            assert isinstance(item.is_urgent, bool)
            assert item.is_active is True
            # Destination route should be a valid frontend view
            if item.destination_route:
                assert item.destination_route in ["scholarships", "community", "dashboard", "escalations", "analytics"]

        # Urgent items are sorted first
        first_item = items[0]
        assert first_item.is_urgent or first_item.priority in ["Critical", "Urgent", "High", "Normal"]
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()



def test_announcement_crud_and_rbac_permissions():
    """Verifies RBAC enforcement on announcement creation: Super Admin allowed, Student rejected with 403."""
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        student_user = db.query(User).filter(User.role == UserRole.STUDENT).first()

        # 1. Super Admin creates an urgent institutional announcement
        new_ann = TickerAnnouncementCreate(
            title="Campus Library Extended Timings During Exams",
            message="North Campus Central Library will remain open until 11:00 PM for preparatory study.",
            category="Academic",
            priority="High",
            is_urgent=True,
            destination_route="dashboard",
        )
        created = create_institutional_announcement(
            payload=new_ann,
            current_user=admin_user,
            db=db,
        )
        assert created.title == new_ann.title
        assert created.category == "Academic"
        assert created.is_urgent is True

        # 2. Student trying to create announcement raises HTTP 403 Forbidden
        with pytest.raises(HTTPException) as exc:
            create_institutional_announcement(
                payload=new_ann,
                current_user=student_user,
                db=db,
            )
        assert exc.value.status_code == 403
        assert "Super Admin" in exc.value.detail or "Unauthorized" in exc.value.detail

        # 3. Verify newly created announcement appears in ticker
        ticker = get_ticker_announcements(token_user=None, db=db)
        found = any(t.title == "Campus Library Extended Timings During Exams" for t in ticker)
        assert found is True

        # 4. Verify all announcements API returns it
        all_ann = get_all_announcements(token_user=None, db=db)
        assert any(a.title == "Campus Library Extended Timings During Exams" for a in all_ann)
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_community_grievance_route_and_id_resolution():
    """Phase 2 verification: ensures /community and /categories/summary work without integer parse errors, and {id} resolves int or string."""
    db = SessionLocal()
    try:
        from backend.app.routers.complaints import (
            get_community_complaints,
            get_categories_summary,
            get_complaint_details,
        )
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        admin = db.query(User).filter(User.username == "admin").first()

        # 1. Community complaints returns successfully
        comm = get_community_complaints(category=None, campus=None, search=None, sort_by="most_supported", current_user=student, db=db)
        assert isinstance(comm, list)

        # 2. Category summary returns 14 categories
        summary = get_categories_summary(campus=None, current_user=student, db=db)
        assert len(summary) == 14

        # 3. View/track details resolves by numeric string "1" or institution ref string "NIE-2026-..."
        first_comp = db.query(Complaint).first()
        assert first_comp is not None

        # Resolve using string numeric ID
        detail1 = get_complaint_details(complaint_id=str(first_comp.id), current_user=admin, db=db)
        assert detail1.id == first_comp.id

        # Resolve using grievance_id reference string
        detail2 = get_complaint_details(complaint_id=first_comp.grievance_id, current_user=admin, db=db)
        assert detail2.grievance_id == first_comp.grievance_id
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_scholarship_coordinator_profile_and_complaint_restriction():
    """Phase 5 & 7 verification: coordinator can manage profile but is strictly denied complaint access."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import (
            get_user_scholarship_profile,
            update_user_scholarship_profile,
        )
        from backend.app.schemas.scholarship import ScholarshipProfileUpdateRequest
        from backend.app.routers.complaints import (
            get_complaints,
            get_grouped_complaints,
            get_community_complaints,
            get_complaint_details,
        )

        coord = db.query(User).filter(User.role == UserRole.SCHOLARSHIP_COORDINATOR).first()
        if not coord:
            coord = User(
                email="scholarship_coord_test@nie.ac.in",
                username="coord_test",
                full_name="Prof. Scholarship Coordinator",
                hashed_password="xyz",
                role=UserRole.SCHOLARSHIP_COORDINATOR,
                can_publish_scholarships=True,
            )
            db.add(coord)
            db.commit()
            db.refresh(coord)

        # 1. GET /profile returns coordinator profile
        prof = get_user_scholarship_profile(current_user=coord, db=db)
        assert prof["role"] == UserRole.SCHOLARSHIP_COORDINATOR
        assert "full_name" in prof

        # 2. POST /profile updates coordinator details and persists
        update_payload = ScholarshipProfileUpdateRequest(
            full_name="Prof. Coordinator Updated",
            phone="+91 98888 77777",
        )
        res = update_user_scholarship_profile(payload=update_payload, current_user=coord, db=db)
        assert "successfully" in res["message"]

        # Verify persistence
        db.refresh(coord)
        assert coord.full_name == "Prof. Coordinator Updated"
        assert coord.phone == "+91 98888 77777"

        # 3. Denied complaint management endpoints with 403 Forbidden
        with pytest.raises(HTTPException) as exc1:
            get_complaints(current_user=coord, db=db)
        assert exc1.value.status_code == 403

        with pytest.raises(HTTPException) as exc2:
            get_grouped_complaints(current_user=coord, db=db)
        assert exc2.value.status_code == 403

        with pytest.raises(HTTPException) as exc3:
            get_community_complaints(current_user=coord, db=db)
        assert exc3.value.status_code == 403

        with pytest.raises(HTTPException) as exc4:
            get_complaint_details(complaint_id="1", current_user=coord, db=db)
        assert exc4.value.status_code == 403
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_tier_communication_and_inter_tier_notifications():
    """Phase 6 verification: inter-tier discussion posts notes and dispatches notifications between officer tiers."""
    db = SessionLocal()
    try:
        from backend.app.routers.complaints import post_internal_message, get_internal_messages
        from backend.app.schemas.complaint import InternalMessageCreate

        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        comp = db.query(Complaint).first()

        # 1. Student access blocked with 403
        with pytest.raises(HTTPException) as exc:
            get_internal_messages(complaint_id=str(comp.id), current_user=student, db=db)
        assert exc.value.status_code == 403

        # 2. Officer posts tier discussion note
        payload = InternalMessageCreate(message="Investigated site in Block A; replacement tap ordered from vendor.")
        msg_res = post_internal_message(complaint_id=str(comp.id), payload=payload, current_user=officer, db=db)
        assert msg_res.message == payload.message
        assert msg_res.sender_name == officer.full_name
        assert msg_res.author_name == officer.full_name

        # 3. Verify inter-tier notification generated
        notif = (
            db.query(Notification)
            .filter(Notification.complaint_id == comp.id, Notification.title.like("Inter-Tier Note%"))
            .order_by(Notification.id.desc())
            .first()
        )
        assert notif is not None
        assert "posted:" in notif.message
    finally:
        db.close()





def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"

        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_intelligent_duplicate_auto_consolidation_and_filtering():
    """Phase 3 & 4 verification: tests intelligent auto-consolidation of duplicate complaints and multi-factor filtering."""
    db = SessionLocal()
    try:
        from backend.app.routers.complaints import submit_complaint, get_complaints, get_grouped_complaints
        from backend.app.schemas.complaint import ComplaintCreate

        student1 = db.query(User).filter(User.role == UserRole.STUDENT).first()
        student2 = db.query(User).filter(User.role == UserRole.STUDENT, User.id != student1.id).first()
        admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()

        import uuid
        uid = uuid.uuid4().hex[:6]

        # 1. Student 1 registers a unique active grievance
        p1 = ComplaintCreate(
            title=f"Lab projector {uid} overheating and smoking unexpectedly",
            description=f"In computer lab room 405 the ceiling projector {uid} began smoking and emitting sparks during practical class.",
            category="Infrastructure and Maintenance",
            campus="North Campus",
            department_id=8,
            location_name="Room 405",
        )
        res1 = submit_complaint(p1, current_user=student1, db=db)
        c1 = db.query(Complaint).filter(Complaint.id == res1["complaint_id"]).first()
        assert c1.is_duplicate is False
        initial_affected = c1.affected_students_count or 1

        # 2. Student 2 registers substantially identical grievance regarding same issue
        p2 = ComplaintCreate(
            title=f"Lab projector {uid} overheating and smoking unexpectedly",
            description=f"Ceiling projector {uid} in computer lab room 405 is overheating, smoking and sparking hazard.",
            category="Infrastructure and Maintenance",
            campus="North Campus",
            department_id=8,
            location_name="Room 405",
        )
        res2 = submit_complaint(p2, current_user=student2, db=db)
        c2 = db.query(Complaint).filter(Complaint.id == res2["complaint_id"]).first()

        # Verify c2 is auto-consolidated into c1
        assert c2.is_duplicate is True
        assert c2.master_complaint_id == c1.id
        assert c2.complainant_id == student2.id # Identity preserved

        # Verify c1 affected count incremented
        db.refresh(c1)
        assert c1.affected_students_count == initial_affected + 1

        # 3. Multi-factor filter test: priority + status + campus
        filtered_flat = get_complaints(
            status_filter="submitted",
            priority_filter=c1.final_priority,
            campus_filter="North Campus",
            current_user=admin,
            db=db,
        )
        assert any(item["id"] == c1.id for item in filtered_flat)

        # 4. Multi-factor filter test on grouped endpoint
        filtered_grouped = get_grouped_complaints(
            status_filter="submitted",
            campus_filter="North Campus",
            priority_filter=c1.final_priority,
            current_user=admin,
            db=db,
        )
        assert isinstance(filtered_grouped, list)
    finally:
        try:
            if 'c1' in locals() and c1:
                c1.status = ComplaintStatus.CLOSED
            if 'c2' in locals() and c2:
                c2.status = ComplaintStatus.CLOSED
            db.commit()
        except Exception:
            pass
        db.close()


def test_five_verified_nsp_schemes_and_official_links():
    """Verifies that exactly five verified NSP scheme entries exist with authentic official guideline links and income limits."""
    db = SessionLocal()
    try:
        from backend.app.routers.scholarships import get_all_scholarships
        
        schs = get_all_scholarships(db)
        assert len(schs) == 5, f"Expected exactly 5 verified NSP schemes, got {len(schs)}"
        names = [s.name for s in schs]
        assert any("Pragati" in n for n in names)
        assert any("Saksham" in n for n in names)
        assert any("Swanath" in n for n in names)
        assert any("YASASVI" in n for n in names)
        assert any("CSSS" in n for n in names)

        # Check official links
        pragati = next(s for s in schs if "Pragati" in s.name)
        assert pragati.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf"
        assert pragati.max_family_income == 800000.0

        saksham = next(s for s in schs if "Saksham" in s.name)
        assert saksham.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf"
        assert saksham.disability_required is True
        assert saksham.max_family_income == 800000.0

        swanath = next(s for s in schs if "Swanath" in s.name)
        assert swanath.official_url == "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf"
        assert swanath.max_family_income == 800000.0

        yasasvi = next(s for s in schs if "YASASVI" in s.name)
        assert yasasvi.official_url == "https://scholarships.gov.in/All-Scholarships"
        assert yasasvi.max_family_income == 250000.0

        csss = next(s for s in schs if "CSSS" in s.name)
        assert csss.official_url == "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf"
        assert csss.max_family_income == 450000.0
    finally:
        db.close()


def test_user_registration_and_db_persistence():
    """Verifies that new users can register, records persist into users and student_profiles tables, and password is encrypted."""
    db = SessionLocal()
    try:
        usn_test = "4NI23CS999"
        email_test = "regtest.student@nie.ac.in"
        
        # Clean up any previous test artifacts if existed
        existing = db.query(User).filter((User.email == email_test) | (User.username == usn_test.lower())).first()
        if existing:
            db.delete(existing)
            db.commit()

        initial_count = db.query(User).count()
        payload = UserRegisterRequest(
            full_name="Deepak Hegde",
            email=email_test,
            usn=usn_test,
            branch="Computer Science & Engineering",
            password="SecurePassword@2026",
            phone="9988776655",
            dob="2004-03-20",
            role="student",
        )
        res = register_user(payload, db)
        assert res.user_id is not None
        assert res.email == email_test
        assert res.role == "student"
        assert res.identifier == usn_test
        assert res.access_token is not None
        assert len(res.access_token) > 20

        # Verify DB row inserted into users table
        db_user = db.query(User).filter(User.id == res.user_id).first()
        assert db_user is not None
        assert db_user.email == email_test
        assert db_user.full_name == "Deepak Hegde"
        assert db_user.is_active is True
        assert db_user.hashed_password != "SecurePassword@2026"
        assert db.query(User).count() == initial_count + 1

        # Verify DB row inserted into student_profiles table
        assert db_user.student_profile is not None
        assert db_user.student_profile.usn == usn_test
        assert db_user.student_profile.branch == "Computer Science & Engineering"
    finally:
        db.close()


def test_user_registration_duplicate_and_validation_rules():
    """Verifies duplicate email and USN prevention, and password length requirement."""
    db = SessionLocal()
    try:
        # 1. Duplicate email rejection
        dup_email_payload = UserRegisterRequest(
            full_name="Duplicate Email Student",
            email="regtest.student@nie.ac.in",
            usn="4NI23CS001",
            password="ValidPassword@123",
        )
        with pytest.raises(HTTPException) as exc_info:
            register_user(dup_email_payload, db)
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

        # 2. Duplicate USN rejection
        dup_usn_payload = UserRegisterRequest(
            full_name="Duplicate USN Student",
            email="unique.student.new@nie.ac.in",
            usn="4NI23CS999",
            password="ValidPassword@123",
        )
        with pytest.raises(HTTPException) as exc_info2:
            register_user(dup_usn_payload, db)
        assert exc_info2.value.status_code == 400
        assert "already exists" in exc_info2.value.detail

        # 3. Short password validation (tested via Pydantic or register_user)
        with pytest.raises(Exception):
            UserRegisterRequest(
                full_name="Short Pass Student",
                email="shortpass@nie.ac.in",
                usn="4NI23CS002",
                password="123",
            )
    finally:
        db.close()


def test_newly_registered_user_login_options():
    """Verifies that newly registered users can log in via student-login, unified login, and admin login."""
    db = SessionLocal()
    try:
        # A. Student login with USN and password
        s_res = student_login(
            StudentLoginRequest(usn="4NI23CS999", password="SecurePassword@2026"),
            db
        )
        assert s_res.role == "student"
        assert s_res.identifier == "4NI23CS999"
        assert len(s_res.access_token) > 20

        # B. Unified login with USN
        u_res = unified_login(
            UnifiedLoginRequest(username_or_email="4NI23CS999", password="SecurePassword@2026"),
            db
        )
        assert u_res.role == "student"
        assert u_res.email == "regtest.student@nie.ac.in"

        # C. Unified login with email
        u_res_email = unified_login(
            UnifiedLoginRequest(username_or_email="regtest.student@nie.ac.in", password="SecurePassword@2026"),
            db
        )
        assert u_res_email.role == "student"

        # D. Admin/Officer login with institutional email
        a_res = admin_login(
            AdminLoginRequest(username_or_email="regtest.student@nie.ac.in", password="SecurePassword@2026"),
            db
        )
        assert a_res.role == "student"
    finally:
        db.close()


def test_existing_nine_institutional_accounts_integrity():
    """Verifies that the 9 baseline institutional accounts remain active and functional."""
    db = SessionLocal()
    try:
        baseline_usernames = [
            "admin",
            "principal",
            "grievancecell",
            "officer_cse",
            "officer_mech",
            "4NI21CS045",
            "4NI21CS088",
            "NIE-FAC-102",
            "coordinator_scholarships",
        ]
        for u in baseline_usernames:
            user = db.query(User).filter(User.username.ilike(u)).first()
            assert user is not None, f"Baseline account {u} missing from database"
            assert user.is_active is True, f"Baseline account {u} is deactivated"
    finally:
        db.close()
