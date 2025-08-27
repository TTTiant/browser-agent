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

Extra primitives (common form ops):
- upload(ctx, selector, file_path)
- select_option(ctx, selector, value, by="value"|"label")
- check(ctx, selector)
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PwTimeoutError,
    async_playwright,
    Playwright,
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
        default_timeout_ms: int = 30_000,
    ) -> None:
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.default_timeout_ms = default_timeout_ms

        self._pw: Optional[Playwright] = None  # playwright instance
        self._browser: Optional[Browser] = None
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
            # close all pages/contexts we created
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

    async def new_context(self) -> Page:
        """
        Create a fresh incognito context + page.
        Returns the Page object to be used as `ctx`.
        """
        self._ensure_started()
        assert self._browser is not None
        ctx = await self._browser.new_context()
        # set a sensible default operation timeout on the context
        ctx.set_default_timeout(self.default_timeout_ms)
        page = await ctx.new_page()
        self._page_to_context[page] = ctx
        return page

    async def close_context(self, ctx: Any) -> None:
        """Close the page and its owning context."""
        page = self._as_page(ctx)
        context = self._page_to_context.pop(page, None)
        try:
            await page.close()
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

    # ---------------- primitives ----------------

    async def goto(self, ctx: Any, url: str, *, timeout_ms: Optional[int] = None) -> None:
        page = self._as_page(ctx)
        await page.goto(url, timeout=timeout_ms or self.default_timeout_ms, wait_until="load")

    async def wait_for(self, ctx: Any, selector: str, *, timeout_ms: Optional[int] = None) -> None:
        page = self._as_page(ctx)
        locator = page.locator(selector)
        await locator.wait_for(state="visible", timeout=timeout_ms or self.default_timeout_ms)

    async def click(self, ctx: Any, selector: str, *, timeout_ms: Optional[int] = None) -> None:
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = timeout_ms or self.default_timeout_ms
        await locator.wait_for(state="visible", timeout=to)
        await locator.scroll_into_view_if_needed()
        await locator.click(timeout=to)

    async def type_text(
        self,
        ctx: Any,
        selector: str,
        text: str,
        *,
        timeout_ms: Optional[int] = None,
        clear_first: bool = True,
    ) -> None:
        """
        Prefer fill() for determinism; fall back to type() for tricky widgets.
        """
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = timeout_ms or self.default_timeout_ms
        await locator.wait_for(state="visible", timeout=to)
        await locator.scroll_into_view_if_needed()
        if clear_first:
            try:
                await locator.fill(text, timeout=to)
                return
            except PwTimeoutError:
                pass  # fall back to click+type
        await locator.click(timeout=to)
        await locator.type(text, timeout=to)

    async def text_content(
        self, ctx: Any, selector: str, *, timeout_ms: Optional[int] = None
    ) -> Optional[str]:
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = timeout_ms or self.default_timeout_ms
        await locator.wait_for(state="visible", timeout=to)
        await locator.scroll_into_view_if_needed()
        text = await locator.first.text_content(timeout=to)
        return text.strip() if text is not None else None

    async def screenshot(self, ctx: Any, path: str, *, full_page: bool = True) -> None:
        page = self._as_page(ctx)
        # ensure parent dir exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=path, full_page=full_page)

    # ----------- extra primitives for forms -----------

    async def upload(
        self, ctx: Any, selector: str, file_path: str, *, timeout_ms: Optional[int] = None
    ) -> None:
        """
        Upload a local file to <input type="file"> via set_input_files().
        """
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = timeout_ms or self.default_timeout_ms
        await locator.wait_for(state="visible", timeout=to)

        # NEW: ensure file exists to avoid confusing Playwright error downstream
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"upload(): file not found: {file_path}")
        await locator.set_input_files(str(p), timeout=to)

    async def select_option(
        self,
        ctx: Any,
        selector: str,
        value: str,
        *,
        by: str = "value",  # or "label"
        timeout_ms: Optional[int] = None,
    ) -> None:
        """
        Select an option in <select>. Choose by 'value' (default) or by 'label'.
        """
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = timeout_ms or self.default_timeout_ms
        await locator.wait_for(state="visible", timeout=to)
        if by == "label":
            await locator.select_option(label=value, timeout=to)
        else:
            await locator.select_option(value=value, timeout=to)

    async def check(self, ctx: Any, selector: str, *, timeout_ms: Optional[int] = None) -> None:
        """
        Check a checkbox/radio; no-op if already checked.
        """
        page = self._as_page(ctx)
        locator = page.locator(selector)
        to = timeout_ms or self.default_timeout_ms
        await locator.wait_for(state="visible", timeout=to)
        await locator.check(timeout=to)

    # ---------------- internals ----------------

    def _ensure_started(self) -> None:
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")

    @staticmethod
    def _as_page(ctx: Any) -> Page:
        if not isinstance(ctx, Page):
            raise TypeError("ctx must be a Playwright Page (returned by new_context()).")
        return ctx
