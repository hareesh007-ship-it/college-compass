"""Dynamic college catalog — discovered + user-preferred schools."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from _paths import COLLEGES_DIR

CATALOG_PATH = COLLEGES_DIR / "catalog.json"

STATE_REGION = {
    "Minnesota": "Midwest",
    "Wisconsin": "Midwest",
    "Iowa": "Midwest",
    "Illinois": "Midwest",
    "Indiana": "Midwest",
    "Michigan": "Midwest",
    "Ohio": "Midwest",
    "North Dakota": "Midwest",
    "South Dakota": "Midwest",
    "Missouri": "Midwest",
    "Nebraska": "Midwest",
    "Kansas": "Midwest",
}


def catalog_path() -> Path:
    return CATALOG_PATH


def load_catalog() -> Dict[str, Any]:
    path = catalog_path()
    if not path.is_file():
        return {"schema_version": 1, "colleges": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_catalog(data: Dict[str, Any]) -> Path:
    COLLEGES_DIR.mkdir(parents=True, exist_ok=True)
    data.setdefault("schema_version", 1)
    data["updated_at"] = date.today().isoformat()
    path = catalog_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def catalog_college_names() -> List[str]:
    return [entry["cache_key"] for entry in load_catalog().get("colleges", [])]


def catalog_entry_for(cache_key: str) -> Dict[str, Any]:
    for entry in load_catalog().get("colleges", []):
        if entry.get("cache_key") == cache_key:
            return entry
    return {}


def entry_to_college(entry: Dict[str, Any]):
    from college_finder import ACT_TO_SAT, College

    sat = entry.get("avg_admit_sat")
    act = entry.get("avg_admit_act")
    if not sat and act:
        sat = ACT_TO_SAT.get(int(act), 1100)
    if not sat:
        sat = 1100
    rate = entry.get("admission_rate")
    if rate is None:
        rate = 0.5
    state = entry.get("state") or ""
    return College(
        name=entry["cache_key"],
        state=state,
        region=STATE_REGION.get(state, entry.get("region") or "Other"),
        public_private=entry.get("public_private") or "Public",
        tuition_in_state=entry.get("tuition_in_state"),
        tuition_out_of_state=entry.get("tuition_out_of_state"),
        avg_admit_gpa=float(entry.get("avg_admit_gpa") or 3.5),
        avg_admit_sat=int(sat),
        acceptance_rate_general=float(rate),
        acceptance_rate_major=None,
        major_rate_note=None,
        ed_available=False,
        ea_deadline=None,
        ed_deadline=None,
        regular_deadline=entry.get("regular_deadline") or "See admissions site",
        business_program=bool(entry.get("has_target_program", True)),
        business_program_note=entry.get("business_program_note"),
        source=entry.get("source") or "discovered",
    )


def load_catalog_as_colleges() -> List:
    entries = load_catalog().get("colleges") or []
    return [entry_to_college(e) for e in entries if e.get("cache_key")]
