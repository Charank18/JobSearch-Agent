"""
Unified job search pipeline supporting both sync and async execution.
Handles scraping, database storage, AI processing, auto-apply, and export.
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.scraper.search.linkedin_scraper import LinkedInScraper
from src.scraper.search.linkedin_applicant import LinkedInApplicant
from src.agents.cv_writer import CVWriter
from src.agents.cover_letter_writer import CoverLetterWriter
from src.agents.job_parser import JobParser
from src.utils.job_database import (
    get_connection, insert_jobs, get_unprocessed_jobs, mark_processed,
    get_unapplied_jobs, mark_applied, export_jobs_json,
)
from src.utils.file_utils import ensure_output_dirs, save_json

logger = logging.getLogger(__name__)

SENIOR_TITLE_KEYWORDS = [
    "senior", "sr.", "sr ", "lead", "principal", "staff", "director",
    "manager", "head of", "vp ", "vice president", "chief", "architect",
    "expert", "specialist", "consultant", "advisor", "executive",
]

EXPERIENCE_KEYWORDS = [
    "5+ years", "5 years", "6+ years", "7+ years", "8+ years", "10+ years",
    "years of experience", "experienced", "proven track record",
]


def is_relevant_job(job: dict) -> bool:
    """Filter to keep ONLY junior/entry-level positions with no experience required."""
    title = (job.get("title") or "").lower()
    
    # Reject senior titles
    for kw in SENIOR_TITLE_KEYWORDS:
        if kw in title:
            return False
    
    # Check seniority level in criteria
    criteria = job.get("criteria") or ""
    if isinstance(criteria, str):
        try:
            criteria = json.loads(criteria)
        except (json.JSONDecodeError, TypeError):
            criteria = {}
    
    seniority = (criteria.get("Seniority level") or "").lower()
    if seniority and seniority not in ("entry level", "internship", "associate", "not applicable", ""):
        return False
    
    # Check description for experience requirements
    description = (job.get("description") or "").lower()
    for kw in EXPERIENCE_KEYWORDS:
        if kw in description:
            return False
    
    # Accept if it's explicitly entry-level or has no clear experience requirement
    if any(term in title for term in ["junior", "entry", "graduate", "fresher", "trainee", "intern"]):
        return True
    
    if any(term in description for term in ["no experience", "0 years", "entry level", "fresh graduate", "new grad"]):
        return True
    
    # If no senior keywords and no high experience requirements, accept it
    return True


async def run_job_search_async(
    query: str,
    locations: Optional[list[str]] = None,
    max_jobs: int = 10,
    generate_cv: bool = False,
    generate_cover_letter: bool = False,
    parse_jobs: bool = True,
    auto_apply: bool = False,
    max_apply: int = 30,
    browser: str = "chromium",
    headless: bool = True,
    login: bool = True,
    experience_levels: Optional[list[str]] = None,
    date_posted: str = "any_time",
) -> dict:
    """Async pipeline: scrape -> store -> process -> apply -> export."""
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
        "jobs_applied": 0,
        "jobs_apply_failed": 0,
        "jobs_apply_skipped": 0,
    }

    scraper = LinkedInScraper(browser_type=browser, headless=headless)
    all_jobs = []

    try:
        await scraper.start()
        logged_in = False
        if login:
            logged_in = await scraper.login()

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

        if auto_apply and logged_in:
            applicant = LinkedInApplicant(scraper.page)
            unapplied = get_unapplied_jobs(conn, limit=max_apply)
            relevant = [j for j in unapplied if is_relevant_job(j)]
            logger.info(f"Auto-apply: {len(relevant)} relevant jobs out of {len(unapplied)} unapplied")

            for job in relevant:
                job_url = job.get("url", "")
                if not job_url or "/jobs/view/" not in job_url:
                    continue
                try:
                    apply_result = await applicant.apply_to_job(job_url)
                    if apply_result["applied"]:
                        mark_applied(conn, job["id"], method="easy_apply",
                                     applied_at=apply_result["applied_at"])
                        results["jobs_applied"] += 1
                    elif apply_result["error"]:
                        mark_applied(conn, job["id"], method=apply_result.get("method", "unknown"),
                                     error=apply_result["error"])
                        if "No Easy Apply" in (apply_result["error"] or ""):
                            results["jobs_apply_skipped"] += 1
                        else:
                            results["jobs_apply_failed"] += 1
                    await asyncio.sleep(random.uniform(3, 7))
                except Exception as e:
                    logger.error(f"Apply error for job {job.get('id')}: {e}")
                    results["jobs_apply_failed"] += 1

            stats = applicant.get_stats()
            logger.info(f"Apply stats: {stats}")

        export_jobs_json(conn, f"jobs/all_jobs_{ts}.json")
        conn.close()

    finally:
        await scraper.stop()

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
    auto_apply: bool = False,
    max_apply: int = 30,
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
            auto_apply=auto_apply,
            max_apply=max_apply,
            **kwargs,
        )
    )
