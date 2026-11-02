"""Delta Air Lines web check-in bot.

Delta's check-in lookup takes the confirmation number plus the passenger's
first and last name. The markup changes regularly, so every interaction goes
through the candidate lists in SELECTORS; update them there when the site
changes rather than touching the flow below.
"""

from __future__ import annotations

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.models import Booking
from app.services.bots.base import AirlineCheckInBot, BotResult, CheckInBotError

SELECTORS: dict[str, list[str]] = {
    "confirmation": [
        "input#confirmationNumber",
        "input[name='confirmationNumber']",
        "input[aria-label*='Confirmation' i]",
        "input[placeholder*='Confirmation' i]",
    ],
    "first_name": [
        "input#firstName",
        "input[name='firstName']",
        "input[aria-label*='First Name' i]",
    ],
    "last_name": [
        "input#lastName",
        "input[name='lastName']",
        "input[aria-label*='Last Name' i]",
    ],
    "submit_lookup": [
        "button[type='submit']:has-text('Find')",
        "button:has-text('Find My Trip')",
        "button:has-text('Continue')",
        "button[type='submit']",
    ],
    "lookup_error": [
        "[role='alert']:has-text('unable')",
        "[role='alert']:has-text('not found')",
        ".error-message",
    ],
    "select_all_passengers": [
        "input[type='checkbox'][aria-label*='Select All' i]",
        "label:has-text('Select All')",
    ],
    "hazmat_accept": [
        "button:has-text('Accept')",
        "button:has-text('I Agree')",
        "input[type='checkbox'][name*='hazmat' i]",
    ],
    "keep_seats": [
        "button:has-text('Keep Seats')",
        "button:has-text('Keep Current Seat')",
        "button:has-text('Continue Without Changing')",
        "button:has-text('Skip')",
    ],
    "decline_upsell": [
        "button:has-text('No Thanks')",
        "button:has-text('Not Now')",
        "a:has-text('No Thanks')",
    ],
    "continue": [
        "button:has-text('Continue')",
        "button:has-text('Next')",
    ],
    "complete_check_in": [
        "button:has-text('Check In')",
        "button:has-text('Complete Check-In')",
        "button:has-text('Confirm')",
    ],
    "view_boarding_pass": [
        "button:has-text('View Boarding Pass')",
        "a:has-text('View Boarding Pass')",
        "button:has-text('Boarding Pass')",
        "a:has-text('Boarding Pass')",
    ],
    "boarding_pass_ready": [
        "[data-testid*='boarding-pass' i]",
        ".boarding-pass",
        "text=/Boarding Pass/i",
        "img[alt*='barcode' i]",
        "canvas",
    ],
}


class DeltaCheckInBot(AirlineCheckInBot):
    airline_iata = "DL"
    check_in_url = "https://www.delta.com/mytrips/check-in"

    async def fill_lookup(self, page: Page, booking: Booking) -> None:
        await self.human_type(page, SELECTORS["confirmation"], booking.pnr_code)
        await self.human_type(page, SELECTORS["first_name"], booking.passenger_first_name)
        await self.human_type(page, SELECTORS["last_name"], booking.passenger_last_name)
        await self.human_click(page, SELECTORS["submit_lookup"])
        await page.wait_for_load_state("domcontentloaded")
        await self.pause(1.5, 3.0)

        for selector in SELECTORS["lookup_error"]:
            loc = page.locator(selector).first
            try:
                if await loc.is_visible(timeout=1500):
                    text = (await loc.inner_text()).strip()
                    raise CheckInBotError(f"Delta rejected the trip lookup: {text[:200]}")
            except PlaywrightTimeoutError:
                continue

    async def confirm_seats(self, page: Page, booking: Booking) -> None:
        await self.dismiss_overlays(page)
        await self.click_if_present(page, SELECTORS["select_all_passengers"])
        await self.click_if_present(page, SELECTORS["continue"])

        await self.click_if_present(page, SELECTORS["hazmat_accept"], timeout_ms=8000)
        await self.pause(1.0, 2.0)

        # Seat and upsell screens appear in varying order; step through until
        # the final check-in button shows up.
        for _ in range(4):
            if await self.click_if_present(page, SELECTORS["keep_seats"]):
                await self.pause(1.0, 2.0)
                continue
            if await self.click_if_present(page, SELECTORS["decline_upsell"]):
                await self.pause(1.0, 2.0)
                continue
            break

        await self.human_click(page, SELECTORS["complete_check_in"])
        await page.wait_for_load_state("networkidle")
        await self.pause(1.5, 3.0)

    async def capture_boarding_pass(self, page: Page, booking: Booking) -> BotResult:
        await self.click_if_present(page, SELECTORS["view_boarding_pass"], timeout_ms=10_000)
        await self.first_visible(page, SELECTORS["boarding_pass_ready"])
        await page.wait_for_load_state("networkidle")
        return await self.save_artifacts(page, booking)
