#!/usr/bin/env python3
"""
Trilo Command Logging Setup Script

This script creates the command logging database and tables for tracking:
- Command usage statistics
- Server activity
- Error tracking
- Performance monitoring

All data is anonymized and follows privacy best practices.
"""

import sqlite3
import sys
from pathlib import Path

# Allow importing project config
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.database import DatabaseConfig

def setup_command_logging():
    """Create the command logging database and tables"""
    
    # Create logs database
    logs_db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    logs_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database if it exists to start fresh
    if logs_db_path.exists():
        logs_db_path.unlink()
        print("  🗑️ Removed existing logging database")
    
    conn = sqlite3.connect(logs_db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Setting up command logging database...")
        
        # Command usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_name TEXT NOT NULL,
                server_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                success BOOLEAN NOT NULL,
                execution_time_ms INTEGER,
                error_message TEXT,
                command_args TEXT
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_command_usage_timestamp ON command_usage(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_command_usage_server ON command_usage(server_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_command_usage_command ON command_usage(command_name)")
        print("  ✅ Created command_usage table")
        
        # Daily command statistics (aggregated)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_command_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                command_name TEXT NOT NULL,
                server_id TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                avg_execution_time_ms REAL,
                UNIQUE(date, command_name, server_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_command_stats(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_command ON daily_command_stats(command_name)")
        print("  ✅ Created daily_command_stats table")
        
        # Server activity tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_commands INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                most_used_command TEXT,
                last_activity DATETIME DEFAULT (datetime('now', 'localtime')),
                UNIQUE(server_id, date)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_server_activity_date ON server_activity(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_server_activity_server ON server_activity(server_id)")
        print("  ✅ Created server_activity table")
        
        # Error tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                command_name TEXT,
                server_id TEXT,
                user_id TEXT,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                resolved BOOLEAN DEFAULT FALSE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_log_type ON error_log(error_type)")
        print("  ✅ Created error_log table")
        
        
        conn.commit()
        print("✅ Command logging database setup complete!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error setting up command logging: {e}")
        raise
    finally:
        conn.close()

def verify_setup():
    """Verify the logging database was created correctly"""
    logs_db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not logs_db_path.exists():
        print("❌ Logging database not found!")
        return False
    
    conn = sqlite3.connect(logs_db_path)
    cursor = conn.cursor()
    
    try:
        print("\n🔍 Verifying command logging setup...")
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'command_usage', 'daily_command_stats', 
            'server_activity', 'error_log'
        ]
        
        for table in expected_tables:
            if table in tables:
                print(f"  ✅ {table} table exists")
            else:
                print(f"  ❌ {table} table missing")
                return False
        
        print("✅ All logging tables verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying setup: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Setting up Trilo Command Logging System...")
    setup_command_logging()
    verify_setup()
    print("\n✨ Command logging system ready!")