import os
import sys
import uvicorn

# Ensure repository root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.config import settings
from backend.app.seeds.seed_data import seed_database
from backend.app.ml.train_model import train_priority_model

def main():
    print("=" * 75)
    print("  NIEresolve — Every Concern Deserves a Response.")
    print("  The National Institute of Engineering (NIE), Mysuru")
    print("  AI-Powered College Grievance Redressal and Student Support Platform")
    print("=" * 75)

    # 1. Initialize DB and Seed Demo Data
    print("\n[1/3] Checking database and institutional seed data...")
    seed_database()

    # 2. Check and Train ML Priority Model
    print("\n[2/3] Checking ML priority prediction model artifacts...")
    if not os.path.exists(settings.MODEL_STORAGE_PATH) or not os.path.exists(settings.VECTORIZER_STORAGE_PATH):
        print("Model artifacts missing. Training priority classifier...")
        train_priority_model()
    else:
        print("ML Model artifacts verified.")

    # 3. Print Demo Credentials
    print("\n[3/3] Ready to launch!")
    print("-" * 75)
    print("  DEMO CREDENTIALS FOR TESTING:")
    print("  1. Student:           USN: 4NI21CS045      | DOB: 2003-05-15")
    print("  2. Faculty:           ID:  NIE-FAC-102     | DOB: 1985-08-20")
    print("  3. Tier 1 Officer:    officer.cse@nie.ac.in | Pass: Officer@123")
    print("  4. Tier 2 Grievance:  grievancecell@nie.ac.in| Pass: Grievance@123")
    print("  5. Tier 3 Principal:  principal@nie.ac.in   | Pass: Principal@123")
    print("  6. Super Admin:       admin@nie.ac.in       | Pass: Admin@123")
    print("-" * 75)
    print(f"  Access Portal at: http://{settings.HOST}:{settings.PORT}")
    print(f"  Interactive API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 75 + "\n")

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

if __name__ == "__main__":
    main()

