"""Re-score catalog entries using cache ranks + quality heuristics."""

from __future__ import annotations

from typing import Any, Dict, List

from college_catalog import load_catalog, save_catalog
from college_research import college_rankings, reload_cache
from discovery_quality import _name_skip, discovery_quality_score


def _parsed_from_entry(entry: Dict[str, Any], ranks: Dict[str, Any]) -> Dict[str, Any]:
    size = entry.get("student_size")
    if not size and (ranks.get("us_news_national") or ranks.get("us_news_undergrad_business")):
        size = 12000
    biz = entry.get("business_program_pct") or 0.0
    if not biz and ranks.get("us_news_undergrad_business"):
        biz = 0.08
    state = entry.get("state") or ""
    abbrev = state[:2].upper() if len(state) == 2 else ""
    return {
        "scorecard_name": entry.get("scorecard_name") or entry.get("cache_key"),
        "student_size": size,
        "business_program_pct": biz,
        "admission_rate": entry.get("admission_rate"),
        "public_private": entry.get("public_private"),
        "state": abbrev or state,
    }


def _score_from_ranks(ranks: Dict[str, Any]) -> float:
    nat = ranks.get("us_news_national")
    biz = ranks.get("us_news_undergrad_business")
    ent = ranks.get("us_news_entrepreneurship")
    reg = ranks.get("us_news_regional_midwest")
    best = None
    for val in (ent, biz, nat, reg):
        if val is not None:
            best = val if best is None else min(best, val)
    if best is None:
        return 0.0
    return round(max(5.0, 95.0 - best * 0.85), 2)


def refine_catalog(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Re-score catalog; drop only specialty/junk names — do not re-filter discovery picks."""
    reload_cache()
    catalog = load_catalog()
    refined: List[Dict[str, Any]] = []

    for entry in catalog.get("colleges") or []:
        label = entry.get("scorecard_name") or entry.get("cache_key") or ""
        if _name_skip(label):
            continue

        ranks = college_rankings(entry["cache_key"])
        parsed = _parsed_from_entry(entry, ranks)
        rank_score = _score_from_ranks(ranks)
        quality = discovery_quality_score(parsed, profile)
        entry["discovery_score"] = max(
            entry.get("discovery_score") or 0,
            rank_score,
            quality,
        )
        if entry.get("source") == "user_preferred" and rank_score:
            entry["discovery_score"] = max(entry["discovery_score"], rank_score, 100.0)

        if not entry.get("student_size") and parsed.get("student_size"):
            entry["student_size"] = parsed["student_size"]
        if not entry.get("business_program_pct") and parsed.get("business_program_pct"):
            entry["business_program_pct"] = parsed["business_program_pct"]

        refined.append(entry)

    refined.sort(
        key=lambda e: (
            e.get("source") != "user_preferred",
            -(e.get("discovery_score") or 0),
            -(e.get("student_size") or 0),
        )
    )
    catalog["colleges"] = refined
    save_catalog(catalog)
    print(f"Refined catalog: {len(refined)} schools (quality-ranked)")
    return catalog
