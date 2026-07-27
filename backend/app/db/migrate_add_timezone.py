"""
MarcoAI – Migration: add timezone column to user_settings
Run once after deploying the code change:
    python -m app.db.migrate_add_timezone
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "marcoai.db"


def migrate(db_path: str | Path = DB_PATH) -> None:
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"DB not found at {db_path} – skipping (fresh install, create_all handles it)")
        return

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Check if column already exists
    cur.execute("PRAGMA table_info(user_settings)")
    columns = {row[1] for row in cur.fetchall()}

    if "timezone" in columns:
        print("Column 'timezone' already exists – nothing to do.")
        conn.close()
        return

    print("Adding column 'timezone' to user_settings …")
    cur.execute(
        "ALTER TABLE user_settings ADD COLUMN timezone VARCHAR(40) NOT NULL DEFAULT 'Europe/Madrid'"
    )
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(path)
