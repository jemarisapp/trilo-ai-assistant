#!/usr/bin/env python3
"""
Trilo Auto Cleanup Script
Automatically runs deduplication and cleanup tasks in the background
"""

import sqlite3
import time
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.command_logger import CommandLogger

def auto_cleanup():
    """Run automatic cleanup tasks"""
    try:
        print("🧹 Starting automatic cleanup...")
        
        # Initialize command logger
        command_logger = CommandLogger()
        
        # Clean up successful command errors
        print("  🔧 Cleaning up Discord API errors...")
        command_logger.cleanup_successful_command_errors()
        
        # Run deduplication
        print("  🔄 Running deduplication...")
        from data.scripts.trilo_deduplicate_logs import deduplicate_command_logs
        deduplicate_command_logs()
        
        # Update daily stats
        print("  📊 Updating daily statistics...")
        command_logger.update_daily_stats()
        
        print("✅ Automatic cleanup completed!")
        
    except Exception as e:
        print(f"❌ Error during automatic cleanup: {e}")

def main():
    """Main function for running cleanup"""
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # Run as daemon (continuous)
        print("🔄 Starting auto-cleanup daemon (press Ctrl+C to stop)...")
        try:
            while True:
                auto_cleanup()
                print(f"⏰ Next cleanup in 5 minutes...")
                time.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            print("\n🛑 Auto-cleanup daemon stopped")
    else:
        # Run once
        auto_cleanup()

if __name__ == "__main__":
    main()
