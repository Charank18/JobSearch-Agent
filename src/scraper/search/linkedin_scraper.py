"""
LinkedIn Job Scraper using Playwright.
Supports anonymization, proxy, multi-browser, and robust data extraction.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Browser, Page

load_dotenv()
logger = logging.getLogger(__name__)

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"

EXPERIENCE_LEVELS = {
    "internship": "1",
    "entry_level": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
    "executive": "6",
}

DATE_POSTED = {
    "any_time": "",
    "past_month": "r2592000",
    "past_week": "r604800",
    "past_24h": "r86400",
}

TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "Europe/London", "Europe/Berlin",
    "Asia/Kolkata", "Asia/Tokyo", "Australia/Sydney",
]


class LinkedInScraper:
    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        proxy: Optional[str] = None,
        anonymize: bool = True,
    ):
        self.browser_type = browser_type
        self.headless = headless
        self.proxy = proxy
        self.anonymize = anonymize
        self.ua = UserAgent()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def _get_browser_args(self) -> dict:
        args = {"headless": self.headless}
        if self.proxy:
            args["proxy"] = {"server": self.proxy}
        return args

    async def _apply_anonymization(self, context):
        if not self.anonymize:
            return
        tz = random.choice(TIMEZONES)
        await context.add_init_script(f"""
            Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
            Object.defineProperty(navigator, 'languages', {{get: () => ['en-US', 'en']}});
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) return 'Intel Inc.';
                if (param === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, param);
            }};
        """)

    async def start(self):
        self.playwright = await async_playwright().start()
        launcher = getattr(self.playwright, self.browser_type)
        browser_args = await self._get_browser_args()
        self.browser = await launcher.launch(**browser_args)
        user_agent = self.ua.random if self.anonymize else None
        ctx_opts = {}
        if user_agent:
            ctx_opts["user_agent"] = user_agent
        if self.anonymize:
            ctx_opts["timezone_id"] = random.choice(TIMEZONES)
            ctx_opts["locale"] = "en-US"
        self.context = await self.browser.new_context(**ctx_opts)
        await self._apply_anonymization(self.context)
        self.page = await self.context.new_page()

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self, username: Optional[str] = None, password: Optional[str] = None):
        username = username or os.getenv("LINKEDIN_USERNAME")
        password = password or os.getenv("LINKEDIN_PASSWORD")
        if not username or not password:
            logger.warning("No LinkedIn credentials provided; scraping without login")
            return False
        try:
            await self.page.goto(LINKEDIN_LOGIN_URL, wait_until="domcontentloaded")
            await self.page.fill("#username", username)
            await self.page.fill("#password", password)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            if "feed" in self.page.url or "mynetwork" in self.page.url:
                logger.info("LinkedIn login successful")
                return True
            logger.warning("Login may have triggered verification; check browser")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def _build_search_url(
        self,
        query: str,
        location: str = "",
        experience_levels: Optional[list] = None,
        date_posted: str = "any_time",
        sort_by: str = "relevance",
        start: int = 0,
    ) -> str:
        params = [f"keywords={quote_plus(query)}"]
        if location:
            params.append(f"location={quote_plus(location)}")
        if experience_levels:
            codes = [EXPERIENCE_LEVELS.get(e, e) for e in experience_levels]
            params.append(f"f_E={','.join(codes)}")
        dp = DATE_POSTED.get(date_posted, "")
        if dp:
            params.append(f"f_TPR={dp}")
        if sort_by == "recent":
            params.append("sortBy=DD")
        if start > 0:
            params.append(f"start={start}")
        return f"{LINKEDIN_SEARCH_URL}?{'&'.join(params)}"

    async def _extract_job_links(self, max_pages: int = 5) -> list[str]:
        links = []
        for page_num in range(max_pages):
            await asyncio.sleep(random.uniform(2, 5))
            cards = await self.page.query_selector_all(
                "div.base-card, li.jobs-search-results__list-item, div.job-search-card"
            )
            for card in cards:
                anchor = await card.query_selector("a.base-card__full-link, a.job-search-card__link-wrapper")
                if anchor:
                    href = await anchor.get_attribute("href")
                    if href and "/jobs/view/" in href:
                        clean = href.split("?")[0]
                        if clean not in links:
                            links.append(clean)
            next_btn = await self.page.query_selector('button[aria-label="Next"], li.artdeco-pagination__indicator--number:last-child button')
            if next_btn and await next_btn.is_enabled():
                await next_btn.click()
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            else:
                break
        return links

    async def _extract_job_details(self, url: str) -> dict:
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(1.5, 3))
            job = {"url": url, "scraped_at": datetime.now().isoformat()}

            title_el = await self.page.query_selector(
                "h1.top-card-layout__title, h1.t-24, h2.top-card-layout__title"
            )
            job["title"] = await title_el.inner_text() if title_el else ""

            company_el = await self.page.query_selector(
                "a.topcard__org-name-link, span.topcard__flavor, a.top-card-layout__company-url"
            )
            job["company"] = (await company_el.inner_text()).strip() if company_el else ""

            location_el = await self.page.query_selector(
                "span.topcard__flavor--bullet, span.top-card-layout__bullet"
            )
            job["location"] = (await location_el.inner_text()).strip() if location_el else ""

            desc_el = await self.page.query_selector(
                "div.show-more-less-html__markup, div.description__text, section.show-more-less-html"
            )
            job["description"] = (await desc_el.inner_text()).strip() if desc_el else ""

            criteria_items = await self.page.query_selector_all(
                "li.description__job-criteria-item"
            )
            criteria = {}
            for item in criteria_items:
                header = await item.query_selector("h3")
                value = await item.query_selector("span")
                if header and value:
                    k = (await header.inner_text()).strip()
                    v = (await value.inner_text()).strip()
                    criteria[k] = v
            job["criteria"] = criteria

            apply_el = await self.page.query_selector(
                "a.apply-button, a[data-tracking-control-name='public_jobs_apply-link-offsite']"
            )
            job["apply_url"] = await apply_el.get_attribute("href") if apply_el else url

            return job
        except Exception as e:
            logger.error(f"Failed to extract details from {url}: {e}")
            return {"url": url, "error": str(e)}

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        max_jobs: int = 10,
        max_pages: int = 5,
        experience_levels: Optional[list] = None,
        date_posted: str = "any_time",
        sort_by: str = "relevance",
        links_only: bool = False,
    ) -> list[dict]:
        url = self._build_search_url(query, location, experience_levels, date_posted, sort_by)
        logger.info(f"Searching: {url}")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(2, 4))

        links = await self._extract_job_links(max_pages)
        links = links[:max_jobs]
        logger.info(f"Found {len(links)} job links")

        if links_only:
            return [{"url": link} for link in links]

        jobs = []
        for i, link in enumerate(links):
            logger.info(f"Extracting job {i+1}/{len(links)}: {link}")
            job = await self._extract_job_details(link)
            jobs.append(job)
            await asyncio.sleep(random.uniform(1, 3))
        return jobs

    async def scrape_job_url(self, url: str) -> dict:
        return await self._extract_job_details(url)


async def main():
    parser = argparse.ArgumentParser(description="LinkedIn Job Scraper")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("location", nargs="?", default="", help="Job location")
    parser.add_argument("--job-url", help="Scrape a specific job URL")
    parser.add_argument("--max-jobs", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--proxy", help="Proxy URL")
    parser.add_argument("--no-anonymize", dest="anonymize", action="store_false", default=True)
    parser.add_argument("--experience-levels", nargs="+", help="Filter by experience")
    parser.add_argument("--date-posted", default="any_time", choices=list(DATE_POSTED.keys()))
    parser.add_argument("--sort-by", default="relevance", choices=["relevance", "recent"])
    parser.add_argument("--links-only", action="store_true")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--login", action="store_true", default=True)
    parser.add_argument("--no-login", dest="login", action="store_false")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.query and not args.job_url:
        parser.error("Either a search query or --job-url is required")

    scraper = LinkedInScraper(
        browser_type=args.browser,
        headless=args.headless,
        proxy=args.proxy,
        anonymize=args.anonymize,
    )

    try:
        await scraper.start()
        if args.login:
            await scraper.login()

        if args.job_url:
            results = [await scraper.scrape_job_url(args.job_url)]
        else:
            results = await scraper.search_jobs(
                query=args.query,
                location=args.location,
                max_jobs=args.max_jobs,
                max_pages=args.max_pages,
                experience_levels=args.experience_levels,
                date_posted=args.date_posted,
                sort_by=args.sort_by,
                links_only=args.links_only,
            )

        output_path = args.output or f"output/linkedin/jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Saved {len(results)} jobs to {output_path}")
        print(json.dumps(results, indent=2, default=str))
    finally:
        await scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
