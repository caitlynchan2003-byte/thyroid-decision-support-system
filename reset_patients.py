"""reset_patients.py - delete all patient and diagnosis records.
Keeps users, treatments, and the activity log.
Run with:  python reset_patients.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "thyroid_cdsm.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    n_pat  = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    n_diag = conn.execute("SELECT COUNT(*) FROM diagnoses").fetchone()[0]

    conn.execute("DELETE FROM diagnoses")
    conn.execute("DELETE FROM patients")
    # restart the auto-increment IDs at 1 again
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('patients', 'diagnoses')")
    conn.commit()
    conn.close()

    print(f"Deleted {n_pat} patient(s) and {n_diag} diagnosis record(s).")
    print("User accounts and treatment data were kept.")


if __name__ == "__main__":
    main()