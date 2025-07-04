"""Database utility functions for SQLite."""

import sqlite3
import os
from typing import Dict, Any

DB_PATH = None

def get_db_path(config: Dict[str, Any]) -> str:
    """Gets the database path from config, ensuring it's a singleton."""
    global DB_PATH
    if DB_PATH is None:
        output_dir = config["output"]["directory"]
        db_file = config["output"]["database_file"]
        DB_PATH = os.path.join(output_dir, db_file)
    return DB_PATH

def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_schema(conn: sqlite3.Connection):
    """Create the database schema if it doesn't exist."""
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS stories (
            story_id TEXT PRIMARY KEY,
            batch_number INTEGER NOT NULL,
            piece TEXT NOT NULL,
            prompt TEXT,
            model_used TEXT,
            rating REAL,
            rd REAL,
            sigma REAL,
            created_at TEXT,
            generation_type TEXT,
            parent_story_id TEXT,
            matches_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            previous_batch_rating REAL,
            FOREIGN KEY (parent_story_id) REFERENCES stories (story_id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            story1_id TEXT NOT NULL,
            story2_id TEXT NOT NULL,
            winner_id TEXT NOT NULL,
            story1_rating_before REAL,
            story2_rating_before REAL,
            story1_rating_after REAL,
            story2_rating_after REAL,
            reasoning TEXT,
            timestamp TEXT,
            FOREIGN KEY (story1_id) REFERENCES stories (story_id),
            FOREIGN KEY (story2_id) REFERENCES stories (story_id),
            FOREIGN KEY (winner_id) REFERENCES stories (story_id)
        );
        
        CREATE TABLE IF NOT EXISTS human_preferences (
            preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            story1_id TEXT NOT NULL,
            story2_id TEXT NOT NULL,
            preferred_story_id TEXT NOT NULL,
            user_session TEXT,
            batch1_name TEXT,
            batch2_name TEXT,
            preferred_batch_name TEXT,
            FOREIGN KEY (story1_id) REFERENCES stories (story_id),
            FOREIGN KEY (story2_id) REFERENCES stories (story_id),
            FOREIGN KEY (preferred_story_id) REFERENCES stories (story_id)
        );

        CREATE TABLE IF NOT EXISTS judge_tests (
            test_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            story1_id TEXT NOT NULL,
            story2_id TEXT NOT NULL,
            user_prediction_id TEXT NOT NULL,
            llm_winner_id TEXT NOT NULL,
            correct BOOLEAN,
            user_session TEXT,
            FOREIGN KEY (story1_id) REFERENCES stories (story_id),
            FOREIGN KEY (story2_id) REFERENCES stories (story_id),
            FOREIGN KEY (user_prediction_id) REFERENCES stories (story_id),
            FOREIGN KEY (llm_winner_id) REFERENCES stories (story_id)
        );

        CREATE INDEX IF NOT EXISTS idx_stories_batch ON stories (batch_number);
        CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches (winner_id);
    """)
    conn.commit()

def wipe_database(db_path: str):
    """Wipe the database file by deleting it."""
    if os.path.exists(db_path):
        os.remove(db_path)