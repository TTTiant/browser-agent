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

from browser_agent.reporting.schemas import JobItem, ApplyResult, ApplyStep, DailyReport
from browser_agent.reporting.writer import write_report
from browser_agent.actions.sites.demo import DemoConfig, build_job_apply_specs


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


@app.command("daily")
def daily(
    site: str = typer.Option("demo", help="Site adapter name"),
    urls_file: Path = typer.Option(None, help="Text file with one job URL per line"),
    limit: int = typer.Option(5, help="Max number of jobs"),
    out_dir: Path = typer.Option(Path("artifacts"), help="Output directory for reports"),
    headless: bool = typer.Option(True, "--headless/--no-headless"),
    slowmo: int = typer.Option(0, "--slowmo"),
    retries: int = typer.Option(0, "--retries"),
    random_delay_ms: Tuple[int, int] = typer.Option((0, 0), "--random-delay-ms"),
) -> None:
    # ensure actions registered
    try:
        import browser_agent.actions.impl  # noqa: F401
    except Exception as e:
        typer.secho(f"[daily] failed to import actions: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    async def _run() -> int:
        from ..core.controller.runner import Runner, StepOutcome  # lazy import

        driver = PlaywrightDriver(headless=headless, slow_mo_ms=slowmo)
        await driver.start()
        ctx = await driver.new_context()
        try:
            # build url list
            job_urls: list[str] = []
            if urls_file and urls_file.exists():
                for line in urls_file.read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if s:
                        job_urls.append(s)
            else:
                job_urls.append("http://127.0.0.1:8765/tests/fixtures/smoke.html")

            rnd = None if (random_delay_ms[0] == 0 and random_delay_ms[1] == 0) else random_delay_ms
            runner = Runner(retries=retries, artifacts_dir=out_dir, random_delay_ms=rnd)

            results: list[ApplyResult] = []
            for url in job_urls[:limit]:
                cfg = DemoConfig(url=url)
                specs = build_job_apply_specs(cfg)
                rows: list[StepOutcome] = await runner.run(driver, ctx, specs)

                # map outcomes -> report
                steps: list[ApplyStep] = []
                ok = True
                err = None
                company = title = salary = location = None
                for r in rows:
                    sel = r.meta.get("selector") if (r.meta and isinstance(r.meta, dict)) else None
                    steps.append(
                        ApplyStep(
                            index=r.index,
                            name=r.name,
                            ok=r.ok,
                            selector=sel,
                            extracted=r.extracted,
                            meta=(r.meta or {}),
                            artifact_path=r.artifact_path,
                            detail=r.detail,
                        )
                    )
                    if not r.ok:
                        ok = False
                        err = err or r.detail
                    if sel == "#company" and r.extracted:
                        company = r.extracted
                    elif sel == "#title" and r.extracted:
                        title = r.extracted
                    elif sel == "#salary" and r.extracted:
                        salary = r.extracted
                    elif sel == "#location" and r.extracted:
                        location = r.extracted

                results.append(
                    ApplyResult(
                        job=JobItem(
                            url=url, company=company, title=title, salary=salary, location=location
                        ),
                        ok=ok,
                        steps=steps,
                        error=err,
                    )
                )

            report = DailyReport(
                site=site,
                total=len(results),
                success=sum(1 for r in results if r.ok),
                failure=sum(1 for r in results if not r.ok),
                items=results,
            )
            json_path, csv_path = write_report(report, out_dir)
            console.print(f"[bold green]Report written[/]: {json_path}  |  {csv_path}")
            return 0
        finally:
            await driver.close_context(ctx)
            await driver.stop()

    code = asyncio.run(_run())
    if code != 0:
        raise typer.Exit(code=code)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
