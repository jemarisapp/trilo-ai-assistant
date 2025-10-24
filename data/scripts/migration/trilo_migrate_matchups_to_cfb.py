import sqlite3
import sys
from pathlib import Path

# Allow importing project config
sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig


def migrate():
    db_path = DatabaseConfig.get_db_path("matchups")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Ensure destination table name uses quotes because of hyphen
        # 1) If destination already exists, skip rename
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cfb-matchups'")
        if cur.fetchone():
            print("'cfb-matchups' already exists. Skipping rename.")
        else:
            # 2) If source exists, rename it
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matchups'")
            if cur.fetchone():
                cur.execute("ALTER TABLE matchups RENAME TO 'cfb-matchups'")
                print("Renamed table 'matchups' -> 'cfb-matchups'")
            else:
                print("Source table 'matchups' not found. Nothing to rename.")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()


