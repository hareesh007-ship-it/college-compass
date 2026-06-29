"""Discovery filters and quality scoring for Midwest / business-focused school search."""

from __future__ import annotations

import re
from typing import Any, Dict

MIN_STUDENT_SIZE = 2500
MIN_BUSINESS_PROGRAM_SHARE = 0.04
LARGE_UNIVERSITY_SIZE = 8000

SKIP_NAME_PATTERNS = re.compile(
    r"(seminary|beauty|barber|cosmetolog|nursing college|school of nursing|"
    r"theological|bible college|massage|truck|welding academy)",
    re.I,
)

BUSINESS_MAJOR_RE = re.compile(
    r"business|management|entrepreneur|finance|accounting|marketing|economics|bba|mba",
    re.I,
)


def is_business_major(intended_major: str) -> bool:
    return bool(BUSINESS_MAJOR_RE.search(intended_major or ""))


def _name_skip(name: str) -> bool:
    return bool(SKIP_NAME_PATTERNS.search(name or ""))


def passes_discovery_filter(parsed: Dict[str, Any], profile: Dict[str, Any]) -> bool:
    """Scorecard row filters — user-preferred schools bypass this."""
    name = parsed.get("scorecard_name") or ""
    if _name_skip(name):
        return False

    size = parsed.get("student_size") or 0
    biz = parsed.get("business_program_pct") or 0.0
    is_public = parsed.get("public_private") == "Public"
    is_university = "university" in name.lower()

    if size and size < MIN_STUDENT_SIZE:
        if not (is_university and is_public and size >= 1500):
            return False

    if is_business_major(profile.get("intended_major") or ""):
        if biz >= MIN_BUSINESS_PROGRAM_SHARE:
            return True
        if is_university and (is_public or size >= LARGE_UNIVERSITY_SIZE or not size):
            return True
        if "business" in name.lower() or "management" in name.lower():
            return True
        return False

    return True


def discovery_quality_score(parsed: Dict[str, Any], profile: Dict[str, Any]) -> float:
    """Higher = better candidate for catalog (used before capping discovery list)."""
    name = (parsed.get("scorecard_name") or "").lower()
    size = parsed.get("student_size") or 0
    biz = parsed.get("business_program_pct") or 0.0
    adm = parsed.get("admission_rate")
    score = 0.0

    if size:
        score += min(size / 500.0, 40.0)
    if biz:
        score += biz * 120.0
    if parsed.get("public_private") == "Public":
        score += 8.0
    if "university" in name:
        score += 12.0
    if any(k in name for k in ("business", "management", "college of")):
        score += 4.0
    if adm is not None:
        # Prefer moderately selective (typical safety/target publics), not near-open-admission
        if 0.35 <= adm <= 0.88:
            score += 15.0
        elif adm > 0.92:
            score -= 10.0
        else:
            score += (1.0 - adm) * 10.0

    home = profile.get("state_of_residence") or ""
    state = parsed.get("state") or ""
    if parsed.get("is_home_state"):
        score += 5.0

    return round(score, 2)
