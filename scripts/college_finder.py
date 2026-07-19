#!/usr/bin/env python3
"""
College finder matcher — Safety / Target / Reach from dynamic catalog + research cache.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from _paths import INPUT, OUTPUT, STUDENT_DATA
from acceptance_data import rate_for_fit
from college_research import apply_to_college, college_rankings, matches_user_interest, sort_rank_key
from profile_fields import PROFILE_XLSX
from program_admit import resolve_program_admit

PROFILE_PATH = PROFILE_XLSX
# Intermediate match data — lives in student data/, not output/, to keep
# output/ clean for the deliverables users open (Excel + HTML).
OUTPUT_JSON = STUDENT_DATA / "college_matches.json"
OUTPUT_MD = STUDENT_DATA / "college_matches.md"

MAX_LISTED_SCHOOLS = 20

# MN public tuition reciprocity: WI, ND, SD (resident rate at public schools)
MN_RECIPROCITY_STATES = {"Wisconsin", "North Dakota", "South Dakota"}

LOCAL_STATES = {"Minnesota", "Wisconsin", "Iowa", "North Dakota", "South Dakota", "Illinois", "Indiana"}

# ACT -> approximate SAT midpoint (College Board concordance, simplified)
ACT_TO_SAT = {
    36: 1590, 35: 1540, 34: 1500, 33: 1460, 32: 1420, 31: 1380,
    30: 1370, 29: 1340, 28: 1310, 27: 1280, 26: 1250, 25: 1220,
    24: 1180, 23: 1140, 22: 1100, 21: 1060, 20: 1020,
}


def sat_to_act_equiv(sat: int) -> int:
    if sat <= 0:
        return 0
    return min(ACT_TO_SAT, key=lambda act: abs(ACT_TO_SAT[act] - sat))


@dataclass
class College:
    name: str
    state: str
    region: str
    public_private: str
    tuition_in_state: Optional[int]
    tuition_out_of_state: Optional[int]
    avg_admit_gpa: float
    avg_admit_sat: int
    acceptance_rate_general: float
    acceptance_rate_major: Optional[float]
    major_rate_note: Optional[str]
    ed_available: bool
    ea_deadline: Optional[str]
    ed_deadline: Optional[str]
    regular_deadline: str
    business_program: bool
    business_program_note: Optional[str]
    source: str
    # Official mid-50% of admitted students when published (median = midpoint of range)
    gpa_mid50_low: Optional[float] = None
    gpa_mid50_high: Optional[float] = None
    sat_mid50_low: Optional[int] = None
    sat_mid50_high: Optional[int] = None
    act_mid50_low: Optional[int] = None
    act_mid50_high: Optional[int] = None
    admit_stats_source: Optional[str] = None
    test_optional: bool = False


def mid50_median_float(low: float, high: float) -> float:
    return round((low + high) / 2, 3)


def mid50_median_int(low: int, high: int) -> int:
    return round((low + high) / 2)


def resolve_admit_stats(college: College) -> Dict[str, Any]:
    """Build display + comparison stats; use published mid-50% when available."""
    gpa_lo, gpa_hi = college.gpa_mid50_low, college.gpa_mid50_high
    sat_lo, sat_hi = college.sat_mid50_low, college.sat_mid50_high
    act_lo, act_hi = college.act_mid50_low, college.act_mid50_high

    gpa_has = gpa_lo is not None and gpa_hi is not None
    sat_has = sat_lo is not None and sat_hi is not None
    act_has = act_lo is not None and act_hi is not None

    gpa_median = mid50_median_float(gpa_lo, gpa_hi) if gpa_has else college.avg_admit_gpa
    sat_median = mid50_median_int(sat_lo, sat_hi) if sat_has else college.avg_admit_sat
    act_median = mid50_median_int(act_lo, act_hi) if act_has else sat_to_act_equiv(college.avg_admit_sat)

    if college.admit_stats_source:
        source = college.admit_stats_source
    elif gpa_has or sat_has or act_has:
        source = "Published mid-50% (partial)"
    else:
        source = "Point estimate (no published mid-50%)"

    return {
        "gpa_mid50_low": gpa_lo,
        "gpa_mid50_high": gpa_hi,
        "gpa_median": gpa_median,
        "gpa_range_display": f"{gpa_lo:.2f}–{gpa_hi:.2f}" if gpa_has else "",
        "gpa_has_range": gpa_has,
        "sat_mid50_low": sat_lo,
        "sat_mid50_high": sat_hi,
        "sat_median": sat_median,
        "sat_range_display": f"{sat_lo}–{sat_hi}" if sat_has else "",
        "sat_has_range": sat_has,
        "act_mid50_low": act_lo,
        "act_mid50_high": act_hi,
        "act_median": act_median,
        "act_range_display": f"{act_lo}–{act_hi}" if act_has else "",
        "act_has_range": act_has,
        "admit_stats_source": source,
    }


def in_mid50(value: float, low: Optional[float], high: Optional[float]) -> Optional[bool]:
    if low is None or high is None:
        return None
    return low <= value <= high


def mid50_yn(in_range: Optional[bool]) -> str:
    if in_range is True:
        return "Y"
    if in_range is False:
        return "N"
    return "—"


def mid50_position(
    value: float,
    low: Optional[float],
    high: Optional[float],
    *,
    decimals: int = 2,
) -> str:
    """Human-readable placement vs published mid-50% band."""
    if low is None or high is None:
        return "—"
    if value < low:
        delta = value - low
        fmt = f"{delta:+.{decimals}f}" if decimals else f"{delta:+.0f}"
        return f"Below ({fmt} vs low)"
    if value > high:
        delta = value - high
        fmt = f"{delta:+.{decimals}f}" if decimals else f"{delta:+.0f}"
        return f"Above ({fmt} vs high)"
    return "In mid-50%"


def get_active_colleges() -> List[College]:
    """Load discovered + user-preferred colleges from data/colleges/catalog.json."""
    from college_catalog import load_catalog_as_colleges

    colleges = load_catalog_as_colleges()
    if not colleges:
        raise RuntimeError(
            "No colleges in catalog. Fill input/student profile input.xlsx "
            "(regions, budget, and/or Schools especially interested in) and run python3 scripts/run.py."
        )
    return colleges


def catalog_college_names() -> List[str]:
    return [c.name for c in get_active_colleges()]




def act_composite(profile: Dict[str, Any]) -> Optional[int]:
    act = profile.get("act")
    if isinstance(act, dict):
        return act.get("composite")
    return act


def effective_sat(profile: Dict[str, Any]) -> int:
    sat = profile.get("sat") or 0
    act = act_composite(profile)
    act_sat = ACT_TO_SAT.get(act, 0) if act else 0
    return max(sat, act_sat)


def effective_act(profile: Dict[str, Any]) -> int:
    sat = profile.get("sat") or 0
    act = act_composite(profile) or 0
    sat_act = sat_to_act_equiv(sat) if sat else 0
    return max(act, sat_act)


def avg_admit_act_from_sat(avg_admit_sat: int) -> int:
    return sat_to_act_equiv(avg_admit_sat)


def tuition_for_student(college: College, home_state: str) -> int:
    if college.state == home_state:
        return college.tuition_in_state or college.tuition_out_of_state or 0
    if (
        college.public_private == "Public"
        and home_state == "Minnesota"
        and college.state in MN_RECIPROCITY_STATES
    ):
        return college.tuition_in_state or college.tuition_out_of_state or 0
    return college.tuition_out_of_state or college.tuition_in_state or 0


def passes_filters(college: College, profile: Dict[str, Any], cat_meta: Optional[Dict[str, Any]] = None) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    prefs = profile.get("preferences", {})
    surrounding = set(prefs.get("surrounding_states", []))
    allowed_states = {profile["state_of_residence"]} | surrounding | LOCAL_STATES
    if college.state not in allowed_states:
        if not any(college.name in i or i in college.name for i in profile.get("schools_interested_in", [])):
            return False, [f"Outside local/surrounding states ({college.state})"]

    if college.public_private == "Public" and not prefs.get("public_ok", True):
        return False, ["Public schools excluded by preference"]
    if college.public_private == "Private" and not prefs.get("private_ok", True):
        return False, ["Private schools excluded by preference"]

    tuition = tuition_for_student(college, profile["state_of_residence"])
    budget = profile.get("budget_max_tuition_per_year", 999999)
    avg_net = (cat_meta or {}).get("avg_net_price")
    # Pass budget if sticker OR average net price is within budget
    within_budget = tuition <= budget or (avg_net is not None and avg_net <= budget)
    if not within_budget:
        if avg_net is not None:
            reasons.append(
                f"Sticker ${tuition:,} and avg net price ${avg_net:,} both exceed budget ${budget:,}"
            )
        else:
            reasons.append(f"Tuition ${tuition:,} exceeds budget ${budget:,}")
        interested = profile.get("schools_interested_in", [])
        if not any(college.name.split(" - ")[0] in i or college.name in i for i in interested):
            return False, reasons

    if not college.business_program and profile.get("intended_major", "").lower() not in ("",):
        reasons.append(college.business_program_note or "No matching undergrad program for intended major")
        return False, reasons

    return True, reasons


def _entry_rank_key(entry: Dict[str, Any], profile: Dict[str, Any]) -> tuple:
    """Lower sort key = higher priority within a fit category."""
    major = profile.get("intended_major", "")
    rank = sort_rank_key(entry, major)
    has_us_news = rank < 900
    adm = entry.get("acceptance_rate_used")
    if adm is None:
        adm = 1.0
    open_admission = adm > 0.92 and not has_us_news
    size = entry.get("student_size") or 0
    disc = entry.get("discovery_score") or 0
    biz = entry.get("business_program_pct") or 0
    return (
        not entry.get("priority_interest", False),
        open_admission,
        rank,
        -int(has_us_news),
        -disc,
        -size,
        -biz,
    )


def apply_category_caps(
    results: List[Dict[str, Any]],
    excluded: List[Dict[str, Any]],
    profile: Dict[str, Any],
    max_listed: int = MAX_LISTED_SCHOOLS,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Keep up to max_listed schools total; always keep user-preferred schools."""
    still_excluded: List[Dict[str, Any]] = []
    for entry in excluded:
        if entry.get("priority_interest"):
            promoted = dict(entry)
            promoted.pop("excluded", None)
            filter_notes = promoted.pop("exclusion_reasons", [])
            if filter_notes:
                promoted.setdefault("reasons", []).append(
                    "Included — listed under Schools especially interested in "
                    f"({'; '.join(filter_notes)})."
                )
            results.append(promoted)
        else:
            still_excluded.append(entry)

    by_category: Dict[str, List[Dict[str, Any]]] = {
        "Safety": [],
        "Target": [],
        "Reach": [],
    }
    for entry in results:
        cat = entry.get("category") or "Target"
        if cat not in by_category:
            cat = "Target"
        by_category[cat].append(entry)

    ranked_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    preferred: List[Dict[str, Any]] = []
    for cat in ("Safety", "Target", "Reach"):
        bucket = sorted(by_category[cat], key=lambda e: _entry_rank_key(e, profile))
        ranked_by_cat[cat] = bucket
        preferred.extend(e for e in bucket if e.get("priority_interest"))

    remaining = max(0, max_listed - len(preferred))
    kept_non_preferred: List[Dict[str, Any]] = []
    for cat in ("Safety", "Target", "Reach"):
        for entry in ranked_by_cat[cat]:
            if entry.get("priority_interest"):
                continue
            if len(kept_non_preferred) >= remaining:
                break
            kept_non_preferred.append(entry)

    kept = preferred + kept_non_preferred
    kept_names = {e["name"] for e in kept}
    total_discovered = sum(len(ranked_by_cat[c]) for c in ranked_by_cat)
    selected: List[Dict[str, Any]] = []
    for cat in ("Safety", "Target", "Reach"):
        for entry in ranked_by_cat[cat]:
            if entry["name"] in kept_names:
                selected.append(entry)
                continue
            trimmed = dict(entry)
            trimmed["excluded"] = True
            trimmed["category"] = cat
            trimmed["exclusion_reasons"] = [
                f"Not in top {max_listed} listed schools "
                f"({total_discovered} discovered; list capped)."
            ]
            still_excluded.append(trimmed)

    order = {"Safety": 0, "Target": 1, "Reach": 2}
    selected.sort(
        key=lambda x: (
            not x.get("priority_interest"),
            order.get(x.get("category"), 9),
            sort_rank_key(x, profile.get("intended_major", "")),
        )
    )
    return selected, still_excluded


def classify_fit(
    college: College,
    gpa: float,
    sat: int,
    acceptance_rate: float,
    stats: Optional[Dict[str, Any]] = None,
    *,
    gpa_weighted: Optional[float] = None,
) -> str:
    stats = stats or resolve_admit_stats(college)
    gpa_median = stats["gpa_median"]
    sat_median = stats["sat_median"]
    gpa_delta = gpa - gpa_median
    sat_delta = sat - sat_median
    if stats["gpa_has_range"] and in_mid50(gpa, stats["gpa_mid50_low"], stats["gpa_mid50_high"]):
        gpa_delta = max(gpa_delta, 0)
    if stats["sat_has_range"] and in_mid50(float(sat), float(stats["sat_mid50_low"]), float(stats["sat_mid50_high"])):
        sat_delta = max(sat_delta, -20)

    # Top national / ultra-selective → Reach regardless of stats
    national = college_rankings(college.name)["us_news_national"]
    if national is not None and national <= 10:
        return "Reach"
    if acceptance_rate < 0.15:
        return "Reach"

    score = 0
    if gpa_delta >= 0.15:
        score += 2
    elif gpa_delta >= -0.05:
        score += 1
    elif gpa_delta >= -0.25:
        score -= 1
    else:
        score -= 2

    # Skip SAT scoring when school is test-optional and student has no scores submitted
    if sat == 0 and college.test_optional:
        pass  # neutral — don't penalise a missing score at a test-optional school
    elif sat_delta >= 80:
        score += 2
    elif sat_delta >= -40:
        score += 1
    elif sat_delta >= -120:
        score -= 1
    else:
        score -= 2

    # Rigor bonus: weighted GPA significantly above unweighted signals strong coursework
    if gpa_weighted is not None and (gpa_weighted - gpa) >= 0.3:
        score += 1

    if acceptance_rate >= 0.65 and score >= 0:
        return "Safety"
    if acceptance_rate >= 0.45 and score >= -1:
        return "Target"
    if score >= 1 and acceptance_rate >= 0.35:
        return "Target"
    if score <= -2 or acceptance_rate < 0.25:
        return "Reach"
    return "Target"


def build_reasons(
    college: College,
    profile: Dict[str, Any],
    category: str,
    tuition: int,
    budget_ok: bool,
    stats: Optional[Dict[str, Any]] = None,
    avg_net: Optional[int] = None,
) -> List[str]:
    gpa = profile["gpa_unweighted"]
    sat = effective_sat(profile)
    act = effective_act(profile)
    stats = stats or resolve_admit_stats(college)
    rate_val, rate_label = rate_for_fit(college.name)
    rate = rate_val if rate_val is not None else (college.acceptance_rate_major or college.acceptance_rate_general)
    rate_pct = f"{rate * 100:.1f}%" if rate is not None else "N/A"

    if stats["gpa_has_range"]:
        gpa_line = (
            f"Your GPA {gpa} vs mid-50% {stats['gpa_range_display']} "
            f"({mid50_position(gpa, stats['gpa_mid50_low'], stats['gpa_mid50_high'])})."
        )
    else:
        gpa_line = f"Your GPA {gpa} (no published mid-50% range for this school)."

    if stats["sat_has_range"]:
        sat_line = (
            f"Your effective SAT {sat} vs mid-50% {stats['sat_range_display']} "
            f"({mid50_position(float(sat), float(stats['sat_mid50_low']), float(stats['sat_mid50_high']), decimals=0)})."
        )
    else:
        sat_line = (
            f"Your effective SAT {sat} (max of SAT {profile.get('sat')} / ACT {act_composite(profile)} equiv) "
            f"(no published mid-50% range)."
        )

    if stats["act_has_range"]:
        act_line = (
            f"Your ACT {act} vs mid-50% {stats['act_range_display']} "
            f"({mid50_position(float(act), float(stats['act_mid50_low']), float(stats['act_mid50_high']), decimals=0)})."
        )
    else:
        act_line = f"Your ACT {act} (no published mid-50% range)."

    reasons = [
        gpa_line,
        sat_line,
        act_line,
        f"Relevant acceptance rate: {rate_pct}"
        + (f" ({rate_label})" if rate_label else "")
        + (f" — {college.major_rate_note}" if college.major_rate_note and not rate_label.startswith("Business") else ""),
    ]

    if college.state == profile["state_of_residence"]:
        reasons.append(f"In-state tuition ${tuition:,}/year — {profile['state_of_residence']} resident.")
    else:
        reasons.append(f"Out-of-state tuition ${tuition:,}/year.")

    budget = profile.get("budget_max_tuition_per_year", 999999)
    if not budget_ok:
        reasons.append(f"⚠ Over budget cap of ${budget:,}/year (sticker and avg net price).")
    elif tuition > budget and avg_net is not None and avg_net <= budget:
        reasons.append(
            f"Sticker ${tuition:,} over budget but avg net price ${avg_net:,} is within budget — included."
        )

    if college.business_program_note:
        reasons.append(college.business_program_note)

    gpa_weighted = profile.get("gpa_weighted")
    if gpa_weighted is not None and (gpa_weighted - gpa) >= 0.3:
        reasons.append(
            f"Weighted GPA {gpa_weighted} (+{gpa_weighted - gpa:.2f} above unweighted) — "
            "rigorous coursework counted in fit scoring."
        )

    if college.test_optional and sat == 0:
        reasons.append("Test-optional school — no test score submitted; SAT scoring skipped in fit calculation.")
    elif college.test_optional:
        reasons.append("Test-optional school — submitting scores is at your discretion.")

    if category == "Reach":
        reasons.append("Classified as reach: stats below average and/or highly selective.")
    elif category == "Safety":
        reasons.append("Classified as safety: stats competitive and acceptance rate relatively high.")

    return reasons


def match_colleges(profile: Dict[str, Any]) -> Dict[str, Any]:
    gpa = profile["gpa_unweighted"]
    sat = effective_sat(profile)
    act = effective_act(profile)
    results: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for raw_college in get_active_colleges():
        college = apply_to_college(raw_college)
        cat_meta = {}
        try:
            from college_catalog import catalog_entry_for

            cat_meta = catalog_entry_for(college.name)
        except Exception:
            pass

        ok, filter_notes = passes_filters(college, profile, cat_meta)
        tuition = tuition_for_student(college, profile["state_of_residence"])
        budget = profile.get("budget_max_tuition_per_year", 999999)
        avg_net = cat_meta.get("avg_net_price")
        budget_ok = tuition <= budget or (avg_net is not None and avg_net <= budget)

        rate_val, rate_label = rate_for_fit(college.name)
        if rate_val is None:
            rate = college.acceptance_rate_major or college.acceptance_rate_general
        else:
            rate = rate_val
        stats = resolve_admit_stats(college)
        gpa_weighted = profile.get("gpa_weighted")
        category = classify_fit(college, gpa, sat, rate, stats, gpa_weighted=gpa_weighted)
        program_admit = resolve_program_admit(college.name, profile, stats, sat, act)
        interested = matches_user_interest(college.name, profile.get("schools_interested_in", []))

        entry = {
            "name": college.name,
            "state": college.state,
            "region": college.region,
            "public_private": college.public_private,
            **college_rankings(college.name),
            "tuition_estimate": tuition,
            "avg_net_price": cat_meta.get("avg_net_price"),
            "within_budget": budget_ok,
            **stats,
            **program_admit,
            "gpa_vs_median": gpa - stats["gpa_median"],
            "sat_vs_median": sat - stats["sat_median"],
            "act_vs_median": act - stats["act_median"],
            "gpa_in_mid50": in_mid50(gpa, stats["gpa_mid50_low"], stats["gpa_mid50_high"]),
            "gpa_position": mid50_position(gpa, stats["gpa_mid50_low"], stats["gpa_mid50_high"]),
            "sat_in_mid50": in_mid50(float(sat), float(stats["sat_mid50_low"]) if stats["sat_mid50_low"] is not None else None, float(stats["sat_mid50_high"]) if stats["sat_mid50_high"] is not None else None),
            "sat_position": mid50_position(float(sat), stats["sat_mid50_low"], stats["sat_mid50_high"], decimals=0),
            "act_in_mid50": in_mid50(float(act), float(stats["act_mid50_low"]) if stats["act_mid50_low"] is not None else None, float(stats["act_mid50_high"]) if stats["act_mid50_high"] is not None else None),
            "act_position": mid50_position(float(act), stats["act_mid50_low"], stats["act_mid50_high"], decimals=0),
            "acceptance_rate_used": rate,
            "acceptance_rate_label": rate_label,
            "test_optional": college.test_optional,
            "category": category,
            "priority_interest": interested,
            "deadlines": {
                "early_action": college.ea_deadline,
                "early_decision": college.ed_deadline if college.ed_available else None,
                "regular": college.regular_deadline,
            },
            "early_decision_available": college.ed_available,
            "reasons": build_reasons(college, profile, category, tuition, budget_ok, stats, avg_net),
            "source": college.source,
            "student_size": cat_meta.get("student_size"),
            "business_program_pct": cat_meta.get("business_program_pct"),
            "discovery_score": cat_meta.get("discovery_score"),
        }

        if not ok:
            entry["excluded"] = True
            entry["exclusion_reasons"] = filter_notes
            excluded.append(entry)
        else:
            if not budget_ok:
                entry["category"] = "Reach" if category != "Safety" else category
                entry["reasons"].append("Budget stretch — consider merit aid or alternate campuses.")
            results.append(entry)

    results, excluded = apply_category_caps(results, excluded, profile)

    by_category: Dict[str, List[str]] = {"Safety": [], "Target": [], "Reach": []}
    for r in results:
        by_category[r["category"]].append(r["name"])

    return {
        "student": profile,
        "matching_notes": {
            "effective_sat_used": sat,
            "effective_act_used": act,
            "methodology": (
                "Discovery catalog + cache; Safety/Target/Reach; "
                f"up to {MAX_LISTED_SCHOOLS} schools listed (+ any Schools especially interested in)."
            ),
            "major": profile["intended_major"],
            "max_listed": MAX_LISTED_SCHOOLS,
        },
        "summary": {
            "safety": by_category["Safety"],
            "target": by_category["Target"],
            "reach": by_category["Reach"],
            "excluded_count": len(excluded),
        },
        "matches": results,
        "excluded": excluded,
    }




def write_markdown(report: Dict[str, Any], path: str) -> None:
    p = report["student"]
    sat = report["matching_notes"]["effective_sat_used"]
    cycle = p.get("application_cycle", {})
    cycle_line = ""
    if cycle:
        cycle_line = (
            f"**Application timeline:** Senior year {cycle.get('senior_year_start', '2026-09')} → "
            f"apply Fall {cycle.get('applying_fall', 2026)} → start college {cycle.get('college_start', '2027-08')}"
        )

    act = p.get("act")
    act_str = ""
    if isinstance(act, dict):
        act_str = (
            f"**ACT:** {act.get('composite')} "
            f"(E{act.get('english')}/M{act.get('math')}/R{act.get('reading')}/S{act.get('science')})"
        )
    else:
        act_str = f"**ACT:** {act}"
    hs = p.get("high_school", "")
    hs_line = f"**High school:** {hs} | **Class of:** {p.get('class_of', 2027)}" if hs else ""

    lines = [
        f"# College Matches — {p['name']}",
        "",
        f"**Grade:** {p['grade']} | **Major:** {p['intended_major']} | **State:** {p['state_of_residence']}",
    ]
    if hs_line:
        lines.append(hs_line)
    if cycle_line:
        lines.append(cycle_line)
    lines.extend([
        f"**GPA:** {p['gpa_unweighted']} unweighted / {p.get('gpa_weighted', '—')} weighted | **SAT:** {p.get('sat')} | {act_str}",
        f"**Effective SAT used:** {sat} | **Effective ACT used:** {report['matching_notes']['effective_act_used']}",
        f"**Budget:** ${p['budget_max_tuition_per_year']:,}/year | **Regions:** {', '.join(p['preferences']['regions'])}",
        "",
    ])
    lines.extend([
        "## Summary",
        "",
        f"- **Safety ({len(report['summary']['safety'])}):** {', '.join(report['summary']['safety']) or 'None'}",
        f"- **Target ({len(report['summary']['target'])}):** {', '.join(report['summary']['target']) or 'None'}",
        f"- **Reach ({len(report['summary']['reach'])}):** {', '.join(report['summary']['reach']) or 'None'}",
        "",
    ])

    if p.get("schools_interested_in"):
        lines.extend(["## Your stated interests", ""])
        for s in p["schools_interested_in"]:
            lines.append(f"- {s}")
        lines.append("")

    for category in ("Safety", "Target", "Reach"):
        bucket = [m for m in report["matches"] if m["category"] == category]
        if not bucket:
            continue
        lines.append(f"## {category}")
        lines.append("")
        for m in bucket:
            flag = " ⭐ **Your interest**" if m.get("priority_interest") else ""
            budget_flag = "" if m["within_budget"] else " 💰 **Over budget**"
            lines.append(f"### {m['name']}{flag}{budget_flag}")
            nat = m.get("us_news_national")
            biz = m.get("us_news_undergrad_business")
            rank_bits = []
            if nat is not None:
                rank_bits.append(f"National #{nat}")
            if biz is not None:
                rank_bits.append(f"Business #{biz}")
            rank_str = " | ".join(rank_bits) if rank_bits else "Regional / unranked (national)"
            lines.append(
                f"{rank_str} | {m['public_private']} | {m['state']} | "
                f"Tuition ~${m['tuition_estimate']:,} | Accept ~{m['acceptance_rate_used']*100:.1f}%"
            )
            dl = m["deadlines"]
            lines.append(
                f"Deadlines — EA: {dl['early_action'] or 'N/A'} | ED: {dl['early_decision'] or 'N/A'} | Regular: {dl['regular']}"
            )
            for r in m["reasons"]:
                lines.append(f"- {r}")
            lines.append("")

    if report["excluded"]:
        lines.extend(["## Excluded (region, budget, or program fit)", ""])
        for m in report["excluded"]:
            lines.append(f"- **{m['name']}:** {'; '.join(m.get('exclusion_reasons', []))}")
        lines.append("")

    applying_fall = p.get("application_cycle", {}).get("applying_fall", 2026)
    first = (p.get("name") or "Student").split()[0]
    preferred = [m["name"] for m in report["matches"] if m.get("priority_interest")]
    ea_schools = [
        m["name"] for m in report["matches"]
        if (m.get("deadlines") or {}).get("early_action")
    ][:3]

    lines.extend([
        "## Recommended next steps (Fall 2026 application cycle)",
        "",
        f"1. **Finalize school list by Aug {applying_fall}** — Target 8–12 schools (mix of Safety / Target / Reach).",
    ])
    if preferred:
        lines.append(f"2. **Priority schools** — {', '.join(preferred)}: confirm deadlines and visit if possible.")
    elif report["matches"]:
        top = [m["name"] for m in report["matches"][:3]]
        lines.append(f"2. **Top targets** — Review fit for {', '.join(top)}.")
    if ea_schools:
        lines.append(
            f"3. **Early Action** — {', '.join(ea_schools)} offer EA; good for {first} without binding ED."
        )
    lines.extend([
        f"4. **Testing** — Use best SAT/ACT per school policy (effective SAT {sat} / ACT {report['matching_notes']['effective_act_used']} for this run).",
        "5. **Early Decision** — Only if one school is a clear first choice (binding).",
        "6. **Common App / essays** — Start personal statement summer before apply year; supplementals in fall.",
        "",
    ])

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    from pipeline import run_pipeline

    return run_pipeline(write_matches=True, write_sheet=False)


if __name__ == "__main__":
    raise SystemExit(main())
