#!/usr/bin/env python3
"""Standalone CLI: export gap analysis markdown to a printable HTML file.

Usage:
    python3 scripts/export_gap_analysis_html.py [output_path]

The pipeline calls build_gap_analysis.write_gap_analysis() directly.
This script is for manual re-export without re-running the full pipeline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _paths import STUDENT_DATA, load_env_file

load_env_file()

from build_gap_analysis import build_gap_markdown, wrap_gap_html
from load_profile import load_profile
from output_paths import selection_output_paths


def main() -> int:
    profile = load_profile()
    paths = selection_output_paths(profile)
    html_path = Path(sys.argv[1]) if len(sys.argv) > 1 else paths["gap_html"]
    matches_path = STUDENT_DATA / "college_matches.json"
    if not matches_path.is_file():
        print(f"Match report not found: {matches_path}")
        print("Run college-compass run first.")
        return 1
    with open(matches_path, encoding="utf-8") as f:
        report = json.load(f)
    doc = wrap_gap_html(build_gap_markdown(profile, report), profile.get("name") or "Student")
    html_path.write_text(doc, encoding="utf-8")
    print(f"Wrote {html_path}")
    print("Open in browser and use File → Print → Save as PDF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
