#!/usr/bin/env python3
"""
Trilo Successful Command Error Cleanup Script

This script cleans up error messages from successful commands and removes
Discord API errors that aren't meaningful for successful operations.
"""

import sqlite3
import sys
from pathlib import Path

# Allow importing project config
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.command_logger import CommandLogger

def cleanup_successful_errors():
    """Clean up error messages from successful commands"""
    
    logs_db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not logs_db_path.exists():
        print("❌ Command logs database not found.")
        return
    
    conn = sqlite3.connect(logs_db_path)
    cursor = conn.cursor()
    
    try:
        print("🧹 Cleaning up successful command errors...")
        
        # Show current stats
        cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 1 AND error_message IS NOT NULL")
        successful_with_errors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 0")
        failed_commands = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 1")
        successful_commands = cursor.fetchone()[0]
        
        print(f"📊 Current Stats:")
        print(f"  • Successful commands: {successful_commands}")
        print(f"  • Failed commands: {failed_commands}")
        print(f"  • Successful commands with error messages: {successful_with_errors}")
        
        if successful_with_errors == 0:
            print("✅ No successful commands with error messages found!")
            return
        
        # Clean up successful commands
        cursor.execute("""
            UPDATE command_usage 
            SET error_message = NULL 
            WHERE success = 1 AND error_message IS NOT NULL
        """)
        
        updated_count = cursor.rowcount
        print(f"✅ Cleaned up {updated_count} successful command error messages")
        
        # Remove Discord API error logs for successful commands
        cursor.execute("""
            DELETE FROM error_log 
            WHERE command_name IN (
                SELECT DISTINCT command_name 
                FROM command_usage 
                WHERE success = 1
            )
            AND error_type IN ('HTTPException', 'NotFound', 'Forbidden')
        """)
        
        error_deleted = cursor.rowcount
        print(f"✅ Removed {error_deleted} Discord API error logs for successful commands")
        
        # Show new stats
        cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 1 AND error_message IS NOT NULL")
        remaining_errors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 1")
        total_successful = cursor.fetchone()[0]
        
        error_rate = (remaining_errors / total_successful * 100) if total_successful > 0 else 0
        
        print(f"\n📊 New Stats:")
        print(f"  • Total successful commands: {total_successful}")
        print(f"  • Successful commands with errors: {remaining_errors}")
        print(f"  • Error rate for successful commands: {error_rate:.2f}%")
        
        conn.commit()
        print("\n🎉 Cleanup complete!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during cleanup: {e}")
    finally:
        conn.close()

def show_current_error_breakdown():
    """Show a breakdown of current errors"""
    
    logs_db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not logs_db_path.exists():
        print("❌ Command logs database not found.")
        return
    
    conn = sqlite3.connect(logs_db_path)
    cursor = conn.cursor()
    
    try:
        print("📊 Current Error Breakdown:")
        print("=" * 50)
        
        # Show error types
        cursor.execute("""
            SELECT error_type, COUNT(*) as count
            FROM error_log 
            GROUP BY error_type 
            ORDER BY count DESC
        """)
        
        error_types = cursor.fetchall()
        if error_types:
            print("🚨 Error Types:")
            for error_type, count in error_types:
                print(f"  • {error_type}: {count} occurrences")
        else:
            print("✅ No error logs found!")
        
        # Show successful vs failed commands
        cursor.execute("""
            SELECT 
                success,
                COUNT(*) as count,
                AVG(execution_time_ms) as avg_time
            FROM command_usage 
            GROUP BY success
        """)
        
        results = cursor.fetchall()
        print(f"\n📈 Command Success Rate:")
        for success, count, avg_time in results:
            status = "✅ Success" if success else "❌ Failed"
            print(f"  • {status}: {count} commands (avg: {avg_time:.1f}ms)")
        
    except Exception as e:
        print(f"❌ Error getting breakdown: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🧹 Trilo Successful Command Error Cleanup")
    print("=" * 50)
    
    show_current_error_breakdown()
    print()
    cleanup_successful_errors()
