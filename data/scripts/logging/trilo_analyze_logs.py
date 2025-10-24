#!/usr/bin/env python3
"""
Trilo Command Log Analysis Script

This script analyzes command usage logs to provide insights into:
- Most popular commands
- Server activity patterns
- Performance metrics
- Error tracking
- Usage statistics

All data is anonymized and privacy-compliant.
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Allow importing project config
project_root = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))
from utils.command_logger_simple import get_command_stats

def analyze_command_usage(days: int = 7):
    """Analyze command usage patterns"""
    logs_db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not logs_db_path.exists():
        print("❌ Command logs database not found. Run trilo_setup_command_logging.py first.")
        return
    
    conn = sqlite3.connect(logs_db_path)
    cursor = conn.cursor()
    
    try:
        print(f"📊 Command Usage Analysis (Last {days} days)")
        print("=" * 50)
        
        # Overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_commands,
                COUNT(DISTINCT server_id) as unique_servers,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(execution_time_ms) as avg_execution_time,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
        """.format(days))
        
        stats = cursor.fetchone()
        total_commands, unique_servers, unique_users, avg_time, errors = stats
        
        print(f"📈 Overall Statistics:")
        print(f"  • Total Commands: {total_commands:,}")
        print(f"  • Unique Servers: {unique_servers:,}")
        print(f"  • Unique Users: {unique_users:,}")
        print(f"  • Average Execution Time: {avg_time:.2f}ms")
        print(f"  • Error Rate: {(errors/total_commands*100):.2f}%" if total_commands > 0 else "  • Error Rate: 0%")
        print()
        
        # Top commands
        print("🔥 Most Popular Commands:")
        cursor.execute("""
            SELECT command_name, COUNT(*) as usage_count
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY command_name 
            ORDER BY usage_count DESC 
            LIMIT 10
        """.format(days))
        
        for i, (command, count) in enumerate(cursor.fetchall(), 1):
            print(f"  {i:2d}. {command:<25} {count:>6,} uses")
        print()
        
        # Server activity
        print("🏠 Server Activity:")
        cursor.execute("""
            SELECT 
                server_id,
                COUNT(*) as command_count,
                COUNT(DISTINCT user_id) as unique_users,
                MAX(timestamp) as last_activity
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY server_id 
            ORDER BY command_count DESC 
            LIMIT 10
        """.format(days))
        
        for i, (server_id, count, users, last_activity) in enumerate(cursor.fetchall(), 1):
            print(f"  {i:2d}. Server {server_id[:8]}... {count:>6,} commands, {users} users, last: {last_activity}")
        print()
        
        # Performance analysis
        print("⚡ Performance Analysis:")
        cursor.execute("""
            SELECT 
                command_name,
                AVG(execution_time_ms) as avg_time,
                MAX(execution_time_ms) as max_time,
                MIN(execution_time_ms) as min_time,
                COUNT(*) as sample_count
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
            AND execution_time_ms IS NOT NULL
            GROUP BY command_name 
            HAVING COUNT(*) >= 5
            ORDER BY avg_time DESC 
            LIMIT 10
        """.format(days))
        
        for command, avg_time, max_time, min_time, samples in cursor.fetchall():
            print(f"  • {command:<25} avg: {avg_time:>6.1f}ms (min: {min_time:>4.0f}ms, max: {max_time:>4.0f}ms, samples: {samples:>3})")
        print()
        
        # Error analysis
        print("🚨 Error Analysis:")
        cursor.execute("""
            SELECT 
                error_type,
                COUNT(*) as error_count,
                command_name
            FROM error_log 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY error_type, command_name
            ORDER BY error_count DESC 
            LIMIT 10
        """.format(days))
        
        error_results = cursor.fetchall()
        if error_results:
            for error_type, count, command in error_results:
                print(f"  • {error_type:<20} in {command:<20} ({count} occurrences)")
        else:
            print("  • No errors recorded in the specified period")
        print()
        
        # Daily usage trends
        print("📅 Daily Usage Trends:")
        cursor.execute("""
            SELECT 
                date(timestamp) as date,
                COUNT(*) as command_count,
                COUNT(DISTINCT server_id) as active_servers
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY date(timestamp) 
            ORDER BY date(timestamp) DESC
        """.format(days))
        
        for date, count, servers in cursor.fetchall():
            print(f"  • {date}: {count:>4,} commands from {servers:>2} servers")
        
    except Exception as e:
        print(f"❌ Error analyzing logs: {e}")
    finally:
        conn.close()

def show_recent_errors(hours: int = 24):
    """Show recent errors for debugging"""
    logs_db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not logs_db_path.exists():
        print("❌ Command logs database not found.")
        return
    
    conn = sqlite3.connect(logs_db_path)
    cursor = conn.cursor()
    
    try:
        print(f"🚨 Recent Errors (Last {hours} hours)")
        print("=" * 50)
        
        cursor.execute("""
            SELECT 
                timestamp,
                error_type,
                command_name,
                error_message,
                server_id
            FROM error_log 
            WHERE timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp DESC 
            LIMIT 20
        """.format(hours))
        
        errors = cursor.fetchall()
        if errors:
            for timestamp, error_type, command, message, server_id in errors:
                print(f"🕐 {timestamp}")
                print(f"   Type: {error_type}")
                print(f"   Command: {command}")
                print(f"   Server: {server_id[:8]}...")
                print(f"   Message: {message[:100]}{'...' if len(message) > 100 else ''}")
                print()
        else:
            print("✅ No errors in the specified period!")
        
    except Exception as e:
        print(f"❌ Error retrieving errors: {e}")
    finally:
        conn.close()

def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up old logs"""
    from utils.command_logger import cleanup_logs
    print(f"🧹 Cleaning up logs older than {days_to_keep} days...")
    cleanup_logs(days_to_keep)
    print("✅ Log cleanup complete!")

def cleanup_successful_errors():
    """Clean up error messages from successful commands"""
    from utils.command_logger import CommandLogger
    logger = CommandLogger()
    print("🧹 Cleaning up successful command errors...")
    logger.cleanup_successful_command_errors()
    print("✅ Successful command error cleanup complete!")

def main():
    parser = argparse.ArgumentParser(description="Analyze Trilo command logs")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    parser.add_argument("--errors", type=int, default=24, help="Show errors from last N hours (default: 24)")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up logs older than N days")
    parser.add_argument("--cleanup-errors", action="store_true", help="Clean up error messages from successful commands")
    parser.add_argument("--stats-only", action="store_true", help="Show only basic statistics")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_old_logs(args.cleanup)
        return
    
    if args.cleanup_errors:
        cleanup_successful_errors()
        return
    
    if args.stats_only:
        stats = get_command_stats(args.days)
        if stats:
            print("📊 Quick Stats:")
            print(f"  • Total Commands: {stats['overall']['total_commands']:,}")
            print(f"  • Unique Servers: {stats['overall']['unique_servers']:,}")
            print(f"  • Error Rate: {stats['overall']['error_rate_percent']:.2f}%")
            print(f"  • Avg Execution Time: {stats['overall']['avg_execution_time_ms']:.2f}ms")
        return
    
    print("🔍 Trilo Command Log Analysis")
    print("=" * 50)
    
    analyze_command_usage(args.days)
    show_recent_errors(args.errors)
    
    print("💡 Tips:")
    print("  • Use --days N to analyze different time periods")
    print("  • Use --errors N to see recent errors")
    print("  • Use --cleanup N to remove old logs")
    print("  • Use --stats-only for quick overview")

if __name__ == "__main__":
    main()
