"""
CLI entrypoint.

D1: doctor/hello for env & smoke.
D2/D3: validate (offline spec check) and run (execute actions in browser).
This version uses Runner for retries, random delay, and failure artifacts.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Tuple

import typer
from pydantic import TypeAdapter, ValidationError
from rich.console import Console
from rich.table import Table

from ..core.settings import settings
from ..core.action import ActionSpec
from ..core import registry
from ..core.errors import ActionExecutionError
from ..core.controller.runner import Runner, StepOutcome
from ..io.playwright_driver import PlaywrightDriver

app = typer.Typer(help="browser-agent CLI")
console = Console()


@app.command("doctor")
def doctor() -> None:
    """Environment check: print key settings to confirm CLI is usable."""
    console.print("[bold green]browser-agent[/] environment")
    console.print(f"- headless: {settings.headless}")
    console.print(f"- timeout:  {settings.request_timeout_seconds}s")
    console.print(f"- allowlist domains: {settings.allowed_domains or '[]'}")


@app.command("hello")
def hello(name: str = "world") -> None:
    """Minimal smoke command."""
    console.print(f"Hello, {name} 👋  (CLI OK)")


@app.command("validate")
def validate(script: Path = typer.Argument(..., help="Path to JSON file of ActionSpec[]")) -> None:
    """
    Offline spec validation: read JSON array [{name, args}] and validate each item
    against the params model bound in the registry. Print a table result and exit
    non-zero if any failures.
    """
    if not script.exists():
        typer.secho(f"[validate] file not found: {script}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    try:
        data = json.loads(script.read_text(encoding="utf-8"))
        specs = TypeAdapter(list[ActionSpec]).validate_python(data)
    except ValidationError as ve:
        typer.secho("[validate] invalid file format for ActionSpec[]", fg=typer.colors.RED)
        console.print(ve)
        raise typer.Exit(code=2)

    try:
        import browser_agent.actions.impl  # noqa: F401
    except Exception as e:  # noqa: BLE001
        typer.secho(f"[validate] failed to import actions: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    table = Table(title="Validation Results", show_header=True, header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("name")
    table.add_column("result")
    table.add_column("detail")

    failures = 0
    for i, spec in enumerate(specs, start=1):
        try:
            _meta, _params = registry.validate_spec(spec)
            table.add_row(str(i), spec.name, "[green]OK[/]", "-")
        except KeyError as ke:
            failures += 1
            table.add_row(str(i), spec.name, "[red]Not Registered[/]", str(ke))
        except ValidationError as ve:
            failures += 1
            msg = ve.errors()[0].get("msg", "invalid args")
            table.add_row(str(i), spec.name, "[red]Invalid Args[/]", msg)

    console.print(table)
    if failures:
        raise typer.Exit(code=1)
    typer.secho("[validate] all specs passed", fg=typer.colors.GREEN)


@app.command("run")
def run(
    script: Path = typer.Argument(..., help="Path to JSON file of ActionSpec[]"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run browser headless"),
    slowmo: int = typer.Option(0, "--slowmo", help="Slow motion in ms (debug)"),
    retries: int = typer.Option(0, "--retries", help="Retry times on ActionExecutionError"),
    artifacts_dir: Path = typer.Option(
        Path("artifacts"), "--artifacts-dir", help="Where to save failure screenshots"
    ),
    # NOTE: Typer parses tuple as two space-separated ints, e.g. "--random-delay-ms 500 1500"
    random_delay_ms: Tuple[int, int] = typer.Option(
        (0, 0),
        "--random-delay-ms",
        help="Random delay range in ms, e.g. --random-delay-ms 500 1500",
    ),
) -> None:
    """
    Execute a list of actions: read JSON -> structure check -> param check -> run in browser.
    Uses Runner to handle retries, optional random delay, and failure artifacts.
    Prints a table of results; returns non-zero on any failure.
    """
    if not script.exists():
        typer.secho(f"[run] file not found: {script}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    # 1) Read and structure-validate (list[ActionSpec])
    try:
        data = json.loads(script.read_text(encoding="utf-8"))
        specs = TypeAdapter(list[ActionSpec]).validate_python(data)
    except ValidationError as ve:
        typer.secho("[run] invalid file format for ActionSpec[]", fg=typer.colors.RED)
        console.print(ve)
        raise typer.Exit(code=2)

    # 2) Import action implementations to trigger registration
    try:
        import browser_agent.actions.impl  # noqa: F401
    except Exception as e:  # noqa: BLE001
        typer.secho(f"[run] failed to import actions: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    async def _run() -> int:
        driver = PlaywrightDriver(headless=headless, slow_mo_ms=slowmo)
        await driver.start()
        ctx = await driver.new_context()
        try:
            # 3) Runner execution
            rnd = None if (random_delay_ms[0] == 0 and random_delay_ms[1] == 0) else random_delay_ms
            runner = Runner(retries=retries, artifacts_dir=artifacts_dir, random_delay_ms=rnd)
            rows: list[StepOutcome] = await runner.run(driver, ctx, specs)

            # 4) Render results
            table = Table(title="Run Results", show_header=True, header_style="bold")
            table.add_column("#", justify="right", style="dim")
            table.add_column("name")
            table.add_column("result")
            table.add_column("detail")

            failures = 0
            for r in rows:
                result = "[green]OK[/]" if r.ok else "[red]FAIL[/]"
                detail = r.detail
                if (not r.ok) and r.artifact_path:
                    detail = f"{detail} (artifact: {r.artifact_path})"
                if not r.ok:
                    failures += 1
                table.add_row(str(r.index), r.name, result, detail)

            console.print(table)
            return 1 if failures else 0

        finally:
            await driver.close_context(ctx)
            await driver.stop()

    code = asyncio.run(_run())
    if code != 0:
        raise typer.Exit(code=code)
    typer.secho("[run] completed successfully", fg=typer.colors.GREEN)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
