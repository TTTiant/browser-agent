# browser_agent/cli/main.py
"""
命令行入口：D1 仅提供帮助与环境自检；D2 开始对接动作与编排循环。
"""
# @file purpose: CLI entrypoint using Typer.

import typer
from rich.console import Console

from ..core.settings import settings

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
