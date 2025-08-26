import asyncio
import functools
import http.server
import socketserver
import threading
from pathlib import Path

import pytest
from pydantic import TypeAdapter
from collections.abc import Iterator
from browser_agent.io.playwright_driver import PlaywrightDriver
from browser_agent.core.action import ActionSpec
from browser_agent.core import registry
import browser_agent.actions.impl  # 注册动作


@pytest.fixture(scope="session")
def web_server() -> Iterator[str]:
    root = Path(__file__).resolve().parents[1]  # 仓库根（含 tests/fixtures）
    port = 8765
    Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.mark.asyncio
async def test_smoke_end_to_end(web_server: str) -> None:
    d = PlaywrightDriver(headless=True)
    await d.start()
    ctx = await d.new_context()
    try:
        data = [
            {"name": "open_url", "args": {"url": f"{web_server}/tests/fixtures/smoke.html"}},
            {"name": "type", "args": {"selector": "#q", "text": "hello"}},
            {"name": "click", "args": {"selector": "#go"}},
            {"name": "wait_for", "args": {"selector": "#result", "timeout_ms": 5000}},
            {"name": "extract_text", "args": {"selector": "#result"}},
        ]
        specs = TypeAdapter(list[ActionSpec]).validate_python(data)

        extracted = None
        for spec in specs:
            _meta, params = registry.validate_spec(spec)
            fn = registry.get_action(spec.name)
            res = await fn(d, ctx, params)
            if spec.name == "extract_text":
                extracted = res.extracted_content

        assert extracted == "hello"
    finally:
        await d.close_context(ctx)
        await d.stop()
