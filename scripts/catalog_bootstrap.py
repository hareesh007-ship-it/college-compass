"""Bootstrap catalog from researched cache when discovery API is unavailable."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Set, Tuple

from _paths import DATA
from catalog_refine import _score_from_ranks
from college_catalog import load_catalog, save_catalog
from college_finder import MN_RECIPROCITY_STATES
from college_research import college_rankings, reload_cache
from discovery_quality import _name_skip

MIDWEST_STATES = {
    "Minnesota", "Wisconsin", "Iowa", "Illinois", "Indiana", "Michigan", "Ohio",
    "North Dakota", "South Dakota", "Missouri", "Nebraska", "Kansas",
}

STATE_IN_NAME = re.compile(
    r"\b(Minnesota|Wisconsin|Iowa|Illinois|Indiana|Michigan|Ohio|"
    r"North Dakota|South Dakota|Missouri|Nebraska|Kansas)\b"
)

NAME_STATE_HINTS: Tuple[Tuple[str, str], ...] = (
    ("Purdue University", "Indiana"),
    ("Indiana University", "Indiana"),
    ("Iowa State University", "Iowa"),
    ("University of Iowa", "Iowa"),
    ("North Dakota State University", "North Dakota"),
    ("University of Illinois", "Illinois"),
    ("University of Wisconsin", "Wisconsin"),
    ("Minnesota State University", "Minnesota"),
    ("St. Cloud State University", "Minnesota"),
    ("Winona State University", "Minnesota"),
    ("University of St. Thomas", "Minnesota"),
    ("Bethel University", "Minnesota"),
    ("Augsburg University", "Minnesota"),
)


def _allowed_states(profile: Dict[str, Any]) -> Set[str]:
    allowed: Set[str] = {profile.get("state_of_residence") or ""}
    prefs = profile.get("preferences") or {}
    allowed.update(prefs.get("surrounding_states") or [])
    if "Midwest" in (prefs.get("regions") or []):
        allowed.update(MIDWEST_STATES)
    allowed.discard("")
    return allowed


def _state_for_college(name: str, allowed: Set[str], home: str) -> str:
    match = STATE_IN_NAME.search(name)
    if match:
        st = match.group(1)
        if st in allowed or st == home:
            return st
    for prefix, st in NAME_STATE_HINTS:
        if name.startswith(prefix) or prefix in name:
            if st in allowed or st == home:
                return st
    return ""


PRIVATE_UNIVERSITIES = (
    "University of St. Thomas",
    "Bethel University",
    "Augsburg University",
)


def _public_private(name: str) -> str:
    if any(p in name for p in PRIVATE_UNIVERSITIES):
        return "Private"
    if any(
        k in name
        for k in ("University of", "State University", "Iowa State", "Purdue University")
    ):
        return "Public"
    return "Private"


def _tuition_for_profile(
    tuition: Dict[str, Any],
    college_state: str,
    home_state: str,
    public_private: str,
) -> int:
    in_st = tuition.get("in_state") or 0
    oos = tuition.get("out_of_state") or in_st or 0
    if college_state == home_state:
        return in_st or oos
    if (
        public_private == "Public"
        and home_state == "Minnesota"
        and college_state in MN_RECIPROCITY_STATES
    ):
        return in_st or oos
    return oos or in_st


def _qualifies_rank(block: Dict[str, Any], rank_score: float) -> bool:
    ranks = block.get("rankings") or {}
    nat = ranks.get("national_university")
    biz = ranks.get("undergrad_business")
    if biz is not None:
        return True
    if nat is not None and nat <= 150:
        return True
    return rank_score >= 20


def bootstrap_catalog_from_cache(profile: Dict[str, Any], min_schools: int = 15) -> Dict[str, Any]:
    """Add strong in-region cache entries when catalog is too thin."""
    reload_cache()
    catalog = load_catalog()
    existing = {e["cache_key"] for e in catalog.get("colleges", [])}
    target = min_schools + len(profile.get("schools_interested_in") or [])
    if len(existing) >= target:
        return catalog

    with open(DATA / "college_research_cache.json", encoding="utf-8") as f:
        cache = json.load(f)

    allowed = _allowed_states(profile)
    home = profile.get("state_of_residence") or ""
    budget = int(profile.get("budget_max_tuition_per_year") or 999999)
    candidates: List[Dict[str, Any]] = []

    for name, block in cache.get("colleges", {}).items():
        if name in existing or _name_skip(name):
            continue
        ranks = block.get("rankings") or {}
        if not (ranks.get("national_university") or ranks.get("undergrad_business")):
            continue

        state = _state_for_college(name, allowed, home)
        if not state:
            continue

        public_private = _public_private(name)
        tuition = block.get("tuition") or {}
        cost = _tuition_for_profile(tuition, state, home, public_private)
        if cost and cost > budget * 1.05:
            continue

        rank_score = _score_from_ranks(college_rankings(name))
        if not _qualifies_rank(block, rank_score):
            continue

        candidates.append(
            {
                "cache_key": name,
                "scorecard_id": (block.get("research_method") or {}).get("scorecard_id"),
                "scorecard_name": name,
                "state": state,
                "public_private": public_private,
                "tuition_in_state": tuition.get("in_state"),
                "tuition_out_of_state": tuition.get("out_of_state") or tuition.get("in_state"),
                "admission_rate": (block.get("acceptance_rates") or {}).get("university_general", {}).get("value"),
                "source": "cache_bootstrap",
                "has_target_program": True,
                "discovery_score": rank_score,
            }
        )

    candidates.sort(key=lambda e: -(e.get("discovery_score") or 0))
    for entry in candidates:
        if len(catalog.get("colleges", [])) >= target:
            break
        catalog.setdefault("colleges", []).append(entry)

    save_catalog(catalog)
    added = len(catalog["colleges"]) - len(existing)
    if added:
        print(f"Bootstrapped {added} schools from researched cache → catalog")
    return catalog
