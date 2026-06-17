import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'planner.db')


def get_db_path():
    return DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                capacity_per_sprint REAL NOT NULL DEFAULT 40.0
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS sprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                start_date TEXT,
                end_date TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                estimate REAL NOT NULL DEFAULT 0.0,
                priority INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'candidate',
                sprint_id INTEGER,
                FOREIGN KEY (sprint_id) REFERENCES sprints(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER NOT NULL,
                depends_on_id INTEGER NOT NULL,
                FOREIGN KEY (story_id) REFERENCES stories(id),
                FOREIGN KEY (depends_on_id) REFERENCES stories(id),
                UNIQUE(story_id, depends_on_id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS sprint_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER NOT NULL,
                sprint_id INTEGER NOT NULL,
                is_over_capacity INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                FOREIGN KEY (story_id) REFERENCES stories(id),
                FOREIGN KEY (sprint_id) REFERENCES sprints(id),
                UNIQUE(story_id, sprint_id)
            )
        ''')
