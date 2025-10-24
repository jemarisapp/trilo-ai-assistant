#!/usr/bin/env python3
"""
Migrate Command Logs to Use Interaction IDs

This script migrates the command_usage table to use interaction.id instead of timestamps
for tracking unique command attempts. This is more accurate than using timestamps.
"""

import sqlite3
import os
from pathlib import Path

def migrate_to_interaction_ids():
    """Migrate the database to use interaction IDs"""
    
    # Database path
    db_path = Path(__file__).parent.parent.parent / "data" / "databases" / "trilo_command_logs.db"
    
    if not db_path.exists():
        print("❌ Command logs database not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🔄 Migrating to interaction ID-based tracking...")
        
        # Check if interaction_id column already exists
        cursor.execute("PRAGMA table_info(command_usage)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'interaction_id' in columns:
            print("✅ Database already has interaction_id column!")
            return
        
        # Add interaction_id column
        print("  📝 Adding interaction_id column...")
        cursor.execute("ALTER TABLE command_usage ADD COLUMN interaction_id TEXT")
        
        # Create index on interaction_id
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_command_usage_interaction_id ON command_usage(interaction_id)")
        
        # For existing records, we can't get the real interaction_id, so we'll use a placeholder
        # and let the new logging system handle it going forward
        cursor.execute("UPDATE command_usage SET interaction_id = 'legacy_' || id WHERE interaction_id IS NULL")
        
        conn.commit()
        conn.close()
        
        print("✅ Migration complete!")
        print("💡 Going forward, new commands will use interaction.id for accurate tracking")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")

if __name__ == "__main__":
    migrate_to_interaction_ids()
