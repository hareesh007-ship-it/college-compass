"""Program-level admission display: mid-50%, direct-admit criteria, holistic, pathway."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from college_research import get_college

DISPLAY_MODE_LABELS = {
    "mid50_band": "Mid-50% band (published)",
    "mid50_partial": "Mid-50% band (partial — see notes)",
    "direct_admit_criteria": "Direct admit (criteria)",
    "holistic_no_stats": "Holistic review (no published stats)",
    "university_only": "University general only",
    "pathway": "Pre-business / pathway",
    "not_applicable": "N/A (no undergrad business path)",
}

# Legacy fallbacks when cache has no admit_profile. Prefer cache admit_profile for each school.
# Keys not listed default to display_mode "university_only".
DEFAULT_ADMIT_PROFILES: Dict[str, Dict[str, Any]] = {
    "University of Illinois Urbana-Champaign": {
        "display_mode": "mid50_band",
        "program_admit_notes": "Gies College of Business first-year direct; stats are Gies-specific.",
    },
    "Purdue University": {
        "display_mode": "mid50_band",
        "program_admit_notes": "Daniels School of Business admitted freshman mid-50%.",
    },
    "University of Wisconsin-Madison": {
        "display_mode": "mid50_partial",
        "program_admit_notes": "Direct entry to Wisconsin School of Business; GPA mid-50% not published (SAT/ACT from CDS).",
    },
    "University of Illinois Chicago": {
        "display_mode": "mid50_partial",
        "program_admit_notes": "UIC Business holistic; ranges are university-wide (US News).",
    },
    "Illinois Institute of Technology": {
        "display_mode": "university_only",
        "program_admit_notes": "Stuart School; no separate business freshman profile published.",
    },
    "MIT": {"display_mode": "not_applicable", "program_admit_notes": "No undergrad business major for this path."},
    "Stanford University": {
        "display_mode": "not_applicable",
        "program_admit_notes": "MS&E is closest; not standard BBA entrepreneurship.",
    },
    "Carnegie Mellon University": {
        "display_mode": "holistic_no_stats",
        "program_admit_notes": "Tepper separate admission; no published UG business mid-50%.",
    },
    "University of Minnesota-Twin Cities": {
        "display_mode": "mid50_partial",
        "program_admit_notes": "Carlson School of Management — direct admit via UMN application. More selective than 80% university-wide rate (~45% estimated for Carlson). Typical Carlson freshman: ACT 28-32, GPA 3.7-4.0. Test-optional through Fall 2027.",
    },
    "Indiana University Bloomington (Kelley School of Business)": {
        "display_mode": "holistic_no_stats",
        "program_admit_notes": "Fall 2026+: KPI + holistic review; no GPA/ACT cutoffs or published rate.",
    },
    "University of Iowa (Tippie College of Business)": {
        "display_mode": "direct_admit_criteria",
        "direct_admit": {
            "gpa_min": 3.60,
            "act_min": 26,
            "sat_min": 1230,
            "logic": "gpa_and_test",
            "guaranteed": True,
        },
        "program_admit_notes": "Guaranteed Tippie BBA direct admit when all criteria met.",
    },
    "University of St. Thomas (Opus College of Business)": {
        "display_mode": "mid50_partial",
        "program_admit_notes": "Opus via central admissions; ACT range only (US News).",
    },
    "Minnesota State University, Mankato (College of Business)": {
        "display_mode": "pathway",
        "program_admit_notes": "General admit first; College of Business competitive after year 1.",
    },
    "St. Cloud State University (G.R. Herberger College of Business)": {
        "display_mode": "university_only",
        "program_admit_notes": "General admission; business program separate requirements.",
    },
    "Bethel University (Business & Economics)": {
        "display_mode": "holistic_no_stats",
        "program_admit_notes": "Holistic admissions; no separate business rate or mid-50%.",
    },
    "Augsburg University (Business Administration)": {
        "display_mode": "holistic_no_stats",
        "program_admit_notes": "Holistic admissions; no separate business mid-50%.",
    },
    "University of Wisconsin-Eau Claire (College of Business)": {
        "display_mode": "university_only",
        "program_admit_notes": "General admit; MN-WI reciprocity tuition.",
    },
    "University of Wisconsin-La Crosse (College of Business)": {
        "display_mode": "university_only",
        "program_admit_notes": "General admit; MN-WI reciprocity tuition.",
    },
    "Iowa State University (Ivy College of Business)": {
        "display_mode": "pathway",
        "program_admit_notes": "Enter as pre-business; major after prerequisites + GPA.",
    },
    "North Dakota State University (College of Business)": {
        "display_mode": "university_only",
        "program_admit_notes": "General admit; MN-ND reciprocity tuition.",
    },
    "Winona State University (College of Business)": {
        "display_mode": "university_only",
        "program_admit_notes": "General admission; business admin B.S.",
    },
}


def _merged_profile(college_name: str) -> Dict[str, Any]:
    cache = get_college(college_name) or {}
    override = cache.get("admit_profile") or {}
    if override:
        base: Dict[str, Any] = {"display_mode": "university_only"}
        base.update(override)
        return base
    return dict(DEFAULT_ADMIT_PROFILES.get(college_name, {"display_mode": "university_only"}))


def _in_band(value: float, low: Optional[float], high: Optional[float]) -> Optional[bool]:
    if low is None or high is None:
        return None
    return low <= value <= high


def _format_direct_admit_requirements(direct: Dict[str, Any]) -> str:
    parts: List[str] = []
    if direct.get("gpa_min") is not None:
        parts.append(f"GPA ≥{direct['gpa_min']:.2f}")
    test_parts: List[str] = []
    if direct.get("act_min") is not None:
        test_parts.append(f"ACT ≥{direct['act_min']}")
    if direct.get("sat_min") is not None:
        test_parts.append(f"SAT ≥{direct['sat_min']}")
    if test_parts:
        parts.append(" or ".join(test_parts))
    return "; ".join(parts) if parts else "—"


def _eval_direct_admit(profile: Dict[str, Any], direct: Dict[str, Any], eff_act: int, eff_sat: int) -> str:
    gpa = float(profile.get("gpa_unweighted", 0))
    gpa_min = direct.get("gpa_min")
    act_min = direct.get("act_min")
    sat_min = direct.get("sat_min")

    gpa_ok = gpa_min is None or gpa >= gpa_min
    act = eff_act or 0
    sat = int(profile.get("sat") or 0)
    act_ok = act_min is not None and act >= act_min
    sat_ok = sat_min is not None and sat >= sat_min
    test_ok = act_ok or sat_ok
    if act_min is None and sat_min is None:
        test_ok = True

    if gpa_ok and test_ok:
        return "Yes"
    if gpa_ok or test_ok:
        return "Partial"
    return "No"


def _mid50_meets_summary(
    profile: Dict[str, Any],
    stats: Dict[str, Any],
    eff_sat: int,
    eff_act: int,
) -> str:
    gpa = float(profile.get("gpa_unweighted", 0))
    in_parts: List[str] = []
    out_parts: List[str] = []

    for label, value, lo_key, hi_key in (
        ("GPA", gpa, "gpa_mid50_low", "gpa_mid50_high"),
        ("SAT", float(eff_sat), "sat_mid50_low", "sat_mid50_high"),
        ("ACT", float(eff_act), "act_mid50_low", "act_mid50_high"),
    ):
        lo, hi = stats.get(lo_key), stats.get(hi_key)
        if lo is None or hi is None:
            continue
        if _in_band(value, lo, hi):
            in_parts.append(label)
        else:
            out_parts.append(label)

    if not in_parts and not out_parts:
        return "—"
    if in_parts and not out_parts:
        return f"In mid-50% ({'/'.join(in_parts)})"
    if in_parts and out_parts:
        return f"Partial ({', '.join(in_parts)} in; {', '.join(out_parts)} outside)"
    return f"Below ({', '.join(out_parts)})"


def resolve_program_admit(
    college_name: str,
    profile: Dict[str, Any],
    stats: Dict[str, Any],
    eff_sat: int,
    eff_act: int,
) -> Dict[str, str]:
    """Sheet fields for program-level admission (columns 6–9)."""
    prof = _merged_profile(college_name)
    mode = prof.get("display_mode", "university_only")
    type_label = DISPLAY_MODE_LABELS.get(mode, mode.replace("_", " ").title())

    requirements = "—"
    meets = "—"
    notes = prof.get("program_admit_notes", "")

    if mode == "direct_admit_criteria":
        direct = prof.get("direct_admit", {})
        requirements = _format_direct_admit_requirements(direct)
        meets = _eval_direct_admit(profile, direct, eff_act, eff_sat)
    elif mode in ("mid50_band", "mid50_partial"):
        meets = _mid50_meets_summary(profile, stats, eff_sat, eff_act)
    elif mode == "holistic_no_stats":
        meets = "Review holistically"
    elif mode == "pathway":
        meets = "Pre-business / apply later"
    elif mode == "university_only":
        meets = "University admit only"
        has_band = stats.get("gpa_has_range") or stats.get("sat_has_range") or stats.get("act_has_range")
        if has_band:
            suffix = "Mid-50% columns = university-wide (not College of Business). No EA/ED."
        else:
            suffix = "No published program mid-50%; general university admission. No EA/ED."
        if suffix.lower() not in (notes or "").lower():
            notes = f"{notes} {suffix}".strip() if notes else suffix
    elif mode == "not_applicable":
        meets = "N/A"

    return {
        "program_admit_type": type_label,
        "program_requirements": requirements,
        "student_meets_program_req": meets,
        "program_admit_notes": notes,
    }
