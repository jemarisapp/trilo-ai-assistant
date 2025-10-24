#!/usr/bin/env python3
"""
Trilo Command Log Deduplication Script

Problem: Commands retry and create multiple log entries with the same timestamp
Solution: For each timestamp, keep only the best result (success > failure, deduplicate errors)
"""

import sqlite3
import os
from pathlib import Path

def deduplicate_command_logs():
    """Deduplicate command logs by timestamp"""
    
    # Database path
    db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not db_path.exists():
        print("❌ Command logs database not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🔍 Analyzing command logs for duplicates...")
        
        # Get all user_id groups and find duplicates within 2-second windows
        cursor.execute("""
            SELECT DISTINCT user_id FROM command_usage
        """)
        users = cursor.fetchall()
        
        duplicate_combinations = []
        
        for (user_id,) in users:
            print(f"DEBUG: Processing user {user_id[:8]}...")
            # Find all entries for this user
            cursor.execute("""
                SELECT id, timestamp, success, error_message, execution_time_ms, command_name
                FROM command_usage 
                WHERE user_id = ?
                ORDER BY timestamp ASC
            """, (user_id,))
            
            user_entries = cursor.fetchall()
            print(f"DEBUG: Found {len(user_entries)} entries for user {user_id[:8]}...")
            
            # Group entries that are within 3 seconds of each other AND have the same command_name
            grouped_entries = []
            current_group = []
            
            for i, entry in enumerate(user_entries):
                if not current_group:
                    current_group.append(entry)
                else:
                    # Check if this entry is within 3 seconds of the last entry in current group AND same command
                    last_timestamp = current_group[-1][1]  # timestamp is at index 1
                    last_command = current_group[-1][5]    # command_name is at index 5
                    current_timestamp = entry[1]
                    current_command = entry[5]
                    
                    # Calculate time difference in seconds
                    cursor.execute("""
                        SELECT ABS(strftime('%s', ?) - strftime('%s', ?))
                    """, (current_timestamp, last_timestamp))
                    time_diff = cursor.fetchone()[0]
                    
                    # Must be within 3 seconds AND same command name
                    if time_diff <= 3 and last_command == current_command:
                        current_group.append(entry)
                    else:
                        # Start a new group
                        if len(current_group) > 1:
                            grouped_entries.append(current_group)
                        current_group = [entry]
            
            # Don't forget the last group
            if len(current_group) > 1:
                grouped_entries.append(current_group)
            
            # Add to duplicate combinations
            for group in grouped_entries:
                timestamp = group[0][1]  # Use first entry's timestamp
                count = len(group)
                print(f"DEBUG: Found group with {count} entries for user {user_id[:8]}... at {timestamp}")
                duplicate_combinations.append((timestamp, user_id, count))
        
        if not duplicate_combinations:
            print("✅ No duplicate timestamp + user combinations found!")
            return
        
        print(f"📊 Found {len(duplicate_combinations)} timestamp + user combinations with duplicates")
        
        total_deleted = 0
        
        for timestamp, user_id, count in duplicate_combinations:
            print(f"\n🕐 Processing timestamp: {timestamp}, user: {user_id[:8]}... ({count} entries)")
            
            # Get all entries for this timestamp + user combination (with 2-second tolerance)
            cursor.execute("""
                SELECT id, success, error_message, execution_time_ms, command_name
                FROM command_usage 
                WHERE user_id = ? 
                AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                ORDER BY success DESC, execution_time_ms ASC
            """, (user_id, timestamp, timestamp))
            
            entries = cursor.fetchall()
            
            # Strategy 1: If ANY entry has success=1, delete all others
            successful_entries = [e for e in entries if e[1] == 1]  # success=1
            
            if successful_entries:
                print(f"  ✅ Found {len(successful_entries)} successful entry(ies) - keeping best success, deleting {count - len(successful_entries)} failures")
                
                # Keep the best successful entry (shortest execution time)
                best_success = min(successful_entries, key=lambda x: x[3])  # execution_time_ms
                keep_id = best_success[0]
                command_name = best_success[4]  # command_name is at index 4
                
                # Delete all other entries for this timestamp + user combination (with 3-second tolerance)
                cursor.execute("""
                    DELETE FROM command_usage 
                    WHERE user_id = ? 
                    AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                    AND id != ?
                """, (user_id, timestamp, timestamp, keep_id))
                deleted = cursor.rowcount
                total_deleted += deleted
                
                # Also clean up corresponding error logs for the deleted entries
                cursor.execute("""
                    DELETE FROM error_log 
                    WHERE server_id = (SELECT server_id FROM command_usage WHERE id = ?)
                    AND command_name = ?
                    AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                """, (keep_id, command_name, timestamp, timestamp))
                error_deleted = cursor.rowcount
                
                print(f"  🗑️  Deleted {deleted} duplicate entries, {error_deleted} error logs, kept success (ID: {keep_id})")
                
            else:
                # Strategy 2: All entries are failures - deduplicate errors
                print(f"  ❌ All {count} entries are failures - deduplicating errors")
                
                # Group by error message
                error_groups = {}
                for entry in entries:
                    error_msg = entry[2] or "No error message"
                    if error_msg not in error_groups:
                        error_groups[error_msg] = []
                    error_groups[error_msg].append(entry)
                
                print(f"  📝 Found {len(error_groups)} unique error types")
                
                # Keep one entry per unique error message
                for error_msg, error_entries in error_groups.items():
                    if len(error_entries) > 1:
                        # Keep the first entry, delete the rest
                        keep_entry = error_entries[0]
                        keep_id = keep_entry[0]
                        command_name = keep_entry[4]  # command_name is at index 4
                        
                        # Delete duplicates for this error type
                        error_ids = [e[0] for e in error_entries[1:]]
                        placeholders = ','.join(['?' for _ in error_ids])
                        cursor.execute(f"DELETE FROM command_usage WHERE id IN ({placeholders})", error_ids)
                        deleted = cursor.rowcount
                        total_deleted += deleted
                        
                        # Also clean up corresponding error logs for the deleted entries
                        cursor.execute("""
                            DELETE FROM error_log 
                            WHERE server_id = (SELECT server_id FROM command_usage WHERE id = ?)
                            AND command_name = ?
                            AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                            AND error_message = ?
                        """, (keep_id, command_name, timestamp, timestamp, error_msg))
                        error_deleted = cursor.rowcount
                        
                        print(f"    🗑️  Deleted {deleted} duplicates, {error_deleted} error logs of '{error_msg[:50]}...' (kept ID: {keep_id})")
                    else:
                        print(f"    ✅ Only 1 entry for '{error_msg[:50]}...' - keeping")
        
        # Commit changes
        conn.commit()
        
        print(f"\n🎉 Deduplication complete!")
        print(f"📊 Total entries removed: {total_deleted}")
        
        # Show final stats
        cursor.execute("SELECT COUNT(*) FROM command_usage")
        remaining = cursor.fetchone()[0]
        print(f"📈 Remaining entries: {remaining}")
        
        # Show success rate
        cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 1")
        successful = cursor.fetchone()[0]
        if remaining > 0:
            success_rate = (successful / remaining) * 100
            print(f"✅ Success rate: {success_rate:.1f}% ({successful}/{remaining})")
        
    except Exception as e:
        print(f"❌ Error during deduplication: {e}")
    finally:
        conn.close()

def show_duplicate_analysis():
    """Show analysis of duplicate timestamps before cleanup"""
    
    db_path = Path(__file__).parent.parent.parent / "databases" / "trilo_command_logs.db"
    
    if not db_path.exists():
        print("❌ Command logs database not found!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🔍 Duplicate Analysis:")
        print("=" * 50)
        
        # Show timestamps with duplicates (using 2-second tolerance)
        # Get all user_id groups and find duplicates within 2-second windows
        cursor.execute("""
            SELECT DISTINCT user_id FROM command_usage
        """)
        users = cursor.fetchall()
        
        duplicate_combinations = []
        
        for (user_id,) in users:
            # Find all entries for this user
            cursor.execute("""
                SELECT id, timestamp, success, error_message, execution_time_ms, command_name
                FROM command_usage 
                WHERE user_id = ?
                ORDER BY timestamp ASC
            """, (user_id,))
            
            user_entries = cursor.fetchall()
            
            # Group entries that are within 3 seconds of each other AND have the same command_name
            grouped_entries = []
            current_group = []
            
            for i, entry in enumerate(user_entries):
                if not current_group:
                    current_group.append(entry)
                else:
                    # Check if this entry is within 3 seconds of the last entry in current group AND same command
                    last_timestamp = current_group[-1][1]  # timestamp is at index 1
                    last_command = current_group[-1][5]    # command_name is at index 5
                    current_timestamp = entry[1]
                    current_command = entry[5]
                    
                    # Calculate time difference in seconds
                    cursor.execute("""
                        SELECT ABS(strftime('%s', ?) - strftime('%s', ?))
                    """, (current_timestamp, last_timestamp))
                    time_diff = cursor.fetchone()[0]
                    
                    # Must be within 3 seconds AND same command name
                    if time_diff <= 3 and last_command == current_command:
                        current_group.append(entry)
                    else:
                        # Start a new group
                        if len(current_group) > 1:
                            grouped_entries.append(current_group)
                        current_group = [entry]
            
            # Don't forget the last group
            if len(current_group) > 1:
                grouped_entries.append(current_group)
            
            # Add to duplicate combinations
            for group in grouped_entries:
                timestamp = group[0][1]  # Use first entry's timestamp
                count = len(group)
                successful = sum(1 for entry in group if entry[2] == 1)  # success is at index 2
                failed = count - successful
                duplicate_combinations.append((timestamp, user_id, count, successful, failed, group))
        
        duplicates = duplicate_combinations
        
        if not duplicates:
            print("✅ No duplicate timestamps found!")
            return
        
        print(f"📊 Found {len(duplicates)} timestamps with duplicates:")
        print()
        
        for timestamp, user_id, count, successful, failed, group in duplicates:
            print(f"🕐 {timestamp}: {count} entries ({successful} success, {failed} failed)")
            
            # Show details for this group
            for i, entry in enumerate(group, 1):
                success, error_message, execution_time_ms, command_name = entry[2], entry[3], entry[4], entry[5]
                status = "✅ SUCCESS" if success else "❌ FAILED"
                error_preview = (error_message[:30] + "...") if error_message and len(error_message) > 30 else (error_message or "No error")
                print(f"    {i}. {status} | {execution_time_ms}ms | {command_name} | {error_preview}")
            print()
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    finally:
        conn.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deduplicate Trilo command logs")
    parser.add_argument("--analyze", action="store_true", help="Show duplicate analysis without cleaning")
    parser.add_argument("--clean", action="store_true", help="Perform deduplication cleanup")
    
    args = parser.parse_args()
    
    if args.analyze:
        show_duplicate_analysis()
    elif args.clean:
        deduplicate_command_logs()
    else:
        print("🔍 Trilo Command Log Deduplication")
        print("=" * 40)
        print("Usage:")
        print("  --analyze    Show duplicate analysis")
        print("  --clean      Perform deduplication cleanup")
        print()
        print("Example:")
        print("  python3 data/scripts/trilo_deduplicate_logs.py --analyze")
        print("  python3 data/scripts/trilo_deduplicate_logs.py --clean")

if __name__ == "__main__":
    main()
