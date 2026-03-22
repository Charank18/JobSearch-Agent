"""
File utilities for managing output directories and templates.
"""

import json
from datetime import datetime
from pathlib import Path


def ensure_output_dirs():
    dirs = [
        "output/linkedin", "output/cvs", "output/cover_letters",
        "output/parsed_jobs", "jobs", "logs",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def save_json(data: dict | list, filepath: str) -> str:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def load_json(filepath: str) -> dict | list:
    with open(filepath) as f:
        return json.load(f)


def timestamped_filename(prefix: str, ext: str = "json") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{ext}"


def save_text(content: str, filepath: str) -> str:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)
    return filepath
