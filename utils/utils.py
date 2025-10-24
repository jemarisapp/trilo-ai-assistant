# File: utils/utils.py

import os
import sqlite3
import discord
from discord import app_commands
from config.database import DatabaseConfig

# --------------------
# Path & DB Management
# --------------------

def get_db_connection(db_name: str) -> sqlite3.Connection:
    """Get a database connection using the centralized configuration"""
    try:
        db_path = DatabaseConfig.get_db_path(db_name)
        conn = sqlite3.connect(db_path)
        # Enable foreign keys and set timeout
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
        return conn
    except Exception as e:
        print(f"Error connecting to database {db_name}: {e}")
        raise

# --------------------
# Server Registration Helpers
# --------------------
    
def ensure_default_commissioner_roles(server_id: str):
    from utils import get_db_connection  # avoid circular import
    with get_db_connection("keys") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM server_config WHERE server_id = ? AND key = 'commissioner_roles'
        """, (server_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO server_config (server_id, key, value)
                VALUES (?, 'commissioner_roles', 'Commish,Commissioners,Commissioner')
            """, (server_id,))
            conn.commit()


# --------------------
# Matchup Status Helpers
# --------------------

STATUS_SUFFIXES = {"✅", "🎲", "☑️"}

def strip_status_suffix(name: str) -> str:
    for suffix in STATUS_SUFFIXES:
        if name.endswith(f"-{suffix}"):
            return name[:-(len(suffix) + 1)]
    return name

def apply_status_suffix(base: str, emoji: str) -> str:
    return f"{base}-{emoji}"

# --------------------
# Team Name Helpers
# --------------------

def format_team_name(name: str) -> str:
    special_cases = {
        "texas a&m": "Texas A&M",
        "texas-am": "Texas A&M",
    }

    name = name.lower().strip()
    if name in special_cases:
        return special_cases[name]

    acronyms = {
        "usc", "lsu", "ucla", "fiu", "fau", "smu", "byu", "tcu",
        "unlv", "utsa", "uab", "usf", "ucf", "umass", "uconn"
    }

    words = name.split()
    return " ".join([word.upper() if word in acronyms else word.capitalize() for word in words])

def clean_team_key(raw: str) -> str:
    raw = raw.lower().strip()
    if raw.startswith("fw-"):
        raw = raw[3:]
    key = raw.replace("-", " ")
    return {"texas am": "texas a&m"}.get(key, key)


