import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

db_path = DatabaseConfig.get_db_path("teams")

nfl_teams = [
    "bills", "dolphins", "patriots", "jets",
    "ravens", "bengals", "browns", "steelers",
    "texans", "colts", "jaguars", "titans",
    "broncos", "chiefs", "raiders", "chargers",
    "cowboys", "giants", "eagles", "commanders",
    "bears", "lions", "packers", "vikings",
    "falcons", "panthers", "saints", "buccaneers",
    "cardinals", "rams", "49ers", "seahawks"
]

def setup_database():
    DatabaseConfig.ensure_data_dir()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS nfl_teams")
    cur.execute("""
        CREATE TABLE nfl_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            team_name TEXT NOT NULL,
            server_id TEXT NOT NULL,
            UNIQUE(user_id, server_id),
            UNIQUE(team_name, server_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfl_valid_teams (
            team_name TEXT PRIMARY KEY NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfl_team_records (
            server_id TEXT NOT NULL,
            team_name TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            PRIMARY KEY (server_id, team_name)
        )
    """)

    cur.executemany("INSERT OR IGNORE INTO nfl_valid_teams (team_name) VALUES (?)", [(t,) for t in nfl_teams])

    conn.commit()
    conn.close()
    print("NFL teams setup complete. Tables 'nfl_teams', 'nfl_valid_teams', 'nfl_team_records' ready.")

if __name__ == "__main__":
    setup_database()


