"""
FastAPI server for the JobSearch Agent.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.utils.job_search_pipeline import run_job_search_async
from src.agents.job_parser import JobParser
from src.agents.cv_writer import CVWriter
from src.agents.cover_letter_writer import CoverLetterWriter
from src.utils.file_utils import ensure_output_dirs
from src.utils.job_database import get_connection, get_all_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
ensure_output_dirs()

app = FastAPI(
    title="JobSearch Agent API",
    description="Intelligent job search automation with AI-powered document generation",
    version="1.0.0",
)

search_results: dict[str, dict] = {}


class SearchRequest(BaseModel):
    query: str
    locations: list[str] = ["India"]
    max_jobs: int = 10
    generate_cv: bool = False
    generate_cover_letter: bool = False
    parse_jobs: bool = True
    experience_levels: Optional[list[str]] = None
    date_posted: str = "any_time"


class ProcessRequest(BaseModel):
    job_description: str
    generate_cv: bool = False
    generate_cover_letter: bool = False


class ParseRequest(BaseModel):
    job_text: str


async def _run_search(search_id: str, req: SearchRequest):
    try:
        result = await run_job_search_async(
            query=req.query,
            locations=req.locations,
            max_jobs=req.max_jobs,
            generate_cv=req.generate_cv,
            generate_cover_letter=req.generate_cover_letter,
            parse_jobs=req.parse_jobs,
            experience_levels=req.experience_levels,
            date_posted=req.date_posted,
        )
        search_results[search_id] = {"status": "completed", "result": result}
    except Exception as e:
        search_results[search_id] = {"status": "failed", "error": str(e)}


@app.post("/search")
async def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    search_id = str(uuid.uuid4())
    search_results[search_id] = {"status": "running", "started_at": datetime.now().isoformat()}
    background_tasks.add_task(_run_search, search_id, req)
    return {"search_id": search_id, "status": "started"}


@app.get("/search/{search_id}")
async def get_search_result(search_id: str):
    if search_id not in search_results:
        raise HTTPException(status_code=404, detail="Search not found")
    return search_results[search_id]


@app.post("/process")
async def process_job(req: ProcessRequest):
    job = {"description": req.job_description, "title": "Unknown", "company": "Unknown"}
    results = {}
    if req.generate_cv:
        writer = CVWriter()
        results["cv_path"] = writer.generate_and_save(job)
    if req.generate_cover_letter:
        writer = CoverLetterWriter()
        results["cover_letter_path"] = writer.generate_and_save(job)
    return results


@app.post("/parse")
async def parse_job(req: ParseRequest):
    parser = JobParser()
    return parser.parse_job(req.job_text)


@app.get("/jobs")
async def list_jobs():
    conn = get_connection()
    jobs = get_all_jobs(conn)
    conn.close()
    return {"total": len(jobs), "jobs": jobs}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
