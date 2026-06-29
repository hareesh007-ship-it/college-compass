"""Shared Safety / Target / Reach definitions for Excel and gap analysis outputs."""

from __future__ import annotations

from typing import Any, Dict, List


FIT_TIERS: List[Dict[str, str]] = [
    {
        "name": "Safety",
        "summary": (
            "Your GPA and test scores are at or above this school's typical admitted profile, "
            "and the school accepts a relatively large share of applicants. Admission is likely "
            "(not guaranteed) if you meet program requirements — good schools to apply to with confidence."
        ),
        "detail": (
            "Classified when your stats score competitively against published mid-50% GPA/SAT bands "
            "and the school's acceptance rate is relatively high (often ~65%+ when your profile aligns). "
            "Use Safeties to balance your list and support financial aid comparisons."
        ),
    },
    {
        "name": "Target",
        "summary": (
            "Your stats fall within or close to the school's published mid-50% ranges — a realistic "
            "match where admission is plausible but not assured. These should be the core of your list."
        ),
        "detail": (
            "Classified when GPA and SAT/ACT align with typical admits at moderately selective schools, "
            "or when your stats are slightly above/below mid-50% at schools with moderate acceptance rates. "
            "Focus application effort and gap-closing here."
        ),
    },
    {
        "name": "Reach",
        "summary": (
            "Admission is possible but less likely: your stats are below the school's typical profile, "
            "the school is highly selective, or tuition exceeds your budget without aid. Apply if you "
            "want the option — do not count on admission."
        ),
        "detail": (
            "Classified when stats fall meaningfully below published mid-50% bands, acceptance rate is "
            "low (often under ~25%), the school is ultra-selective (e.g. top-10 national), or budget "
            "is a stretch. Reach schools need strong essays, hooks, or merit aid to be realistic."
        ),
    },
]


def fit_tier_excel_rows(num_columns: int) -> List[List[str]]:
    """Rows inserted into the selection sheet header block before column headers."""
    pad = [""] * (num_columns - 1)
    rows: List[List[str]] = [
        [""] + pad,
        ["How schools are classified (Safety / Target / Reach)"] + pad,
    ]
    for tier in FIT_TIERS:
        rows.append([tier["name"], tier["summary"]] + pad[2:])
    rows.append([""] + pad)
    return rows


def fit_tier_markdown_section() -> str:
    """Markdown section for gap analysis HTML (print-to-PDF)."""
    lines = [
        "## How schools are classified",
        "",
        "Each recommended school is labeled **Safety**, **Target**, or **Reach** by comparing your "
        "unweighted GPA and best SAT/ACT (whichever is stronger) to published mid-50% admit ranges "
        "and acceptance rates from official sources and the research cache.",
        "",
    ]
    for tier in FIT_TIERS:
        lines.extend([
            f"### {tier['name']}",
            "",
            tier["summary"],
            "",
            tier["detail"],
            "",
        ])
    lines.append("---")
    lines.append("")
    return "\n".join(lines)
