"""Fill cache research gaps for catalog schools (US News + Scorecard)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List

from _paths import DATA
from cache_sync import CACHE_PATH, is_scorecard_stub, _merge_parsed, _fetch_parsed
from us_news_lookup import fetch_us_news_rankings

RANK_FIELDS = (
    "national_university",
    "undergrad_business",
    "regional_universities_midwest",
    "entrepreneurship",
)


@dataclass
class ResearchReport:
    researched: int = 0
    skipped: int = 0
    failed: int = 0


def _load_cache() -> Dict[str, Any]:
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: Dict[str, Any]) -> None:
    cache["last_updated"] = date.today().isoformat()
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def has_ranking(block: Dict[str, Any]) -> bool:
    rankings = block.get("rankings") or {}
    return any(rankings.get(field) is not None for field in RANK_FIELDS)


def needs_research(block: Dict[str, Any]) -> bool:
    return not has_ranking(block)


def _catalog_by_key(catalog: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {e["cache_key"]: e for e in catalog.get("colleges") or []}


def research_college(cache_key: str, block: Dict[str, Any], catalog_entry: Dict[str, Any]) -> bool:
    """Refresh Scorecard fields and fetch US News ranks when missing."""
    parsed = _fetch_parsed(catalog_entry)
    if parsed:
        _merge_parsed(block, parsed)

    if has_ranking(block):
        return False

    lookup_name = catalog_entry.get("scorecard_name") or cache_key
    ranks = fetch_us_news_rankings(lookup_name.split(" - ")[0])
    if not ranks:
        return False

    today = date.today().isoformat()
    ranking_block = block.setdefault("rankings", {})
    for field in RANK_FIELDS:
        if field in ranks and ranks[field] is not None:
            ranking_block[field] = ranks[field]
    ranking_block["notes"] = "US News Best Colleges 2026 (auto fetch)"

    tuition = block.setdefault("tuition", {})
    if not tuition.get("source_url") or is_scorecard_stub(block):
        src = ranks.get("source_url")
        if src:
            tuition["source_url"] = src.replace("/overall-rankings", "/paying")

    rm = block.setdefault("research_method", {})
    rm["backend"] = "web"
    rm["scope"] = "pipeline auto-research"
    rm["researched_at"] = today
    urls = list(rm.get("source_urls") or [])
    src = ranks.get("source_url")
    if src and src not in urls:
        urls.append(src)
    rm["source_urls"] = urls

    block["researched_at"] = today
    return True


def research_catalog_colleges(catalog: Dict[str, Any]) -> ResearchReport:
    """Research every catalog school that lacks US News / regional / business rank."""
    cache = _load_cache()
    colleges = cache.setdefault("colleges", {})
    by_key = _catalog_by_key(catalog)
    report = ResearchReport()

    for cache_key, catalog_entry in by_key.items():
        block = colleges.get(cache_key)
        if block is None:
            continue
        if not needs_research(block):
            report.skipped += 1
            continue
        try:
            if research_college(cache_key, block, catalog_entry):
                report.researched += 1
                print(f"  Researched: {cache_key}")
            else:
                report.failed += 1
                print(f"  WARN: Could not find US News ranks for {cache_key}")
        except Exception as exc:
            report.failed += 1
            print(f"  WARN: Research failed for {cache_key}: {exc}")

    _save_cache(cache)
    from college_research import reload_cache

    reload_cache()
    print(
        f"Cache research: {report.researched} updated, "
        f"{report.skipped} already complete, {report.failed} gaps remain"
    )
    return report
