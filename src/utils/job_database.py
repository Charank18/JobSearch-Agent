"""
SQLite database for job storage with deduplication.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path("jobs/jobs.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            criteria TEXT,
            apply_url TEXT,
            scraped_at TEXT,
            source TEXT DEFAULT 'linkedin',
            processed INTEGER DEFAULT 0,
            cv_generated INTEGER DEFAULT 0,
            cover_letter_generated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
        CREATE INDEX IF NOT EXISTS idx_jobs_processed ON jobs(processed);
    """)


def insert_job(conn: sqlite3.Connection, job: dict) -> bool:
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO jobs
            (url, title, company, location, description, criteria, apply_url, scraped_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.get("url", ""),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("description", ""),
                json.dumps(job.get("criteria", {})),
                job.get("apply_url", ""),
                job.get("scraped_at", datetime.now().isoformat()),
                job.get("source", "linkedin"),
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False


def insert_jobs(conn: sqlite3.Connection, jobs: list[dict]) -> int:
    inserted = 0
    for job in jobs:
        if insert_job(conn, job):
            inserted += 1
    return inserted


def get_unprocessed_jobs(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM jobs WHERE processed = 0 ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_processed(conn: sqlite3.Connection, job_id: int, cv: bool = False, cover: bool = False):
    conn.execute(
        "UPDATE jobs SET processed = 1, cv_generated = ?, cover_letter_generated = ? WHERE id = ?",
        (int(cv), int(cover), job_id),
    )
    conn.commit()


def get_all_jobs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def export_jobs_json(conn: sqlite3.Connection, output_path: str):
    jobs = get_all_jobs(conn)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(jobs, f, indent=2, default=str)
    return len(jobs)
