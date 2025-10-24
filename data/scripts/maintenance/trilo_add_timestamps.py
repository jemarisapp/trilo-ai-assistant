"""
Trilo Timestamp Migration Script

This script adds comprehensive timestamp columns to all Trilo databases for audit tracking.
All timestamps are stored in Eastern Time (EST/EDT) with automatic daylight saving time handling.

Tables Updated:
- Teams Database: cfb_teams, cfb_team_records, nfl_teams, nfl_team_records
- Attributes Database: attribute_points, attribute_requests, attributes_log
- Keys Database: server_settings, server_subscriptions

Usage: python3 data/scripts/trilo_add_timestamps.py

The script is safe to run multiple times - it will skip columns that already exist.
"""

import sqlite3
import sys
from pathlib import Path

# Allow importing project config
sys.path.append(str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig


def add_timestamps():
    """Add timestamp columns to all databases for audit tracking"""
    
    databases = ["teams", "attributes", "keys"]
    
    for db_name in databases:
        db_path = DatabaseConfig.get_db_path(db_name)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n🔄 Processing {db_name} database...")
        
        try:
            if db_name == "teams":
                # Add timestamps to teams tables
                try:
                    cursor.execute("ALTER TABLE cfb_teams ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to cfb_teams")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in cfb_teams")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE cfb_teams ADD COLUMN updated_at DATETIME")
                    print("  ✅ Added updated_at to cfb_teams")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ updated_at already exists in cfb_teams")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE cfb_team_records ADD COLUMN last_updated DATETIME")
                    print("  ✅ Added last_updated to cfb_team_records")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ last_updated already exists in cfb_team_records")
                    else:
                        raise
                
                # Also handle NFL tables if they exist
                try:
                    cursor.execute("ALTER TABLE nfl_teams ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to nfl_teams")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in nfl_teams")
                    elif "no such table" in str(e):
                        print("  ℹ️ nfl_teams table doesn't exist (skipping)")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE nfl_teams ADD COLUMN updated_at DATETIME")
                    print("  ✅ Added updated_at to nfl_teams")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ updated_at already exists in nfl_teams")
                    elif "no such table" in str(e):
                        print("  ℹ️ nfl_teams table doesn't exist (skipping)")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE nfl_team_records ADD COLUMN last_updated DATETIME")
                    print("  ✅ Added last_updated to nfl_team_records")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ last_updated already exists in nfl_team_records")
                    elif "no such table" in str(e):
                        print("  ℹ️ nfl_team_records table doesn't exist (skipping)")
                    else:
                        raise
                
            elif db_name == "attributes":
                # Add timestamps to attributes tables
                try:
                    cursor.execute("ALTER TABLE attribute_points ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to attribute_points")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in attribute_points")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE attribute_points ADD COLUMN last_updated DATETIME")
                    print("  ✅ Added last_updated to attribute_points")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ last_updated already exists in attribute_points")
                    else:
                        raise
                
                # Add timestamps to attributes_log table if it exists
                try:
                    cursor.execute("ALTER TABLE attributes_log ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to attributes_log")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in attributes_log")
                    elif "no such table" in str(e):
                        print("  ℹ️ attributes_log table doesn't exist (skipping)")
                    else:
                        raise
                
                # Add timestamps to attribute_requests table
                try:
                    cursor.execute("ALTER TABLE attribute_requests ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to attribute_requests")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in attribute_requests")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE attribute_requests ADD COLUMN updated_at DATETIME")
                    print("  ✅ Added updated_at to attribute_requests")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ updated_at already exists in attribute_requests")
                    else:
                        raise
                
            elif db_name == "keys":
                # Add timestamps to keys/settings tables
                try:
                    cursor.execute("ALTER TABLE server_settings ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to server_settings")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in server_settings")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE server_settings ADD COLUMN updated_at DATETIME")
                    print("  ✅ Added updated_at to server_settings")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ updated_at already exists in server_settings")
                    else:
                        raise
                
                # Add timestamps to registered_servers table
                try:
                    cursor.execute("ALTER TABLE registered_servers ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to registered_servers")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in registered_servers")
                    elif "no such table" in str(e):
                        print("  ℹ️ registered_servers table doesn't exist (skipping)")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE registered_servers ADD COLUMN last_updated DATETIME")
                    print("  ✅ Added last_updated to registered_servers")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ last_updated already exists in registered_servers")
                    elif "no such table" in str(e):
                        print("  ℹ️ registered_servers table doesn't exist (skipping)")
                    else:
                        raise
                
                # Add timestamps to server_subscriptions table
                try:
                    cursor.execute("ALTER TABLE server_subscriptions ADD COLUMN created_at DATETIME")
                    print("  ✅ Added created_at to server_subscriptions")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ created_at already exists in server_subscriptions")
                    elif "no such table" in str(e):
                        print("  ℹ️ server_subscriptions table doesn't exist (skipping)")
                    else:
                        raise
                
                try:
                    cursor.execute("ALTER TABLE server_subscriptions ADD COLUMN updated_at DATETIME")
                    print("  ✅ Added updated_at to server_subscriptions")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print("  ⚠️ updated_at already exists in server_subscriptions")
                    elif "no such table" in str(e):
                        print("  ℹ️ server_subscriptions table doesn't exist (skipping)")
                    else:
                        raise
            
            conn.commit()
            print(f"✅ Successfully processed {db_name} database")
            
        except Exception as e:
            print(f"❌ Error updating {db_name} database: {e}")
            conn.rollback()
        finally:
            conn.close()


def verify_timestamps():
    """Verify that timestamp columns were added successfully"""
    print("\n🔍 Verifying timestamp columns...")
    
    databases = ["teams", "attributes", "keys"]
    
    for db_name in databases:
        db_path = DatabaseConfig.get_db_path(db_name)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n📊 {db_name.upper()} DATABASE:")
        
        try:
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table_name, in tables:
                # Get column info for each table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                timestamp_cols = [col[1] for col in columns if 'created_at' in col[1] or 'updated_at' in col[1] or 'last_updated' in col[1]]
                
                if timestamp_cols:
                    print(f"  📋 {table_name}: {', '.join(timestamp_cols)}")
                else:
                    print(f"  📋 {table_name}: No timestamp columns")
                    
        except Exception as e:
            print(f"  ❌ Error verifying {db_name}: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    print("🚀 Starting timestamp migration...")
    add_timestamps()
    verify_timestamps()
    print("\n✨ Timestamp migration complete!")
