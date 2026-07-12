"""Single pipeline: discover → cache sync → research → match → outputs."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

from _paths import OUTPUT, STUDENT_DATA
from cache_sync import sync_catalog_to_cache
from college_finder import OUTPUT_JSON, OUTPUT_MD, match_colleges, write_markdown
from discover_colleges import discover_colleges
from college_catalog import save_catalog
from load_profile import load_profile
from profile_fields import PROFILE_XLSX
from research_colleges import research_catalog_colleges

ProfileBundle = Tuple[Dict[str, Any], Dict[str, Any], str]


def prepare_from_profile(profile: Dict[str, Any]) -> None:
    """Discover schools, sync cache, research gaps, validate."""
    try:
        catalog = discover_colleges(profile)
    except (RuntimeError, OSError) as exc:
        from college_catalog import load_catalog

        existing = load_catalog()
        if existing.get("colleges"):
            catalog = existing
            print(f"WARN: Discovery API failed ({exc}); using existing catalog ({len(catalog['colleges'])} schools)")
        else:
            raise
    else:
        save_catalog(catalog)
        print(f"Discovered {len(catalog['colleges'])} colleges → catalog")

    from catalog_bootstrap import bootstrap_catalog_from_cache
    from catalog_refine import refine_catalog
    from college_catalog import load_catalog

    bootstrap_catalog_from_cache(profile)
    refine_catalog(profile)
    catalog = load_catalog()
    save_catalog(catalog)

    sync_catalog_to_cache(catalog)
    research_catalog_colleges(catalog)

    # Auto-research: fetch admissions pages and extract mid-50%, deadlines, program rates
    try:
        from pro_config import load_pro_config
        backend = load_pro_config().get("research_backend", "cursor")
    except Exception:
        backend = "cursor"
    from auto_research_colleges import auto_research_catalog
    auto_research_catalog(catalog, backend)

    sync_catalog_to_cache(catalog)

    from validate_cache import validate_cache, CACHE_PATH

    with open(CACHE_PATH, encoding="utf-8") as f:
        cache_data = json.load(f)
    from college_finder import catalog_college_names

    errors, warnings = validate_cache(cache_data, catalog_college_names())
    for msg in warnings:
        print(f"WARN: {msg}")
    if errors:
        for msg in errors:
            print(f"ERROR: {msg}")
        raise RuntimeError(f"Cache validation failed with {len(errors)} error(s)")


def load_and_match() -> ProfileBundle:
    profile = load_profile()
    source = profile.pop("_source", str(PROFILE_XLSX))
    prepare_from_profile(profile)
    report = match_colleges(profile)
    return profile, report, source


def write_match_artifacts(report: Dict[str, Any], profile_source: str) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    write_markdown(report, OUTPUT_MD)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")
    s = report["summary"]
    print(
        f"Safety: {len(s['safety'])} | Target: {len(s['target'])} | "
        f"Reach: {len(s['reach'])} | Excluded: {s['excluded_count']}"
    )
    try:
        from run_log import log_matcher_run  # noqa: WPS433

        log_matcher_run(profile_path=profile_source, summary=s)
    except Exception:
        pass


def run_pipeline(*, write_matches: bool = True, write_sheet: bool = True) -> int:
    profile, report, source = load_and_match()
    os.makedirs(OUTPUT, exist_ok=True)
    os.makedirs(STUDENT_DATA, exist_ok=True)

    if write_matches:
        write_match_artifacts(report, source)
    if write_sheet:
        from build_selection_sheet import write_selection_outputs  # noqa: WPS433

        write_selection_outputs(profile, report, source)

    return 0
