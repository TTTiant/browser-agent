# browser-agent
Minimal web agent baseline using Python 3.11, Playwright + Chromium, Pydantic v2, custom planner/loop.

## Quickstart
uv venv --python 3.11
source .venv/bin/activate
uv sync
uvx playwright install chromium
pre-commit install
browser-agent --help

## Validate a script (offline)

You can validate a list of actions without launching a browser.

1) Create a JSON file (`specs.json`) with an array of `ActionSpec`:
```json
[
  {"name": "open_url", "args": {"url": "https://example.com"}},
  {"name": "click",    "args": {"selector": "#submit"}}
]


## Run a script (headless or visible)

You can execute an ActionSpec list end-to-end with a real browser.

1) Start a local HTTP server (from repo root) so the fixture is reachable:
```bash
python -m http.server 8000 --bind 127.0.0.1

2)Create Json file
[
  {"name":"open_url","args":{"url":"http://127.0.0.1:8000/tests/fixtures/smoke.html"}},
  {"name":"type","args":{"selector":"#q","text":"hello"}},
  {"name":"click","args":{"selector":"#go"}},
  {"name":"wait_for","args":{"selector":"#result","timeout_ms":5000}},
  {"name":"extract_text","args":{"selector":"#result"}}
]

3)Run: browser-agent run specs/smoke.json --no-headless --slowmo 200
