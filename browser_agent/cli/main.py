# browser_agent/cli/main.py
"""
命令行入口：D1 仅提供帮助与环境自检；D2 开始对接动作与编排循环。
"""
# @file purpose: CLI entrypoint using Typer.

import typer
import json
import asyncio

from rich.console import Console
from ..core.settings import settings
from pathlib import Path
from rich.table import Table
from pydantic import TypeAdapter, ValidationError
from ..core.action import ActionSpec
from ..core import registry
from ..core.errors import ActionExecutionError
from ..io.playwright_driver import PlaywrightDriver


app = typer.Typer(help="browser-agent CLI")
console = Console()


@app.command("doctor")
def doctor() -> None:
    """环境自检：打印关键配置，验证 CLI 可用。"""
    console.print("[bold green]browser-agent[/] environment")
    console.print(f"- headless: {settings.headless}")
    console.print(f"- timeout:  {settings.request_timeout_seconds}s")
    console.print(f"- allowlist domains: {settings.allowed_domains or '[]'}")


@app.command("hello")
def hello(name: str = "world") -> None:
    """最小可运行命令，验证安装与脚手架。"""
    console.print(f"Hello, {name} 👋  (CLI OK)")


@app.command("validate")
def validate(script: Path = typer.Argument(..., help="Path to JSON file of ActionSpec[]")) -> None:
    """
    离线参数校验：读取 JSON 数组 [{name, args}]，逐项用注册表绑定的 Pydantic 模型校验。
    成功 / 失败逐行输出；若存在失败以非零码退出。
    """
    if not script.exists():
        typer.secho(f"[validate] file not found: {script}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    # 先把文件内容校验成 list[ActionSpec]（结构与字段名正确）
    try:
        data = json.loads(script.read_text(encoding="utf-8"))
        specs = TypeAdapter(list[ActionSpec]).validate_python(data)
    except ValidationError as ve:
        typer.secho("[validate] invalid file format for ActionSpec[]", fg=typer.colors.RED)
        console.print(ve)
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
            # 展示首个错误的简要信息（更详细可打印 ve.errors()）
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
) -> None:
    """
    Execute a list of actions: read JSON -> structure check -> param check -> run in browser.
    Prints a table of results; returns non-zero on any failure.
    """
    if not script.exists():
        typer.secho(f"[run] file not found: {script}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    # 1) 读取并做结构校验（list[ActionSpec]）
    try:
        data = json.loads(script.read_text(encoding="utf-8"))
        specs = TypeAdapter(list[ActionSpec]).validate_python(data)
    except ValidationError as ve:
        typer.secho("[run] invalid file format for ActionSpec[]", fg=typer.colors.RED)
        console.print(ve)
        raise typer.Exit(code=2)

    # 2) 导入动作实现，触发注册（很重要）
    try:
        import browser_agent.actions.impl  # noqa: F401
    except Exception as e:  # noqa: BLE001
        typer.secho(f"[run] failed to import actions: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    table = Table(title="Run Results", show_header=True, header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("name")
    table.add_column("result")
    table.add_column("detail")

    async def _run() -> int:
        driver = PlaywrightDriver(headless=headless, slow_mo_ms=slowmo)
        await driver.start()
        ctx = await driver.new_context()
        failures = 0

        try:
            for i, spec in enumerate(specs, start=1):
                try:
                    # 3) 参数校验（基于绑定的 Pydantic v2 模型）
                    _meta, params = registry.validate_spec(spec)
                    # 4) 找到动作函数并执行
                    fn = registry.get_action(spec.name)
                    res = await fn(driver, ctx, params)  # 参数模型实例作为第三参

                    status = "[green]OK[/]" if res.ok else "[yellow]FAIL[/]"
                    detail = "-"
                    if res.extracted_content:
                        text = res.extracted_content
                        detail = (text[:120] + "…") if len(text) > 120 else text
                    elif "url" in res.meta:
                        detail = str(res.meta["url"])

                    if not res.ok:
                        failures += 1
                    table.add_row(str(i), spec.name, status, detail)
                except (ValidationError, KeyError) as e:
                    failures += 1
                    table.add_row(str(i), spec.name, "[red]Invalid[/]", str(e))
                except ActionExecutionError as e:
                    failures += 1
                    table.add_row(str(i), spec.name, "[red]Error[/]", str(e))
                except Exception as e:  # noqa: BLE001
                    failures += 1
                    table.add_row(str(i), spec.name, "[red]Error[/]", f"{type(e).__name__}: {e}")
        finally:
            await driver.close_context(ctx)
            await driver.stop()

        console.print(table)
        return 1 if failures else 0

    code = asyncio.run(_run())
    if code != 0:
        raise typer.Exit(code=code)
    typer.secho("[run] completed successfully", fg=typer.colors.GREEN)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
