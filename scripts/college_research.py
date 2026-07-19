"""Load and apply cached college research from data/college_research_cache.json."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from _paths import DATA

CACHE_PATH = DATA / "college_research_cache.json"

_CACHE: Optional[Dict[str, Any]] = None


def load_cache(path: Path = CACHE_PATH) -> Dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        if not path.is_file():
            raise FileNotFoundError(
                f"Research cache not found: {path}\n"
                "Run: college-compass --student <name> run  (to build it)\n"
                "Or:  cp data/college_research_cache.json.example data/college_research_cache.json"
            )
        with open(path, encoding="utf-8") as f:
            _CACHE = json.load(f)
    return _CACHE


def reload_cache(path: Path = CACHE_PATH) -> Dict[str, Any]:
    global _CACHE
    _CACHE = None
    return load_cache(path)


def resolve_cache_key(name: str) -> Optional[str]:
    """Map a user-entered school name to an exact cache key when possible."""
    colleges = load_cache().get("colleges", {})
    if name in colleges:
        return name
    low = name.lower().strip()
    for key in colleges:
        if key.lower() == low:
            return key
    query_tokens = [
        t
        for t in re.split(r"[\s,.()-]+", low)
        if len(t) > 2 and t not in {"school", "university", "college", "state"}
    ]
    if not query_tokens:
        return None
    best_key: Optional[str] = None
    best_score = 0
    for key in colleges:
        key_low = key.lower()
        score = sum(1 for token in query_tokens if token in key_low)
        for token in query_tokens:
            if token in {"duluth", "cloud", "thomas", "carlson", "mankato"} and token in key_low:
                score += 5
        if score > best_score:
            best_score = score
            best_key = key
    if best_score >= 2 or (best_score >= 1 and len(query_tokens) == 1):
        return best_key
    return None


def matches_user_interest(college_name: str, interested: List[str]) -> bool:
    """True if the college matches any Schools especially interested in entry."""
    if not interested:
        return False
    resolved = resolve_cache_key(college_name) or college_name
    for item in interested:
        item = str(item).strip()
        if not item:
            continue
        if college_name in item or item in college_name:
            return True
        item_key = resolve_cache_key(item) or item
        if resolved == item_key or resolved in item_key or item_key in resolved:
            return True
    return False


def get_college(name: str) -> Optional[Dict[str, Any]]:
    key = resolve_cache_key(name) or name
    return load_cache().get("colleges", {}).get(key)


def college_rankings(name: str) -> Dict[str, Any]:
    """US News 2026 ranks for sheet + matcher."""
    data = load_cache()
    entry = get_college(name) or {}
    rankings = entry.get("rankings", {})
    return {
        "us_news_national": rankings.get("national_university"),
        "us_news_undergrad_business": rankings.get("undergrad_business"),
        "us_news_entrepreneurship": rankings.get("entrepreneurship"),
        "us_news_regional_midwest": rankings.get("regional_universities_midwest"),
        "us_news_regional_note": rankings.get("regional_note"),
        "us_news_rankings_source": data.get("rankings_source", ""),
    }


def sort_rank_key(entry: Dict[str, Any], intended_major: str = "") -> int:
    display, _ = program_rank_for_major(entry, intended_major)
    if display.startswith("R-MW #"):
        try:
            return int(display.replace("R-MW #", "").split()[0])
        except ValueError:
            pass
    if display and display != "—":
        try:
            return int(display.split()[0])
        except ValueError:
            pass
    for key in ("us_news_undergrad_business", "us_news_national", "us_news_regional_midwest"):
        val = entry.get(key)
        if val is not None:
            return val
    return 999


def _major_rank_kind(intended_major: str) -> str:
    """Map student intended major to US News specialty bucket."""
    m = (intended_major or "").lower()
    if "entrepreneur" in m:
        return "entrepreneurship"
    if any(k in m for k in ("business", "management", "finance", "accounting", "marketing", "economics")):
        return "undergrad_business"
    return "undergrad_business"


def us_news_column_label(intended_major: str) -> str:
    kind = _major_rank_kind(intended_major)
    labels = {
        "entrepreneurship": "US News — Entrepreneurship Rank (2026)",
        "undergrad_business": "US News — Undergrad Business Rank (2026)",
    }
    return labels.get(kind, "US News — Program Rank (2026)")


def accept_rate_program_column_label(intended_major: str) -> str:
    """Sheet header for program-level accept rate (column paired with university general)."""
    kind = _major_rank_kind(intended_major)
    labels = {
        "entrepreneurship": "Accept Rate (Entrepreneurship Program)",
        "undergrad_business": "Accept Rate (Business Program)",
    }
    return labels.get(kind, "Accept Rate (Program)")


def program_rank_for_major(entry: Dict[str, Any], intended_major: str) -> tuple[str, str]:
    """
    Return (display rank, optional fallback note).
    Priority: major-specific specialty → undergrad business → regional Midwest → national.
    """
    kind = _major_rank_kind(intended_major)

    if kind == "entrepreneurship":
        ent = entry.get("us_news_entrepreneurship")
        if ent is not None:
            return str(ent), ""
        biz = entry.get("us_news_undergrad_business")
        if biz is not None:
            return str(biz), "business program"
        reg = entry.get("us_news_regional_midwest")
        if reg is not None:
            return f"R-MW #{reg}", "regional"
        nat = entry.get("us_news_national")
        if nat is not None:
            return str(nat), "national"
        return "—", ""

    biz = entry.get("us_news_undergrad_business")
    if biz is not None:
        return str(biz), ""
    reg = entry.get("us_news_regional_midwest")
    if reg is not None:
        return f"R-MW #{reg}", "regional"
    nat = entry.get("us_news_national")
    if nat is not None:
        return str(nat), "national"
    return "—", ""


def acceptance_schools() -> Dict[str, Any]:
    """Acceptance rate block keyed by college name (for acceptance_data.py)."""
    schools: Dict[str, Any] = {}
    for name, entry in load_cache().get("colleges", {}).items():
        rates = entry.get("acceptance_rates")
        if rates:
            schools[name] = rates
    return schools


def apply_to_college(college: Any) -> Any:
    """Merge cached tuition, admit mid-50%, and fallback accept rates into a College."""
    entry = get_college(college.name)
    if not entry:
        return college

    kwargs: Dict[str, Any] = {}
    tuition = entry.get("tuition", {})
    if tuition.get("in_state") is not None:
        kwargs["tuition_in_state"] = tuition["in_state"]
    if tuition.get("out_of_state") is not None:
        kwargs["tuition_out_of_state"] = tuition["out_of_state"]

    stats = entry.get("admit_stats", {})
    for field in (
        "gpa_mid50_low", "gpa_mid50_high",
        "sat_mid50_low", "sat_mid50_high",
        "act_mid50_low", "act_mid50_high",
        "admit_stats_source",
    ):
        if stats.get(field) is not None:
            kwargs[field] = stats[field]

    rates = entry.get("acceptance_rates", {})
    gen = rates.get("university_general", {})
    biz = rates.get("business_program", {})
    if gen.get("value") is not None:
        kwargs["acceptance_rate_general"] = gen["value"]
    if biz.get("value") is not None:
        kwargs["acceptance_rate_major"] = biz["value"]

    note = entry.get("business_program_note")
    if note:
        kwargs["business_program_note"] = note

    deadlines = entry.get("deadlines", {})
    if deadlines.get("early_action") is not None:
        kwargs["ea_deadline"] = deadlines["early_action"]
    if deadlines.get("early_decision") is not None:
        kwargs["ed_deadline"] = deadlines["early_decision"]
    if deadlines.get("regular") is not None:
        kwargs["regular_deadline"] = deadlines["regular"]
    if "ed_available" in deadlines:
        kwargs["ed_available"] = deadlines["ed_available"]

    admit_profile = entry.get("admit_profile", {})
    notes_text = (admit_profile.get("program_admit_notes") or "").lower()
    if admit_profile.get("test_optional") or "test-optional" in notes_text or "test optional" in notes_text:
        kwargs["test_optional"] = True

    return replace(college, **kwargs) if kwargs else college
