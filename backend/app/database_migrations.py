import sqlite3
import os
from backend.app.database import engine, Base
from backend.app.config import settings

def run_migrations():
    """
    Applies non-destructive schema migrations for existing SQLite databases.
    Ensures newly added columns and tables are created while preserving existing data.
    """
    # 1. Create all newly defined tables if they do not exist yet
    Base.metadata.create_all(bind=engine)

    # 2. Check and add missing columns to SQLite tables
    db_file = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    if not os.path.isabs(db_file):
        db_file = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), db_file))

    if not os.path.exists(db_file):
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        # Complaints table column updates
        cursor.execute("PRAGMA table_info(complaints)")
        complaints_cols = [row[1] for row in cursor.fetchall()]

        complaints_additions = [
            ("campus", "VARCHAR(50) DEFAULT 'North Campus'"),
            ("upvote_count", "INTEGER DEFAULT 0"),
            ("is_confidential_evidence", "BOOLEAN DEFAULT 0"),
            ("resolved_at", "DATETIME"),
            ("confirmation_deadline", "DATETIME"),
            ("is_auto_confirmed", "BOOLEAN DEFAULT 0"),
            ("reopen_count", "INTEGER DEFAULT 0"),
            ("reopen_reason", "TEXT"),
            ("reopened_at", "DATETIME"),
        ]

        for col_name, col_type in complaints_additions:
            if col_name not in complaints_cols:
                print(f"[Migration] Adding column '{col_name}' to 'complaints' table...")
                cursor.execute(f"ALTER TABLE complaints ADD COLUMN {col_name} {col_type}")

        # Student Profiles table column updates
        cursor.execute("PRAGMA table_info(student_profiles)")
        student_cols = [row[1] for row in cursor.fetchall()]

        student_additions = [
            ("parent_phone_number", "VARCHAR(20)"),
            ("parent_name", "VARCHAR(100)"),
            ("parent_relation", "VARCHAR(50) DEFAULT 'Father'"),
            ("student_phone_number", "VARCHAR(20)"),
        ]

        for col_name, col_type in student_additions:
            if col_name not in student_cols:
                print(f"[Migration] Adding column '{col_name}' to 'student_profiles' table...")
                cursor.execute(f"ALTER TABLE student_profiles ADD COLUMN {col_name} {col_type}")

        # Users table column updates
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [row[1] for row in cursor.fetchall()]

        user_additions = [
            ("can_publish_scholarships", "BOOLEAN DEFAULT 0"),
        ]

        for col_name, col_type in user_additions:
            if col_name not in user_cols:
                print(f"[Migration] Adding column '{col_name}' to 'users' table...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")

        conn.commit()
        print("[Migration] Database schema migrations completed successfully.")
    except Exception as e:
        print(f"[Migration] Schema migration notice: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migrations()

