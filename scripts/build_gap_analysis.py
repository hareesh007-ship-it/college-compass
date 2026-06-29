#!/usr/bin/env python3
"""Generate College Prep Gap Analysis from profile + match report (same inputs as selection sheet)."""

from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from _paths import INPUT, OUTPUT
from load_profile import profile_first_name
from output_paths import selection_output_paths
from fit_categories import fit_tier_markdown_section


# ---------------------------------------------------------------------------
# HTML envelope — used by write_gap_analysis() and export_gap_analysis_html.py
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       max-width: 820px; margin: 40px auto; padding: 0 24px 48px; color: #1a1a1a; line-height: 1.55; }
h1 { font-size: 1.75rem; border-bottom: 2px solid #333; padding-bottom: 8px; }
h2 { font-size: 1.25rem; margin-top: 2rem; color: #222; }
h3 { font-size: 1.05rem; margin-top: 1.25rem; }
p, li { font-size: 0.95rem; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 20px; font-size: 0.9rem; }
th, td { border: 1px solid #ccc; padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: #f5f5f5; }
hr { border: none; border-top: 1px solid #ddd; margin: 24px 0; }
code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-size: 0.88em; }
.print-hint { background: #fff8e1; border: 1px solid #f0d060; padding: 12px 16px; border-radius: 6px;
              margin-bottom: 24px; font-size: 0.9rem; }
@media print { .print-hint { display: none; } body { margin: 0; max-width: none; } }
"""


def _md_table_block(lines: list) -> str:
    rows = [line.strip() for line in lines if line.strip()]
    if len(rows) < 2:
        return "\n".join(html.escape(x) for x in lines)

    def split_row(row: str) -> list:
        return [c.strip() for c in row.strip("|").split("|")]

    header = split_row(rows[0])
    body_rows = (
        [split_row(r) for r in rows[2:]]
        if len(rows) > 2 and re.match(r"^[\|\s:\-]+$", rows[1])
        else [split_row(r) for r in rows[1:]]
    )
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{html.escape(c)}</th>" for c in header)
    out.append("</tr></thead><tbody>")
    for row in body_rows:
        out.append("<tr>")
        out.extend(f"<td>{html.escape(c)}</td>" for c in row)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _convert_md(text: str) -> str:
    lines = text.splitlines()
    out: list = []
    i = 0
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("|"):
            close_ul()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(_md_table_block(table_lines))
            continue

        if stripped.startswith("---"):
            close_ul()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith("### "):
            close_ul()
            out.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            i += 1
            continue

        if stripped.startswith("## "):
            close_ul()
            out.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            i += 1
            continue

        if stripped.startswith("# "):
            close_ul()
            out.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            raw = stripped[2:]
            raw = re.sub(r"\*\*(.+?)\*\*", lambda m: f"@@BOLD{html.escape(m.group(1))}@@/BOLD", raw)
            item = html.escape(raw).replace("@@BOLD", "<strong>").replace("@@/BOLD", "</strong>")
            out.append(f"<li>{item}</li>")
            i += 1
            continue

        if not stripped:
            close_ul()
            i += 1
            continue

        close_ul()
        para = stripped
        parts = re.split(r"(\*\*.+?\*\*|`[^`]+`)", para)
        rendered = []
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                rendered.append(f"<strong>{html.escape(part[2:-2])}</strong>")
            elif part.startswith("`") and part.endswith("`"):
                rendered.append(f"<code>{html.escape(part[1:-1])}</code>")
            else:
                rendered.append(html.escape(part))
        out.append(f"<p>{''.join(rendered)}</p>")
        i += 1

    close_ul()
    return "\n".join(out)


def wrap_gap_html(markdown_text: str, student_name: str) -> str:
    """Wrap converted markdown in a printable HTML document."""
    body = _convert_md(markdown_text)
    title = student_name or "Student"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>College Prep Gap Analysis — {html.escape(str(title))}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="print-hint">
  <strong>Save as PDF (macOS):</strong> Open this file in Safari or Chrome →
  <strong>File → Print…</strong> (⌘P) → <strong>PDF → Save as PDF</strong>.
  You can delete this yellow box from the PDF; it is hidden when printing.
</div>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def _sheet_helpers():
    from build_selection_sheet import apply_recommendation, sort_entries

    return apply_recommendation, sort_entries


def _load_academic_record(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Canonical location: students/<name>/data/academic_record.json
    # Generated by the LLM research assistant — not a user-editable input file.
    from _paths import STUDENT_DATA
    candidate = STUDENT_DATA / "academic_record.json"
    if candidate.is_file():
        with open(candidate, encoding="utf-8") as f:
            return json.load(f)
    return None


def _short_name(name: str, max_len: int = 42) -> str:
    if len(name) <= max_len:
        return name
    base = name.split(" - ")[0].split(" (")[0]
    return base if len(base) <= max_len else base[: max_len - 1] + "…"


def _primary_interest(profile: Dict[str, Any], report: Dict[str, Any]) -> str:
    preferred = profile.get("schools_interested_in") or []
    if preferred:
        from college_research import resolve_cache_key

        key = resolve_cache_key(preferred[0]) or preferred[0]
        return key.split(" - ")[0]
    for entry in report.get("matches", []):
        if entry.get("priority_interest"):
            return _short_name(entry["name"], 60)
    return "—"


def school_gap_flags(entry: Dict[str, Any]) -> List[str]:
    flags: List[str] = []
    if not entry.get("within_budget"):
        flags.append("Over budget")
    req = str(entry.get("student_meets_program_req") or "")
    if any(x in req for x in ("Partial", "No", "Below", "Does not")):
        flags.append(f"Program: {req}")
    for key, label in (("gpa_position", "GPA"), ("sat_position", "SAT"), ("act_position", "ACT")):
        pos = entry.get(key) or "—"
        if pos != "—" and "Below" in str(pos):
            flags.append(f"{label} {pos}")
    if entry.get("category") == "Reach":
        flags.append("Reach classification")
    return flags


def _tier_assessment(entries: List[Dict[str, Any]], category: str) -> str:
    in_tier = [e for e in entries if e.get("category") == category and not e.get("excluded")]
    if not in_tier:
        return "—"
    with_gaps = [e for e in in_tier if school_gap_flags(e) != ["None identified"] and school_gap_flags(e)]
    flagged = [e for e in in_tier if school_gap_flags(e)]
    if not flagged:
        return "Strong fit — no material gaps on published criteria"
    if category == "Safety":
        return "Solid fit — minor or budget-only flags on some schools"
    if category == "Target":
        return "Review gaps below — stats or program criteria may need attention"
    return "Stretch profile — prioritize reach strategy and alternatives"


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _profile_snapshot_rows(profile: Dict[str, Any], eff_sat: int, eff_act: int) -> List[List[str]]:
    act = profile.get("act")
    act_note = ""
    if isinstance(act, dict):
        act_note = (
            f"E{act.get('english')}/M{act.get('math')}/R{act.get('reading')}/S{act.get('science')}; "
            f"effective SAT {eff_sat}"
        )
    else:
        act_note = f"Effective SAT {eff_sat}"
    budget_note = "No financial aid assumed" if not profile.get("financial_aid_needed") else "Financial aid expected"
    return [
        ["GPA (unweighted)", str(profile["gpa_unweighted"]), profile.get("gpa_source", "")],
        ["GPA (weighted)", str(profile.get("gpa_weighted") or "—"), ""],
        ["ACT", str(eff_act), act_note],
        ["SAT", str(profile.get("sat") or "—"), "Submit ACT if sharing scores (typically stronger)"],
        ["Budget", f"${profile['budget_max_tuition_per_year']:,}/yr tuition", budget_note],
    ]


def _school_fit_rows(entries: List[Dict[str, Any]]) -> List[List[str]]:
    apply_recommendation, _ = _sheet_helpers()
    rows: List[List[str]] = []
    for entry in entries:
        if entry.get("excluded"):
            continue
        gaps = school_gap_flags(entry)
        gap_text = "; ".join(gaps) if gaps else "None identified"
        rows.append([
            _short_name(entry["name"], 48),
            entry.get("category", ""),
            apply_recommendation(entry),
            entry.get("gpa_position") or "—",
            entry.get("sat_position") or "—",
            entry.get("act_position") or "—",
            "Y" if entry.get("within_budget") else "N",
            entry.get("student_meets_program_req") or "—",
            gap_text,
        ])
    return rows


def _target_detail_section(entries: List[Dict[str, Any]]) -> List[str]:
    apply_recommendation, _ = _sheet_helpers()
    lines: List[str] = []
    targets = [
        e for e in entries
        if e.get("category") in ("Target", "Reach") and not e.get("excluded")
    ]
    priority = [e for e in entries if e.get("priority_interest") and not e.get("excluded")]
    seen = set()
    for entry in priority + targets:
        name = entry["name"]
        if name in seen:
            continue
        seen.add(name)
        flags = school_gap_flags(entry)
        if not flags:
            continue
        lines.append(f"### {_short_name(name, 70)}")
        lines.append(f"**Fit:** {entry.get('category')} | **Apply:** {apply_recommendation(entry)}")
        if entry.get("program_admit_notes"):
            lines.append(f"**Admit notes:** {entry['program_admit_notes']}")
        lines.append("")
        lines.append("**Gaps:**")
        for flag in flags:
            lines.append(f"- {flag}")
        for reason in entry.get("reasons") or []:
            if "Below" in reason or "budget" in reason.lower() or "Partial" in reason:
                lines.append(f"- {reason}")
        lines.append("")
    return lines


def _academic_sections(profile: Dict[str, Any], record: Optional[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    highlights = profile.get("academic_highlights") or {}
    senior = highlights.get("senior_courses_planned_tentative") or []
    if record:
        senior = senior or record.get("senior_plan_tentative") or []

    if senior:
        lines.append("**Senior plan (tentative):**")
        for course in senior:
            lines.append(f"- {course}")
        lines.append("")
        ap_count = len(highlights.get("ap_completed_or_in_progress") or []) + len(
            highlights.get("ap_planned_senior") or []
        )
        has_calc = any("calc" in c.lower() for c in senior)
        has_econ = any("econ" in c.lower() for c in senior)
        if ap_count <= 4 and not has_calc:
            lines.append(
                "**Rigor gap:** Senior schedule shows limited AP load for selective business programs. "
                "Consider AP Calculus and/or AP Economics if registration allows."
            )
            lines.append("")

    if record and record.get("course_history_summary"):
        lines.append("**GPA trend (unweighted by term):**")
        for grade, data in sorted(record["course_history_summary"].items()):
            gpas = data.get("term_gpa_unweighted") or []
            if gpas:
                terms = " / ".join(f"{g:.3f}" for g in gpas)
                lines.append(f"- {grade.replace('_', ' ').title()}: {terms}")
        lines.append("")
        g11 = record["course_history_summary"].get("grade_11", {}).get("term_gpa_unweighted") or []
        g10 = record["course_history_summary"].get("grade_10", {}).get("term_gpa_unweighted") or []
        if g11 and g10 and sum(g11) / len(g11) < sum(g10) / len(g10) - 0.05:
            lines.append(
                "**Trend gap:** Junior-year GPA dipped vs. sophomore year. Protect senior fall grades "
                "(sent to Nov EA schools)."
            )
            lines.append("")

    act = profile.get("act")
    if isinstance(act, dict) and act.get("reading") and act["reading"] <= 26:
        lines.append(
            f"**English/reading:** ACT Reading {act['reading']} is the lowest subsection — "
            "invest in essays and senior English rigor."
        )
        lines.append("")

    activities = profile.get("activities_summary") or {}
    awards = activities.get("awards") or []
    if awards:
        lines.append("**Strengths to emphasize:**")
        for award in awards:
            lines.append(f"- {award}")
        lines.append("")

    if not lines:
        lines.append(
            "Add senior course plan and activities to the Excel profile or "
            "`data/academic_record.json` for richer academic gap notes."
        )
    return lines


def _testing_section(profile: Dict[str, Any], eff_sat: int, eff_act: int) -> List[str]:
    sat = profile.get("sat") or 0
    lines = [
        f"- **Effective scores used for matching:** SAT {eff_sat} (max of SAT / ACT equiv), ACT {eff_act}.",
    ]
    if sat and eff_act and sat < eff_sat - 50:
        lines.append(
            f"- **Strategy:** Raw SAT {sat} is weaker than ACT {eff_act} equivalent — "
            "submit ACT where scores are optional but helpful."
        )
    else:
        lines.append("- **Strategy:** Use your stronger score (typically ACT) when submitting test scores.")
    lines.append(
        "- **Retake:** Only if targeting a modest ACT bump without hurting senior grades — not required for safeties."
    )
    return lines


def _deadline_rows(entries: List[Dict[str, Any]], applying_fall: int) -> List[List[str]]:
    apply_recommendation, _ = _sheet_helpers()
    rows: List[List[str]] = []
    for entry in entries:
        if entry.get("excluded") or apply_recommendation(entry).startswith("No"):
            continue
        dl = entry.get("deadlines") or {}
        ea = dl.get("early_action") or "—"
        reg = dl.get("regular") or "—"
        rows.append([_short_name(entry["name"], 40), entry.get("category", ""), ea, reg])
    rows.sort(key=lambda r: (0 if r[2] != "—" else 1, r[0]))
    return rows[:15]


def _not_gap_bullets(entries: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[str]:
    bullets: List[str] = []
    home = profile.get("state_of_residence", "")
    for entry in entries:
        if entry.get("excluded"):
            continue
        flags = school_gap_flags(entry)
        if flags:
            continue
        bullets.append(
            f"**{_short_name(entry['name'], 45)}** — stats and budget align for {entry.get('category', 'fit')} tier."
        )
    if home:
        bullets.append(f"{home} resident tuition advantage at in-state public schools.")
    biz = profile.get("academic_highlights", {}).get("business_coursework") or []
    if biz:
        bullets.append(f"Business coursework foundation: {', '.join(biz[:3])}.")
    return bullets[:12]


def _priority_actions(
    entries: List[Dict[str, Any]],
    profile: Dict[str, Any],
    applying_fall: int,
) -> List[List[str]]:
    actions: List[List[str]] = []
    n = 1

    def add(action: str, timing: str) -> None:
        nonlocal n
        actions.append([str(n), action, timing])
        n += 1

    targets_with_gaps = [
        e for e in entries
        if e.get("category") in ("Target", "Reach")
        and not e.get("excluded")
        and school_gap_flags(e)
    ]
    if targets_with_gaps:
        names = ", ".join(_short_name(e["name"], 25) for e in targets_with_gaps[:3])
        add(f"Address stat/program gaps for target schools ({names})", "Before applications")

    add("Finalize senior schedule with counselor (rigor + English 12 + science if needed)", f"Summer {applying_fall}")
    add("Protect senior fall GPA (Nov EA deadlines)", f"Fall {applying_fall}")
    add("Draft Common App essay and school supplements", f"Aug–Sep {applying_fall}")

    ea_schools = [
        e for e in entries
        if not e.get("excluded")
        and (e.get("deadlines") or {}).get("early_action")
    ]
    if ea_schools:
        add(
            f"Submit EA applications ({len(ea_schools)} schools with EA dates on checklist)",
            f"Nov {applying_fall}",
        )

    for entry in entries:
        if entry.get("priority_interest") and not entry.get("excluded"):
            add(f"Complete application: {_short_name(entry['name'], 35)}", "By regular deadline")
            break

    add("Regenerate match list after profile or school list changes", "`python3 scripts/run.py`")
    return actions


def build_gap_markdown(profile: Dict[str, Any], report: Dict[str, Any]) -> str:
    """Build full gap analysis markdown from the same match report as the selection sheet."""
    _, sort_entries = _sheet_helpers()
    today = date.today().strftime("%B %d, %Y")
    student = profile.get("name") or "Student"
    cycle = profile.get("application_cycle") or {}
    applying = cycle.get("applying_fall", 2026)
    college_start = cycle.get("college_start", "2027-08")
    major = profile.get("intended_major", "")
    notes = report.get("matching_notes") or {}
    eff_sat = notes.get("effective_sat_used", 0)
    eff_act = notes.get("effective_act_used", 0)
    summary = report.get("summary") or {}
    entries = sort_entries(report)
    recommended = [e for e in entries if not e.get("excluded")]
    record = _load_academic_record(profile)
    n_rec = len(recommended)

    safety_names = summary.get("safety") or []
    target_names = summary.get("target") or []
    reach_names = summary.get("reach") or []

    def name_list(names: List[str]) -> str:
        if not names:
            return "—"
        return ", ".join(_short_name(n, 35) for n in names[:8]) + ("…" if len(names) > 8 else "")

    exec_para = (
        f"{student.split()[0] if student else 'Student'} has **{n_rec} recommended schools** "
        f"({len(safety_names)} Safety, {len(target_names)} Target, {len(reach_names)} Reach) "
        f"from the current catalog and research cache. "
    )
    if target_names:
        exec_para += (
            "Focus gap analysis on **Target** schools and any **top-interest** picks where stats, "
            "budget, or program criteria flag a gap."
        )
    else:
        exec_para += "Current list is heavily weighted toward Safety — consider whether more selective targets are desired."

    sections: List[str] = [
        f"# College Prep Gap Analysis — {student}",
        "",
        f"**Prepared:** {today}  ",
        f"**High school:** {profile.get('high_school', '')} ({profile.get('high_school_district', '')})  ",
        f"**Class of:** {profile.get('class_of', '')} | **Applying:** Fall {applying} | **Start college:** {college_start}  ",
        f"**Intended major:** {major}  ",
        f"**Primary interest:** {_primary_interest(profile, report)}  ",
        "",
        f"**Sources:** {profile.get('gpa_source', 'Student profile')}, match report "
        f"({n_rec} recommended schools; {notes.get('methodology', 'discovery + cache')})",
        "",
        fit_tier_markdown_section(),
        "## Executive summary",
        "",
        exec_para,
        "",
        _md_table(
            ["Tier", "Count", "Schools (sample)", "Assessment"],
            [
                ["Safety", str(len(safety_names)), name_list(safety_names), _tier_assessment(entries, "Safety")],
                ["Target", str(len(target_names)), name_list(target_names), _tier_assessment(entries, "Target")],
                ["Reach", str(len(reach_names)), name_list(reach_names), _tier_assessment(entries, "Reach")],
            ],
        ),
        "",
        "---",
        "",
        "## Profile snapshot",
        "",
        _md_table(["Metric", "Value", "Notes"], _profile_snapshot_rows(profile, eff_sat, eff_act)),
        "",
        "---",
        "",
        "## Recommended schools — fit & gaps",
        "",
        "Same schools and columns logic as the US College Selection sheet.",
        "",
        _md_table(
            [
                "University",
                "Fit",
                "Apply?",
                "GPA vs mid-50%",
                "SAT vs mid-50%",
                "ACT vs mid-50%",
                "Budget",
                "Program req",
                "Key gaps",
            ],
            _school_fit_rows(entries),
        ),
        "",
        "---",
        "",
        "## Target & top-interest schools — detail",
        "",
    ]
    detail = _target_detail_section(entries)
    sections.extend(detail if detail else ["No material gaps flagged on Target/Reach schools with published criteria.", ""])
    sections.extend([
        "---",
        "",
        "## Academic preparation",
        "",
    ])
    sections.extend(_academic_sections(profile, record))
    sections.extend([
        "",
        "---",
        "",
        "## Testing strategy",
        "",
    ])
    sections.extend(_testing_section(profile, eff_sat, eff_act))
    sections.extend([
        "",
        "---",
        "",
        "## Application deadlines (recommended list)",
        "",
        _md_table(
            ["University", "Fit", "Early Action", "Regular"],
            _deadline_rows(entries, applying),
        ),
        "",
        "See the **College Selection** tab in the selection spreadsheet for per-school deadlines.",
        "",
        "---",
        "",
        "## What is NOT a gap",
        "",
    ])
    not_gaps = _not_gap_bullets(entries, profile)
    sections.extend(f"- {b}" for b in not_gaps)
    sections.extend([
        "",
        "---",
        "",
        "## Priority action list",
        "",
        _md_table(["Priority", "Action", "Timing"], _priority_actions(entries, profile, applying)),
        "",
        "---",
        "",
        "## Document maintenance",
        "",
        f"This file is **auto-generated** on {today} by `scripts/build_gap_analysis.py` "
        f"when you run `python3 scripts/run.py`.",
        "",
        "**Regenerate when:** senior schedule is finalized, grades update, school list changes, or new test scores.",
        "",
        f"**Companion files:** `{profile_first_name(profile)} - US College Selection.xlsx`, `college_matches.md`",
        "",
    ])
    return "\n".join(sections)


def build_gap_summary_rows(
    profile: Dict[str, Any],
    report: Dict[str, Any],
    gap_html: Path,
) -> List[List[str]]:
    """Condensed gap summary for Excel tab 3."""
    _, sort_entries = _sheet_helpers()
    summary = report.get("summary") or {}
    entries = [e for e in sort_entries(report) if not e.get("excluded")]
    flagged = sum(1 for e in entries if school_gap_flags(e))
    return [
        ["College Prep Gap Analysis — Summary"],
        ["Generated", date.today().isoformat()],
        ["Full report (HTML)", str(gap_html.name)],
        [""],
        ["Recommended schools", str(len(entries))],
        ["Safety / Target / Reach", f"{len(summary.get('safety', []))} / {len(summary.get('target', []))} / {len(summary.get('reach', []))}"],
        ["Schools with flagged gaps", str(flagged)],
        [""],
        ["Open in browser", f"Double-click {gap_html.name} → Print → Save as PDF"],
        ["Regenerate", "python3 scripts/run.py"],
    ]


def write_gap_analysis(
    profile: Dict[str, Any],
    report: Dict[str, Any],
    *,
    major_label: Optional[str] = None,
) -> Path:
    """Write gap analysis HTML for one major.

    major_label — first word of the major used as filename suffix when a student
    has two majors, e.g. "Business" → "Alex - College Prep Gap Analysis - Business.html".
    Omit (or pass None) for single-major runs to keep the original filename.
    """
    from output_paths import gap_html_path

    html_path = gap_html_path(profile, major_label)
    md_text = build_gap_markdown(profile, report)
    html_doc = wrap_gap_html(md_text, profile.get("name") or "Student")
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {html_path}")
    return html_path
