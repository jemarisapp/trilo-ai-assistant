import sqlite3
import os

# Set database file name and path
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "bot_data_power_rankings.db")

# Create and connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Table for ranking submissions
cursor.execute("""
CREATE TABLE IF NOT EXISTS ranking_submissions (
    submission_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    server_id         TEXT NOT NULL,
    season            TEXT NOT NULL,
    week              TEXT NOT NULL,
    rank_1            INTEGER,
    rank_2            INTEGER,
    rank_3            INTEGER,
    rank_4            INTEGER,
    rank_5            INTEGER,
    rank_6            INTEGER,
    rank_7            INTEGER,
    rank_8            INTEGER,
    rank_9            INTEGER,
    rank_10           INTEGER,
    timestamp         DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

# 2. Table for currently active week (per server)
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_week (
    server_id TEXT PRIMARY KEY,
    season    TEXT NOT NULL,
    week      TEXT NOT NULL
);
""")

# 3. Table for all weeks set by commissioners
cursor.execute("""
CREATE TABLE IF NOT EXISTS available_weeks (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id TEXT NOT NULL,
    season    TEXT NOT NULL,
    week      TEXT NOT NULL,
    UNIQUE(server_id, season, week)
);
""")

# Commit and close
conn.commit()
conn.close()

print("✅ Power rankings database setup complete.")
