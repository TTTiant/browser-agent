# browser_agent/actions/sites/demo.py
"""
Demo site adapter that builds ActionSpec sequences for simple pages.

This adapter assumes each job posting page exposes predictable selectors:
- #company, #title, #salary, #location (if present)
- It also demonstrates a simple "apply" click flow if #apply exists.

You can adapt the selectors per real site in follow-up adapters.
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

from ...core.action import ActionSpec


class DemoConfig(BaseModel):
    """Config to build apply flow for a job URL."""

    url: str = Field(..., description="Job posting url")
    query_text: str = "hello"  # For demo typing (if page has an input#q)
    selectors_company: str = "#company"
    selectors_title: str = "#title"
    selectors_salary: str = "#salary"
    selectors_location: str = "#location"
    selectors_apply_button: str = "#apply"  # if exists


def build_job_apply_specs(cfg: DemoConfig) -> List[ActionSpec]:
    """
    Build a sequence of ActionSpec for one job page:
      1) open url
      2) type demo query if exists
      3) (optional) click "apply" if exists
      4) extract company/title/salary/location
      5) snapshot
    """
    specs: List[ActionSpec] = []

    specs.append(ActionSpec(name="open_url", args={"url": cfg.url}))

    # If the demo page has an input#q and button#go, try to simulate a search.
    specs.append(ActionSpec(name="type", args={"selector": "#q", "text": cfg.query_text}))
    specs.append(ActionSpec(name="click", args={"selector": "#go"}))

    # Extract fields
    specs.append(ActionSpec(name="extract_text", args={"selector": cfg.selectors_company}))
    specs.append(ActionSpec(name="extract_text", args={"selector": cfg.selectors_title}))
    specs.append(ActionSpec(name="extract_text", args={"selector": cfg.selectors_salary}))
    specs.append(ActionSpec(name="extract_text", args={"selector": cfg.selectors_location}))

    # Snapshot at the end
    specs.append(
        ActionSpec(name="snapshot", args={"path": "artifacts/demo-job.png", "full_page": True})
    )
    return specs
