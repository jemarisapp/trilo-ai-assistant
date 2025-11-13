"""
Trilo Command Logging Utilities

This module provides utilities for logging command usage, errors, and performance
while maintaining user privacy and following best practices.

Privacy Features:
- No personal data (names, messages) are logged
- Only anonymized usage statistics
- Server IDs and User IDs are hashed for additional privacy
- Automatic data retention and cleanup
"""

import sqlite3
import time
import json
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import wraps
import traceback
import discord

class CommandLogger:
    """Handles all command logging operations with privacy protection"""
    
    def __init__(self):
        self.logs_db_path = Path(__file__).parent.parent / "data" / "databases" / "trilo_command_logs.db"
        self.logs_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _hash_id(self, id_string: str) -> str:
        """Hash an ID for additional privacy protection"""
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]
    
    def _sanitize_args(self, args: Dict[str, Any]) -> str:
        """Sanitize command arguments to remove sensitive data"""
        sanitized = {}
        
        # Only keep non-sensitive argument types
        safe_types = (str, int, float, bool, type(None))
        
        for key, value in args.items():
            if isinstance(value, safe_types):
                # Remove any potential personal identifiers
                if isinstance(value, str):
                    # Remove mentions, channels, and other Discord-specific data
                    if not any(x in str(value).lower() for x in ['@', '#', '<', '>']):
                        sanitized[key] = value
                else:
                    sanitized[key] = value
        
        return json.dumps(sanitized) if sanitized else "{}"
    
    def log_command_usage(
        self, 
        command_name: str, 
        server_id: str, 
        user_id: str, 
        success: bool, 
        execution_time_ms: int,
        error_message: Optional[str] = None,
        command_args: Optional[Dict[str, Any]] = None
    ):
        """Log a command usage event"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Hash IDs for privacy
            hashed_server_id = self._hash_id(server_id)
            hashed_user_id = self._hash_id(user_id)
            
            # Sanitize arguments
            sanitized_args = self._sanitize_args(command_args or {})
            
            # Get current timestamp for deduplication
            cursor.execute("SELECT datetime('now', 'localtime')")
            current_timestamp = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO command_usage 
                (command_name, server_id, user_id, success, execution_time_ms, 
                 error_message, command_args, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                command_name, hashed_server_id, hashed_user_id, success,
                execution_time_ms, error_message, sanitized_args, current_timestamp
            ))
            
            conn.commit()
            conn.close()
            
            # Note: Automatic deduplication disabled - use manual scripts for cleanup
            # Run: python3 data/scripts/trilo_deduplicate_logs.py --clean
            
        except Exception as e:
            print(f"Warning: Failed to log command usage: {e}")
    
    def log_error(
        self, 
        error_type: str, 
        error_message: str, 
        command_name: Optional[str] = None,
        server_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stack_trace: Optional[str] = None
    ):
        """Log an error event"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Hash IDs for privacy
            hashed_server_id = self._hash_id(server_id) if server_id else None
            hashed_user_id = self._hash_id(user_id) if user_id else None
            
            cursor.execute("""
                INSERT INTO error_log 
                (error_type, command_name, server_id, user_id, error_message, 
                 stack_trace, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (
                error_type, command_name, hashed_server_id, hashed_user_id,
                error_message, stack_trace
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Warning: Failed to log error: {e}")
    
    
    def update_daily_stats(self):
        """Update daily aggregated statistics"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Get yesterday's date
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Aggregate command usage for yesterday
            cursor.execute("""
                INSERT OR REPLACE INTO daily_command_stats 
                (date, command_name, server_id, usage_count, success_count, error_count, avg_execution_time_ms)
                SELECT 
                    date(timestamp) as date,
                    command_name,
                    server_id,
                    COUNT(*) as usage_count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count,
                    AVG(execution_time_ms) as avg_execution_time_ms
                FROM command_usage 
                WHERE date(timestamp) = ?
                GROUP BY date(timestamp), command_name, server_id
            """, (yesterday,))
            
            # Update server activity
            cursor.execute("""
                INSERT OR REPLACE INTO server_activity 
                (server_id, date, total_commands, unique_users, most_used_command, last_activity)
                SELECT 
                    server_id,
                    date(timestamp) as date,
                    COUNT(*) as total_commands,
                    COUNT(DISTINCT user_id) as unique_users,
                    (SELECT command_name FROM command_usage cu2 
                     WHERE cu2.server_id = cu.server_id AND date(cu2.timestamp) = date(cu.timestamp)
                     GROUP BY command_name ORDER BY COUNT(*) DESC LIMIT 1) as most_used_command,
                    MAX(timestamp) as last_activity
                FROM command_usage cu
                WHERE date(timestamp) = ?
                GROUP BY server_id, date(timestamp)
            """, (yesterday,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Warning: Failed to update daily stats: {e}")
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove logs older than specified days"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            
            # Clean up old command usage logs
            cursor.execute("DELETE FROM command_usage WHERE date(timestamp) < ?", (cutoff_date,))
            usage_deleted = cursor.rowcount
            
            
            # Keep error logs longer (90 days)
            error_cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            cursor.execute("DELETE FROM error_log WHERE date(timestamp) < ?", (error_cutoff,))
            error_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"🧹 Cleaned up {usage_deleted} usage logs, {error_deleted} error logs")
            
        except Exception as e:
            print(f"Warning: Failed to cleanup old logs: {e}")
    
    def cleanup_successful_command_errors(self):
        """Remove error messages from successful commands and fix Discord API error false failures"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # First, fix commands that failed due to Discord API errors but should be considered successful
            cursor.execute("""
                UPDATE command_usage 
                SET success = 1, error_message = NULL 
                WHERE success = 0 
                AND error_message LIKE '%10062%'
            """)
            
            fixed_commands = cursor.rowcount
            
            # Also fix "already acknowledged" errors
            cursor.execute("""
                UPDATE command_usage 
                SET success = 1, error_message = NULL 
                WHERE success = 0 
                AND (error_message LIKE '%already acknowledged%' OR error_message LIKE '%already been acknowledged%')
            """)
            
            fixed_acknowledged = cursor.rowcount
            
            # Update other successful commands to have NULL error messages
            cursor.execute("""
                UPDATE command_usage 
                SET error_message = NULL 
                WHERE success = 1 AND error_message IS NOT NULL
            """)
            
            updated_count = cursor.rowcount
            
            # Remove error logs for Discord API errors
            cursor.execute("""
                DELETE FROM error_log 
                WHERE error_type IN ('HTTPException', 'NotFound', 'Forbidden')
                AND (error_message LIKE '%10062%' 
                     OR error_message LIKE '%unknown interaction%'
                     OR error_message LIKE '%already acknowledged%'
                     OR error_message LIKE '%already been acknowledged%')
            """)
            
            error_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"🧹 Fixed {fixed_commands} commands with error code 10062 (marked as successful)")
            print(f"🧹 Fixed {fixed_acknowledged} commands with 'already acknowledged' errors")
            print(f"🧹 Cleaned up {updated_count} successful command error messages")
            print(f"🧹 Removed {error_deleted} Discord API error logs")
            
        except Exception as e:
            print(f"Warning: Failed to cleanup successful command errors: {e}")
    
    def startup_cleanup(self):
        """Run comprehensive cleanup when bot starts up"""
        try:
            print("🚀 Running startup cleanup...")
            
            # Clean up Discord API errors
            self.cleanup_successful_command_errors()
            
            # Run deduplication
            from data.scripts.trilo_deduplicate_logs import deduplicate_command_logs
            deduplicate_command_logs()
            
            # Update daily stats
            self.update_daily_stats()
            
            print("✅ Startup cleanup completed!")
            
        except Exception as e:
            print(f"Warning: Failed to run startup cleanup: {e}")
    
    def _auto_deduplicate_timestamp_user(self, timestamp: str, user_id: str):
        """Auto-deduplicate entries for the same timestamp and user (with +/- 2 second tolerance)"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Check if there are multiple entries for this timestamp + user combination (with 2-second tolerance)
            cursor.execute("""
                SELECT COUNT(*) FROM command_usage 
                WHERE user_id = ? 
                AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
            """, (user_id, timestamp, timestamp))
            count = cursor.fetchone()[0]
            
            if count <= 1:
                conn.close()
                return
            
            # Get all entries for this timestamp + user combination (with 2-second tolerance)
            cursor.execute("""
                SELECT id, success, error_message, execution_time_ms, timestamp
                FROM command_usage 
                WHERE user_id = ? 
                AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                ORDER BY success DESC, execution_time_ms ASC
            """, (user_id, timestamp, timestamp))
            
            entries = cursor.fetchall()
            
            # If ANY entry has success=1, delete all others
            successful_entries = [e for e in entries if e[1] == 1]
            
            if successful_entries:
                # Keep the best successful entry
                best_success = min(successful_entries, key=lambda x: x[3])
                keep_id = best_success[0]
                
                # Delete all other entries for this timestamp + user combination (with 2-second tolerance)
                cursor.execute("""
                    DELETE FROM command_usage 
                    WHERE user_id = ? 
                    AND timestamp BETWEEN datetime(?, '-3 seconds') AND datetime(?, '+3 seconds')
                    AND id != ?
                """, (user_id, timestamp, timestamp, keep_id))
                conn.commit()
            else:
                # All failures - deduplicate by error message
                error_groups = {}
                for entry in entries:
                    error_msg = entry[2] or "No error message"
                    if error_msg not in error_groups:
                        error_groups[error_msg] = []
                    error_groups[error_msg].append(entry)
                
                # Keep one entry per unique error
                for error_msg, error_entries in error_groups.items():
                    if len(error_entries) > 1:
                        keep_entry = error_entries[0]
                        keep_id = keep_entry[0]
                        
                        # Delete duplicates
                        error_ids = [e[0] for e in error_entries[1:]]
                        if error_ids:
                            placeholders = ','.join(['?' for _ in error_ids])
                            cursor.execute(f"DELETE FROM command_usage WHERE id IN ({placeholders})", error_ids)
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            # Don't print warnings for auto-deduplication to avoid spam
            pass
    
    def _cleanup_recent_user_entries(self, user_id: str, cleanup_window_seconds: int = 30):
        """Clean up recent duplicates for a user (runs on every command) with 2-second tolerance"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Find all recent entries for this user
            cursor.execute("""
                SELECT id, timestamp, success, error_message, execution_time_ms, command_name
                FROM command_usage 
                WHERE user_id = ? 
                AND timestamp >= datetime('now', 'localtime', '-{} seconds')
                ORDER BY timestamp ASC
            """.format(cleanup_window_seconds), (user_id,))
            
            user_entries = cursor.fetchall()
            
            if len(user_entries) <= 1:
                conn.close()
                return
            
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
            
            # Clean up each group
            for group in grouped_entries:
                if len(group) > 1:
                    # Use the first entry's timestamp for deduplication
                    timestamp = group[0][1]
                    self._auto_deduplicate_timestamp_user(timestamp, user_id)
            
            conn.close()
            
        except Exception as e:
            # Don't print warnings for cleanup to avoid spam
            pass
    
    def _periodic_cleanup_user(self, user_id: str, cleanup_window_minutes: int = 5):
        """Periodically clean up recent duplicates for a user (runs occasionally)"""
        try:
            # Only run cleanup occasionally (30% chance) to avoid performance impact
            import random
            if random.random() > 0.3:  # 70% chance to skip
                return
                
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Find recent duplicates for this user in the last few minutes (with 2-second tolerance)
            cursor.execute("""
                SELECT timestamp, COUNT(*) as count
                FROM command_usage 
                WHERE user_id = ? 
                AND timestamp >= datetime('now', 'localtime', '-{} minutes')
                GROUP BY timestamp
                HAVING COUNT(*) > 1
            """.format(cleanup_window_minutes), (user_id,))
            
            recent_duplicates = cursor.fetchall()
            
            if recent_duplicates:
                # Clean up recent duplicates
                for timestamp, count in recent_duplicates:
                    if count > 1:
                        self._auto_deduplicate_timestamp_user(timestamp, user_id)
            
            conn.close()
            
        except Exception as e:
            # Don't print warnings for periodic cleanup
            pass
    
    def should_log_error(self, error_type: str, error_message: str, command_name: str) -> bool:
        """Determine if an error should be logged based on type and context"""
        
        # Don't log specific Discord API errors that are common and not real failures
        if error_type == 'HTTPException':
            # Don't log "unknown interaction" errors (error code 10062)
            if 'unknown interaction' in error_message.lower() or '10062' in error_message:
                return False
            
            # Don't log "already acknowledged" errors
            if 'already acknowledged' in error_message.lower() or 'already been acknowledged' in error_message.lower():
                return False
            
            # Don't log interaction timeout errors
            if 'interaction' in error_message.lower() and 'timeout' in error_message.lower():
                return False
            
            # Log other HTTPException errors as they might be meaningful
            return True
        
        # Don't log "already acknowledged" errors regardless of error type
        if 'already acknowledged' in error_message.lower() or 'already been acknowledged' in error_message.lower():
            return False
        
        # Don't log NotFound and Forbidden errors (usually Discord API quirks)
        if error_type in ['NotFound', 'Forbidden']:
            return False
        
        # Don't log timeout errors for quick commands
        if 'timeout' in error_message.lower() and command_name in ['settings view', 'teams who-has']:
            return False
        
        # Log everything else
        return True

# Global logger instance
command_logger = CommandLogger()

async def safe_respond(interaction, message: str, ephemeral: bool = False):
    """Safely send a response to an interaction, checking if already responded"""
    try:
        if not interaction.response.is_done():
            return await interaction.response.send_message(message, ephemeral=ephemeral)
        else:
            return await interaction.followup.send(message, ephemeral=ephemeral)
    except discord.HTTPException as e:
        # Only log meaningful errors, not Discord API quirks like 10062
        error_message = f"Failed to send response: {str(e)}"
        if command_logger.should_log_error("HTTPException", error_message, "unknown"):
            command_logger.log_error(
                error_type="HTTPException",
                error_message=error_message,
                command_name="unknown",
                server_id=str(interaction.guild.id) if interaction.guild else "unknown",
                user_id=str(interaction.user.id) if hasattr(interaction, 'user') else "unknown"
            )
        return None

def log_command(command_name: str):
    """
    Decorator to automatically log command usage
    
    Usage:
    @log_command("teams assign-user")
    async def assign_user_to_team_unified(interaction, ...):
        # command implementation
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                # Extract interaction from args (first argument is usually interaction)
                interaction = args[0] if args else None
                server_id = str(interaction.guild.id) if interaction and hasattr(interaction, 'guild') else "unknown"
                user_id = str(interaction.user.id) if interaction and hasattr(interaction, 'user') else "unknown"
                
                # Execute the command with timeout protection
                import asyncio
                
                # Commands that need longer timeouts (multi-image processing, multi-channel edits)
                # Heavier flows touch many channels or call external APIs and can exceed 25s
                long_timeout_commands = [
                    # Image extraction / creation flows
                    "matchups create-from-image",
                    "matchups cfb-create-from-image",
                    "matchups nfl-create-from-image",
                    "matchups create-from-text",
                    "matchups create",
                    # Category-wide operations
                    "matchups tag-users",
                    "matchups sync-records",
                    "matchups make-public",
                    "matchups make-private",
                    "matchups add-game-status",
                    # Deletions in large categories may take longer
                    "matchups delete",
                ]
                
                # Use longer timeout for image processing commands (120 seconds = 2 minutes)
                # This allows time for processing multiple images + network delays
                # Regular commands get 25 seconds
                # Discord allows up to 15 minutes for deferred interactions, but we cap at 2 min to prevent hung commands
                timeout = 120.0 if command_name in long_timeout_commands else 25.0
                
                try:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    return result
                except asyncio.TimeoutError:
                    # Handle timeout gracefully
                    if interaction and not interaction.response.is_done():
                        await interaction.response.send_message("⏰ Command timed out. Please try again.", ephemeral=True)
                    raise
                
            except Exception as e:
                error_message = str(e)
                
                # Check if it's a Discord API error that we should handle gracefully
                if isinstance(e, (discord.HTTPException, discord.NotFound, discord.Forbidden)):
                    # Check if this is a Discord API quirk that shouldn't be logged as a failure
                    if not command_logger.should_log_error(type(e).__name__, error_message, command_name):
                        # This is a Discord API quirk (like 10062), treat as successful
                        success = True
                        error_message = None
                    else:
                        # This is a meaningful Discord API error
                        success = False
                        command_logger.log_error(
                            error_type=type(e).__name__,
                            error_message=error_message,
                            command_name=command_name,
                            server_id=server_id,
                            user_id=user_id,
                            stack_trace=traceback.format_exc()
                        )
                    # Don't re-raise Discord API errors to prevent double error logging
                    return None
                else:
                    # Log other errors and re-raise
                    success = False
                    command_logger.log_error(
                        error_type=type(e).__name__,
                        error_message=error_message,
                        command_name=command_name,
                        server_id=server_id,
                        user_id=user_id,
                        stack_trace=traceback.format_exc()
                    )
                    raise
                
            finally:
                # Calculate execution time
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                # Log command usage
                command_logger.log_command_usage(
                    command_name=command_name,
                    server_id=server_id,
                    user_id=user_id,
                    success=success,
                    execution_time_ms=execution_time_ms,
                    error_message=error_message
                )
                
        
        return wrapper
    return decorator

def get_command_stats(days: int = 7) -> Dict[str, Any]:
    """Get command usage statistics for the last N days"""
    try:
        conn = sqlite3.connect(command_logger.logs_db_path)
        cursor = conn.cursor()
        
        # Get overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_commands,
                COUNT(DISTINCT server_id) as unique_servers,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(execution_time_ms) as avg_execution_time
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
        """.format(days))
        
        overall_stats = cursor.fetchone()
        
        # Get top commands
        cursor.execute("""
            SELECT command_name, COUNT(*) as usage_count
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY command_name 
            ORDER BY usage_count DESC 
            LIMIT 10
        """.format(days))
        
        top_commands = cursor.fetchall()
        
        # Get error rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
            FROM command_usage 
            WHERE date(timestamp) >= date('now', '-{} days')
        """.format(days))
        
        error_stats = cursor.fetchone()
        error_rate = (error_stats[1] / error_stats[0] * 100) if error_stats[0] > 0 else 0
        
        conn.close()
        
        return {
            'overall': {
                'total_commands': overall_stats[0],
                'unique_servers': overall_stats[1], 
                'unique_users': overall_stats[2],
                'avg_execution_time_ms': round(overall_stats[3], 2) if overall_stats[3] else 0,
                'error_rate_percent': round(error_rate, 2)
            },
            'top_commands': [{'command': cmd[0], 'usage': cmd[1]} for cmd in top_commands]
        }
        
    except Exception as e:
        print(f"Error getting command stats: {e}")
        return {}

# Auto-update daily stats (call this periodically)
def update_daily_stats():
    """Update daily aggregated statistics - call this once per day"""
    command_logger.update_daily_stats()

# Auto-cleanup old logs (call this periodically)
def cleanup_logs(days_to_keep: int = 30):
    """Clean up old logs - call this periodically"""
    command_logger.cleanup_old_logs(days_to_keep)