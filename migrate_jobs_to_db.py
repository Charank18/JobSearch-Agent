"""
Utility to migrate existing JSON job files into the SQLite database.
"""

import json
import sys
from pathlib import Path

from src.utils.job_database import get_connection, insert_jobs


def migrate(json_path: str, db_path: str = "jobs/jobs.db"):
    with open(json_path) as f:
        jobs = json.load(f)

    if not isinstance(jobs, list):
        jobs = [jobs]

    conn = get_connection(db_path)
    inserted = insert_jobs(conn, jobs)
    conn.close()

    print(f"Migrated {inserted} new jobs from {json_path} (skipped {len(jobs) - inserted} duplicates)")
    return inserted


if __name__ == "__main__":
    if len(sys.argv) < 2:
        json_files = list(Path("output/linkedin").glob("*.json"))
        if not json_files:
            print("Usage: python migrate_jobs_to_db.py <path_to_json>")
            sys.exit(1)
        for f in json_files:
            migrate(str(f))
    else:
        migrate(sys.argv[1])
