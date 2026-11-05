# NIEresolve

> **"Every Concern Deserves a Response."**  
> **Institution:** The National Institute of Engineering (NIE), Mysuru  
> **Project Type:** AI-Powered College Grievance Redressal and Student Support Platform

---

## 🏛️ Executive Summary

**NIEresolve** is an enterprise-grade institutional grievance management and student support platform designed specifically for **The National Institute of Engineering (NIE), Mysuru**. It streamlines campus feedback, automates multi-tier dispute escalations, applies machine learning to prioritize grievances and detect duplicates, enables geotagged evidence verification, and offers personalized scholarship intelligence alongside an institutional AI assistant.

---

## ⚡ Core Platform Workflow

```
[Student / Faculty Login]
         │ (USN/ID + DOB Authentication)
         ▼
[Submit Complaint] ──► [Live GPS Capture] + [Evidence Upload]
         │
         ├──► [ML Priority Classification] (Critical / High / Medium / Low)
         │       └── [Safety-Critical Urgency Guardrail Override]
         │
         ├──► [Intelligent Duplicate Detection] (TF-IDF Cosine Similarity)
         │       └── [Merge into Master Case with Private Complainant Tracking]
         │
         ▼
[Tier 1: Department Level] (15 Calendar Days Window)
         │  • Evidence Verification (Verified / Rejected / Additional Evidence)
         │  • Officer Investigation & Remarks
         │
         ├──► [Unresolved after 15 Days] ──► [Auto-Escalate to Tier 2]
         │                                       │
         ▼                                       ▼
[Tier 2: Grievance Cell]                   [Tier 3: Principal / Higher Authority]
 (15 Calendar Days Window)                  (Executive Review & Direct Closure)
         │                                       │
         └───────────────────────────────────────┘
                            │
                            ▼
                   [Formal Resolution]
                            │
                            ▼
              [Complainant Confirmation]
              (Satisfied: Closed / Unsatisfied: Reopened)
```

---

## 🚀 Key Features

### 1. Role-Based Access Control (RBAC) & Secure Login
- **Student Authentication:** University Seat Number (USN, e.g., `4NI21CS045`) + Date of Birth (DOB). Hashed using bcrypt; DOB is never exposed in API payloads or client state.
- **Faculty Authentication:** Faculty ID (e.g., `NIE-FAC-102`) + Date of Birth.
- **Administrative Login:** Email / Username + Password for Tier 1 Department Officers, Tier 2 Grievance Cell, Tier 3 Principal, and Super Admin.
- **JWT Session Tokens:** Secure stateless authorization across all protected endpoints.

### 2. Geo-Tagged Evidence Verification
- **Device Geolocation Capture:** Captures latitude, longitude, and accuracy radius upon submission.
- **Exception Workflow:** Accommodates students submitting from desktop workstations without GPS sensors via required exception rationale.
- **Officer Verification Workflow:** Authorizes designated officers to review uploaded photos/documents and mark evidence as `Verified`, `Rejected`, or `Requires Additional Evidence`.

### 3. Machine Learning Priority Classification
- **Model:** TF-IDF text vectorization + Logistic Regression classifier with balanced class weights trained on institutional grievance data.
- **Classes:** `Critical`, `High`, `Medium`, `Low`.
- **Interpretable AI:** Provides confidence scores and key contributing feature tokens.
- **Safety-Critical Guardrail:** Automatic urgent override for life-safety, harassment, and structural hazards (e.g., exposed high voltage wiring, chemical spills, ragging).
- **Manual Officer Override:** Permits authorized officers to change priority with mandatory audit trail justification.

### 4. Duplicate Complaint Detection and Merging
- **Semantic Similarity Engine:** TF-IDF cosine similarity vector comparison against unresolved complaints within the same department or category.
- **Pre-submission Warning:** Proactively informs complainants of matching active cases.
- **Master-Duplicate Linking:** Consolidates duplicate reports under a master grievance ID, tracks the count of affected individuals, combines evidence, preserves complainant confidentiality, and synchronizes status updates across all complainants.

### 5. Automated Three-Tier Escalation Matrix
- **Tier 1 (Department Level):** Handled by Department Grievance Officers and Coordinators. Fixed 15 calendar day SLA.
- **Tier 2 (Institutional Grievance Cell):** If unresolved within 15 calendar days at Tier 1, cases automatically escalate to Tier 2.
- **Tier 3 (Principal / Higher Authority):** If unresolved after an additional 15 calendar days at Tier 2, cases automatically escalate to Tier 3.
- **Background Scheduler:** Asynchronous periodic supervisor automatically advances tiers, issues countdown warnings (&le; 3 days remaining), and notifies authorities without client-side dependencies.
- **Pause Capability:** Administrators can temporarily freeze SLA timers for legitimate pending inspections with mandatory recorded reasons.

### 6. Transparent Scholarship Recommendation System
- **Student Profile:** Collects CGPA, family income, reservation category, branch, year, semester, and domicile.
- **Genuine Database:** Contains real schemes relevant to engineering students in Karnataka and India (Karnataka SSP Post-Matric, AICTE Pragati for Girls, AICTE Saksham for Specially-Abled, CSSS Central Sector, and FAEA).
- **Rule-Based Engine:** Ranks opportunities into `Eligible` (100% match), `Potentially Eligible`, and `Not Eligible` with clear requirement explanations, required documents, deadlines, and official portal links.

### 7. Institutional AI Chatbot (NIEresolve AI)
- **Institution-Specific Knowledge Base:** Trained on NIE policies, campus departments, hostel wardens, examination section guidelines, and safety directives.
- **Dynamic Database Queries:** Authenticated students can query live grievance statuses (e.g., *"What is the status of my complaints?"* or *"What is the status of NIE-2026-0001?"*).
- **Source Citations & Hallucination Prevention:** Direct citations to official handbooks; clearly informs when information is not in verified records.

---

## 🔑 Demo Credentials for Testing

| Role | Username / Identifier | Password / DOB | Full Name & Designation |
| :--- | :--- | :--- | :--- |
| **Student** | `4NI21CS045` | `2003-05-15` | Ananya Sharma (B.Tech CSE, 6th Sem, OBC) |
| **Student (Duplicate)** | `4NI21CS088` | `2003-11-22` | Rahul Verma (B.Tech CSE, 6th Sem, Gen) |
| **Faculty** | `NIE-FAC-102` | `1985-08-20` | Dr. Ramesh Kumar (Assoc. Prof, Mechanical) |
| **Tier 1: Dept Officer** | `officer.cse@nie.ac.in` | `Officer@123` | Prof. Sudhir Rao (CSE Grievance Officer) |
| **Tier 2: Grievance Cell** | `grievancecell@nie.ac.in`| `Grievance@123`| Dr. K. S. Venkatesh (Cell Head) |
| **Tier 3: Principal** | `principal@nie.ac.in` | `Principal@123` | Dr. Rohini Nagapadma (Principal, NIE) |
| **Super Admin** | `admin@nie.ac.in` | `Admin@123` | System Administrator (IT Operations) |

---

## 💻 Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, Uvicorn, SQLite (PostgreSQL ready).
- **Frontend:** Single Page Application (SPA), React 18, Tailwind CSS, Lucide Icons, Chart.js.
- **Machine Learning & NLP:** Scikit-learn, TF-IDF vectorization, Logistic Regression, Cosine Similarity.
- **Authentication:** PyJWT, Bcrypt password hashing.
- **Background Tasks:** Asyncio background escalation monitor.

---

## 📁 Repository Structure

```
NIEresolve/
├── backend/
│   ├── app/
│   │   ├── config.py              # Application settings, JWT key, escalation days
│   │   ├── database.py            # SQLAlchemy engine, session maker, SQLite PRAGMA
│   │   ├── scheduler.py           # Background async periodic escalation monitor
│   │   ├── auth/                  # Security utilities, JWT encoding, RBAC guards
│   │   ├── models/                # SQLAlchemy database entities (User, Complaint, etc.)
│   │   ├── schemas/               # Pydantic request and response schemas
│   │   ├── ml/                    # ML model training, priority predictor, duplicate detector
│   │   │   ├── priority_model.py  # Model inference & safety-critical override
│   │   │   ├── duplicate_detector.py # TF-IDF cosine similarity engine
│   │   │   ├── train_model.py     # Offline ML training script with metrics
│   │   │   └── data/              # Model artifacts (.joblib)
│   │   ├── services/              # Business logic (Complaints, Escalation, Scholarships, Chatbot)
│   │   ├── routers/               # API endpoints (auth, complaints, evidence, escalations, etc.)
│   │   └── seeds/                 # Comprehensive realistic seed data for NIE Mysuru
│   ├── tests/
│   │   └── test_all.py            # Comprehensive automated test suite (13 test cases)
│   └── uploads/                   # Secure storage for uploaded evidence files
├── frontend/
│   ├── index.html                 # Main Single Page Application shell
│   ├── css/
│   │   └── style.css              # Custom styling, NIE navy/gold theme accents
│   └── js/
│       └── app.js                 # Complete React 18 SPA (Role-based dashboards, Modals, Chatbot)
├── data/
│   └── sample_training_data.csv   # Labeled grievance dataset for priority classification
├── main.py                        # FastAPI application setup, static mounts, routes
├── run.py                         # One-click startup script (auto-seed, model check, uvicorn)
├── requirements.txt               # Python package dependencies
├── .env.example                   # Environment configuration template
└── README.md                      # Documentation
```

---

## 🛠️ Local Setup & Quickstart

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed.
- Modern web browser (Chrome, Edge, Firefox, Safari).

### 1. Clone & Navigate to Repository
```bash
git clone <repository_url>
cd NIEresolve
```

### 2. Configure Environment
Copy the example environment configuration:
```bash
cp .env.example .env
```

### 3. Run One-Click Startup Script
```bash
python run.py
```
This single command automatically:
1. Creates the database tables and populates realistic NIE Mysuru seed data.
2. Trains and validates the ML grievance priority classifier.
3. Launches the web platform and background 15-day escalation monitor at `http://127.0.0.1:8000`.

### 4. Access the Application
- **Web Application Portal:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the complete 13-case test suite covering authentication, RBAC, ML predictions, duplicate detection, evidence verification, merging, 15-day escalation, scholarships, and chatbot RAG:
```bash
python -m pytest backend/tests/test_all.py -v
```

**Test Coverage Highlights:**
- Student login with USN and DOB & DOB privacy validation.
- Faculty login with Faculty ID & DOB.
- Administrative authentication for Tier 1 Department Officers.
- ML urgency prediction & safety-critical keyword guardrail.
- TF-IDF cosine similarity duplicate detection.
- Complaint registration with GPS location & initial 15-day SLA deadline.
- Officer evidence verification (`Verified`, `Rejected`).
- Duplicate complaint merging with preserved audit trail.
- Automatic 15-day escalation from Tier 1 to Tier 2.
- Rule-based scholarship recommendation engine.
- Institutional RAG knowledge base answers & personalized live database queries.
- Student resolution satisfaction confirmation and reopening workflow.

---

## 📜 License & Accreditation
Designed and developed for **The National Institute of Engineering (NIE), Mysuru**.  
*Every Concern Deserves a Response.*
