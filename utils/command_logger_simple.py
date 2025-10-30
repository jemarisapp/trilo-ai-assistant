"""
Simplified Trilo Command Logging Utilities

This module provides utilities for logging command usage, errors, and performance
without requiring discord dependencies for testing.
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
            
            cursor.execute("""
                INSERT INTO command_usage 
                (command_name, server_id, user_id, success, execution_time_ms, 
                 error_message, command_args, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (
                command_name, hashed_server_id, hashed_user_id, success,
                execution_time_ms, error_message, sanitized_args
            ))
            
            conn.commit()
            conn.close()
            
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
    
    def log_performance(
        self, 
        command_name: str, 
        server_id: str, 
        execution_time_ms: int
    ):
        """Log performance metrics"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
            cursor = conn.cursor()
            
            # Get memory usage (simplified)
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
            except ImportError:
                memory_mb = 0.0
            
            # Hash server ID for privacy
            hashed_server_id = self._hash_id(server_id)
            
            cursor.execute("""
                INSERT INTO performance_metrics 
                (command_name, server_id, execution_time_ms, memory_usage_mb, timestamp)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            """, (command_name, hashed_server_id, execution_time_ms, memory_mb))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Warning: Failed to log performance: {e}")
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get command usage statistics for the last N days"""
        try:
            conn = sqlite3.connect(self.logs_db_path)
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

# Global logger instance
command_logger = CommandLogger()

def get_command_stats(days: int = 7) -> Dict[str, Any]:
    """Get command usage statistics"""
    return command_logger.get_stats(days)

