"""
LinkedIn Easy Apply auto-applicant.
Logs into LinkedIn, navigates to job pages, and submits Easy Apply applications.
Handles multi-step forms, resume upload, and common form fields.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from playwright.async_api import Page

load_dotenv()
logger = logging.getLogger(__name__)

RESUME_PATH = Path("data/CK_Resume.pdf")

FORM_ANSWERS = {
    "phone": "9999999999",
    "city": "Hyderabad",
    "years of experience": "1",
    "experience": "1",
    "salary": "0",
    "expected salary": "0",
    "desired salary": "0",
    "notice period": "0",
    "gpa": "9.07",
    "cgpa": "9.07",
    "linkedin": "https://www.linkedin.com/in/charankarnati",
    "github": "https://github.com/Charank18",
    "website": "https://github.com/Charank18",
    "portfolio": "https://github.com/Charank18",
}

YES_KEYWORDS = [
    "authorized", "legally authorized", "right to work",
    "eligible", "willing to relocate", "relocate",
    "proficient", "comfortable", "able to commute",
    "do you have", "have you completed",
]

NO_KEYWORDS = [
    "sponsorship", "require sponsorship", "need sponsorship",
    "disability", "veteran",
]


class LinkedInApplicant:
    """Handles the Easy Apply flow on LinkedIn job pages."""

    def __init__(self, page: Page, resume_path: Optional[str] = None):
        self.page = page
        self.resume_path = Path(resume_path) if resume_path else RESUME_PATH
        self.applied_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    async def apply_to_job(self, job_url: str) -> dict:
        """Navigate to a job and attempt Easy Apply. Returns application result."""
        result = {
            "url": job_url,
            "applied": False,
            "method": None,
            "error": None,
            "applied_at": None,
        }

        try:
            await self.page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(2, 4))

            easy_apply_btn = await self._find_easy_apply_button()
            if not easy_apply_btn:
                result["error"] = "No Easy Apply button found"
                result["method"] = "external"
                self.skipped_count += 1
                logger.info(f"Skipped (no Easy Apply): {job_url}")
                return result

            await easy_apply_btn.click()
            await asyncio.sleep(random.uniform(1.5, 3))

            success = await self._complete_application_flow()

            if success:
                result["applied"] = True
                result["method"] = "easy_apply"
                result["applied_at"] = datetime.now().isoformat()
                self.applied_count += 1
                logger.info(f"Applied successfully: {job_url}")
            else:
                result["error"] = "Could not complete application flow"
                self.failed_count += 1
                logger.warning(f"Failed to complete application: {job_url}")

        except Exception as e:
            result["error"] = str(e)
            self.failed_count += 1
            logger.error(f"Error applying to {job_url}: {e}")

        return result

    async def _find_easy_apply_button(self):
        """Locate the Easy Apply button on the page."""
        selectors = [
            'button.jobs-apply-button',
            'button[aria-label*="Easy Apply"]',
            'button.jobs-apply-button--top-card',
            'button:has-text("Easy Apply")',
            'button:has-text("Apply now")',
            'div.jobs-apply-button--top-card button',
        ]
        for sel in selectors:
            try:
                btn = await self.page.query_selector(sel)
                if btn:
                    text = (await btn.inner_text()).strip().lower()
                    if "easy apply" in text or "apply" in text:
                        return btn
            except Exception:
                continue
        return None

    async def _complete_application_flow(self) -> bool:
        """Walk through the multi-step Easy Apply modal."""
        max_steps = 10
        for step in range(max_steps):
            await asyncio.sleep(random.uniform(1, 2))

            modal = await self.page.query_selector(
                'div.jobs-easy-apply-modal, div.jobs-easy-apply-content, '
                'div[data-test-modal], div.artdeco-modal'
            )
            if not modal:
                already = await self.page.query_selector(
                    'span:has-text("Application submitted"), '
                    'h3:has-text("Application submitted"), '
                    'span:has-text("Your application was sent")'
                )
                return already is not None

            await self._handle_resume_upload(modal)
            await self._fill_form_fields(modal)
            await self._handle_radio_buttons(modal)
            await self._handle_dropdowns(modal)
            await self._handle_checkboxes(modal)

            submitted = await self._click_submit_or_next(modal)
            if submitted:
                await asyncio.sleep(random.uniform(1.5, 3))
                dismiss = await self.page.query_selector(
                    'button[aria-label="Dismiss"], button:has-text("Done"), '
                    'button:has-text("Close")'
                )
                if dismiss:
                    await dismiss.click()
                return True

        await self._try_dismiss_modal()
        return False

    async def _handle_resume_upload(self, modal):
        """Upload resume if a file input is present and no resume is attached."""
        if not self.resume_path.exists():
            logger.warning(f"Resume file not found: {self.resume_path}")
            return
        try:
            file_input = await modal.query_selector('input[type="file"]')
            if file_input:
                existing = await modal.query_selector(
                    'div.jobs-document-upload-redesign-card__container, '
                    'div[class*="document-upload"]'
                )
                if not existing:
                    await file_input.set_input_files(str(self.resume_path.resolve()))
                    logger.info("Resume uploaded")
                    await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f"Resume upload skipped: {e}")

    async def _fill_form_fields(self, modal):
        """Fill text input and textarea fields using FORM_ANSWERS."""
        inputs = await modal.query_selector_all(
            'input[type="text"], input[type="tel"], input[type="number"], '
            'input[type="email"], input[type="url"], textarea'
        )
        for inp in inputs:
            try:
                current_val = await inp.input_value()
                if current_val and current_val.strip():
                    continue

                label_text = ""
                inp_id = await inp.get_attribute("id")
                if inp_id:
                    label_el = await modal.query_selector(f'label[for="{inp_id}"]')
                    if label_el:
                        label_text = (await label_el.inner_text()).strip().lower()

                if not label_text:
                    aria = await inp.get_attribute("aria-label") or ""
                    placeholder = await inp.get_attribute("placeholder") or ""
                    label_text = (aria or placeholder).lower()

                answer = self._match_answer(label_text)
                if answer:
                    await inp.fill(answer)
                    logger.debug(f"Filled '{label_text}' with '{answer}'")
            except Exception:
                continue

    def _match_answer(self, label: str) -> Optional[str]:
        """Match a form label to a predefined answer."""
        label = label.lower().strip()
        for key, val in FORM_ANSWERS.items():
            if key in label:
                return val
        if "phone" in label or "mobile" in label:
            return FORM_ANSWERS["phone"]
        if "city" in label or "location" in label:
            return FORM_ANSWERS["city"]
        if "experience" in label or "years" in label:
            return FORM_ANSWERS["years of experience"]
        if "salary" in label or "compensation" in label or "ctc" in label:
            return FORM_ANSWERS["salary"]
        if "gpa" in label or "cgpa" in label or "grade" in label:
            return FORM_ANSWERS["gpa"]
        if "github" in label:
            return FORM_ANSWERS["github"]
        if "linkedin" in label:
            return FORM_ANSWERS["linkedin"]
        if "website" in label or "portfolio" in label or "url" in label:
            return FORM_ANSWERS["website"]
        if "notice" in label:
            return FORM_ANSWERS["notice period"]
        return None

    async def _handle_radio_buttons(self, modal):
        """Handle yes/no radio button questions."""
        fieldsets = await modal.query_selector_all('fieldset, div[data-test-form-element]')
        for fs in fieldsets:
            try:
                legend = await fs.query_selector('legend, span.t-14')
                if not legend:
                    continue
                question = (await legend.inner_text()).strip().lower()

                should_yes = any(kw in question for kw in YES_KEYWORDS)
                should_no = any(kw in question for kw in NO_KEYWORDS)

                if should_yes:
                    yes_radio = await fs.query_selector(
                        'input[value="Yes"], label:has-text("Yes")'
                    )
                    if yes_radio:
                        await yes_radio.click()
                elif should_no:
                    no_radio = await fs.query_selector(
                        'input[value="No"], label:has-text("No")'
                    )
                    if no_radio:
                        await no_radio.click()
            except Exception:
                continue

    async def _handle_dropdowns(self, modal):
        """Select first valid option in any empty dropdowns."""
        selects = await modal.query_selector_all('select')
        for select in selects:
            try:
                current = await select.input_value()
                if current and current.strip():
                    continue
                options = await select.query_selector_all('option')
                for opt in options[1:]:
                    val = await opt.get_attribute("value")
                    if val and val.strip():
                        await select.select_option(val)
                        break
            except Exception:
                continue

    async def _handle_checkboxes(self, modal):
        """Check required unchecked checkboxes (terms, agreements)."""
        checkboxes = await modal.query_selector_all('input[type="checkbox"]')
        for cb in checkboxes:
            try:
                checked = await cb.is_checked()
                if not checked:
                    required = await cb.get_attribute("required")
                    aria = (await cb.get_attribute("aria-label") or "").lower()
                    if required or "agree" in aria or "terms" in aria or "follow" in aria:
                        await cb.check()
            except Exception:
                continue

    async def _click_submit_or_next(self, modal) -> bool:
        """Click Submit (returns True) or Next/Review (returns False to continue loop)."""
        submit_selectors = [
            'button[aria-label="Submit application"]',
            'button:has-text("Submit application")',
            'button:has-text("Submit")',
        ]
        for sel in submit_selectors:
            btn = await modal.query_selector(sel)
            if btn and await btn.is_enabled():
                await btn.click()
                return True

        next_selectors = [
            'button[aria-label="Continue to next step"]',
            'button[aria-label="Review your application"]',
            'button:has-text("Next")',
            'button:has-text("Review")',
            'button:has-text("Continue")',
        ]
        for sel in next_selectors:
            btn = await modal.query_selector(sel)
            if btn and await btn.is_enabled():
                await btn.click()
                return False

        return False

    async def _try_dismiss_modal(self):
        """Dismiss the Easy Apply modal if stuck."""
        dismiss_selectors = [
            'button[aria-label="Dismiss"]',
            'button[aria-label="Discard"]',
            'button:has-text("Discard")',
            'button:has-text("Save")',
        ]
        for sel in dismiss_selectors:
            btn = await self.page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(0.5)
                confirm = await self.page.query_selector(
                    'button:has-text("Discard"), button[data-test-dialog-primary-btn]'
                )
                if confirm:
                    await confirm.click()
                return

    def get_stats(self) -> dict:
        return {
            "applied": self.applied_count,
            "failed": self.failed_count,
            "skipped": self.skipped_count,
            "total": self.applied_count + self.failed_count + self.skipped_count,
        }
