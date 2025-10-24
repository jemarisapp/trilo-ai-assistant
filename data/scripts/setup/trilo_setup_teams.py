import sqlite3
import sys
from pathlib import Path

# Add the parent directory to the path so we can import config
sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

# Get database path from configuration
db_path = DatabaseConfig.get_db_path("teams")

def setup_database():
    # Ensure the database directory exists
    DatabaseConfig.ensure_data_dir()
    
    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop the `cfb_teams` table if it exists (optional, for fresh setup)
    cursor.execute("DROP TABLE IF EXISTS cfb_teams")
    
    # Create the `cfb_teams` table with a `server_id` column for server-specific assignments
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

    # Create a `cfb_valid_teams` table that will store the list of valid team names
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cfb_valid_teams (
            team_name TEXT PRIMARY KEY NOT NULL
        )
    """)

    # Create cfb_team_records table for tracking wins/losses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cfb_team_records (
            server_id TEXT NOT NULL,
            team_name TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            PRIMARY KEY (server_id, team_name)
        )
    """)

    # Insert valid team names into the `cfb_valid_teams` table
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
    
    print("Database setup complete. The 'cfb_teams', 'cfb_valid_teams', and 'cfb_team_records' tables have been created.")

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
