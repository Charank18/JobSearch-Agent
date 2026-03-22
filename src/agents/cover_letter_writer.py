"""
AI-powered cover letter generation agent using Google Gemini.
"""

import logging
import os
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

from src.prompts.prompts import RESUME_DATA, COVER_LETTER_PROMPT
from src.utils.file_utils import save_text

load_dotenv()
logger = logging.getLogger(__name__)


class CoverLetterWriter:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate_cover_letter(self, job: dict) -> str:
        skills_flat = []
        for category in RESUME_DATA["skills"].values():
            skills_flat.extend(category)

        current_exp = RESUME_DATA["experience"][0]
        prompt = COVER_LETTER_PROMPT.format(
            name=RESUME_DATA["name"],
            current_role=f"{current_exp['role']} at {current_exp['company']}",
            skills=", ".join(skills_flat[:15]),
            achievement=current_exp["highlights"][0],
            job_title=job.get("title", ""),
            job_company=job.get("company", ""),
            job_description=job.get("description", "")[:2000],
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return ""

    def generate_and_save(self, job: dict) -> str:
        text = self.generate_cover_letter(job)
        if not text:
            return ""
        company = job.get("company", "unknown").replace(" ", "_")[:30]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/cover_letters/cover_{company}_{ts}.txt"
        save_text(text, filename)
        logger.info(f"Cover letter saved to {filename}")
        return filename
