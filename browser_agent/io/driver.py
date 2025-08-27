"""
Browser driver protocol (abstraction).

This Protocol defines the minimal browser control surface that action
implementations rely on. It allows plugging different backends
(e.g., Playwright, future CDP-based drivers) without changing actions.

Notes:
- `ctx` represents an execution context for a sequence of actions.
  In the Playwright implementation it is a `Page` created via `new_context()`.
- Implementations should provide sensible default timeouts and
  ensure interactions wait for visibility when appropriate.
"""

from __future__ import annotations

from typing import Any, Protocol, Literal


class BrowserDriver(Protocol):
    # -------- lifecycle --------
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def new_context(self) -> Any: ...
    async def close_context(self, ctx: Any) -> None: ...

    # -------- navigation & waits --------
    async def goto(self, ctx: Any, url: str, *, timeout_ms: int | None = None) -> None: ...
    async def wait_for(self, ctx: Any, selector: str, *, timeout_ms: int | None = None) -> None: ...

    # -------- basic interactions --------
    async def click(self, ctx: Any, selector: str, *, timeout_ms: int | None = None) -> None: ...
    async def type_text(
        self,
        ctx: Any,
        selector: str,
        text: str,
        *,
        timeout_ms: int | None = None,
        clear_first: bool = True,
    ) -> None: ...
    async def text_content(
        self, ctx: Any, selector: str, *, timeout_ms: int | None = None
    ) -> str | None: ...

    # -------- common form helpers (new) --------
    async def upload(
        self,
        ctx: Any,
        selector: str,
        file_path: str,
        *,
        timeout_ms: int | None = None,
    ) -> None: ...
    async def select_option(
        self,
        ctx: Any,
        selector: str,
        value: str,
        *,
        by: Literal["value", "label"] = "value",
        timeout_ms: int | None = None,
    ) -> None: ...
    async def check(self, ctx: Any, selector: str, *, timeout_ms: int | None = None) -> None: ...

    # -------- utilities --------
    async def screenshot(self, ctx: Any, path: str, *, full_page: bool = True) -> None: ...
