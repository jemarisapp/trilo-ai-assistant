import sqlite3
import uuid
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import config
sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

# Get database path from configuration
DB_PATH = DatabaseConfig.get_db_path("keys")

# Generate a unique access key
def generate_access_key():
    return str(uuid.uuid4())

# Initialize database
def initialize_database():
    # Ensure the database directory exists
    DatabaseConfig.ensure_data_dir()
    
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_keys (
            key TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS used_keys (
            key TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_servers (
            server_id INTEGER PRIMARY KEY,
            access_key TEXT
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_settings (
        server_id TEXT NOT NULL,
        setting TEXT NOT NULL,
        new_value TEXT NOT NULL,
        PRIMARY KEY (server_id, setting)
    );
    """)
    
    # Insert some sample access keys (if table is empty)
    cursor.execute("SELECT COUNT(*) FROM access_keys")
    if cursor.fetchone()[0] == 0:
        keys_to_generate = 5
        for _ in range(keys_to_generate):
            cursor.execute("INSERT INTO access_keys (key) VALUES (?)", (generate_access_key(),))

    connection.commit()
    connection.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    initialize_database()
