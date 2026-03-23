"""
CLI interface for the JobSearch Agent.
"""

import json
import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from src.utils.job_search_pipeline import run_job_search
from src.utils.file_utils import load_json, ensure_output_dirs

console = Console()


@click.group()
def cli():
    """JobSearch Agent - Intelligent job search automation."""
    ensure_output_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/jobsearch.log", mode="a"),
        ],
    )


@cli.command()
@click.argument("query")
@click.option("--locations", "-l", multiple=True, default=["India"])
@click.option("--max-jobs", "-m", default=10, help="Max jobs to scrape")
@click.option("--generate-cv", is_flag=True, help="Generate tailored CVs")
@click.option("--generate-cover-letter", is_flag=True, help="Generate cover letters")
@click.option("--auto-apply", is_flag=True, help="Auto-apply via Easy Apply")
@click.option("--max-apply", default=30, help="Max jobs to apply to per run")
@click.option("--no-parse", is_flag=True, help="Skip job parsing")
@click.option("--browser", default="chromium", type=click.Choice(["chromium", "firefox", "webkit"]))
@click.option("--headless/--no-headless", default=True)
@click.option("--no-login", is_flag=True)
@click.option("--experience-levels", "-e", multiple=True)
@click.option("--date-posted", default="any_time",
              type=click.Choice(["any_time", "past_month", "past_week", "past_24h"]))
def search(query, locations, max_jobs, generate_cv, generate_cover_letter,
           auto_apply, max_apply, no_parse, browser, headless, no_login,
           experience_levels, date_posted):
    """Search for jobs, generate documents, and optionally auto-apply."""
    console.print(f"\n[bold green]Searching for:[/] {query}")
    console.print(f"[bold]Locations:[/] {', '.join(locations)}")
    console.print(f"[bold]Max jobs:[/] {max_jobs}")
    if auto_apply:
        console.print(f"[bold yellow]Auto-apply:[/] ENABLED (max {max_apply})")
    console.print()

    result = run_job_search(
        query=query,
        locations=list(locations),
        max_jobs=max_jobs,
        generate_cv=generate_cv,
        generate_cover_letter=generate_cover_letter,
        parse_jobs=not no_parse,
        auto_apply=auto_apply,
        max_apply=max_apply,
        browser=browser,
        headless=headless,
        login=not no_login,
        experience_levels=list(experience_levels) if experience_levels else None,
        date_posted=date_posted,
    )

    table = Table(title="Pipeline Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, val in result.items():
        if key not in ("query", "locations"):
            table.add_row(key.replace("_", " ").title(), str(val))
    console.print(table)


@cli.command()
@click.argument("filepath")
@click.option("--generate-cv", is_flag=True)
@click.option("--generate-cover-letter", is_flag=True)
def process(filepath, generate_cv, generate_cover_letter):
    """Process existing job data from a JSON file."""
    from src.agents.cv_writer import CVWriter
    from src.agents.cover_letter_writer import CoverLetterWriter
    from src.agents.job_parser import JobParser

    jobs = load_json(filepath)
    if not isinstance(jobs, list):
        jobs = [jobs]

    console.print(f"Processing {len(jobs)} jobs from {filepath}")

    parser = JobParser()
    cv_writer = CVWriter() if generate_cv else None
    cl_writer = CoverLetterWriter() if generate_cover_letter else None

    for i, job in enumerate(jobs):
        console.print(f"\n[bold]Job {i+1}:[/] {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
        parser.parse_and_save(job)
        if cv_writer:
            cv_writer.generate_and_save(job)
        if cl_writer:
            cl_writer.generate_and_save(job)

    console.print(f"\n[bold green]Done![/] Processed {len(jobs)} jobs")


@cli.command()
def applied():
    """Show all jobs that were successfully applied to."""
    from src.utils.job_database import get_connection, get_applied_jobs

    conn = get_connection()
    jobs = get_applied_jobs(conn)
    conn.close()

    if not jobs:
        console.print("[yellow]No applications yet.[/]")
        return

    table = Table(title=f"Applied Jobs ({len(jobs)} total)")
    table.add_column("#", style="dim")
    table.add_column("Company", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Location")
    table.add_column("Applied At", style="dim")

    for i, j in enumerate(jobs, 1):
        table.add_row(
            str(i),
            (j.get("company") or "N/A")[:30],
            (j.get("title") or "N/A")[:35],
            (j.get("location") or "")[:25],
            (j.get("applied_at") or "")[:19],
        )

    console.print(table)


if __name__ == "__main__":
    cli()
