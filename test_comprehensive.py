"""
Comprehensive test suite for JobSearch Agent.
"""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))


def test_database_operations():
    print("[TEST] Database operations...")
    from src.utils.job_database import get_connection, insert_job, insert_jobs, get_all_jobs, export_jobs_json

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = get_connection(db_path)

        job = {
            "url": "https://linkedin.com/jobs/view/123",
            "title": "Software Engineer",
            "company": "TestCorp",
            "location": "Bangalore, India",
            "description": "Build cool stuff",
            "criteria": {"Seniority level": "Entry level"},
            "apply_url": "https://apply.test.com",
        }
        assert insert_job(conn, job), "Insert should succeed"
        assert not insert_job(conn, job), "Duplicate insert should be skipped"

        jobs = get_all_jobs(conn)
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Software Engineer"

        batch = [
            {"url": f"https://linkedin.com/jobs/view/{i}", "title": f"Job {i}"}
            for i in range(200, 205)
        ]
        count = insert_jobs(conn, batch)
        assert count == 5

        export_path = os.path.join(tmpdir, "export.json")
        export_jobs_json(conn, export_path)
        assert Path(export_path).exists()

        conn.close()
    print("  PASSED")


def test_file_utils():
    print("[TEST] File utilities...")
    from src.utils.file_utils import save_json, load_json, timestamped_filename, save_text

    with tempfile.TemporaryDirectory() as tmpdir:
        data = {"test": True, "items": [1, 2, 3]}
        path = os.path.join(tmpdir, "sub", "test.json")
        save_json(data, path)
        loaded = load_json(path)
        assert loaded == data

        txt_path = os.path.join(tmpdir, "test.txt")
        save_text("hello world", txt_path)
        with open(txt_path) as f:
            assert f.read() == "hello world"

        fname = timestamped_filename("test", "json")
        assert fname.startswith("test_")
        assert fname.endswith(".json")

    print("  PASSED")


def test_resume_data():
    print("[TEST] Resume data integrity...")
    from src.prompts.prompts import RESUME_DATA

    assert RESUME_DATA["name"] == "Charan Karnati"
    assert len(RESUME_DATA["experience"]) >= 3
    assert len(RESUME_DATA["publications"]) >= 3
    assert "Python" in RESUME_DATA["skills"]["languages"]
    assert RESUME_DATA["education"]["cgpa"] == "9.07"
    print("  PASSED")


def test_prompt_templates():
    print("[TEST] Prompt templates...")
    from src.prompts.prompts import CV_GENERATION_PROMPT, COVER_LETTER_PROMPT, JOB_PARSER_PROMPT

    assert "{name}" in CV_GENERATION_PROMPT
    assert "{job_title}" in CV_GENERATION_PROMPT
    assert "{name}" in COVER_LETTER_PROMPT
    assert "{job_text}" in JOB_PARSER_PROMPT
    print("  PASSED")


def test_scraper_url_building():
    print("[TEST] LinkedIn URL building...")
    try:
        from src.scraper.search.linkedin_scraper import LinkedInScraper
    except ImportError:
        print("  SKIPPED (playwright not installed)")
        return

    scraper = LinkedInScraper()
    url = scraper._build_search_url("Python Developer", "Bangalore")
    assert "keywords=Python" in url
    assert "location=Bangalore" in url

    url2 = scraper._build_search_url("SWE", experience_levels=["entry_level"], date_posted="past_week")
    assert "f_E=2" in url2
    assert "f_TPR=r604800" in url2

    url3 = scraper._build_search_url("ML", sort_by="recent", start=25)
    assert "sortBy=DD" in url3
    assert "start=25" in url3
    print("  PASSED")


def test_config_files():
    print("[TEST] Config files exist and are valid...")
    import yaml

    for config_file in ["config/jobsearch_config.yaml", "config/cv_app_agent_config.yaml", "config/file_config.yaml"]:
        assert Path(config_file).exists(), f"Missing {config_file}"
        with open(config_file) as f:
            data = yaml.safe_load(f)
            assert data is not None

    assert Path("data/resume.json").exists()
    with open("data/resume.json") as f:
        resume = json.load(f)
        assert resume["name"] == "Charan Karnati"
    print("  PASSED")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 50)
    print("JobSearch Agent - Comprehensive Tests")
    print("=" * 50)

    tests = [
        test_database_operations,
        test_file_utils,
        test_resume_data,
        test_prompt_templates,
        test_scraper_url_building,
        test_config_files,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 50)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
