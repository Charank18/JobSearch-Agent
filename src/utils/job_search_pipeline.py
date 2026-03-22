"""
Unified job search pipeline supporting both sync and async execution.
Handles scraping, database storage, AI processing, and export.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.scraper.search.linkedin_scraper import LinkedInScraper
from src.agents.cv_writer import CVWriter
from src.agents.cover_letter_writer import CoverLetterWriter
from src.agents.job_parser import JobParser
from src.utils.job_database import get_connection, insert_jobs, get_unprocessed_jobs, mark_processed, export_jobs_json
from src.utils.file_utils import ensure_output_dirs, save_json

logger = logging.getLogger(__name__)


async def run_job_search_async(
    query: str,
    locations: Optional[list[str]] = None,
    max_jobs: int = 10,
    generate_cv: bool = False,
    generate_cover_letter: bool = False,
    parse_jobs: bool = True,
    browser: str = "chromium",
    headless: bool = True,
    login: bool = True,
    experience_levels: Optional[list[str]] = None,
    date_posted: str = "any_time",
) -> dict:
    """Async pipeline for FastAPI / event-loop contexts."""
    ensure_output_dirs()
    results = {
        "query": query,
        "locations": locations or ["India"],
        "started_at": datetime.now().isoformat(),
        "jobs_found": 0,
        "jobs_inserted": 0,
        "cvs_generated": 0,
        "cover_letters_generated": 0,
        "jobs_parsed": 0,
    }

    scraper = LinkedInScraper(browser_type=browser, headless=headless)
    all_jobs = []

    try:
        await scraper.start()
        if login:
            await scraper.login()

        for location in (locations or ["India"]):
            logger.info(f"Searching '{query}' in '{location}'")
            jobs = await scraper.search_jobs(
                query=query,
                location=location,
                max_jobs=max_jobs,
                experience_levels=experience_levels,
                date_posted=date_posted,
            )
            all_jobs.extend(jobs)
    finally:
        await scraper.stop()

    results["jobs_found"] = len(all_jobs)

    conn = get_connection()
    results["jobs_inserted"] = insert_jobs(conn, all_jobs)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_json(all_jobs, f"output/linkedin/search_{ts}.json")

    if parse_jobs or generate_cv or generate_cover_letter:
        unprocessed = get_unprocessed_jobs(conn, limit=max_jobs)

        parser = JobParser() if parse_jobs else None
        cv_writer = CVWriter() if generate_cv else None
        cl_writer = CoverLetterWriter() if generate_cover_letter else None

        for job in unprocessed:
            try:
                if parser:
                    parser.parse_and_save(job)
                    results["jobs_parsed"] += 1

                cv_done = False
                cl_done = False

                if cv_writer:
                    if cv_writer.generate_and_save(job):
                        results["cvs_generated"] += 1
                        cv_done = True

                if cl_writer:
                    if cl_writer.generate_and_save(job):
                        results["cover_letters_generated"] += 1
                        cl_done = True

                mark_processed(conn, job["id"], cv=cv_done, cover=cl_done)
            except Exception as e:
                logger.error(f"Error processing job {job.get('id')}: {e}")

    export_jobs_json(conn, f"jobs/all_jobs_{ts}.json")
    conn.close()

    results["completed_at"] = datetime.now().isoformat()
    save_json(results, f"output/pipeline_result_{ts}.json")
    return results


def run_job_search(
    query: str,
    locations: Optional[list[str]] = None,
    max_jobs: int = 10,
    generate_cv: bool = False,
    generate_cover_letter: bool = False,
    parse_jobs: bool = True,
    **kwargs,
) -> dict:
    """Sync wrapper for CLI / standalone scripts."""
    return asyncio.run(
        run_job_search_async(
            query=query,
            locations=locations,
            max_jobs=max_jobs,
            generate_cv=generate_cv,
            generate_cover_letter=generate_cover_letter,
            parse_jobs=parse_jobs,
            **kwargs,
        )
    )
