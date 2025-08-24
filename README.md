# browser-agent
Minimal web agent baseline using Python 3.11, Playwright + Chromium, Pydantic v2, custom planner/loop.

## Quickstart
uv venv --python 3.11
source .venv/bin/activate
uv sync
uvx playwright install chromium
pre-commit install
browser-agent --help
