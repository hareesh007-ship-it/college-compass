#!/usr/bin/env python3
"""Validate data/college_research_cache.json structure and cross-check matcher colleges."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from _paths import DATA

CACHE_PATH = DATA / "college_research_cache.json"

RESERVED_COLLEGE_KEYS = frozenset({
    "admit_profile",
    "rankings",
    "tuition",
    "admit_stats",
    "acceptance_rates",
    "deadlines",
    "business_program_note",
    "business_program_secondary",
    "researched_at",
    "research_method",
})

VALID_RESEARCH_BACKENDS = frozenset({"cursor", "openai", "anthropic", "local", "manual", "scorecard", "web", "claude-research"})

VALID_DISPLAY_MODES = frozenset({
    "mid50_band",
    "mid50_partial",
    "direct_admit_criteria",
    "holistic_no_stats",
    "university_only",
    "pathway",
    "not_applicable",
})

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_matcher_colleges() -> List[str]:
    from college_finder import catalog_college_names  # noqa: WPS433

    return catalog_college_names()


def _is_rate_block(value: Any) -> bool:
    return isinstance(value, dict) and "value" in value and "display" in value


def validate_cache(data: Dict[str, Any], matcher_names: List[str]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if data.get("schema_version") != 1:
        errors.append(f"schema_version must be 1, got {data.get('schema_version')!r}")

    colleges = data.get("colleges")
    if not isinstance(colleges, dict):
        errors.append("colleges must be an object")
        return errors, warnings

    cache_names = set(colleges.keys())
    matcher_set = set(matcher_names)

    for key in sorted(cache_names):
        if key in RESERVED_COLLEGE_KEYS:
            errors.append(
                f"Orphan reserved key {key!r} at colleges top level — "
                f"nest under the correct college entry"
            )

    for name in sorted(cache_names):
        if name in RESERVED_COLLEGE_KEYS:
            continue
        entry = colleges[name]
        if not isinstance(entry, dict):
            errors.append(f"{name}: entry must be an object")
            continue

        researched_at = entry.get("researched_at")
        if researched_at is not None and not DATE_RE.match(str(researched_at)):
            errors.append(f"{name}: researched_at must be YYYY-MM-DD, got {researched_at!r}")

        rankings = entry.get("rankings")
        if rankings is not None and not isinstance(rankings, dict):
            errors.append(f"{name}: rankings must be an object")

        tuition = entry.get("tuition")
        if tuition is not None:
            if not isinstance(tuition, dict):
                errors.append(f"{name}: tuition must be an object")
            elif tuition.get("out_of_state") is None and tuition.get("in_state") is None:
                warnings.append(f"{name}: tuition has no in_state or out_of_state value")

        rates = entry.get("acceptance_rates")
        if rates is not None:
            if not isinstance(rates, dict):
                errors.append(f"{name}: acceptance_rates must be an object")
            else:
                for slot in ("university_general", "business_program"):
                    block = rates.get(slot)
                    if block is not None and not _is_rate_block(block):
                        errors.append(f"{name}: acceptance_rates.{slot} must have value and display")

        admit_profile = entry.get("admit_profile")
        if admit_profile is not None:
            if not isinstance(admit_profile, dict):
                errors.append(f"{name}: admit_profile must be an object")
            else:
                mode = admit_profile.get("display_mode")
                if mode and mode not in VALID_DISPLAY_MODES:
                    errors.append(f"{name}: unknown admit_profile.display_mode {mode!r}")
                direct = admit_profile.get("direct_admit")
                if direct is not None and not isinstance(direct, dict):
                    errors.append(f"{name}: admit_profile.direct_admit must be an object")

        research_method = entry.get("research_method")
        if research_method is not None:
            if not isinstance(research_method, dict):
                errors.append(f"{name}: research_method must be an object")
            else:
                backend = research_method.get("backend")
                if backend is not None and backend not in VALID_RESEARCH_BACKENDS:
                    errors.append(
                        f"{name}: research_method.backend must be one of "
                        f"{sorted(VALID_RESEARCH_BACKENDS)}, got {backend!r}"
                    )
                researched = research_method.get("researched_at")
                if researched is not None and not DATE_RE.match(str(researched)):
                    errors.append(
                        f"{name}: research_method.researched_at must be YYYY-MM-DD, got {researched!r}"
                    )
                urls = research_method.get("source_urls")
                if urls is not None and not isinstance(urls, list):
                    errors.append(f"{name}: research_method.source_urls must be an array")

    orphan_cache = cache_names - matcher_set - RESERVED_COLLEGE_KEYS
    for name in sorted(orphan_cache):
        warnings.append(f"Cache entry not in catalog: {name!r}")

    missing_cache = matcher_set - cache_names
    for name in sorted(missing_cache):
        warnings.append(f"Catalog college missing from cache: {name!r}")

    return errors, warnings


def main() -> int:
    path = CACHE_PATH
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])

    if not path.is_file():
        print(f"ERROR: cache file not found: {path}", file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    matcher_names = _load_matcher_colleges()
    errors, warnings = validate_cache(data, matcher_names)

    print(f"Validated {path} ({len(data.get('colleges', {}))} cache entries, "
          f"{len(matcher_names)} matcher colleges)")

    for msg in warnings:
        print(f"WARN: {msg}")

    for msg in errors:
        print(f"ERROR: {msg}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        _maybe_log_validate(False, len(errors), len(warnings), str(path))
        return 1

    print(f"OK — {len(warnings)} warning(s)")
    _maybe_log_validate(True, 0, len(warnings), str(path))
    return 0


def _maybe_log_validate(ok: bool, errors: int, warnings: int, cache_path: str) -> None:
    try:
        from run_log import log_validate  # noqa: WPS433

        log_validate(ok=ok, errors=errors, warnings=warnings, cache_path=cache_path)
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
