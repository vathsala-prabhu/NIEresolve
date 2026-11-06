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
    ComplaintCampus,
    ComplaintCategory,
    ComplaintEvidence,
    ComplaintLocation,
    ComplaintTimeline,
    ComplaintVote,
    InternalComplaintMessage,
)
from backend.app.models.escalation import EscalationConfig, EscalationLog
from backend.app.models.scholarship import (
    Scholarship,
    ScholarshipRecommendation,
    ScholarshipAnnouncement,
    ScholarshipApplication,
    ScholarshipStageSchedule,
)
from backend.app.models.chatbot import KnowledgeBaseItem, KnowledgeBaseCategory
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.announcement import InstitutionalAnnouncement
from backend.app.auth.security import hash_password

def seed_scholarship_module(db: Session):
    """Safely provisions the scholarship coordinator, verified NSP schemes, announcements, and application schedules."""
    now = utc_now()

    # 1. Scholarship Coordinator User
    coord = db.query(User).filter(User.email == "coordinator.scholarships@nie.ac.in").first()
    if not coord:
        print("[Seed] Creating Scholarship Coordinator account...")
        coord = User(
            email="coordinator.scholarships@nie.ac.in",
            username="coordinator_scholarships",
            full_name="Prof. Savitha Murthy",
            hashed_password=hash_password("Scholarship@123"),
            role=UserRole.SCHOLARSHIP_COORDINATOR,
            can_publish_scholarships=True,
            is_active=True,
        )
        db.add(coord)
        db.flush()

    # 1.1 Ensure Exactly the 5 Verified NSP Schemes Exist and Are Active
    verified_schemes = [
        {
            "name": "AICTE Pragati Scholarship Scheme for Girl Students (Technical Degree)",
            "provider": "All India Council for Technical Education (AICTE), Ministry of Education",
            "description": "Dedicated government scheme to provide financial assistance to meritorious girl students admitted to AICTE approved technical degree courses to empower women in STEM. Up to two girl children per family are eligible.",
            "eligible_categories": "All",
            "min_cgpa": 0.0,
            "max_family_income": 800000.0,
            "eligible_courses": "Technical Degree (Undergraduate B.E. / B.Tech)",
            "eligible_branches": "All",
            "eligible_genders": "Female",
            "eligible_domiciles": "All-India",
            "disability_required": False,
            "financial_benefits": "₹50,000 per annum towards college fee, computer equipment, and books (max 2 girls per family)",
            "required_documents": "Class 10 & 12 marksheets, Family Income Certificate, AICTE Institute Bonafide Certificate",
            "application_deadline": now + timedelta(days=60),
            "official_url": "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf",
        },
        {
            "name": "AICTE Saksham Scholarship Scheme for Specially-Abled Students (Technical Degree)",
            "provider": "All India Council for Technical Education (AICTE), Ministry of Education",
            "description": "Financial grant of ₹50,000 per annum to encourage and assist specially-abled students with benchmark disability of not less than 40% pursuing technical degree courses.",
            "eligible_categories": "All",
            "min_cgpa": 0.0,
            "max_family_income": 800000.0,
            "eligible_courses": "Technical Degree (Undergraduate B.E. / B.Tech)",
            "eligible_branches": "All",
            "eligible_genders": "All",
            "eligible_domiciles": "All-India",
            "disability_required": True,
            "financial_benefits": "₹50,000 per annum for every year of technical degree study",
            "required_documents": "Disability Certificate issued by Competent Medical Authority (UDID Card), Family Income Certificate",
            "application_deadline": now + timedelta(days=60),
            "official_url": "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf",
        },
        {
            "name": "AICTE Swanath Scholarship Scheme (Technical Degree)",
            "provider": "All India Council for Technical Education (AICTE), Ministry of Education",
            "description": "Institutional scheme to provide financial support of ₹50,000 per annum to orphaned students, children of parents deceased due to Covid-19, or children of Armed Forces & Central Paramilitary Forces personnel martyred in action.",
            "eligible_categories": "All",
            "min_cgpa": 0.0,
            "max_family_income": 800000.0,
            "eligible_courses": "Technical Degree (Undergraduate B.E. / B.Tech)",
            "eligible_branches": "All",
            "eligible_genders": "All",
            "eligible_domiciles": "All-India",
            "disability_required": False,
            "financial_benefits": "₹50,000 per annum towards tuition fee and educational maintenance",
            "required_documents": "Death Certificate of parents / Martyr Certificate from Competent Authority, Family Income Certificate, Institute Bonafide",
            "application_deadline": now + timedelta(days=60),
            "official_url": "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf",
        },
        {
            "name": "PM YASASVI Central Sector Scheme of Top Class Education in College for OBC, EBC and DNT Students",
            "provider": "Ministry of Social Justice and Empowerment, Govt of India",
            "description": "Central sector scholarship to recognize and promote quality higher education among OBC, EBC, and DNT students studying in notified higher education institutions.",
            "eligible_categories": "OBC, EBC, DNT",
            "min_cgpa": 0.0,
            "max_family_income": 250000.0,
            "eligible_courses": "College / University Undergraduate Degree",
            "eligible_branches": "All",
            "eligible_genders": "All",
            "eligible_domiciles": "All-India",
            "disability_required": False,
            "financial_benefits": "Full tuition fee and non-refundable charges up to prescribed ceiling + living and books allowance",
            "required_documents": "Caste / Category Certificate (OBC/EBC/DNT), Valid Income Certificate from Competent Revenue Authority, Institute Fee Receipt",
            "application_deadline": now + timedelta(days=60),
            "official_url": "https://scholarships.gov.in/All-Scholarships",
        },
        {
            "name": "PM-USP Central Sector Scheme of Scholarship for College and University Students (CSSS)",
            "provider": "Department of Higher Education, Ministry of Education, Govt of India",
            "description": "Merit-cum-means scholarship providing ₹12,000 per annum at undergraduate level to meritorious students scoring above the 80th percentile in Class XII board exams pursuing regular degree courses.",
            "eligible_categories": "All",
            "min_cgpa": 0.0,
            "max_family_income": 450000.0,
            "eligible_courses": "College and University Undergraduate Degree",
            "eligible_branches": "All",
            "eligible_genders": "All",
            "eligible_domiciles": "All-India",
            "disability_required": False,
            "financial_benefits": "₹12,000 per annum for undergraduate years, ₹20,000 per annum at post-graduation level",
            "required_documents": "Class 12 Board Scorecard / Percentile Verification, Revenue Authority Income Certificate, College Bonafide",
            "application_deadline": now + timedelta(days=60),
            "official_url": "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf",
        },
    ]

    verified_names = [s["name"] for s in verified_schemes]
    # Deactivate or remove any old unverified scholarships
    db.query(Scholarship).filter(Scholarship.name.notin_(verified_names)).update({"is_active": False}, synchronize_session=False)

    for s in verified_schemes:
        existing = db.query(Scholarship).filter(Scholarship.name == s["name"]).first()
        if existing:
            for k, v in s.items():
                setattr(existing, k, v)
            existing.is_active = True
            existing.last_verified_date = now
        else:
            db.add(Scholarship(**s, last_verified_date=now, is_active=True))
    db.commit()

    # 2. Scholarship Announcements
    if db.query(ScholarshipAnnouncement).count() == 0:
        print("[Seed] Seeding realistic scholarship announcements & verification schedules...")
        ann1 = ScholarshipAnnouncement(
            scholarship_name="State Scholarship Portal (SSP) Post-Matric Karnataka 2026-27",
            title="Physical Seal & Signature Verification Schedule",
            description="All eligible B.Tech and M.Tech students who have submitted the SSP e-attestation form are requested to attend the physical document verification for the Principal's institutional seal and signature.",
            eligibility_criteria="SC, ST, OBC (Cat-1, 2A, 2B, 3A, 3B), and EWS students domiciled in Karnataka with valid RD certificate numbers.",
            application_start_date=now - timedelta(days=20),
            application_deadline=now + timedelta(days=25),
            links_and_documents="https://ssp.postmatric.karnataka.gov.in\nhttps://nie.ac.in/scholarships/ssp-guide.pdf",
            event_date=now + timedelta(days=6),
            event_time_window="10:30 AM – 1:30 PM",
            event_location="Scholarship Section, Room 104, Administrative Block",
            required_documents="1. SSP Online Application Acknowledgement\n2. College Fee Paid Receipt 2026-27\n3. Original Income & Caste Certificate\n4. Previous Year Marksheets\n5. Student Bank Passbook Copy",
            responsible_authority="Prof. Savitha Murthy (Nodal Scholarship Coordinator)",
            seal_signature_instructions="Ensure department mentor counter-signature is obtained on page 2 before submitting for Principal's seal.",
            is_urgent=True,
            status="published",
            author_id=coord.id,
            published_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        db.add(ann1)

        ann2 = ScholarshipAnnouncement(
            scholarship_name="NIE Alumni Merit-cum-Means Financial Aid 2026",
            title="Merit-cum-Means Applications Open for Academic Year 2026-27",
            description="The NIE Alumni Association invites applications from meritorious engineering students facing financial hardship for direct tuition fee waivers.",
            eligibility_criteria="B.Tech 2nd, 3rd, and 4th year students with CGPA >= 7.50 and family annual income below ₹4,00,000.",
            application_start_date=now - timedelta(days=10),
            application_deadline=now + timedelta(days=15),
            links_and_documents="https://niealumni.org.in/scholarships\nhttps://nie.ac.in/alumni-aid-form.pdf",
            event_date=now + timedelta(days=12),
            event_time_window="2:00 PM – 4:30 PM",
            event_location="Alumni Affairs Office, Golden Jubilee Block",
            required_documents="1. Duly filled Alumni Aid Form\n2. Two Faculty Recommendation Letters\n3. Latest Grade Cards\n4. Parent Income Proof (ITR / Tahsildar Certificate)",
            responsible_authority="Er. H.S. Ganesh (Alumni Liaison Officer)",
            seal_signature_instructions="Requires endorsement from Department Head of Department (HOD).",
            is_urgent=False,
            status="published",
            author_id=coord.id,
            published_at=now - timedelta(days=3),
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        )
        db.add(ann2)
        db.flush()

    # 3. Student Application Progress Tracking
    student_user = db.query(User).filter(User.username == "4NI21CS045").first()
    if student_user and db.query(ScholarshipApplication).filter(ScholarshipApplication.student_id == student_user.id).count() == 0:
        print("[Seed] Seeding student application timeline with configurable stages...")
        ssp_sch = db.query(Scholarship).filter(Scholarship.name.ilike("%SSP%")).first()

        app = ScholarshipApplication(
            scholarship_id=ssp_sch.id if ssp_sch else None,
            scholarship_name="SSP Post-Matric Karnataka 2026-27",
            student_id=student_user.id,
            application_number="SSP-2026-NIE-8842",
            current_stage="Required Seal and Signature",
            status="in_progress",
            submitted_at=now - timedelta(days=18),
            updated_at=now - timedelta(days=1),
        )
        db.add(app)
        db.flush()

        stages_data = [
            (1, "Scholarship Announced", "completed", now - timedelta(days=20), None, None, None, None, None, "Official state notification published.", now - timedelta(days=20)),
            (2, "Application Submitted Online", "completed", now - timedelta(days=18), None, "SSP Portal Online", "SSP Form, Aadhaar, Income Certificate", "Student Self", None, "Application submitted with ref SSP-2026-NIE-8842.", now - timedelta(days=18)),
            (3, "Document Verification by College Officer", "completed", now - timedelta(days=12), "11:00 AM - 1:00 PM", "Room 104, Administrative Block", "College Fee Receipt, Caste Certificate", "Prof. Savitha Murthy", None, "All uploaded certificates verified successfully against State DB.", now - timedelta(days=12)),
            (4, "Scholarship Coordinator Review", "completed", now - timedelta(days=5), None, "Administrative Block", "Academic Transcripts (CGPA 8.75)", "Prof. Savitha Murthy", None, "Verified academic eligibility and fee clearance.", now - timedelta(days=5)),
            (5, "Required Seal and Signature", "in_progress", now + timedelta(days=6), "10:30 AM – 1:30 PM", "Scholarship Section, Room 104, Admin Block", "Original SSP acknowledgement slip & Fee receipt", "Dr. Rohini Nagapadma / Coordinator", "Must obtain faculty mentor signature before bringing to Room 104 for Principal's official seal.", "Scheduled appointment confirmed for seal & signature processing.", None),
            (6, "Institutional Approval & Dispatch", "pending", now + timedelta(days=10), None, "Principal's Office", None, "Dr. Rohini Nagapadma", None, "Awaiting seal and signature completion.", None),
            (7, "Forwarded to State Welfare Department", "pending", now + timedelta(days=15), None, "Social Welfare Department, Mysuru", None, "District Officer", None, "Pending institutional dispatch.", None),
            (8, "Final Approval & Disbursal (DBT)", "pending", now + timedelta(days=30), None, "Direct Benefit Transfer (DBT)", None, "State Treasury", None, "Disbursal directly to Aadhaar-seeded bank account.", None),
        ]

        for order, name, st, exp_d, win, loc, docs, auth, seal_inst, rem, comp_at in stages_data:
            s_sched = ScholarshipStageSchedule(
                application_id=app.id,
                stage_name=name,
                stage_order=order,
                status=st,
                expected_date=exp_d,
                expected_time_window=win,
                location_or_office=loc,
                required_documents=docs,
                responsible_authority=auth,
                seal_signature_instructions=seal_inst,
                officer_remarks=rem,
                completed_at=comp_at,
                updated_at=now,
            )
            db.add(s_sched)

    db.commit()


def seed_institutional_announcements(db: Session):
    """Provisions sample institutional announcements for the live ticker and notice boards."""
    now = utc_now()
    admin = db.query(User).filter(User.email == "superadmin@nie.ac.in").first()
    admin_id = admin.id if admin else None

    sample_notices = [
        {
            "title": "SSP Karnataka e-Attestation & Seal Verification Camp",
            "message": "Physical verification camp begins Monday at Admin Block Rm 102 (10 AM - 4 PM). Bring original caste, income & fee receipts.",
            "category": "Scholarship",
            "priority": "Urgent",
            "is_urgent": True,
            "destination_route": "scholarships",
        },
        {
            "title": "Fast-Track Semester Revaluation & Photocopy Window Open",
            "message": "Odd semester VTU/Autonomous fast-track revaluation applications are accepted through the student portal till Nov 18, 5:00 PM.",
            "category": "Academic",
            "priority": "High",
            "is_urgent": True,
            "destination_route": "dashboard",
        },
        {
            "title": "South Campus High-Voltage Transformer Maintenance",
            "message": "Planned sub-station maintenance on Saturday (6:00 AM - 11:30 AM). Backup generators will supply central server and lab grids.",
            "category": "Infrastructure",
            "priority": "Normal",
            "is_urgent": False,
            "destination_route": "community",
        },
        {
            "title": "Campus Placement Drive 2026: Tier-1 IT & Core Engineering",
            "message": "Eligible 7th sem students must verify their placement portal profiles by Nov 20. Upcoming company visits: Bosch, Cisco & Tech Mahindra.",
            "category": "Career / Placement",
            "priority": "Normal",
            "is_urgent": False,
            "destination_route": "community",
        },
        {
            "title": "NIE Alumni Meritorious Financial Aid Window Extended",
            "message": "Deadline extended to Nov 25. Eligible 2nd, 3rd, and 4th year BE students can submit verified applications to the Scholarship Cell.",
            "category": "Scholarship",
            "priority": "High",
            "is_urgent": False,
            "destination_route": "scholarships",
        },
    ]

    for item in sample_notices:
        existing = db.query(InstitutionalAnnouncement).filter(
            InstitutionalAnnouncement.title == item["title"]
        ).first()
        if not existing:
            db.add(InstitutionalAnnouncement(
                title=item["title"],
                message=item["message"],
                category=item["category"],
                priority=item["priority"],
                is_urgent=item["is_urgent"],
                is_active=True,
                destination_route=item["destination_route"],
                author_id=admin_id,
                published_at=now,
                created_at=now,
                updated_at=now,
            ))
    db.commit()
    print("[Seed] Seeded institutional announcements for news ticker.")


def seed_database():
    """Initializes schema and populates realistic institutional seed data for NIE Mysuru."""
    print("[Seed] Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("[Seed] Database already contains records. Seeding scholarship enhancements and announcements...")
            seed_scholarship_module(db)
            seed_institutional_announcements(db)
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
            phone="9880011223",
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
            parent_phone_number="9845123456",
            parent_name="Suresh Sharma",
            parent_relation="Father",
            student_phone_number="9880011223",
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
            phone="9880044556",
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
            parent_phone_number="9900987654",
            parent_name="Ramesh Verma",
            parent_relation="Father",
            student_phone_number="9880044556",
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
            phone="9844012345",
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

        print("[Seed] Seeding genuine verified NSP scholarships...")
        scholarships_data = [
            {
                "name": "AICTE Pragati Scholarship Scheme for Girl Students (Technical Degree)",
                "provider": "All India Council for Technical Education (AICTE), Ministry of Education",
                "description": "Dedicated government scheme to provide financial assistance to meritorious girl students admitted to AICTE approved technical degree courses to empower women in STEM. Up to two girl children per family are eligible.",
                "eligible_categories": "All",
                "min_cgpa": 0.0,
                "max_family_income": 800000.0,
                "eligible_courses": "Technical Degree (Undergraduate B.E. / B.Tech)",
                "eligible_branches": "All",
                "eligible_genders": "Female",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "₹50,000 per annum towards college fee, computer equipment, and books (max 2 girls per family)",
                "required_documents": "Class 10 & 12 marksheets, Family Income Certificate, AICTE Institute Bonafide Certificate",
                "application_deadline": utc_now() + timedelta(days=60),
                "official_url": "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf",
            },
            {
                "name": "AICTE Saksham Scholarship Scheme for Specially-Abled Students (Technical Degree)",
                "provider": "All India Council for Technical Education (AICTE), Ministry of Education",
                "description": "Financial grant of ₹50,000 per annum to encourage and assist specially-abled students with benchmark disability of not less than 40% pursuing technical degree courses.",
                "eligible_categories": "All",
                "min_cgpa": 0.0,
                "max_family_income": 800000.0,
                "eligible_courses": "Technical Degree (Undergraduate B.E. / B.Tech)",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": True,
                "financial_benefits": "₹50,000 per annum for every year of technical degree study",
                "required_documents": "Disability Certificate issued by Competent Medical Authority (UDID Card), Family Income Certificate",
                "application_deadline": utc_now() + timedelta(days=60),
                "official_url": "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf",
            },
            {
                "name": "AICTE Swanath Scholarship Scheme (Technical Degree)",
                "provider": "All India Council for Technical Education (AICTE), Ministry of Education",
                "description": "Institutional scheme to provide financial support of ₹50,000 per annum to orphaned students, children of parents deceased due to Covid-19, or children of Armed Forces & Central Paramilitary Forces personnel martyred in action.",
                "eligible_categories": "All",
                "min_cgpa": 0.0,
                "max_family_income": 800000.0,
                "eligible_courses": "Technical Degree (Undergraduate B.E. / B.Tech)",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "₹50,000 per annum towards tuition fee and educational maintenance",
                "required_documents": "Death Certificate of parents / Martyr Certificate from Competent Authority, Family Income Certificate, Institute Bonafide",
                "application_deadline": utc_now() + timedelta(days=60),
                "official_url": "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf",
            },
            {
                "name": "PM YASASVI Central Sector Scheme of Top Class Education in College for OBC, EBC and DNT Students",
                "provider": "Ministry of Social Justice and Empowerment, Govt of India",
                "description": "Central sector scholarship to recognize and promote quality higher education among OBC, EBC, and DNT students studying in notified higher education institutions.",
                "eligible_categories": "OBC, EBC, DNT",
                "min_cgpa": 0.0,
                "max_family_income": 250000.0,
                "eligible_courses": "College / University Undergraduate Degree",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "Full tuition fee and non-refundable charges up to prescribed ceiling + living and books allowance",
                "required_documents": "Caste / Category Certificate (OBC/EBC/DNT), Valid Income Certificate from Competent Revenue Authority, Institute Fee Receipt",
                "application_deadline": utc_now() + timedelta(days=60),
                "official_url": "https://scholarships.gov.in/All-Scholarships",
            },
            {
                "name": "PM-USP Central Sector Scheme of Scholarship for College and University Students (CSSS)",
                "provider": "Department of Higher Education, Ministry of Education, Govt of India",
                "description": "Merit-cum-means scholarship providing ₹12,000 per annum at undergraduate level to meritorious students scoring above the 80th percentile in Class XII board exams pursuing regular degree courses.",
                "eligible_categories": "All",
                "min_cgpa": 0.0,
                "max_family_income": 450000.0,
                "eligible_courses": "College and University Undergraduate Degree",
                "eligible_branches": "All",
                "eligible_genders": "All",
                "eligible_domiciles": "All-India",
                "disability_required": False,
                "financial_benefits": "₹12,000 per annum for undergraduate years, ₹20,000 per annum at post-graduation level",
                "required_documents": "Class 12 Board Scorecard / Percentile Verification, Revenue Authority Income Certificate, College Bonafide",
                "application_deadline": utc_now() + timedelta(days=60),
                "official_url": "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf",
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
            category=ComplaintCategory.INFRASTRUCTURE,
            campus=ComplaintCampus.NORTH_CAMPUS,
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
            upvote_count=24,
            affected_students_count=25,
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
            remarks="Registered by student via portal for North Campus.",
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
            campus=ComplaintCampus.SOUTH_CAMPUS,
            department_id=dept_objs["HOSTEL"].id,
            complainant_id=student_user.id,
            is_anonymous=False,
            location_name="Sharavathi Girls Hostel, Wing C Room 304",
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
            upvote_count=35,
            affected_students_count=36,
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
            remarks="Submitted by student for South Campus.",
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

        # Seed Internal Messages between Tiers on comp2
        db.add(InternalComplaintMessage(
            complaint_id=comp2.id,
            sender_id=officer_cse.id,
            message="Plumbing inspection completed. Main overhead tank booster pump bearing damaged. Requisition #EST-440 submitted to estate division.",
            created_at=now - timedelta(days=2),
        ))
        db.add(InternalComplaintMessage(
            complaint_id=comp2.id,
            sender_id=grievance_cell_user.id,
            message="Emergency purchase order fast-tracked with finance committee. Replacement pump installation scheduled for Friday morning.",
            created_at=now - timedelta(days=1),
        ))

        # Complaint 3: Critical Campus Safety Complaint (Demonstrating Instant Critical Override)
        comp3 = Complaint(
            grievance_id="NIE-2026-0003",
            title="Live 440V Electrical Cable Exposed Near Mechanical Block Walkway",
            description="Sparking exposed 440V high voltage wire lying near North Block entrance after heavy rains. Water logging around the junction box posing extreme electrocution hazard.",
            category=ComplaintCategory.CAMPUS_SAFETY,
            campus=ComplaintCampus.NORTH_CAMPUS,
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
            upvote_count=52,
            affected_students_count=53,
        )
        db.add(comp3)
        db.flush()

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
            category=ComplaintCategory.LABORATORY,
            campus=ComplaintCampus.NORTH_CAMPUS,
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
            upvote_count=8,
            affected_students_count=9,
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

        # Complaint 5: Resolved - Awaiting Complainant Confirmation (Demonstrating 5-Day Confirmation Window)
        comp5 = Complaint(
            grievance_id="NIE-2026-0005",
            title="Placement Registration Portal Crashes During Tier-1 Company Openings",
            description="Placement portal timed out repeatedly during Infosys and Cisco recruitment test registrations. Over 40 students could not submit slot preferences.",
            category=ComplaintCategory.PLACEMENT,
            campus=ComplaintCampus.NORTH_CAMPUS,
            department_id=dept_objs["CSE"].id,
            complainant_id=student_user.id,
            is_anonymous=False,
            location_name="Training & Placement Cell, Admin Block 1st Floor",
            status=ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
            current_tier=ComplaintTier.TIER_1,
            predicted_priority=ComplaintPriority.HIGH,
            final_priority=ComplaintPriority.HIGH,
            priority_confidence=0.88,
            priority_explanation="High-impact career service issue affecting placement eligibility.",
            submission_date=now - timedelta(days=4),
            resolved_at=now - timedelta(days=2),
            resolution_date=now - timedelta(days=2),
            confirmation_deadline=now + timedelta(days=3), # 3 days remaining in 5-day window
            student_confirmed=None, # Awaiting student response
            resolution_remarks="Placement server pool scaled up to 64GB RAM and load balancer updated. Registration window extended by 48 hours for all eligible batches.",
            upvote_count=42,
            affected_students_count=43,
        )
        db.add(comp5)
        db.flush()

        db.add(ComplaintTimeline(
            complaint_id=comp5.id,
            action="Marked as Resolved by Officer",
            actor_id=officer_cse.id,
            remarks="Placement server memory expanded; registrations extended by 48 hours. Awaiting complainant confirmation.",
            from_status=ComplaintStatus.UNDER_INVESTIGATION,
            to_status=ComplaintStatus.RESOLVED_AWAITING_CONFIRMATION,
            timestamp=now - timedelta(days=2),
        ))

        # Seed sample Community Support Votes
        db.add(ComplaintVote(complaint_id=comp1.id, user_id=student_user2.id, created_at=now - timedelta(days=4)))
        db.add(ComplaintVote(complaint_id=comp2.id, user_id=student_user2.id, created_at=now - timedelta(days=10)))
        db.add(ComplaintVote(complaint_id=comp5.id, user_id=student_user2.id, created_at=now - timedelta(days=3)))

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

        # Seed scholarship module and institutional announcements
        seed_scholarship_module(db)
        seed_institutional_announcements(db)

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

