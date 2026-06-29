"""Load published acceptance rate data with source URLs."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from _paths import DATA

RATES_PATH = DATA / "acceptance_rates.json"


def load_acceptance_data() -> Dict[str, Any]:
    try:
        from college_research import acceptance_schools, load_cache

        schools = acceptance_schools()
        if schools:
            cache = load_cache()
            return {
                "_schema_note": cache.get("notes", ""),
                "_source": "data/college_research_cache.json",
                "schools": schools,
            }
    except (ImportError, FileNotFoundError, json.JSONDecodeError):
        pass
    with open(RATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_school_rates(school_name: str) -> Optional[Dict[str, Any]]:
    data = load_acceptance_data()
    return data.get("schools", {}).get(school_name)


def rate_for_fit(school_name: str) -> Tuple[Optional[float], str]:
    """Return (numeric rate for matching, explanation). Prefer business program rate."""
    entry = get_school_rates(school_name)
    if not entry:
        return None, "No rate data"

    biz = entry.get("business_program", {})
    if biz.get("value") is not None:
        return biz["value"], biz.get("label", "Business program rate")

    sec = entry.get("business_program_secondary", {})
    if sec.get("value") is not None and sec.get("use_for_fit"):
        return sec["value"], sec.get("label", "Secondary business rate")

    gen = entry.get("university_general", {})
    if gen.get("value") is not None:
        return gen["value"], gen.get("label", "University general rate")

    return None, biz.get("display", "Not published")


def display_pair(school_name: str) -> Tuple[str, str, str]:
    """Return (col1 display, col2 display, combined source note)."""
    entry = get_school_rates(school_name)
    if not entry:
        return "", "", ""

    gen = entry.get("university_general", {})
    biz = entry.get("business_program", {})

    col1 = gen.get("display", "")
    col2 = biz.get("display", "")

    # Append secondary business rate in col2 when primary not published
    sec = entry.get("business_program_secondary")
    if sec and (biz.get("value") is None):
        col2 = f"{col2}; alt: {sec.get('display', '')}" if col2 else sec.get("display", "")

    sources = []
    if gen.get("source_url"):
        sources.append(f"General: {gen['source_url']}")
    if biz.get("source_url"):
        sources.append(f"Business: {biz['source_url']}")
    if sec and sec.get("source_url"):
        sources.append(f"Alt: {sec['source_url']}")

    note = " | ".join(sources)
    if biz.get("source_note"):
        note = f"{biz['source_note']} ({note})" if note else biz["source_note"]
    return col1, col2, note
