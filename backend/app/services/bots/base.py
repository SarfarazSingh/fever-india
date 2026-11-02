"""Playwright RPA base class for airline web check-in."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Iterable

from playwright.async_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.config import BOARDING_PASS_DIR, Settings, get_settings
from app.models import Booking

logger = logging.getLogger(__name__)

STEALTH_INIT_SCRIPT = r"""
(() => {
  Object.defineProperty(Navigator.prototype, 'webdriver', { get: () => undefined });

  if (!window.chrome) { window.chrome = {}; }
  if (!window.chrome.runtime) {
    window.chrome.runtime = { connect: () => {}, sendMessage: () => {}, id: undefined };
  }
  window.chrome.app = window.chrome.app || { isInstalled: false };
  window.chrome.csi = window.chrome.csi || (() => ({}));
  window.chrome.loadTimes = window.chrome.loadTimes || (() => ({}));

  Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

  const fakePlugins = [
    { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
    { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
  ];
  Object.defineProperty(navigator, 'plugins', {
    get: () => {
      const arr = fakePlugins.map(p => Object.assign(Object.create(Plugin.prototype), p, { length: 1 }));
      arr.item = i => arr[i];
      arr.namedItem = n => arr.find(p => p.name === n);
      arr.refresh = () => {};
      return arr;
    },
  });

  Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
  Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

  const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
  if (originalQuery) {
    window.navigator.permissions.query = (parameters) =>
      parameters && parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
  }

  const patchWebGL = (proto) => {
    if (!proto) return;
    const getParameter = proto.getParameter;
    proto.getParameter = function (param) {
      if (param === 37445) return 'Intel Inc.';               // UNMASKED_VENDOR_WEBGL
      if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
      return getParameter.call(this, param);
    };
  };
  patchWebGL(window.WebGLRenderingContext && WebGLRenderingContext.prototype);
  patchWebGL(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
})();
"""

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-default-browser-check",
    "--no-first-run",
]


class CheckInBotError(RuntimeError):
    def __init__(self, message: str, screenshot_path: Path | None = None):
        super().__init__(message)
        self.screenshot_path = screenshot_path


@dataclass
class BotResult:
    boarding_pass_path: Path
    screenshot_path: Path | None = None


class AirlineCheckInBot(ABC):
    """Template for a single airline's web check-in flow.

    Subclasses implement the four steps; the base class owns the browser,
    stealth configuration, human-like input helpers and artifact storage.
    """

    airline_iata: ClassVar[str]
    check_in_url: ClassVar[str]
    output_dir: ClassVar[Path] = BOARDING_PASS_DIR

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -- steps implemented by each airline ---------------------------------

    async def open(self, page: Page) -> None:
        response = await page.goto(self.check_in_url, wait_until="domcontentloaded")
        await self.raise_if_blocked(page, response.status if response else None)
        await self.dismiss_overlays(page)

    BLOCK_MARKERS: ClassVar[tuple[str, ...]] = (
        "access denied",
        "you don't have permission to access",
        "request unsuccessful. incapsula",
        "pardon our interruption",
        "verify you are human",
        "are you a robot",
    )

    async def raise_if_blocked(self, page: Page, status: int | None) -> None:
        try:
            text = (await page.locator("body").inner_text(timeout=5000))[:2000].lower()
        except PlaywrightTimeoutError:
            text = ""
        marker = next((m for m in self.BLOCK_MARKERS if m in text), None)
        if marker or status in (403, 429):
            raise CheckInBotError(
                f"Blocked by {self.airline_iata} bot protection "
                f"(HTTP {status if status is not None else 'n/a'}"
                f"{', page says ' + repr(marker) if marker else ''})"
            )

    @abstractmethod
    async def fill_lookup(self, page: Page, booking: Booking) -> None:
        """Enter the PNR / passenger name and submit the trip lookup."""

    @abstractmethod
    async def confirm_seats(self, page: Page, booking: Booking) -> None:
        """Click through travel-document, hazmat and seat confirmation steps."""

    @abstractmethod
    async def capture_boarding_pass(self, page: Page, booking: Booking) -> BotResult:
        """Reach the boarding pass page and persist it via `save_artifacts`."""

    async def dismiss_overlays(self, page: Page) -> None:
        """Close cookie banners and marketing modals if present."""
        for selector in (
            "#onetrust-accept-btn-handler",
            "button:has-text('Accept All')",
            "button:has-text('Accept all cookies')",
            "button[aria-label='Close']",
        ):
            loc = page.locator(selector).first
            try:
                if await loc.is_visible(timeout=1500):
                    await loc.click()
                    await self.pause(0.3, 0.8)
            except PlaywrightTimeoutError:
                continue
            except Exception:  # noqa: BLE001 - overlays are best effort
                continue

    # -- orchestration ------------------------------------------------------

    async def run(self, booking: Booking) -> BotResult:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.settings.playwright_headless, args=LAUNCH_ARGS)
            try:
                context = await self._new_context(browser)
                page = await context.new_page()
                page.set_default_timeout(self.settings.playwright_timeout_ms)
                try:
                    await self.open(page)
                    await self.fill_lookup(page, booking)
                    await self.confirm_seats(page, booking)
                    return await self.capture_boarding_pass(page, booking)
                except Exception as exc:
                    shot = await self._failure_screenshot(page, booking)
                    if isinstance(exc, CheckInBotError):
                        exc.screenshot_path = exc.screenshot_path or shot
                        raise
                    raise CheckInBotError(f"{type(exc).__name__}: {exc}", shot) from exc
                finally:
                    await context.close()
            finally:
                await browser.close()

    async def _new_context(self, browser: Browser) -> BrowserContext:
        context = await browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": random.choice([1366, 1440, 1536]), "height": random.choice([864, 900])},
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
            device_scale_factor=1,
            java_script_enabled=True,
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        await context.add_init_script(STEALTH_INIT_SCRIPT)
        return context

    # -- helpers ------------------------------------------------------------

    @staticmethod
    async def pause(low: float = 0.4, high: float = 1.2) -> None:
        await asyncio.sleep(random.uniform(low, high))

    async def first_visible(self, page: Page, selectors: Iterable[str], timeout_ms: int | None = None) -> Locator:
        """Return the first selector that becomes visible, trying each in turn."""
        selectors = list(selectors)
        deadline_ms = timeout_ms or self.settings.playwright_timeout_ms
        per_try = max(1000, deadline_ms // max(1, len(selectors)))
        for selector in selectors:
            loc = page.locator(selector).first
            try:
                await loc.wait_for(state="visible", timeout=per_try)
                return loc
            except PlaywrightTimeoutError:
                continue
        raise CheckInBotError(f"None of the expected elements appeared: {selectors}")

    async def human_type(self, page: Page, selectors: Iterable[str], text: str) -> None:
        field = await self.first_visible(page, selectors)
        await field.scroll_into_view_if_needed()
        await field.click()
        await field.fill("")
        await field.press_sequentially(text, delay=random.randint(60, 140))
        await self.pause(0.2, 0.6)

    async def human_click(self, page: Page, selectors: Iterable[str], timeout_ms: int | None = None) -> None:
        target = await self.first_visible(page, selectors, timeout_ms)
        await target.scroll_into_view_if_needed()
        await target.hover()
        await self.pause(0.15, 0.45)
        await target.click()

    async def click_if_present(self, page: Page, selectors: Iterable[str], timeout_ms: int = 4000) -> bool:
        try:
            await self.human_click(page, selectors, timeout_ms)
            return True
        except CheckInBotError:
            return False

    def artifact_stem(self, booking: Booking) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{booking.pnr_code}_{ts}"

    async def save_artifacts(self, page: Page, booking: Booking) -> BotResult:
        stem = self.artifact_stem(booking)
        png_path = self.output_dir / f"{stem}.png"
        await page.screenshot(path=str(png_path), full_page=True)
        if self.settings.playwright_headless:
            pdf_path = self.output_dir / f"{stem}.pdf"
            await page.emulate_media(media="screen")
            await page.pdf(path=str(pdf_path), format="A4", print_background=True)
            return BotResult(boarding_pass_path=pdf_path, screenshot_path=png_path)
        # page.pdf() is only supported by headless Chromium.
        return BotResult(boarding_pass_path=png_path, screenshot_path=png_path)

    async def _failure_screenshot(self, page: Page, booking: Booking) -> Path | None:
        path = self.output_dir / f"{self.artifact_stem(booking)}_failed.png"
        try:
            await page.screenshot(path=str(path), full_page=True)
            return path
        except Exception:  # noqa: BLE001
            logger.debug("Could not capture failure screenshot", exc_info=True)
            return None
