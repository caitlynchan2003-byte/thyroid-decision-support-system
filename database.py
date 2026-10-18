"""database.py - all SQLite access for the Thyroid CDSM."""

import sqlite3
import hashlib
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "thyroid_cdsm.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema():
    """Auto-upgrade an existing database: add the medical_history column
    to the diagnoses table if it isn't there yet (safe to call repeatedly)."""
    conn = get_connection()
    cols = [c[1] for c in conn.execute("PRAGMA table_info(diagnoses)")]
    if "medical_history" not in cols:
        conn.execute("ALTER TABLE diagnoses ADD COLUMN medical_history TEXT")
        conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- authentication ----------
def verify_user(username: str, password: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password)),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def change_password(username: str, new_password: str):
    conn = get_connection()
    conn.execute("UPDATE users SET password = ? WHERE username = ?",
                 (hash_password(new_password), username))
    conn.commit()
    conn.close()


# ---------- activity log ----------
def log_action(username: str, action: str, details: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO activity_log (username, action, details) VALUES (?, ?, ?)",
        (username, action, details))
    conn.commit()
    conn.close()


def get_activity_log(limit: int = 200) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT log_time, username, action, details FROM activity_log "
        "ORDER BY log_id DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return df


# ---------- patients ----------
def get_patient_by_ic(ic_number: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE ic_number = ?",
                       (ic_number,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_or_get_patient(ic_number, name, age, sex) -> int:
    existing = get_patient_by_ic(ic_number)
    if existing:
        return existing["patient_id"]
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO patients (ic_number, name, age, sex) VALUES (?, ?, ?, ?)",
        (ic_number, name, age, sex))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


# ---------- diagnoses ----------
def save_diagnosis(patient_id, hormones, result, confidence, diagnosed_by, history=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO diagnoses
           (patient_id, TSH, T3, TT4, T4U, FTI,
            diagnosis_result, confidence_score, diagnosed_by, medical_history)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, hormones["TSH"], hormones["T3"], hormones["TT4"],
         hormones["T4U"], hormones["FTI"], result, confidence, diagnosed_by, history))
    conn.commit()
    conn.close()


def get_patient_history(patient_id) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT diagnosed_at, diagnosis_result, confidence_score,
                  TSH, T3, TT4, T4U, FTI, medical_history, diagnosed_by
           FROM diagnoses WHERE patient_id = ? ORDER BY diagnosis_id DESC""",
        conn, params=(patient_id,))
    conn.close()
    return df


def search_records(name="", ic="", diagnosis="") -> pd.DataFrame:
    query = """
        SELECT p.ic_number, p.name, p.age, p.sex,
               d.diagnosis_result, d.confidence_score, d.diagnosed_at, d.diagnosed_by
        FROM patients p
        LEFT JOIN diagnoses d ON p.patient_id = d.patient_id
        WHERE 1 = 1
    """
    params = []
    if name:
        query += " AND p.name LIKE ?";          params.append(f"%{name}%")
    if ic:
        query += " AND p.ic_number LIKE ?";     params.append(f"%{ic}%")
    if diagnosis:
        query += " AND d.diagnosis_result = ?"; params.append(diagnosis)
    query += " ORDER BY d.diagnosis_id DESC"
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# ---------- treatments ----------
def get_treatment(diagnosis_result: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM treatments WHERE diagnosis_result = ?",
                       (diagnosis_result,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- dashboard ----------
def get_dashboard_data() -> pd.DataFrame:
    """Diagnoses joined with patient age/sex for richer charts."""
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT d.diagnosis_result, d.confidence_score, d.diagnosed_at,
                  p.age, p.sex
           FROM diagnoses d JOIN patients p ON d.patient_id = p.patient_id""",
        conn)
    conn.close()
    return df


def get_counts():
    conn = get_connection()
    n_patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    n_diag = conn.execute("SELECT COUNT(*) FROM diagnoses").fetchone()[0]
    conn.close()
    return n_patients, n_diag


# ---------- user management (admin) ----------
def get_all_users() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT user_id, username, role, full_name FROM users ORDER BY user_id", conn)
    conn.close()
    return df


def add_user(username, password, role, full_name) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, full_name))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def delete_user(username) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()