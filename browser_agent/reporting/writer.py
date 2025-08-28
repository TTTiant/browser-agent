# browser_agent/reporting/writer.py
"""
Writers to persist DailyReport as JSON and CSV.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Tuple

from .schemas import DailyReport


def write_report(report: DailyReport, out_dir: Path) -> Tuple[Path, Path]:
    """
    Write a DailyReport into out_dir as JSON and CSV.
    Returns (json_path, csv_path).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "report.json"
    csv_path = out_dir / "report.csv"

    # JSON
    json_path.write_text(report.model_dump_json(indent=2, by_alias=True), encoding="utf-8")

    # CSV: one row per job with basic fields (first error per job if any)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["site", "url", "company", "title", "salary", "location", "ok", "error"])
        for item in report.items:
            writer.writerow(
                [
                    report.site,
                    item.job.url,
                    item.job.company or "",
                    item.job.title or "",
                    item.job.salary or "",
                    item.job.location or "",
                    "OK" if item.ok else "FAIL",
                    (item.error or ""),
                ]
            )

    return json_path, csv_path
