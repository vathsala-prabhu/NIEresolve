import os
import sys
from datetime import datetime, timedelta

# Ensure repo root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, Base, engine, utc_now
from backend.app.models.user import User, UserRole, Department, StudentProfile, FacultyProfile
from backend.app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTier,
    ComplaintPriority,
    ComplaintCategory,
    ComplaintEvidence,
    ComplaintLocation,
    ComplaintTimeline,
)
from backend.app.models.escalation import EscalationConfig, EscalationLog
from backend.app.models.scholarship import Scholarship, ScholarshipRecommendation
from backend.app.models.chatbot import KnowledgeBaseItem, KnowledgeBaseCategory
from backend.app.models.notification import Notification, NotificationType
from backend.app.auth.security import hash_password

def seed_database():
    """Initializes schema and populates realistic institutional seed data for NIE Mysuru."""
    print("[Seed] Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("[Seed] Database already contains records. Skipping seed.")
            return

        print("[Seed] Seeding departments...")
        departments_data = [
            {"code": "CSE", "name": "Computer Science & Engineering", "description": "Department of CSE, Administrative & Academic Blocks"},
            {"code": "ISE", "name": "Information Science & Engineering", "description": "Department of ISE, Sir M.V. Block"},
            {"code": "ECE", "name": "Electronics & Communication Engineering", "description": "Department of ECE, Golden Jubilee Block"},
            {"code": "EEE", "name": "Electrical & Electronics Engineering", "description": "Department of EEE, Heritage North Block"},
            {"code": "MECH", "name": "Mechanical Engineering", "description": "Department of Mechanical Engineering, Workshop & South Block"},
            {"code": "CIVIL", "name": "Civil Engineering", "description": "Department of Civil Engineering & Structural Labs"},
            {"code": "HOSTEL", "name": "Hostel & Residential Administration", "description": "Cauvery Boys Hostel, Sharavathi & Kapila Girls Hostels"},
            {"code": "ESTATE", "name": "Estate & Campus Infrastructure", "description": "Campus Maintenance, Power Substations & Water Works"},
            {"code": "EXAM", "name": "Autonomous Examination Section", "description": "Controller of Examinations (CoE) Office & Valuation Center"},
        ]
        dept_objs = {}
        for d in departments_data:
            dept = Department(code=d["code"], name=d["name"], description=d["description"])
            db.add(dept)
            db.flush()
            dept_objs[d["code"]] = dept

        print("[Seed] Seeding users with secure credentials...")
        # 1. Super Admin
        admin_user = User(
            email="admin@nie.ac.in",
            username="admin",
            full_name="System Administrator",
            hashed_password=hash_password("Admin@123"),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(admin_user)

        # 2. Principal / Tier 3 Authority
        principal_user = User(
            email="principal@nie.ac.in",
            username="principal",
            full_name="Dr. Rohini Nagapadma",
            hashed_password=hash_password("Principal@123"),
            role=UserRole.PRINCIPAL,
            is_active=True,
        )
        db.add(principal_user)

        # 3. Institutional Grievance Cell Head / Tier 2
        grievance_cell_user = User(
            email="grievancecell@nie.ac.in",
            username="grievancecell",
            full_name="Dr. K. S. Venkatesh",
            hashed_password=hash_password("Grievance@123"),
            role=UserRole.GRIEVANCE_CELL,
            is_active=True,
        )
        db.add(grievance_cell_user)

        # 4. Department Officer / Tier 1 (CSE)
        officer_cse = User(
            email="officer.cse@nie.ac.in",
            username="officer_cse",
            full_name="Prof. Sudhir Rao",
            hashed_password=hash_password("Officer@123"),
            role=UserRole.DEPT_OFFICER,
            department_id=dept_objs["CSE"].id,
            is_active=True,
        )
        db.add(officer_cse)
        db.flush()
        dept_objs["CSE"].grievance_officer_id = officer_cse.id

        # 5. Department Officer / Tier 1 (MECH)
        officer_mech = User(
            email="officer.mech@nie.ac.in",
            username="officer_mech",
            full_name="Dr. H. N. Suresh",
            hashed_password=hash_password("Officer@123"),
            role=UserRole.DEPT_OFFICER,
            department_id=dept_objs["MECH"].id,
            is_active=True,
        )
        db.add(officer_mech)
        db.flush()
        dept_objs["MECH"].grievance_officer_id = officer_mech.id

        # 6. Student Demo Account
        student_user = User(
            email="4ni21cs045@nie.ac.in",
            username="4NI21CS045",
            full_name="Ananya Sharma",
            hashed_password=hash_password("2003-05-15"),
            role=UserRole.STUDENT,
            department_id=dept_objs["CSE"].id,
            is_active=True,
        )
        db.add(student_user)
        db.flush()

        student_profile = StudentProfile(
            user_id=student_user.id,
            usn="4NI21CS045",
            hashed_dob=hash_password("2003-05-15"),
            dob_raw_display="2003-05-15",
            course="B.Tech",
            branch="Computer Science & Engineering",
            semester=6,
            year=3,
            section="B",
            cgpa=8.75,
            category="OBC",
            annual_income=220000.0,
            state_of_domicile="Karnataka",
            disability_status=False,
            existing_scholarships="None",
        )
        db.add(student_profile)

        # 7. Second Student (for duplicate complaint testing)
        student_user2 = User(
            email="4ni21cs088@nie.ac.in",
            username="4NI21CS088",
            full_name="Rahul Verma",
            hashed_password=hash_password("2003-11-22"),
            role=UserRole.STUDENT,
            department_id=dept_objs["CSE"].id,
            is_active=True,
        )
        db.add(student_user2)
        db.flush()

        student_profile2 = StudentProfile(
            user_id=student_user2.id,
            usn="4NI21CS088",
            hashed_dob=hash_password("2003-11-22"),
            dob_raw_display="2003-11-22",
            course="B.Tech",
            branch="Computer Science & Engineering",
            semester=6,
            year=3,
            section="B",
            cgpa=7.80,
            category="General",
            annual_income=450000.0,
            state_of_domicile="Karnataka",
            disability_status=False,
        )
        db.add(student_profile2)

        # 8. Faculty Demo Account
        faculty_user = User(
            email="fac102@nie.ac.in",
            username="NIE-FAC-102",
            full_name="Dr. Ramesh Kumar",
            hashed_password=hash_password("1985-08-20"),
            role=UserRole.FACULTY,
            department_id=dept_objs["MECH"].id,
            is_active=True,
        )
        db.add(faculty_user)
        db.flush()

        faculty_profile = FacultyProfile(
            user_id=faculty_user.id,
            faculty_id="NIE-FAC-102",
            hashed_dob=hash_password("1985-08-20"),
            department_name="Mechanical Engineering",
            designation="Associate Professor",
            qualification="Ph.D. in Thermal Sciences",
        )
        db.add(faculty_profile)

        print("[Seed] Seeding escalation configuration (15 days)...")
        db.add(EscalationConfig(tier_name=ComplaintTier.TIER_1, duration_days=15, description="Department Level Grievance Resolution"))
        db.add(EscalationConfig(tier_name=ComplaintTier.TIER_2, duration_days=15, description="Institutional Grievance Redressal Cell Review"))

        print("[Seed] Seeding genuine scholarships...")
        scholarships_data = [
            {
                "name": "State Scholarship Portal (SSP) - Post-Matric Scholarship",
                "provider": "Government of Karnataka (Social Welfare / Backward Classes)",
                "description": "Comprehensive fee concession and maintenance allowance for eligible Karnataka domicile students pursuing professional technical courses.",
                "eligible_categories": "SC, ST, OBC, Cat-1, 2A, 2B, 3A, 3B",
                "min_cgpa": 0.0,
                "max_family_income": 250000.0,
                "eligible_courses": "B.Tech, M.Tech, MCA",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "Karnataka",
                "disability_required": False,
                "financial_benefits": "Full tuition fee reimbursement + ₹1,000 monthly maintenance stipend",
                "required_documents": "Caste & Income Certificate (RD Number), SSLC Marksheet, College Admission Receipt, Aadhaar linked Bank Passbook",
                "application_deadline": utc_now() + timedelta(days=25),
                "official_url": "https://ssp.postmatric.karnataka.gov.in",
            },
            {
                "name": "AICTE Pragati Scholarship Scheme for Girls",
                "provider": "All India Council for Technical Education (AICTE)",
                "description": "Financial assistance to meritorious girl students admitted to AICTE approved technical degree institutions to empower women in STEM.",
                "eligible_categories": "All",
                "min_cgpa": 7.0,
                "max_family_income": 800000.0,
                "eligible_courses": "B.Tech",
                "eligible_branches": "All",
                "eligible_genders": "Female",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "₹50,000 per annum towards college fee, computer equipment, and books",
                "required_documents": "Class 10 & 12 marksheets, Family Income Certificate, AICTE Institute Bonafide Certificate",
                "application_deadline": utc_now() + timedelta(days=40),
                "official_url": "https://scholarships.gov.in",
            },
            {
                "name": "Central Sector Scheme of Scholarship (CSSS)",
                "provider": "Department of Higher Education, Ministry of Education, Govt of India",
                "description": "Scholarships for top percentile students in Class XII board exams pursuing regular university undergraduate engineering programs.",
                "eligible_categories": "All",
                "min_cgpa": 7.5,
                "max_family_income": 450000.0,
                "eligible_courses": "B.Tech",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "₹12,000 per annum for undergraduate years, ₹20,000 per annum at PG level",
                "required_documents": "12th Board Scorecard, Revenue Officer Income Certificate, College Bonafide",
                "application_deadline": utc_now() + timedelta(days=18),
                "official_url": "https://scholarships.gov.in",
            },
            {
                "name": "AICTE Saksham Scholarship Scheme for Specially-Abled Students",
                "provider": "AICTE",
                "description": "Financial grant for specially-abled students with disability not less than 40% pursuing technical degree degrees.",
                "eligible_categories": "All",
                "min_cgpa": 0.0,
                "max_family_income": 800000.0,
                "eligible_courses": "B.Tech",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": True,
                "financial_benefits": "₹50,000 per annum for every year of technical study",
                "required_documents": "Disability Certificate issued by Competent Medical Authority (UDID), Income Certificate",
                "application_deadline": utc_now() + timedelta(days=45),
                "official_url": "https://www.aicte-india.org",
            },
            {
                "name": "Foundation for Academic Excellence and Access (FAEA) Scholarship",
                "provider": "BHEL & TATA Trusts / FAEA India",
                "description": "Grants to socially and economically disadvantaged students with outstanding academic ambition in engineering.",
                "eligible_categories": "SC, ST, BPL",
                "min_cgpa": 8.0,
                "max_family_income": 300000.0,
                "eligible_courses": "B.Tech",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "Full tuition fee, hostel mess allowance, and textbook allowance up to graduation",
                "required_documents": "FAEA Application Form, Marks cards, Recommendation Letter from Head of Department",
                "application_deadline": utc_now() + timedelta(days=60),
                "official_url": "https://www.faeaindia.org",
            },
        ]
        for s in scholarships_data:
            sch = Scholarship(**s, last_verified_date=utc_now(), is_active=True)
            db.add(sch)

        print("[Seed] Seeding institutional knowledge base...")
        kb_data = [
            {
                "category": KnowledgeBaseCategory.POLICY,
                "title": "NIE Institutional Grievance Redressal Policy & Three-Tier Escalation Matrix",
                "content": (
                    "The National Institute of Engineering (NIE), Mysuru operates a strict Three-Tier Redressal Framework:\n"
                    "1. Tier 1 (Department Level): Handled by the designated Department Grievance Officer. Expected action within 15 calendar days.\n"
                    "2. Tier 2 (Institutional Grievance Cell): If unresolved after 15 calendar days at Tier 1, the case is automatically escalated to Tier 2 for committee review.\n"
                    "3. Tier 3 (Principal / Higher Authority): If unresolved after an additional 15 calendar days at Tier 2, the case is escalated to Tier 3 for executive intervention.\n"
                    "Students receive real-time notifications at each tier transition."
                ),
                "keywords": "escalation, tier 1, tier 2, tier 3, 15 days, deadline, policy, grievance cell, principal",
                "source_reference": "NIE Student Governance Charter, Regulation 9.1",
            },
            {
                "category": KnowledgeBaseCategory.FAQ,
                "title": "How to Submit and Track a Grievance in NIEresolve",
                "content": (
                    "To raise a grievance:\n"
                    "1. Log in using your USN and Date of Birth (Students) or Faculty ID and DOB (Faculty).\n"
                    "2. Navigate to 'Submit Complaint'.\n"
                    "3. Fill in title, detailed description, select the accurate category and department.\n"
                    "4. Allow browser GPS access to geotag the location, and upload photo evidence.\n"
                    "5. Once submitted, your grievance receives a unique tracking ID (e.g., NIE-2026-0001) and ML priority assessment.\n"
                    "Track the real-time 6-stage lifecycle directly from your dashboard."
                ),
                "keywords": "how to submit, how to track, grievance id, student login, usn, dob, upload photo, gps",
                "source_reference": "NIEresolve User Manual v2.0",
            },
            {
                "category": KnowledgeBaseCategory.DEPARTMENT,
                "title": "Department Responsibilities and Contact Directory",
                "content": (
                    "- Computer Science & Engineering (CSE): Academic concerns, lab workstations, autonomous curriculum.\n"
                    "- Mechanical Engineering (MECH): Workshop safety, machine tool calibration, departmental labs.\n"
                    "- Hostel Administration: Cauvery Boys Hostel, Kapila & Sharavathi Girls Hostels, mess hygiene, water supply.\n"
                    "- Estate & Campus Infrastructure: Power outages, electrical safety, plumbing, classroom furniture.\n"
                    "- Autonomous Examination Section: Grade card anomalies, hall tickets, re-evaluation, CIE disputes."
                ),
                "keywords": "departments, cse, mechanical, hostel, estate, exam section, who handles, wardens",
                "source_reference": "NIE Academic Directory 2025-26",
            },
            {
                "category": KnowledgeBaseCategory.SCHOLARSHIP,
                "title": "Scholarship Guidelines: SSP, NSP, and AICTE Schemes",
                "content": (
                    "Karnataka domicile students must apply through the State Scholarship Portal (SSP). Essential prerequisites:\n"
                    "1. Caste and Income Certificate with valid RD Number.\n"
                    "2. Aadhaar-seeded NPCI bank account.\n"
                    "3. E-attestation completed by the NIE Institutional Nodal Officer (Room 104, Administrative Block).\n"
                    "Girl students with family income < 8 LPA are strongly advised to apply for the AICTE Pragati scheme."
                ),
                "keywords": "ssp, scholarship, nsp, pragati, eligibility, income certificate, e-attestation, documents",
                "source_reference": "NIE Scholarship Desk Notice 2026",
            },
            {
                "category": KnowledgeBaseCategory.POLICY,
                "title": "Zero Tolerance Campus Safety & Anti-Ragging Directives",
                "content": (
                    "NIE Mysuru enforces strict zero-tolerance towards ragging, harassment, and discrimination.\n"
                    "Grievances categorized under 'Campus Safety' or 'Harassment and Misconduct' bypass normal routing and trigger instant Critical Priority review.\n"
                    "Anti-Ragging Squad 24x7 Helpline: +91 821 2480475 | Email: antiragging@nie.ac.in."
                ),
                "keywords": "ragging, harassment, misconduct, safety, urgent, helpline, anti-ragging squad",
                "source_reference": "Supreme Court Anti-Ragging Guidelines & NIE Code of Conduct",
            },
        ]
        for k in kb_data:
            item = KnowledgeBaseItem(**k, is_active=True)
            db.add(item)

        print("[Seed] Seeding sample complaints with realistic timelines and escalations...")
        now = utc_now()

        # Complaint 1: Active Tier 1 complaint for student (Ananya)
        comp1 = Complaint(
            grievance_id="NIE-2026-0001",
            title="Computer Lab 4 Workstations Overheating and Tripping Circuit",
            description="Workstations 15 through 30 in Computer Lab 4 shut down continuously during data structures practical sessions due to AC compressor failure. Burning smell detected.",
            category=ComplaintCategory.LAB,
            department_id=dept_objs["CSE"].id,
            complainant_id=student_user.id,
            is_anonymous=False,
            location_name="Computer Science Block 2nd Floor, Lab 4",
            status=ComplaintStatus.UNDER_INVESTIGATION,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=ComplaintPriority.HIGH,
            final_priority=ComplaintPriority.HIGH,
            priority_confidence=0.82,
            priority_explanation="ML Classifier: 82% confidence for High priority. Laboratory equipment disruption affecting 30+ students.",
            submission_date=now - timedelta(days=6),
            expected_deadline=now + timedelta(days=9),
            tier1_entered_at=now - timedelta(days=6),
            assigned_to_id=officer_cse.id,
        )
        db.add(comp1)
        db.flush()

        db.add(ComplaintLocation(
            complaint_id=comp1.id,
            latitude=12.2834,
            longitude=76.6412,
            accuracy_meters=8.5,
            captured_at=now - timedelta(days=6),
        ))

        db.add(ComplaintTimeline(
            complaint_id=comp1.id,
            action="Complaint Submitted",
            actor_id=student_user.id,
            remarks="Registered by student via portal.",
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            timestamp=now - timedelta(days=6),
        ))
        db.add(ComplaintTimeline(
            complaint_id=comp1.id,
            action="Evidence Verified",
            actor_id=officer_cse.id,
            remarks="Photographic evidence of tripped circuit breaker confirmed.",
            from_status=ComplaintStatus.SUBMITTED,
            to_status=ComplaintStatus.VERIFIED,
            timestamp=now - timedelta(days=5),
        ))
        db.add(ComplaintTimeline(
            complaint_id=comp1.id,
            action="Status Changed to Under Investigation",
            actor_id=officer_cse.id,
            remarks="Department technician dispatched to inspect server room cooling units.",
            from_status=ComplaintStatus.VERIFIED,
            to_status=ComplaintStatus.UNDER_INVESTIGATION,
            timestamp=now - timedelta(days=3),
        ))

        # Complaint 2: Escalated to Tier 2 (Exceeded 15 days in Tier 1)
        comp2 = Complaint(
            grievance_id="NIE-2026-0002",
            title="Severe Water Pressure Drop in Sharavathi Girls Hostel 3rd Floor",
            description="Water supply to washrooms on the 3rd floor of Sharavathi hostel has been erratic for over three weeks. Students forced to carry water buckets up stairs.",
            category=ComplaintCategory.HOSTEL,
            department_id=dept_objs["HOSTEL"].id,
            complainant_id=student_user.id,
            is_anonymous=False,
            location_name="Sharavathi Girls Hostel, Wing C",
            status=ComplaintStatus.ASSIGNED,
            current_tier=ComplaintTier.TIER_2,
            predicted_priority=ComplaintPriority.HIGH,
            final_priority=ComplaintPriority.HIGH,
            priority_confidence=0.78,
            priority_explanation="ML Classifier: 78% confidence for High priority. Essential residential hostel amenity.",
            submission_date=now - timedelta(days=18),
            expected_deadline=now + timedelta(days=12),
            tier1_entered_at=now - timedelta(days=18),
            tier2_entered_at=now - timedelta(days=3),
        )
        db.add(comp2)
        db.flush()

        db.add(ComplaintLocation(
            complaint_id=comp2.id,
            latitude=12.2851,
            longitude=76.6430,
            accuracy_meters=12.0,
            captured_at=now - timedelta(days=18),
        ))
        db.add(ComplaintTimeline(
            complaint_id=comp2.id,
            action="Complaint Submitted",
            actor_id=student_user.id,
            remarks="Submitted by student.",
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            timestamp=now - timedelta(days=18),
        ))
        db.add(ComplaintTimeline(
            complaint_id=comp2.id,
            action="Auto-Escalated to Tier 2 (Grievance Cell)",
            actor_id=None,
            remarks="Automatic Institutional Escalation: Unresolved after 15 calendar days at Department Level.",
            from_status=ComplaintStatus.SUBMITTED,
            to_status=ComplaintStatus.ASSIGNED,
            timestamp=now - timedelta(days=3),
        ))
        db.add(EscalationLog(
            complaint_id=comp2.id,
            from_tier=ComplaintTier.TIER_1,
            to_tier=ComplaintTier.TIER_2,
            escalation_date=now - timedelta(days=3),
            reason="Unresolved after 15 calendar days at Tier 1 (Hostel Dept).",
            automated=True,
            notified_authorities="Institutional Grievance Redressal Cell",
        ))

        # Complaint 3: Critical Campus Safety Complaint (Demonstrating Instant Critical Override)
        comp3 = Complaint(
            grievance_id="NIE-2026-0003",
            title="Live 440V Electrical Cable Exposed Near Mechanical Block Walkway",
            description="Sparking exposed 440V high voltage wire lying near North Block entrance after heavy rains. Water logging around the junction box posing extreme electrocution hazard.",
            category=ComplaintCategory.SAFETY,
            department_id=dept_objs["ESTATE"].id,
            complainant_id=faculty_user.id,
            is_anonymous=False,
            location_name="North Block Walkway adjacent to Machine Shop",
            status=ComplaintStatus.VERIFIED,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=ComplaintPriority.CRITICAL,
            final_priority=ComplaintPriority.CRITICAL,
            priority_confidence=0.96,
            priority_explanation="Safety-Critical Override: detected high-risk factors (live wire, high voltage, electrocution).",
            is_safety_critical=True,
            submission_date=now - timedelta(days=1),
            expected_deadline=now + timedelta(days=14),
            tier1_entered_at=now - timedelta(days=1),
        )
        db.add(comp3)
        db.flush()

        db.add(ComplaintLocation(
            complaint_id=comp3.id,
            latitude=12.2828,
            longitude=76.6405,
            accuracy_meters=5.0,
            captured_at=now - timedelta(days=1),
        ))
        db.add(ComplaintTimeline(
            complaint_id=comp3.id,
            action="Complaint Submitted",
            actor_id=faculty_user.id,
            remarks="Submitted by Faculty Dr. Ramesh Kumar. Flagged as Critical Campus Hazard.",
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            timestamp=now - timedelta(days=1),
        ))

        # Complaint 4: Potential duplicate complaint submitted by Rahul
        comp4 = Complaint(
            grievance_id="NIE-2026-0004",
            title="Overheating AC and Power Trips in Computer Lab 4",
            description="Computers in 6th sem CSE lab 4 shut down due to AC failure. Lab session disrupted by server overheating.",
            category=ComplaintCategory.LAB,
            department_id=dept_objs["CSE"].id,
            complainant_id=student_user2.id,
            is_anonymous=False,
            location_name="CSE Block Room 208 Lab 4",
            status=ComplaintStatus.SUBMITTED,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=ComplaintPriority.HIGH,
            final_priority=ComplaintPriority.HIGH,
            priority_confidence=0.80,
            priority_explanation="ML Classifier: 80% confidence for High priority.",
            duplicate_similarity_score=0.74,
            duplicate_flag_reason="High similarity (74%) with NIE-2026-0001: 'Computer Lab 4 Workstations Overheating and Tripping Circuit'",
            submission_date=now - timedelta(hours=4),
            expected_deadline=now + timedelta(days=15),
            tier1_entered_at=now - timedelta(hours=4),
        )
        db.add(comp4)
        db.flush()

        db.add(ComplaintTimeline(
            complaint_id=comp4.id,
            action="Complaint Submitted",
            actor_id=student_user2.id,
            remarks="Submitted by student Rahul Verma. Flagged as possible duplicate of NIE-2026-0001.",
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            timestamp=now - timedelta(hours=4),
        ))

        # Seed initial notification for student
        db.add(Notification(
            user_id=student_user.id,
            complaint_id=comp1.id,
            title="Investigation In Progress",
            message="Your grievance NIE-2026-0001 has been assigned to Prof. Sudhir Rao for departmental inspection.",
            notification_type=NotificationType.STATUS_UPDATE,
            created_at=now - timedelta(days=3),
        ))
        db.add(Notification(
            user_id=student_user.id,
            complaint_id=comp2.id,
            title="Grievance Escalated to Tier 2",
            message="Grievance NIE-2026-0002 has been escalated to the Institutional Grievance Redressal Cell.",
            notification_type=NotificationType.ESCALATED,
            created_at=now - timedelta(days=3),
        ))

        db.commit()
        print("[Seed] Successfully seeded realistic NIE Mysuru database!")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

