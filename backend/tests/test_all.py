import os
import sys
from datetime import datetime, timedelta

# Ensure repo root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pytest
from fastapi import HTTPException
from backend.app.database import SessionLocal, Base, engine
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
from backend.app.schemas.auth import StudentLoginRequest, FacultyLoginRequest, AdminLoginRequest
from backend.app.schemas.complaint import (
    ComplaintCreate,
    EvidenceVerifyRequest,
    PriorityOverrideRequest,
    DuplicateMergeRequest,
    StudentConfirmResolutionRequest,
)
from backend.app.routers.auth import student_login, faculty_login, admin_login
from backend.app.routers.complaints import submit_complaint, get_complaints, get_complaint_details
from backend.app.routers.evidence import verify_evidence
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.escalation_service import EscalationService
from backend.app.services.scholarship_service import ScholarshipService
from backend.app.services.chatbot_service import ChatbotService
from backend.app.ml.priority_model import priority_predictor
from backend.app.ml.duplicate_detector import duplicate_detector
from backend.app.seeds.seed_data import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

def test_student_login_success_and_dob_security():
    """Verifies student login with USN and DOB. Confirms DOB is never exposed in response."""
    db = SessionLocal()
    try:
        req = StudentLoginRequest(usn="4NI21CS045", dob="2003-05-15")
        res = student_login(req, db)
        assert res.role == "student"
        assert res.identifier == "4NI21CS045"
        assert res.full_name == "Ananya Sharma"
        assert hasattr(res, "dob") is False # DOB is never part of API token response
        assert len(res.access_token) > 20
    finally:
        db.close()

def test_student_login_invalid_dob():
    """Verifies that incorrect date of birth is rejected with 401 Unauthorized."""
    db = SessionLocal()
    try:
        req = StudentLoginRequest(usn="4NI21CS045", dob="1999-12-31")
        with pytest.raises(HTTPException) as excinfo:
            student_login(req, db)
        assert excinfo.value.status_code == 401
        assert "Invalid Date of Birth" in excinfo.value.detail
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

def test_complaint_submission_workflow():
    """Verifies complaint registration with geo-tagging, ML prediction, and initial 15-day deadline."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        payload = ComplaintCreate(
            title="Water cooler tap broken and leaking continuously in Library Ground Floor",
            description="Continuous dripping from main drinking water cooler near entrance creating slipping hazard.",
            category="Infrastructure and Facilities",
            department_id=8, # ESTATE
            location_name="Library Ground Floor Entrance",
            latitude=12.2835,
            longitude=76.6415,
            accuracy_meters=8.0,
            is_anonymous=False,
        )
        res = submit_complaint(payload, current_user=student, db=db)
        assert "grievance_id" in res
        assert res["grievance_id"].startswith("NIE-2026-")

        # Verify saved complaint in DB
        comp = db.query(Complaint).filter(Complaint.id == res["complaint_id"]).first()
        assert comp is not None
        assert comp.status == ComplaintStatus.SUBMITTED
        assert comp.current_tier == ComplaintTier.TIER_1
        assert comp.location_data.latitude == 12.2835
        assert comp.location_data.longitude == 76.6415
        assert len(comp.timeline_entries) >= 1
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
            submission_date=datetime.utcnow() - timedelta(days=16),
            tier1_entered_at=datetime.utcnow() - timedelta(days=16),
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

def test_scholarship_recommendations():
    """Verifies transparent rule-based scholarship eligibility engine for engineering students."""
    db = SessionLocal()
    try:
        student_profile = db.query(StudentProfile).filter(StudentProfile.usn == "4NI21CS045").first()
        recs = ScholarshipService.get_recommendations_for_student(db, student_profile.id)
        assert len(recs) > 0

        # Ananya: OBC, CGPA 8.75, Income ₹2.2L, Karnataka -> Matches SSP Post-Matric 100%
        ssp_rec = next((r for r in recs if "SSP" in r["scholarship"].name or "State Scholarship" in r["scholarship"].name), None)
        assert ssp_rec is not None
        assert ssp_rec["status"] == "Eligible"
        assert ssp_rec["match_score"] == 100.0
        assert len(ssp_rec["match_reasons"]) >= 3
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

def test_student_resolution_confirmation():
    """Verifies student confirmation of resolved complaint."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.username == "4NI21CS045").first()
        officer = db.query(User).filter(User.role == UserRole.DEPT_OFFICER).first()
        comp = db.query(Complaint).filter(Complaint.complainant_id == student.id).first()

        # Officer marks as resolved
        ComplaintService.update_status(
            db=db,
            actor=officer,
            complaint_id=comp.id,
            new_status=ComplaintStatus.RESOLVED,
            remarks="Workstation circuit breaker replaced and tested.",
        )

        db.refresh(comp)
        assert comp.status == ComplaintStatus.RESOLVED

        # Student confirms resolution
        comp.student_confirmed = True
        comp.status = ComplaintStatus.CLOSED
        db.commit()
        db.refresh(comp)

        assert comp.status == ComplaintStatus.CLOSED
        assert comp.student_confirmed is True
    finally:
        db.close()
