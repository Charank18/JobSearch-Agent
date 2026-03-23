"""
AI-powered job description parser using Google Gemini.
"""

import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai

from src.prompts.prompts import JOB_PARSER_PROMPT
from src.utils.file_utils import save_json

load_dotenv()
logger = logging.getLogger(__name__)


class JobParser:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def parse_job(self, job_text: str) -> dict:
        prompt = JOB_PARSER_PROMPT.format(job_text=job_text[:4000])
        try:
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON")
            return {"raw_response": response.text if response else ""}
        except Exception as e:
            logger.error(f"Job parsing failed: {e}")
            return {"error": str(e)}

    def parse_and_save(self, job: dict) -> str:
        description = job.get("description", "")
        if not description:
            return ""
        parsed = self.parse_job(description)
        parsed["original_url"] = job.get("url", "")
        company = job.get("company", "unknown").replace(" ", "_")[:30]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/parsed_jobs/parsed_{company}_{ts}.json"
        save_json(parsed, filename)
        logger.info(f"Parsed job saved to {filename}")
        return filename
