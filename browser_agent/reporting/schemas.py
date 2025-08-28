"""
Reporting data models for job application runs.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class JobItem(BaseModel):
    """Minimal representation of a job posting we plan to apply for."""

    url: str
    company: Optional[str] = None
    title: Optional[str] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    extras: Dict[str, Any] = Field(default_factory=dict)


class ApplyStep(BaseModel):
    """One executed step outcome associated with a job application."""

    index: int
    name: str
    ok: bool
    selector: Optional[str] = None
    extracted: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    artifact_path: Optional[str] = None
    detail: str = "-"


class ApplyResult(BaseModel):
    """Application outcome for a single job."""

    job: JobItem
    ok: bool
    steps: List[ApplyStep] = Field(default_factory=list)
    error: Optional[str] = None


class DailyReport(BaseModel):
    """A collection of application results."""

    site: str
    total: int
    success: int
    failure: int
    items: List[ApplyResult]
