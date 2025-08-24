"""
Playwright 实现：D1 仅提供结构与基本生命周期，具体交互在 D3/D4 完成。
"""
# @file purpose: Provide Playwright-based BrowserDriver implementation (skeleton).

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from ..core.settings import settings


class PlaywrightDriver:
    def __init__(self) -> None:
        self._p: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._p = await async_playwright().start()
        assert self._p is not None
        self._browser = await self._p.chromium.launch(headless=settings.headless)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._p:
            await self._p.stop()

    async def new_context(self) -> BrowserContext:
        assert self._browser is not None, "Driver not started"
        return await self._browser.new_context()

    async def close_context(self, ctx: BrowserContext) -> None:
        await ctx.close()

    async def goto(self, ctx: BrowserContext, url: str) -> None:
        page = await ctx.new_page()
        await page.goto(url)

    async def click(self, ctx: BrowserContext, selector: str) -> None:
        page = ctx.pages[-1]
        await page.click(selector)

    async def type_text(self, ctx: BrowserContext, selector: str, text: str) -> None:
        page = ctx.pages[-1]
        await page.fill(selector, text)

    async def wait_for(
        self, ctx: BrowserContext, selector: str, timeout_ms: int | None = None
    ) -> None:
        page = ctx.pages[-1]
        await page.wait_for_selector(selector, timeout=timeout_ms)

    async def text_content(self, ctx: BrowserContext, selector: str) -> str | None:
        page = ctx.pages[-1]
        return await page.text_content(selector)

    async def screenshot(self, ctx: BrowserContext, path: str) -> None:
        page = ctx.pages[-1]
        await page.screenshot(path=path)
