"""
setup_database.py
Creates the SQLite database for the Thyroid CDSM and pre-loads
treatment recommendations and starter user accounts.
Run once:  python setup_database.py
"""

import sqlite3
import hashlib
from pathlib import Path

# Resolve paths relative to THIS file, so it works no matter where you run it from
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "thyroid_cdsm.db"


def hash_password(password: str) -> str:
    """SHA-256 hash, matching the methodology in Chapter 3."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_tables(conn):
    cur = conn.cursor()

    # 1. patients - one row per person, IC number prevents duplicates
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            ic_number   TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            age         INTEGER,
            sex         TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. diagnoses - one row per visit; links to a patient
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnoses (
            diagnosis_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id       INTEGER NOT NULL,
            TSH              REAL,
            T3               REAL,
            TT4              REAL,
            T4U              REAL,
            FTI              REAL,
            diagnosis_result TEXT,
            confidence_score REAL,
            diagnosed_by     TEXT,
            diagnosed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
    """)

    # 3. treatments - one row per diagnosis category (lookup table)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            treatment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnosis_result TEXT UNIQUE NOT NULL,
            medication       TEXT,
            dosage           TEXT,
            lifestyle_advice TEXT,
            followup_weeks   INTEGER
        )
    """)

    # 4. users - login accounts with hashed passwords and roles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            role      TEXT NOT NULL,
            full_name TEXT
        )
    """)

    # 5. activity_log - audit trail of everything users do
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            log_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action   TEXT,
            details  TEXT,
            log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def seed_treatments(conn):
    """Typical first-line values as editable starting points.
    NOTE: these are templates for an academic prototype - verify against
    current clinical guidelines (e.g. ATA) before any real use."""
    treatments = [
        # diagnosis_result, medication, dosage, lifestyle_advice, followup_weeks
        ("Negative",
         "None",
         "Not applicable",
         "No thyroid treatment needed. Maintain a balanced diet with adequate iodine and attend routine health screening.",
         52),
        ("Hyperthyroid",
         "Carbimazole (antithyroid drug); beta-blocker for symptom relief if needed",
         "Carbimazole 15-40 mg/day initially, titrated to response",
         "Avoid excess iodine intake. Monitor for palpitations and weight loss. Report fever or sore throat promptly.",
         6),
        ("Primary Hypothyroid",
         "Levothyroxine (LT4)",
         "~1.6 mcg/kg/day; start lower in elderly or cardiac patients",
         "Take on an empty stomach 30-60 min before breakfast, at a consistent time daily. Recheck TSH after dose changes.",
         8),
        ("Compensated Hypothyroid",
         "Levothyroxine (low dose) if symptomatic, otherwise monitor",
         "25-50 mcg/day if treated; otherwise observe",
         "Subclinical pattern. Monitor TSH periodically; treat if symptomatic or TSH continues to rise.",
         12),
        ("Other Thyroid Condition",
         "Refer to endocrinologist for evaluation",
         "As determined by specialist assessment",
         "Heterogeneous category. Specialist review recommended to confirm the specific condition before treatment.",
         4),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR IGNORE INTO treatments
        (diagnosis_result, medication, dosage, lifestyle_advice, followup_weeks)
        VALUES (?, ?, ?, ?, ?)
    """, treatments)
    conn.commit()


def seed_users(conn):
    """Starter accounts. CHANGE THESE PASSWORDS before any real deployment."""
    users = [
        # username, password, role, full_name
        ("admin",  hash_password("admin123"),  "admin",  "System Administrator"),
        ("doctor", hash_password("doctor123"), "doctor", "Dr. Default"),
        ("nurse",  hash_password("nurse123"),  "nurse",  "Nurse Default"),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR IGNORE INTO users (username, password, role, full_name)
        VALUES (?, ?, ?, ?)
    """, users)
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    seed_treatments(conn)
    seed_users(conn)
    conn.close()
    print(f"Database created at: {DB_PATH}")
    print("Tables: patients, diagnoses, treatments, users, activity_log")
    print("Seeded 5 treatment rows and 3 user accounts (admin / doctor / nurse).")


if __name__ == "__main__":
    main()
