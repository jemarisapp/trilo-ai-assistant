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
    db_path = DatabaseConfig.get_db_path("teams")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Rename base tables if the new ones do not exist yet
        def rename_if_exists(old, new):
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (new,))
            if cur.fetchone():
                print(f"'{new}' already exists. Skipping rename from '{old}'.")
                return
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (old,))
            if cur.fetchone():
                cur.execute(f"ALTER TABLE {old} RENAME TO {new}")
                print(f"Renamed table '{old}' -> '{new}'")
            else:
                print(f"Source table '{old}' not found. Nothing to rename.")

        rename_if_exists("teams", "cfb_teams")
        rename_if_exists("team_records", "cfb_team_records")
        rename_if_exists("valid_teams", "cfb_valid_teams")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()


