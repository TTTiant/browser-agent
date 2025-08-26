"""
Core action implementations bound to BrowserDriver:
- open_url / wait_for / click / type / extract_text
Each action:
  1) Expects a BrowserDriver + ctx + validated params (Pydantic v2)
  2) Returns ActionResult, or raises ActionExecutionError on failure
"""
# @file purpose: Implement and register core actions.

from __future__ import annotations

from typing import Any

from browser_agent.core.registry import action
from browser_agent.core.result import ActionResult
from browser_agent.core.errors import ActionExecutionError
from browser_agent.io.driver import BrowserDriver  # Protocol

from .params import (
    OpenUrlParams,
    WaitForParams,
    ClickParams,
    TypeParams,
    ExtractTextParams,
)


@action("open_url", params_model=OpenUrlParams)
async def open_url(driver: BrowserDriver, ctx: Any, params: OpenUrlParams) -> ActionResult:
    try:
        await driver.goto(ctx, str(params.url))
        return ActionResult.success(step="open_url", url=str(params.url))
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="open_url",
            message="failed to open url",
            url=str(params.url),
            cause=e,
        ) from e


@action("wait_for", params_model=WaitForParams)
async def wait_for(driver: BrowserDriver, ctx: Any, params: WaitForParams) -> ActionResult:
    try:
        await driver.wait_for(ctx, params.selector, timeout_ms=params.timeout_ms)
        return ActionResult.success(step="wait_for", selector=params.selector)
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="wait_for",
            message="element did not become visible in time",
            selector=params.selector,
            cause=e,
        ) from e


@action("click", params_model=ClickParams)
async def click(driver: BrowserDriver, ctx: Any, params: ClickParams) -> ActionResult:
    try:
        await driver.click(ctx, params.selector)
        return ActionResult.success(step="click", selector=params.selector)
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="click",
            message="failed to click element",
            selector=params.selector,
            cause=e,
        ) from e


@action("type", params_model=TypeParams)
async def type_action(driver: BrowserDriver, ctx: Any, params: TypeParams) -> ActionResult:
    """
    Named type_action to avoid shadowing Python's built-in `type`.
    Registered name is still "type".
    """
    try:
        await driver.type_text(ctx, params.selector, params.text)
        return ActionResult.success(step="type", selector=params.selector, length=len(params.text))
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="type",
            message="failed to input text",
            selector=params.selector,
            cause=e,
        ) from e


@action("extract_text", params_model=ExtractTextParams)
async def extract_text(driver: BrowserDriver, ctx: Any, params: ExtractTextParams) -> ActionResult:
    try:
        txt = await driver.text_content(ctx, params.selector)
        return ActionResult(
            ok=True,
            extracted_content=txt,
            include_in_memory=True,
            meta={"step": "extract_text", "selector": params.selector, "empty": txt is None},
        )
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="extract_text",
            message="failed to extract text",
            selector=params.selector,
            cause=e,
        ) from e
