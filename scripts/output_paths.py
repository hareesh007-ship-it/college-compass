"""Output file paths derived from student profile."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from _paths import OUTPUT
from load_profile import profile_first_name


def gap_html_path(profile: Dict[str, Any], major_label: Optional[str] = None) -> Path:
    """Gap analysis HTML path — with optional major suffix for multi-major runs.

    No suffix:   Alex - College Prep Gap Analysis.html
    With suffix: Alex - College Prep Gap Analysis - Business.html
    """
    first = profile_first_name(profile)
    if major_label:
        return OUTPUT / f"{first} - College Prep Gap Analysis - {major_label}.html"
    return OUTPUT / f"{first} - College Prep Gap Analysis.html"


def selection_output_paths(profile: Dict[str, Any]) -> Dict[str, Path]:
    """XLSX + gap-analysis HTML paths for this student."""
    first = profile_first_name(profile)
    return {
        "xlsx": OUTPUT / f"{first} - US College Selection.xlsx",
        "gap_html": gap_html_path(profile),
    }


def tuition_column_label(profile: Dict[str, Any]) -> str:
    return f"Tuition ({profile_first_name(profile)})"
