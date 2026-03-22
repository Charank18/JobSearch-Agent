"""
AI-powered CV generation agent using Google Gemini.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

from src.prompts.prompts import RESUME_DATA, CV_GENERATION_PROMPT
from src.utils.file_utils import save_text

load_dotenv()
logger = logging.getLogger(__name__)


class CVWriter:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def _format_experience(self) -> str:
        lines = []
        for exp in RESUME_DATA["experience"]:
            lines.append(f"\n{exp['role']} at {exp['company']} ({exp['period']})")
            for h in exp["highlights"]:
                lines.append(f"  - {h}")
        return "\n".join(lines)

    def _format_skills(self) -> str:
        s = RESUME_DATA["skills"]
        parts = [
            f"Languages: {', '.join(s['languages'])}",
            f"Frameworks: {', '.join(s['frameworks'])}",
            f"ML/AI: {', '.join(s['ml_ai'])}",
            f"Infrastructure: {', '.join(s['infra'])}",
        ]
        return "\n".join(parts)

    def generate_cv(self, job: dict) -> str:
        edu = RESUME_DATA["education"]
        prompt = CV_GENERATION_PROMPT.format(
            name=RESUME_DATA["name"],
            education=f"{edu['degree']} from {edu['institution']} (CGPA: {edu['cgpa']})",
            experience=self._format_experience(),
            skills=self._format_skills(),
            publications="\n".join(f"- {p}" for p in RESUME_DATA["publications"]),
            job_title=job.get("title", ""),
            job_company=job.get("company", ""),
            job_location=job.get("location", ""),
            job_description=job.get("description", "")[:3000],
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"CV generation failed: {e}")
            return ""

    def generate_and_save(self, job: dict) -> str:
        cv_text = self.generate_cv(job)
        if not cv_text:
            return ""
        company = job.get("company", "unknown").replace(" ", "_")[:30]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/cvs/cv_{company}_{ts}.txt"
        save_text(cv_text, filename)
        logger.info(f"CV saved to {filename}")
        return filename
