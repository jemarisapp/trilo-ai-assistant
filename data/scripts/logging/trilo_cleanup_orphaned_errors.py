#!/usr/bin/env python3
"""
Clean up orphaned error logs that don't have corresponding command_usage entries
"""

import sqlite3
from pathlib import Path

def cleanup_duplicate_errors():
    """Remove duplicate error logs for the same command execution"""
    db_path = Path("data/databases/trilo_command_logs.db")
    
    if not db_path.exists():
        print("❌ Command logs database not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🧹 Cleaning up duplicate error logs...")
        
        # Find error logs that have duplicates within 3 seconds for same server + command
        cursor.execute("""
            SELECT server_id, command_name, timestamp, COUNT(*) as count
            FROM error_log 
            GROUP BY server_id, command_name, 
                     strftime('%Y-%m-%d %H:%M:%S', timestamp)
            HAVING COUNT(*) > 1
        """)
        
        duplicate_groups = cursor.fetchall()
        
        if not duplicate_groups:
            print("✅ No duplicate error logs found!")
            return
        
        print(f"📊 Found {len(duplicate_groups)} groups with duplicate error logs")
        
        total_deleted = 0
        
        for server_id, command_name, timestamp, count in duplicate_groups:
            print(f"  🕐 {timestamp} | {command_name} | {count} duplicates")
            
            # Get all error logs for this group
            cursor.execute("""
                SELECT id, error_type, error_message, timestamp
                FROM error_log 
                WHERE server_id = ? AND command_name = ?
                AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                ORDER BY timestamp ASC
            """, (server_id, command_name, timestamp, timestamp))
            
            error_entries = cursor.fetchall()
            
            # Keep the first entry, delete the rest
            if len(error_entries) > 1:
                keep_id = error_entries[0][0]
                delete_ids = [e[0] for e in error_entries[1:]]
                
                placeholders = ','.join(['?' for _ in delete_ids])
                cursor.execute(f"DELETE FROM error_log WHERE id IN ({placeholders})", delete_ids)
                deleted = cursor.rowcount
                total_deleted += deleted
                
                print(f"    🗑️  Deleted {deleted} duplicate error logs (kept ID: {keep_id})")
        
        conn.commit()
        
        print(f"\n🎉 Duplicate error cleanup complete!")
        print(f"📊 Total error logs removed: {total_deleted}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_duplicate_errors()
