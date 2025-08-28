# browser_agent/core/controller/runner.py
"""
Minimal sequential runner for ActionSpec[].

Responsibilities:
- Validate each spec via registry
- Execute actions with retries
- Optional random per-step delay
- On failure: save screenshot artifact (if artifacts_dir is set)
- Return per-step outcomes for CLI rendering and reporting
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .. import registry
from ..action import ActionSpec
from ..errors import ActionExecutionError


@dataclass
class StepOutcome:
    """UI-friendly outcome used by CLI and reporters."""

    index: int
    name: str
    ok: bool
    detail: str = "-"
    artifact_path: str | None = None
    # Filled from ActionResult on success:
    extracted: str | None = None  # e.g., text extracted by extract_text
    meta: dict[str, Any] | None = None  # e.g., {"selector": "#company"} or {"url": "..."}


class Runner:
    def __init__(
        self,
        *,
        retries: int = 0,
        artifacts_dir: Path | None = None,
        random_delay_ms: tuple[int, int] | None = None,
    ) -> None:
        self.retries = max(0, retries)
        self.artifacts_dir = artifacts_dir
        self.random_delay_ms = random_delay_ms
        if self.artifacts_dir:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, driver: Any, ctx: Any, specs: list[ActionSpec]) -> list[StepOutcome]:
        outcomes: list[StepOutcome] = []

        for i, spec in enumerate(specs, start=1):
            name = spec.name

            # 1) validate params
            try:
                _meta, params = registry.validate_spec(spec)
            except (ValidationError, KeyError) as e:
                artifact = await self._on_failure(driver, ctx, i, name)
                outcomes.append(
                    StepOutcome(
                        index=i,
                        name=name,
                        ok=False,
                        detail=f"invalid spec: {e}",
                        artifact_path=artifact,
                    )
                )
                await self._maybe_delay()
                continue

            # 2) execute with retries
            attempt = 0
            while True:
                try:
                    fn = registry.get_action(name)
                    res = await fn(driver, ctx, params)

                    # Human-friendly detail for CLI
                    detail = "-"
                    if getattr(res, "extracted_content", None):
                        text = res.extracted_content
                        detail = (
                            (text[:120] + "…")
                            if isinstance(text, str) and len(text) > 120
                            else str(text)
                        )
                    elif isinstance(getattr(res, "meta", None), dict):
                        m = res.meta
                        if "url" in m:
                            detail = str(m["url"])
                        elif "selector" in m:
                            detail = f'selector="{m["selector"]}"'

                    # --- SUCCESS PAYLOAD FILL ---
                    extracted = getattr(res, "extracted_content", None)
                    meta = res.meta if isinstance(getattr(res, "meta", None), dict) else None

                    outcomes.append(
                        StepOutcome(
                            index=i,
                            name=name,
                            ok=bool(res.ok),
                            detail=detail,
                            extracted=extracted,
                            meta=meta,
                        )
                    )
                    break

                except ActionExecutionError as e:
                    attempt += 1
                    if attempt > self.retries:
                        artifact = await self._on_failure(driver, ctx, i, name)
                        outcomes.append(
                            StepOutcome(
                                index=i,
                                name=name,
                                ok=False,
                                detail=str(e),
                                artifact_path=artifact,
                            )
                        )
                        break
                    # simple backoff
                    await asyncio.sleep(0.5 * attempt)

                finally:
                    await self._maybe_delay()

        return outcomes

    async def _maybe_delay(self) -> None:
        if not self.random_delay_ms:
            return
        low, high = self.random_delay_ms
        if low < 0 or high < 0 or high < low:
            return
        ms = random.randint(low, high)
        await asyncio.sleep(ms / 1000)

    async def _on_failure(self, driver: Any, ctx: Any, index: int, name: str) -> str | None:
        """Best-effort failure artifact (screenshot)."""
        if not self.artifacts_dir:
            return None
        png = self.artifacts_dir / f"fail-{index:02d}-{name}.png"
        try:
            await driver.screenshot(ctx, str(png), full_page=True)
            return str(png)
        except Exception:
            return None
