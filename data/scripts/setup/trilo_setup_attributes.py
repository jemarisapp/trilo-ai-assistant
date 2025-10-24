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
DB_PATH = DatabaseConfig.get_db_path("attributes")

def initialize_database():
    """Initialize the attribute points database"""
    # Ensure the database directory exists
    DatabaseConfig.ensure_data_dir()
    
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Create attribute_points table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attribute_points (
            user_id TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    """)

    # Create attribute_requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attribute_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            attribute_name TEXT NOT NULL,
            current_value INTEGER NOT NULL,
            requested_value INTEGER NOT NULL,
            points_cost INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()
    print("Attribute points database initialized successfully.")

if __name__ == "__main__":
    initialize_database()
