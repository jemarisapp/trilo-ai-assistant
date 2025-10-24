import sqlite3
import sys
from itertools import permutations
from pathlib import Path

# Add the parent directory to the path so we can import config
sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

# Get database path from configuration
db_path = DatabaseConfig.get_db_path("matchups")

# List of teams
teams = [
    "boston college", "california", "clemson", "duke", "florida state",
    "georgia tech", "louisville", "miami", "nc state", "north carolina",
    "pittsburgh", "smu", "stanford", "syracuse", "virginia", "virginia tech",
    "wake forest", "army", "charlotte", "east carolina", "florida atlantic",
    "memphis", "navy", "north texas", "rice", "temple", "tulane", "tulsa",
    "uab", "usf", "utsa", "arizona", "arizona state", "baylor", "byu",
    "cincinnati", "colorado", "houston", "iowa state", "kansas", "kansas state",
    "oklahoma state", "tcu", "texas tech", "ucf", "utah", "west virginia",
    "illinois", "indiana", "iowa", "maryland", "michigan", "michigan state",
    "minnesota", "nebraska", "northwestern", "ohio state", "oregon", "penn state",
    "purdue", "rutgers", "ucla", "usc", "washington", "wisconsin",
    "florida international", "jax state", "kennesaw state", "liberty", "louisiana tech",
    "middle tennessee st", "new mexico state", "sam houston", "utep", "western kentucky",
    "notre dame", "uconn", "umass", "akron", "ball state", "bowling green",
    "buffalo", "central michigan", "eastern michigan", "kent state", "miami university",
    "northern illinois", "ohio", "toledo", "western michigan", "air force", "boise state",
    "colorado state", "fresno state", "hawai'i", "nevada", "new mexico", "san diego state",
    "san jose state", "unlv", "utah state", "wyoming", "oregon state", "washington state",
    "alabama", "arkansas", "auburn", "florida", "georgia", "kentucky", "lsu",
    "mississippi state", "missouri", "oklahoma", "ole miss", "south carolina", "tennessee",
    "texas", "texas a&m", "vanderbilt", "appalachian state", "arkansas state",
    "coastal carolina", "georgia southern", "georgia state", "james madison", "louisiana",
    "marshall", "old dominion", "south alabama", "southern mississippi", "texas state",
    "troy", "ul monroe", "fcs school"
]

def setup_database():
    # Ensure the database directory exists
    DatabaseConfig.ensure_data_dir()
    
    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop the `cfb-matchups` table if it exists (optional, for fresh setup)
    cursor.execute("DROP TABLE IF EXISTS \"cfb-matchups\"")

    # Create the `cfb-matchups` table
    cursor.execute("""
        CREATE TABLE "cfb-matchups" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matchup TEXT NOT NULL UNIQUE
        )
    """)

    # Generate all unique matchups
    print("Generating matchups...")
    matchups = set(f"{team1} vs {team2}" for team1, team2 in permutations(teams, 2))

    # Insert matchups into the database
    print("Inserting matchups into the database...")
    cursor.executemany("INSERT OR IGNORE INTO \"cfb-matchups\" (matchup) VALUES (?)", [(matchup,) for matchup in matchups])

    # Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Database setup complete. {len(matchups)} matchups have been created.")

if __name__ == "__main__":
    setup_database()
