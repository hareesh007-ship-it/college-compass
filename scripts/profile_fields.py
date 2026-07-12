"""Single source of truth for student profile Excel fields ↔ JSON paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from _paths import INPUT

PROFILE_XLSX = INPUT / "student profile input.xlsx"


@dataclass(frozen=True)
class ProfileFieldSpec:
    label: str
    path: str
    required: bool = False
    example: str = ""
    comment: str = ""
    kind: str = "str"  # str, int, float, bool, comma_list, semicolon_list


ProfileSection = Tuple[str, List[ProfileFieldSpec]]

PROFILE_SECTIONS: List[ProfileSection] = [
    (
        "REQUIRED — fill these for matching",
        [
            ProfileFieldSpec(
                "Student full name",
                "name",
                True,
                "Alex Sample",
                "Required. Legal name or name used on applications.",
            ),
            ProfileFieldSpec(
                "Intended major",
                "intended_major",
                True,
                "Business Administration",
                "Required. Drives program fit and specialty rank column (e.g. entrepreneurship, CS, nursing).",
            ),
            ProfileFieldSpec(
                "State of residence",
                "state_of_residence",
                True,
                "Minnesota",
                "Required. Used for in-state tuition and regional filters.",
            ),
            ProfileFieldSpec(
                "Max tuition budget (USD per year)",
                "budget_max_tuition_per_year",
                True,
                "35000",
                "Required. Whole dollars only — sticker price before aid, e.g. 35000.",
                "int",
            ),
            ProfileFieldSpec(
                "College preferences — regions",
                "preferences.regions",
                True,
                "Minnesota, Midwest",
                "Required. Comma-separated regions where you want schools considered.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "College preferences — surrounding states",
                "preferences.surrounding_states",
                True,
                "Wisconsin, Iowa, North Dakota, South Dakota, Illinois, Indiana",
                "Required. Comma-separated US states to include beyond your home region.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "Public schools OK?",
                "preferences.public_ok",
                True,
                "Yes",
                "Required. Enter Yes or No.",
                "bool",
            ),
            ProfileFieldSpec(
                "Private schools OK?",
                "preferences.private_ok",
                True,
                "Yes",
                "Required. Enter Yes or No.",
                "bool",
            ),
            ProfileFieldSpec(
                "Prefer local / nearby colleges?",
                "preferences.prefer_local",
                True,
                "Yes",
                "Required. Yes = favor schools in your regions/states; No = open to wider geography.",
                "bool",
            ),
            ProfileFieldSpec(
                "Key courses / coursework",
                "academic_highlights.key_coursework_summary",
                True,
                "AP Env Science, AP CSP, AP Gov; Personal Finance, Accounting 1, Intro to Business; AP Statistics planned",
                "Required summary of AP, honors, and major-related courses. "
                "You may also add transcript.pdf in the input folder instead of listing every course here.",
            ),
        ],
    ),
    (
        "ACADEMICS & TESTS — strongly recommended",
        [
            ProfileFieldSpec("Grade", "grade", False, "12", "Current grade level, e.g. 11 or 12.", "int"),
            ProfileFieldSpec("Class of", "class_of", False, "2027", "High school graduation year.", "int"),
            ProfileFieldSpec(
                "Unweighted GPA",
                "gpa_unweighted",
                False,
                "3.50",
                "4.0 scale from official transcript. Leave blank only if providing transcript.pdf in input/.",
                "float",
            ),
            ProfileFieldSpec(
                "Weighted GPA",
                "gpa_weighted",
                False,
                "3.70",
                "Optional if your school reports weighted GPA.",
                "float",
            ),
            ProfileFieldSpec(
                "GPA source / transcript date",
                "gpa_source",
                False,
                "Official transcript MM/DD/YYYY",
                "Where GPA came from — helps verify against transcript file.",
            ),
            ProfileFieldSpec(
                "SAT total",
                "sat",
                False,
                "1200",
                "Leave blank if using ACT only. Superscore not used — enter best single sitting unless noted.",
                "int",
            ),
            ProfileFieldSpec(
                "ACT composite",
                "act.composite",
                False,
                "26",
                "Leave blank if using SAT only. Matcher uses the better of SAT vs ACT equivalent.",
                "int",
            ),
            ProfileFieldSpec("ACT English", "act.english", False, "25", "Optional subscore.", "int"),
            ProfileFieldSpec("ACT Math", "act.math", False, "27", "Optional subscore.", "int"),
            ProfileFieldSpec("ACT Reading", "act.reading", False, "25", "Optional subscore.", "int"),
            ProfileFieldSpec("ACT Science", "act.science", False, "26", "Optional subscore.", "int"),
            ProfileFieldSpec("ACT sittings", "act.sittings", False, "1", "Number of times ACT was taken (optional).", "int"),
        ],
    ),
    (
        "APPLICATION TIMELINE",
        [
            ProfileFieldSpec(
                "Senior year start (YYYY-MM)",
                "application_cycle.senior_year_start",
                False,
                "2026-09",
                "First month of senior year, e.g. 2026-09.",
            ),
            ProfileFieldSpec(
                "Applying fall year",
                "application_cycle.applying_fall",
                False,
                "2026",
                "Calendar year you submit applications, e.g. 2026 for Fall 2027 entry.",
                "int",
            ),
            ProfileFieldSpec(
                "College start (YYYY-MM)",
                "application_cycle.college_start",
                False,
                "2027-08",
                "Expected first month of college, e.g. 2027-08.",
            ),
        ],
    ),
    (
        "HIGH SCHOOL & INTERESTS — optional (Excel or files in input/)",
        [
            ProfileFieldSpec(
                "High school name",
                "high_school",
                False,
                "Sample High School",
                "Optional. Shown on selection sheet header.",
            ),
            ProfileFieldSpec("High school district", "high_school_district", False, "Sample School District", "Optional."),
            ProfileFieldSpec(
                "High school CEEB code",
                "high_school_ceeb",
                False,
                "000000",
                "Optional 6-digit code if known (Common App / counselor).",
            ),
            ProfileFieldSpec(
                "Schools especially interested in",
                "schools_interested_in",
                False,
                "University of Minnesota - Carlson School of Management",
                "Comma-separated. Required to include specific schools you already want considered — "
                "these are always added to the search list. Discovery also finds schools from regions/budget via College Scorecard.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "Campus size preference",
                "preferences.campus_size",
                False,
                "",
                "Optional: small, medium, large, or leave blank for no preference.",
            ),
            ProfileFieldSpec(
                "Financial aid needed?",
                "financial_aid_needed",
                False,
                "No",
                "Yes or No — informational for planning; budget field drives matcher filter.",
                "bool",
            ),
            ProfileFieldSpec(
                "Early decision OK?",
                "early_decision_ok",
                False,
                "Yes",
                "Yes if binding Early Decision is acceptable; No if you will not apply ED.",
                "bool",
            ),
        ],
    ),
    (
        "COURSES & ACTIVITIES — optional (Excel or resume/transcript in input/)",
        [
            ProfileFieldSpec(
                "AP courses (completed or in progress)",
                "academic_highlights.ap_completed_or_in_progress",
                False,
                "AP Environmental Science, AP Computer Science Principles, AP US Government & Politics",
                "Comma-separated. Or leave blank if listed on transcript.pdf.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "AP courses planned (senior year)",
                "academic_highlights.ap_planned_senior",
                False,
                "AP Statistics",
                "Optional.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "Business / major-related coursework",
                "academic_highlights.business_coursework",
                False,
                "Personal Finance, Accounting 1, Introduction to Business",
                "Optional detail beyond Key courses row.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "Senior courses planned",
                "academic_highlights.senior_courses_planned_tentative",
                False,
                "AP Statistics, Criminal Studies, Stress Management, Marketing 1, Investment Strategies",
                "Tentative schedule OK.",
                "comma_list",
            ),
            ProfileFieldSpec(
                "Class rank",
                "academic_highlights.class_rank",
                False,
                "Not reported",
                "Optional — many schools no longer report rank.",
            ),
            ProfileFieldSpec(
                "DECA / business club planned?",
                "academic_highlights.deca_planned",
                False,
                "Yes",
                "Yes or No — optional.",
                "bool",
            ),
            ProfileFieldSpec(
                "Work / jobs",
                "activities_summary.work",
                False,
                "Lifeguard — Lakeside Community Center",
                "Optional. Or provide resume.pdf in input/.",
                "semicolon_list",
            ),
            ProfileFieldSpec(
                "Awards & honors",
                "activities_summary.awards",
                False,
                "State Science Fair — Second Place; National Merit Commended Scholar",
                "Optional. Or provide resume.pdf in input/.",
                "semicolon_list",
            ),
            ProfileFieldSpec(
                "Other activities",
                "activities_summary.other",
                False,
                "Varsity Swimming (4 years); Student Council; Red Cross CPR/AED certified",
                "Sports, clubs, volunteering — optional.",
                "semicolon_list",
            ),
        ],
    ),
    (
        "OTHER — optional",
        [
            ProfileFieldSpec("Citizenship", "citizenship", False, "US", "Optional."),
            ProfileFieldSpec("Gender", "gender", False, "male", "Optional — used only if relevant to your process."),
            ProfileFieldSpec(
                "Notes",
                "notes",
                False,
                "Senior (grade 12) Fall 2026 applications. Transcript/resume/ACT in input/ folder.",
                "Free text for anything else agents should know.",
            ),
            ProfileFieldSpec(
                "Any other preference",
                "preferences.any_other_preference",
                False,
                "",
                "Open text for preferences not covered above — e.g. urban campus, strong study-abroad, "
                "diversity, religious affiliation, must-have clubs, distance from home. "
                "Used by LLM-assisted research to tailor school suggestions and cache notes.",
            ),
        ],
    ),
]


def field_by_label() -> dict[str, ProfileFieldSpec]:
    return {spec.label: spec for _title, fields in PROFILE_SECTIONS for spec in fields}
