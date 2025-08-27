"""
Core action implementations bound to BrowserDriver:
- open_url / wait_for / click / type / extract_text
- (NEW) upload_resume / select_option / check / snapshot

Each action:
  1) Expects a BrowserDriver + ctx + validated params (Pydantic v2)
  2) Returns ActionResult, or raises ActionExecutionError on failure
"""

# @file purpose: Implement and register core actions.
# mypy: ignore-errors
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

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


# ------------------------------------------------------------------------------
# 新增通用动作（与 PlaywrightDriver 新原语配合）
# 为了不动你现有 params.py，这里先内联参数模型，后续可移入 actions/params.py
# ------------------------------------------------------------------------------


class UploadResumeParams(BaseModel):
    """Upload a local file to <input type=file>."""

    selector: str = Field(..., description="CSS/xpath selector for <input type=file>")
    file_path: str = Field(..., description="Local resume file path")
    timeout_ms: int = 10_000


@action("upload_resume", params_model=UploadResumeParams)
async def upload_resume(
    driver: BrowserDriver, ctx: Any, params: UploadResumeParams
) -> ActionResult:
    try:
        # 依赖 driver.upload(ctx, selector, file_path, timeout_ms=?)
        await driver.upload(ctx, params.selector, params.file_path, timeout_ms=params.timeout_ms)  # type: ignore[attr-defined]
        return ActionResult.success(
            step="upload_resume", selector=params.selector, file=params.file_path
        )
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="upload_resume",
            message="failed to upload file",
            selector=params.selector,
            path=params.file_path,
            cause=e,
        ) from e


class SelectOptionParams(BaseModel):
    """Select an option in <select> by value or label."""

    selector: str
    value: str
    by: Literal["value", "label"] = "value"
    timeout_ms: int = 10_000


@action("select_option", params_model=SelectOptionParams)
async def select_option_action(driver, ctx, params: "SelectOptionParams"):
    """
    依赖 driver.select_option(ctx, selector, value, by="value"|"label", timeout_ms=?)
    """
    try:
        await driver.select_option(
            ctx,
            params.selector,
            params.value,
            by=params.by,
            timeout_ms=params.timeout_ms,
        )
        return ActionResult.success(
            step="select_option",
            selector=params.selector,
            by=params.by,
        )
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="select_option",
            message="failed to select option",
            selector=params.selector,
            details={
                "value": getattr(params, "value", None),
                "by": getattr(params, "by", None),
                "timeout_ms": getattr(params, "timeout_ms", None),
                "cause": repr(e),
            },
            cause=e,
        ) from e


class CheckParams(BaseModel):
    """Check a checkbox/radio (no-op if already checked)."""

    selector: str
    timeout_ms: int = 10_000


@action("check", params_model=CheckParams)
async def check_action(driver: BrowserDriver, ctx: Any, params: CheckParams) -> ActionResult:
    try:
        # 依赖 driver.check(ctx, selector, timeout_ms=?)
        await driver.check(ctx, params.selector, timeout_ms=params.timeout_ms)
        return ActionResult.success(step="check", selector=params.selector)
    except Exception as e:  # noqa: BLE001
        raise ActionExecutionError(
            action="check",
            message="failed to check element",
            selector=params.selector,
            cause=e,
        ) from e


class SnapshotParams(BaseModel):
    """Take a screenshot (default full page)."""

    path: str = Field(..., description="Where to save PNG file")
    full_page: bool = True


@action("snapshot", params_model=SnapshotParams)
async def snapshot_action(
    driver: "BrowserDriver", ctx: any, params: "SnapshotParams"
) -> "ActionResult":
    """
    依赖 driver.screenshot(ctx, path, full_page=?)
    """
    try:
        await driver.screenshot(ctx, params.path, full_page=params.full_page)
        return ActionResult.success(
            step="snapshot",
            path=params.path,
            full_page=params.full_page,
        )
    except Exception as e:  # noqa: BLE001
        # 注意：ActionExecutionError 不接受 path/full_page 关键字参数
        # 把它们放到 details 里，避免 TypeError 覆盖真实根因
        raise ActionExecutionError(
            action="snapshot",
            message="failed to take screenshot",
            details={
                "path": getattr(params, "path", None),
                "full_page": getattr(params, "full_page", None),
                "cause": repr(e),
            },
            cause=e,
        ) from e
