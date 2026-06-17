import sqlite3
import os
from contextlib import contextmanager
from .config import get_config

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


def round_half_hour(value):
    return round(value * 2) / 2


def round_time(value):
    granularity = float(get_config('time_granularity', 0.25))
    multiplier = 1.0 / granularity
    return round(value * multiplier) / multiplier


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_name_lower ON skills (LOWER(name))')

        c.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                capacity_per_sprint REAL NOT NULL DEFAULT 40.0
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS member_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                capacity_per_sprint REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (member_id) REFERENCES members(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id),
                UNIQUE(member_id, skill_id)
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
                display_order INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'candidate',
                sprint_id INTEGER,
                FOREIGN KEY (sprint_id) REFERENCES sprints(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS story_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                required_hours REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (story_id) REFERENCES stories(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id),
                UNIQUE(story_id, skill_id)
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
                is_skill_mismatch INTEGER DEFAULT 0,
                skill_breakdown TEXT,
                FOREIGN KEY (story_id) REFERENCES stories(id),
                FOREIGN KEY (sprint_id) REFERENCES sprints(id),
                UNIQUE(story_id, sprint_id)
            )
        ''')

        try:
            c.execute("SELECT display_order FROM stories LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE stories ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0")

        try:
            c.execute("SELECT is_skill_mismatch FROM sprint_assignments LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE sprint_assignments ADD COLUMN is_skill_mismatch INTEGER DEFAULT 0")
            c.execute("ALTER TABLE sprint_assignments ADD COLUMN skill_breakdown TEXT")
