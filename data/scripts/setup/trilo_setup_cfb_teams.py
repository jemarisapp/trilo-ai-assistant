import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

db_path = DatabaseConfig.get_db_path("teams")

def setup_database():
    DatabaseConfig.ensure_data_dir()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS cfb_teams")
    cursor.execute("""
        CREATE TABLE cfb_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            team_name TEXT NOT NULL,
            server_id TEXT NOT NULL,
            UNIQUE(user_id, server_id),
            UNIQUE(team_name, server_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cfb_valid_teams (
            team_name TEXT PRIMARY KEY NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cfb_team_records (
            server_id TEXT NOT NULL,
            team_name TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            PRIMARY KEY (server_id, team_name)
        )
    """)

    valid_teams = [
        ("boston college",), ("california",), ("clemson",), ("duke",), ("florida state",),
        ("georgia tech",), ("louisville",), ("miami",), ("nc state",), ("north carolina",),
        ("pittsburgh",), ("smu",), ("stanford",), ("syracuse",), ("virginia",), ("virginia tech",),
        ("wake forest",), ("army",), ("charlotte",), ("east carolina",), ("florida atlantic",),
        ("memphis",), ("navy",), ("north texas",), ("rice",), ("temple",), ("tulane",), ("tulsa",),
        ("uab",), ("usf",), ("utsa",), ("arizona",), ("arizona state",), ("baylor",), ("byu",),
        ("cincinnati",), ("colorado",), ("houston",), ("iowa state",), ("kansas",), ("kansas state",),
        ("oklahoma state",), ("tcu",), ("texas tech",), ("ucf",), ("utah",), ("west virginia",),
        ("illinois",), ("indiana",), ("iowa",), ("maryland",), ("michigan",), ("michigan state",),
        ("minnesota",), ("nebraska",), ("northwestern",), ("ohio state",), ("oregon",), ("penn state",),
        ("purdue",), ("rutgers",), ("ucla",), ("usc",), ("washington",), ("wisconsin",),
        ("florida international",), ("jax state",), ("kennesaw state",), ("liberty",), ("louisiana tech",),
        ("middle tennessee st",), ("new mexico state",), ("sam houston",), ("utep",), ("western kentucky",),
        ("notre dame",), ("uconn",), ("umass",), ("akron",), ("ball state",), ("bowling green",),
        ("buffalo",), ("central michigan",), ("eastern michigan",), ("kent state",), ("miami university",),
        ("northern illinois",), ("ohio",), ("toledo",), ("western michigan",), ("air force",), ("boise state",),
        ("colorado state",), ("fresno state",), ("hawai'i",), ("nevada",), ("new mexico",), ("san diego state",),
        ("san jose state",), ("unlv",), ("utah state",), ("wyoming",), ("oregon state",), ("washington state",),
        ("alabama",), ("arkansas",), ("auburn",), ("florida",), ("georgia",), ("kentucky",), ("lsu",),
        ("mississippi state",), ("missouri",), ("oklahoma",), ("ole miss",), ("south carolina",), ("tennessee",),
        ("texas",), ("texas a&m",), ("vanderbilt",), ("appalachian state",), ("arkansas state",),
        ("coastal carolina",), ("georgia southern",), ("georgia state",), ("james madison",), ("louisiana",),
        ("marshall",), ("old dominion",), ("south alabama",), ("southern mississippi",), ("texas state",),
        ("troy",), ("ul monroe",)
    ]
    cursor.executemany("INSERT OR IGNORE INTO cfb_valid_teams (team_name) VALUES (?)", valid_teams)

    conn.commit()
    conn.close()
    print("CFB teams setup complete. Tables 'cfb_teams', 'cfb_valid_teams', 'cfb_team_records' ready.")

if __name__ == "__main__":
    setup_database()


