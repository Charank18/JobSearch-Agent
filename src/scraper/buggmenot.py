"""
BugMeNot credential scraper for job site logins.
"""

import argparse
import asyncio
import json
import logging
import random
from typing import Optional

from fake_useragent import UserAgent
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

BUGMENOT_URL = "https://bugmenot.com/view/{website}"


class BugMeNotScraper:
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.ua = UserAgent()

    async def get_credentials(self, website: str) -> list[dict]:
        async with async_playwright() as p:
            launch_opts = {"headless": self.headless}
            if self.proxy:
                launch_opts["proxy"] = {"server": self.proxy}

            browser = await p.chromium.launch(**launch_opts)
            context = await browser.new_context(user_agent=self.ua.random)
            page = await context.new_page()

            url = BUGMENOT_URL.format(website=website)
            logger.info(f"Fetching credentials from {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(random.uniform(1, 2))

                accounts = await page.query_selector_all("article.account")
                credentials = []

                for account in accounts:
                    fields = await account.query_selector_all("kbd")
                    if len(fields) >= 2:
                        username = (await fields[0].inner_text()).strip()
                        password = (await fields[1].inner_text()).strip()

                        rate_el = await account.query_selector("ul.stats li:first-child")
                        success_rate = ""
                        if rate_el:
                            success_rate = (await rate_el.inner_text()).strip()

                        credentials.append({
                            "website": website,
                            "username": username,
                            "password": password,
                            "success_rate": success_rate,
                        })

                logger.info(f"Found {len(credentials)} credential sets for {website}")
                return credentials
            except Exception as e:
                logger.error(f"Failed to scrape {website}: {e}")
                return []
            finally:
                await browser.close()


async def main():
    parser = argparse.ArgumentParser(description="BugMeNot Credential Scraper")
    parser.add_argument("--website", required=True, help="Target website")
    parser.add_argument("--visible", action="store_true", help="Show browser")
    parser.add_argument("--proxy", help="Proxy URL")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    scraper = BugMeNotScraper(headless=not args.visible, proxy=args.proxy)
    creds = await scraper.get_credentials(args.website)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(creds, f, indent=2)
        logger.info(f"Saved to {args.output}")

    print(json.dumps(creds, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
