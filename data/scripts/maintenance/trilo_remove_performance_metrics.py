#!/usr/bin/env python3
"""
Remove performance_metrics table from existing databases
"""

import sqlite3
from pathlib import Path

def remove_performance_metrics():
    """Remove performance_metrics table and related data"""
    db_path = Path("data/databases/trilo_command_logs.db")
    
    if not db_path.exists():
        print("❌ Command logs database not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🧹 Removing performance_metrics table...")
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='performance_metrics'
        """)
        
        if not cursor.fetchone():
            print("✅ performance_metrics table doesn't exist - nothing to remove")
            return
        
        # Drop the table
        cursor.execute("DROP TABLE performance_metrics")
        
        # Drop related indexes
        cursor.execute("DROP INDEX IF EXISTS idx_performance_timestamp")
        cursor.execute("DROP INDEX IF EXISTS idx_performance_command")
        
        conn.commit()
        
        print("✅ performance_metrics table removed successfully!")
        
    except Exception as e:
        print(f"❌ Error removing performance_metrics table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    remove_performance_metrics()
