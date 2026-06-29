"""Sync catalog + College Scorecard data into college_research_cache.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional, Tuple

from _paths import DATA
from scorecard_api import fetch_school_by_id, parse_row, search_schools

CACHE_PATH = DATA / "college_research_cache.json"


@dataclass
class SyncReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0


def _load_cache() -> Dict[str, Any]:
    if not CACHE_PATH.is_file():
        return {
            "schema_version": 1,
            "last_updated": date.today().isoformat(),
            "rankings_source": "US News Best Colleges 2026 where researched; Scorecard otherwise",
            "colleges": {},
        }
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: Dict[str, Any]) -> None:
    cache["last_updated"] = date.today().isoformat()
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _rate_block(value: Optional[float], label: str, source_url: str) -> Dict[str, Any]:
    if value is None:
        return {
            "value": None,
            "display": "Not yet researched",
            "label": label,
            "source_url": source_url,
            "source_note": "Auto stub — run scoped research for program-level rate",
        }
    return {
        "value": value,
        "display": f"{value * 100:.1f}%",
        "label": label,
        "source_url": source_url,
        "source_note": "College Scorecard (auto)",
    }


def is_scorecard_stub(block: Dict[str, Any]) -> bool:
    return (block.get("research_method") or {}).get("backend") == "scorecard"


def _tuition_from_scorecard(block: Dict[str, Any]) -> bool:
    tuition = block.get("tuition") or {}
    year = str(tuition.get("year") or "")
    url = str(tuition.get("source_url") or "").lower()
    return "scorecard" in year.lower() or "collegescorecard" in url


def _rate_from_scorecard(block: Dict[str, Any]) -> bool:
    rate = (block.get("acceptance_rates") or {}).get("university_general") or {}
    note = str(rate.get("source_note") or "")
    return "Scorecard" in note or "scorecard" in note.lower()


def _stub_from_parsed(parsed: Dict[str, Any], catalog_entry: Dict[str, Any]) -> Dict[str, Any]:
    today = date.today().isoformat()
    url = parsed.get("school_url") or catalog_entry.get("school_url") or "https://collegescorecard.ed.gov/"
    if url and not url.startswith("http"):
        url = f"https://{url}"
    rate = parsed.get("admission_rate")
    return {
        "researched_at": today,
        "rankings": {
            "national_university": None,
            "undergrad_business": None,
            "entrepreneurship": None,
            "regional_universities_midwest": None,
            "notes": "Scorecard stub — US News ranks filled by research step when available",
        },
        "tuition": {
            "in_state": parsed.get("tuition_in_state"),
            "out_of_state": parsed.get("tuition_out_of_state"),
            "year": "Scorecard latest",
            "source_url": url,
        },
        "acceptance_rates": {
            "university_general": _rate_block(rate, "University-wide (Scorecard)", url),
            "business_program": _rate_block(None, "Program-specific — not yet researched", url),
        },
        "deadlines": {
            "early_action": None,
            "early_decision": None,
            "regular": None,
            "ed_available": False,
        },
        "business_program_note": f"Discovered via {catalog_entry.get('source', 'scorecard')}; confirm program fit.",
        "research_method": {
            "backend": "scorecard",
            "scope": "catalog sync",
            "researched_at": today,
            "source_urls": [url] if url else [],
            "scorecard_id": parsed.get("scorecard_id"),
        },
    }


def _find_existing_key(colleges: Dict[str, Any], entry: Dict[str, Any]) -> Optional[str]:
    sid = entry.get("scorecard_id")
    if sid is not None:
        for key, block in colleges.items():
            if (block.get("research_method") or {}).get("scorecard_id") == sid:
                return key
    cache_key = entry.get("cache_key")
    name = entry.get("scorecard_name") or cache_key
    for key in colleges:
        if key == cache_key or key == name:
            return key
        if name and (name in key or key in name):
            return key
    return None


def _fetch_parsed(catalog_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sid = catalog_entry.get("scorecard_id")
    if sid is not None:
        try:
            row = fetch_school_by_id(int(sid))
            if row:
                return row
        except (RuntimeError, ValueError, TypeError, OSError):
            pass
    name = catalog_entry.get("scorecard_name") or catalog_entry.get("cache_key")
    state = catalog_entry.get("state") or ""
    abbrev = state[:2].upper() if len(state) == 2 else None
    try:
        rows = search_schools(name=name.split(" - ")[0], states=[abbrev] if abbrev else None, per_page=5)
        if not rows:
            rows = search_schools(name=name.split(" - ")[0], per_page=5)
        if rows:
            return parse_row(rows[0])
    except (RuntimeError, OSError):
        return None
    return None


def _catalog_parsed(catalog_entry: Dict[str, Any]) -> Dict[str, Any]:
    url = catalog_entry.get("school_url") or ""
    if url and not url.startswith("http"):
        url = f"https://{url}"
    return {
        "scorecard_id": catalog_entry.get("scorecard_id"),
        "scorecard_name": catalog_entry.get("scorecard_name") or catalog_entry.get("cache_key"),
        "school_url": url,
        "tuition_in_state": catalog_entry.get("tuition_in_state"),
        "tuition_out_of_state": catalog_entry.get("tuition_out_of_state"),
        "admission_rate": catalog_entry.get("admission_rate"),
        "avg_admit_sat": catalog_entry.get("avg_admit_sat"),
        "avg_admit_act": catalog_entry.get("avg_admit_act"),
        "student_size": catalog_entry.get("student_size"),
        "business_program_pct": catalog_entry.get("business_program_pct"),
    }


def _merge_parsed(block: Dict[str, Any], parsed: Dict[str, Any]) -> bool:
    if not parsed:
        return False
    stub = is_scorecard_stub(block)
    updated = False
    url = parsed.get("school_url") or (block.get("tuition") or {}).get("source_url") or ""
    if url and not str(url).startswith("http"):
        url = f"https://{url}"

    if stub or _tuition_from_scorecard(block):
        tuition = block.setdefault("tuition", {})
        for key in ("in_state", "out_of_state"):
            val = parsed.get(f"tuition_{key}")
            if val is not None and tuition.get(key) != val:
                tuition[key] = val
                updated = True
        if updated or stub:
            tuition["year"] = "Scorecard latest"
            if url:
                tuition["source_url"] = url

    if stub or _rate_from_scorecard(block):
        rate = parsed.get("admission_rate")
        if rate is not None:
            rates = block.setdefault("acceptance_rates", {})
            gen = rates.setdefault("university_general", {})
            if gen.get("value") != rate:
                rates["university_general"] = _rate_block(rate, "University-wide (Scorecard)", url)
                updated = True

    rm = block.setdefault("research_method", {})
    sid = parsed.get("scorecard_id")
    if sid is not None and rm.get("scorecard_id") != sid:
        rm["scorecard_id"] = sid
        updated = True
    if stub and url:
        urls = list(rm.get("source_urls") or [])
        if url not in urls:
            urls.append(url)
            rm["source_urls"] = urls
            updated = True

    if updated and stub:
        block["researched_at"] = date.today().isoformat()
    return updated


def sync_catalog_to_cache(catalog: Dict[str, Any]) -> SyncReport:
    """Ensure every catalog school has a cache entry and refresh Scorecard fields."""
    cache = _load_cache()
    colleges = cache.setdefault("colleges", {})
    report = SyncReport()

    for entry in catalog.get("colleges") or []:
        parsed = _fetch_parsed(entry) or _catalog_parsed(entry)
        existing_key = _find_existing_key(colleges, entry)
        if existing_key:
            entry["cache_key"] = existing_key
            block = colleges[existing_key]
            if _merge_parsed(block, parsed):
                report.updated += 1
            else:
                report.unchanged += 1
            continue

        cache_key = entry["cache_key"]
        if cache_key in colleges:
            entry["cache_key"] = cache_key
            if _merge_parsed(colleges[cache_key], parsed):
                report.updated += 1
            else:
                report.unchanged += 1
            continue

        colleges[cache_key] = _stub_from_parsed(parsed, entry)
        report.added += 1

    _save_cache(cache)
    from college_research import reload_cache

    reload_cache()
    print(
        f"Cache sync: {report.added} added, {report.updated} updated, "
        f"{report.unchanged} unchanged → {CACHE_PATH}"
    )
    return report
