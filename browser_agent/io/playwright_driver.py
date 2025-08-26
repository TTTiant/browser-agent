"""
Playwright-based BrowserDriver implementation.

Conforms to io/driver.py's BrowserDriver Protocol:
- start() / stop()
- new_context() / close_context(ctx)
- goto(ctx, url)
- click(ctx, selector)
- type_text(ctx, selector, text)
- wait_for(ctx, selector, timeout_ms?)
- text_content(ctx, selector) -> Optional[str]
- screenshot(ctx, path)
"""
# @file purpose: Provide Playwright-based BrowserDriver implementation.

from __future__ import annotations

from typing import Any, Dict, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PwTimeoutError,
    async_playwright,
)


class PlaywrightDriver:
    """
    A concrete BrowserDriver based on Playwright Chromium.
    - `ctx` in this implementation is a Playwright `Page`.
    - Each `new_context()` creates an incognito BrowserContext + a new Page.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        slow_mo_ms: int = 0,
        default_nav_timeout_ms: int = 30_000,
        default_action_timeout_ms: int = 10_000,
    ) -> None:
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.default_nav_timeout_ms = default_nav_timeout_ms
        self.default_action_timeout_ms = default_action_timeout_ms

        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        # Track which BrowserContext a Page belongs to so we can close cleanly.
        self._page_to_context: Dict[Page, BrowserContext] = {}

    # ---------------- lifecycle ----------------

    async def start(self) -> None:
        """Launch Playwright and a Chromium browser once."""
        if self._browser is not None:
            return
        pw = await async_playwright().start()
        self._pw = pw
        self._browser = await pw.chromium.launch(headless=self.headless, slow_mo=self.slow_mo_ms)

    async def stop(self) -> None:
        """Close all contexts and stop Playwright."""
        try:
            # Close all contexts we created
            for page, ctx in list(self._page_to_context.items()):
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await ctx.close()
                except Exception:
                    pass
            self._page_to_context.clear()

            if self._browser is not None:
                await self._browser.close()
        finally:
            if self._pw is not None:
                await self._pw.stop()
            self._pw = None
            self._browser = None

    # ---------------- context/page management ----------------

    async def new_context(self) -> Any:
        """
        Create an incognito BrowserContext and a Page, return the Page as ctx.
        The Protocol uses `Any` for ctx; here it's a Playwright Page.
        """
        self._ensure_started()
        assert self._browser is not None
        ctx = await self._browser.new_context()
        page = await ctx.new_page()
        self._page_to_context[page] = ctx
        return page  # ctx

    async def close_context(self, ctx: Any) -> None:
        """Close the given Page and its BrowserContext."""
        page = self._as_page(ctx)
        # Close page first, then context
        try:
            await page.close()
        finally:
            context = self._page_to_context.pop(page, None)
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

    # ---------------- primitives ----------------

    async def goto(self, ctx: Any, url: str) -> None:
        """Navigate and wait for load."""
        page = self._as_page(ctx)
        await page.goto(url, timeout=self.default_nav_timeout_ms, wait_until="load")

    async def click(self, ctx: Any, selector: str) -> None:
        """Wait until visible, then click."""
        page = self._as_page(ctx)
        locator = page.locator(selector)
        await locator.wait_for(state="visible", timeout=self.default_action_timeout_ms)
        await locator.scroll_into_view_if_needed()
        await locator.click(timeout=self.default_action_timeout_ms)

    async def type_text(self, ctx: Any, selector: str, text: str) -> None:
        """
        Fill (preferred) or type into an input.
        We try fill() first for determinism; fall back to type() if needed.
        """
        page = self._as_page(ctx)
        locator = page.locator(selector)
        await locator.wait_for(state="visible", timeout=self.default_action_timeout_ms)
        await locator.scroll_into_view_if_needed()
        try:
            await locator.fill(text, timeout=self.default_action_timeout_ms)
        except PwTimeoutError:
            await locator.click(timeout=self.default_action_timeout_ms)
            await locator.type(text, timeout=self.default_action_timeout_ms)

    async def wait_for(self, ctx: Any, selector: str, timeout_ms: int | None = None) -> None:
        """Wait until the element is visible (or timeout)."""
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = self.default_action_timeout_ms if timeout_ms is None else timeout_ms
        await locator.wait_for(state="visible", timeout=to)

    async def text_content(self, ctx: Any, selector: str) -> str | None:
        """Return visible text for the first matched element (stripped)."""
        page = self._as_page(ctx)
        locator = page.locator(selector)
        await locator.wait_for(state="visible", timeout=self.default_action_timeout_ms)
        await locator.scroll_into_view_if_needed()
        txt = await locator.first.text_content(timeout=self.default_action_timeout_ms)
        return txt.strip() if txt is not None else None

    async def screenshot(self, ctx: Any, path: str) -> None:
        """Take a full-page screenshot to the given path."""
        page = self._as_page(ctx)
        await page.screenshot(path=path, full_page=True)

    # ---------------- internals ----------------

    def _ensure_started(self) -> None:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")

    @staticmethod
    def _as_page(ctx: Any) -> Page:
        if not isinstance(ctx, Page):
            raise TypeError("ctx must be a Playwright Page (returned by new_context()).")
        return ctx
