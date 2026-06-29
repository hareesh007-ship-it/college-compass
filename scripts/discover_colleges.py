"""Discover colleges from Excel profile (Scorecard + user list + optional LLM).

Full reference for setup, API key, pipeline, fallbacks, and quality ranking:
  docs/DELIVERY_CHANNEL.md §8
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Set

from college_catalog import save_catalog
from discovery_quality import discovery_quality_score, passes_discovery_filter
from llm_discover import suggest_school_names
from scorecard_api import parse_row, search_schools

STATE_TO_ABBREV = {
    "Minnesota": "MN", "Wisconsin": "WI", "Iowa": "IA", "Illinois": "IL", "Indiana": "IN",
    "Michigan": "MI", "Ohio": "OH", "North Dakota": "ND", "South Dakota": "SD", "Missouri": "MO",
    "Nebraska": "NE", "Kansas": "KS", "California": "CA", "New York": "NY", "Texas": "TX",
}

ABBREV_TO_STATE = {v: k for k, v in STATE_TO_ABBREV.items()}

REGION_ABBREVS = {
    "Midwest": ["MN", "WI", "IA", "IL", "IN", "MI", "OH", "ND", "SD", "MO", "NE", "KS"],
    "Minnesota": ["MN"],
}

MAX_SCORECARD = 40


def _state_abbrevs(profile: Dict[str, Any]) -> List[str]:
    prefs = profile.get("preferences") or {}
    abbrevs: Set[str] = set()
    home = profile.get("state_of_residence") or ""
    if home in STATE_TO_ABBREV:
        abbrevs.add(STATE_TO_ABBREV[home])
    for region in prefs.get("regions") or []:
        for ab in REGION_ABBREVS.get(region, []):
            abbrevs.add(ab)
    for state in prefs.get("surrounding_states") or []:
        if state in STATE_TO_ABBREV:
            abbrevs.add(STATE_TO_ABBREV[state])
    return sorted(abbrevs)


def _tuition_for_student(entry: Dict[str, Any], home_abbrev: str) -> int:
    st = entry.get("state") or ""
    if st == home_abbrev:
        return entry.get("tuition_in_state") or entry.get("tuition_out_of_state") or 0
    return entry.get("tuition_out_of_state") or entry.get("tuition_in_state") or 0


def _passes_budget_and_type(entry: Dict[str, Any], profile: Dict[str, Any], home_abbrev: str) -> bool:
    prefs = profile.get("preferences") or {}
    if entry.get("public_private") == "Public" and not prefs.get("public_ok", True):
        return False
    if entry.get("public_private") == "Private" and not prefs.get("private_ok", True):
        return False
    budget = int(profile.get("budget_max_tuition_per_year") or 999999)
    tuition = _tuition_for_student(entry, home_abbrev)
    if tuition and tuition > budget:
        return False
    return True


def _catalog_entry(cache_key: str, parsed: Dict[str, Any], source: str) -> Dict[str, Any]:
    state_full = ABBREV_TO_STATE.get(parsed.get("state") or "", parsed.get("state") or "")
    return {
        "cache_key": cache_key,
        "scorecard_id": parsed.get("scorecard_id"),
        "scorecard_name": parsed.get("scorecard_name") or cache_key,
        "state": state_full,
        "city": parsed.get("city"),
        "public_private": parsed.get("public_private"),
        "tuition_in_state": parsed.get("tuition_in_state"),
        "tuition_out_of_state": parsed.get("tuition_out_of_state"),
        "admission_rate": parsed.get("admission_rate"),
        "avg_admit_sat": parsed.get("avg_admit_sat"),
        "avg_admit_act": parsed.get("avg_admit_act"),
        "school_url": parsed.get("school_url"),
        "source": source,
        "has_target_program": True,
        "student_size": parsed.get("student_size"),
        "business_program_pct": parsed.get("business_program_pct"),
        "discovery_score": parsed.get("discovery_score"),
    }


def _best_scorecard_row(user_name: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(rows) == 1:
        return rows[0]
    query = user_name.lower()
    best = rows[0]
    best_score = -1
    for row in rows:
        sname = (row.get("school.name") or "").lower()
        score = sum(1 for word in query.split() if len(word) > 2 and word in sname)
        if "twin cities" in query and "twin cities" in sname:
            score += 15
        if "carlson" in query and "minnesota" in sname and "moorhead" not in sname and "duluth" not in sname:
            score += 10
        if "duluth" in query and "duluth" in sname:
            score += 15
        if "duluth" in query and "twin cities" in sname:
            score -= 20
        size = row.get("latest.student.size") or 0
        try:
            score += min(int(size) / 2000, 8)
        except (TypeError, ValueError):
            pass
        if score > best_score:
            best_score = score
            best = row
    return best


def _resolve_name(name: str, home_abbrev: str) -> Dict[str, Any]:
    from catalog_bootstrap import _public_private, _state_for_college
    from college_research import get_college, resolve_cache_key

    cache_key = resolve_cache_key(name) or name
    cached = get_college(cache_key)
    if cached:
        tuition = cached.get("tuition") or {}
        rates = cached.get("acceptance_rates") or {}
        home_state = ABBREV_TO_STATE.get(home_abbrev, "")
        return _catalog_entry(
            cache_key,
            {
                "scorecard_id": (cached.get("research_method") or {}).get("scorecard_id"),
                "scorecard_name": cache_key.split(" - ")[0],
                "state": _state_for_college(cache_key, {home_state}, home_state) or home_state,
                "public_private": _public_private(cache_key),
                "tuition_in_state": tuition.get("in_state"),
                "tuition_out_of_state": tuition.get("out_of_state") or tuition.get("in_state"),
                "admission_rate": (rates.get("university_general") or {}).get("value"),
            },
            "user_preferred",
        )

    query = name.split(" - ")[0].strip() if " - " in name else name
    query = re.sub(r"\b(school|university|college)\b", "", query, flags=re.I).strip() or query
    try:
        rows = search_schools(name=query, states=[home_abbrev] if home_abbrev else None, per_page=10)
        if not rows:
            rows = search_schools(name=query, per_page=10)
    except (RuntimeError, OSError) as exc:
        print(f"WARN: Scorecard lookup failed for {name!r}: {exc}")
        rows = []
    if not rows:
        return _catalog_entry(
            name,
            {
                "scorecard_id": None,
                "scorecard_name": name,
                "state": home_abbrev,
                "public_private": "Private",
            },
            "user_preferred",
        )
    parsed = parse_row(_best_scorecard_row(name, rows))
    scorecard_name = parsed.get("scorecard_name") or name
    cache_key = resolve_cache_key(scorecard_name) or resolve_cache_key(name) or scorecard_name
    return _catalog_entry(cache_key, parsed, "user_preferred")


def discover_colleges(profile: Dict[str, Any]) -> Dict[str, Any]:
    home_abbrev = STATE_TO_ABBREV.get(profile.get("state_of_residence") or "", "")
    state_list = _state_abbrevs(profile)
    by_id: Dict[Any, Dict[str, Any]] = {}
    ordered: List[Dict[str, Any]] = []

    def add(entry: Dict[str, Any]) -> None:
        sid = entry.get("scorecard_id")
        key = entry["cache_key"]
        if entry.get("source") == "user_preferred":
            for i, existing in enumerate(ordered):
                if existing.get("cache_key") == key:
                    ordered[i] = entry
                    if sid is not None:
                        by_id[sid] = entry
                    return
        if sid is not None and sid in by_id:
            return
        if sid is not None:
            by_id[sid] = entry
        elif any(e["cache_key"] == key for e in ordered):
            return
        ordered.append(entry)

    for raw_name in profile.get("schools_interested_in") or []:
        name = str(raw_name).strip()
        if name:
            add(_resolve_name(name, home_abbrev))

    for llm_name in suggest_school_names(profile):
        add(_resolve_name(llm_name, home_abbrev))

    if state_list:
        try:
            rows = search_schools(states=state_list, per_page=100)
        except (RuntimeError, OSError) as exc:
            print(f"WARN: College Scorecard search failed: {exc}")
            rows = []
        candidates: List[Dict[str, Any]] = []
        for row in rows:
            parsed = parse_row(row)
            if not parsed.get("offers_bachelors", True):
                continue
            if not _passes_budget_and_type(parsed, profile, home_abbrev):
                continue
            if not passes_discovery_filter(parsed, profile):
                continue
            parsed["is_home_state"] = bool(home_abbrev and parsed.get("state") == home_abbrev)
            parsed["discovery_score"] = discovery_quality_score(parsed, profile)
            candidates.append(parsed)
        candidates.sort(
            key=lambda p: (
                -p.get("discovery_score", 0),
                -(p.get("student_size") or 0),
                -(p.get("business_program_pct") or 0),
            )
        )
        for parsed in candidates[:MAX_SCORECARD]:
            add(_catalog_entry(parsed["scorecard_name"], parsed, "scorecard"))

    return {
        "schema_version": 1,
        "discovered_at": date.today().isoformat(),
        "intended_major": profile.get("intended_major"),
        "state_abbrevs_searched": state_list,
        "colleges": ordered,
    }


def discover_and_save(profile: Dict[str, Any]) -> Dict[str, Any]:
    catalog = discover_colleges(profile)
    path = save_catalog(catalog)
    n = len(catalog["colleges"])
    print(f"Discovered {n} colleges → {path}")
    for entry in catalog["colleges"][:8]:
        print(f"  - {entry['cache_key']} ({entry['source']})")
    if n > 8:
        print(f"  ... and {n - 8} more")
    return catalog
