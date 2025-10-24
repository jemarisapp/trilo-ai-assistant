import sqlite3
import sys
from itertools import permutations
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

db_path = DatabaseConfig.get_db_path("matchups")

nfl_teams = [
    "Bills", "Dolphins", "Patriots", "Jets",
    "Ravens", "Bengals", "Browns", "Steelers",
    "Texans", "Colts", "Jaguars", "Titans",
    "Broncos", "Chiefs", "Raiders", "Chargers",
    "Cowboys", "Giants", "Eagles", "Commanders",
    "Bears", "Lions", "Packers", "Vikings",
    "Falcons", "Panthers", "Saints", "Buccaneers",
    "Cardinals", "Rams", "49ers", "Seahawks"
]

def setup_database():
    DatabaseConfig.ensure_data_dir()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fresh setup for NFL table
    cur.execute("DROP TABLE IF EXISTS \"nfl-matchups\"")
    cur.execute("""
        CREATE TABLE "nfl-matchups" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matchup TEXT NOT NULL UNIQUE
        )
    """)

    print("Generating NFL matchups...")
    all_matchups = set(f"{t1} vs {t2}" for t1, t2 in permutations(nfl_teams, 2))
    print("Inserting NFL matchups into the database...")
    cur.executemany("INSERT OR IGNORE INTO \"nfl-matchups\" (matchup) VALUES (?)", [(m,) for m in all_matchups])

    conn.commit()
    conn.close()
    print(f"NFL matchups setup complete. {len(all_matchups)} matchups created.")

if __name__ == "__main__":
    setup_database()


