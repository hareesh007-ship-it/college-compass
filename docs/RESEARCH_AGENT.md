# College Research Agent Playbook

**Project:** college-compass  
**Audience:** Humans and Cursor AI agents  
**Last updated:** 2026-06-27

Read this file **before** editing college research data or running web research. In a new chat, attach `@docs/RESEARCH_AGENT.md` plus the specific school name(s).

---

## 1. Purpose

College research means gathering **official, citable data** for schools in the matcher and writing it to **one JSON cache**. The Python pipeline (`scripts/college_finder.py`, `scripts/build_selection_sheet.py`) reads that cache — it does not re-research on each run.

This playbook prevents:

- Copying stats from one school to another (e.g. Carlson ranked #54 from UIC)
- Splitting data across legacy files
- Orphan JSON keys (e.g. `admit_profile` at the wrong level)
- Expensive “research all 21 schools again” loops

---

## 2. Scope commands (cost control)

**Default:** If the user’s intent is unclear, **ask** — do not assume a full refresh.

| Command | Agent behavior |
|---------|----------------|
| `update cache only: <school> <field>` | Edit `college_research_cache.json` only. No web search unless the field is missing or user says data is wrong. |
| `research school: <name>` | Web research for **one** school. Update all cache blocks needed for the sheet. |
| `research field: <schools> <field>` | One field across named schools (e.g. `research field: recommended deadlines`). Not a full refresh. |
| `full refresh: all` | All catalog schools — **only when the user explicitly says this**. |

**Current catalog:** run `college-compass run` and check `data/colleges/catalog.json` for the live school list (generated dynamically from the student profile + Scorecard API).

---

## 3. Single write target

| Do | Don’t |
|----|-------|
| Write research to `data/college_research_cache.json` | Edit `data/acceptance_rates.json` (legacy) |
| Match college keys **exactly** to catalog `cache_key` names | Edit `data/us_news_rankings_2026.json` (deprecated) |
| Override program admit via nested `admit_profile` under the college | Hardcode tuition, rates, or mid-50% into matcher seed data |

**College key names (must match exactly):**

```
University of Illinois Urbana-Champaign
Purdue University
University of Wisconsin-Madison
University of Illinois Chicago
Illinois Institute of Technology
MIT
Stanford University
Carnegie Mellon University
University of Minnesota - Carlson School of Management
Indiana University Bloomington (Kelley School of Business)
University of Iowa (Tippie College of Business)
University of St. Thomas (Opus College of Business)
Minnesota State University, Mankato (College of Business)
St. Cloud State University (Gherkin Business School)
Bethel University (Business & Economics)
Augsburg University (Business Administration)
University of Wisconsin-Eau Claire (College of Business)
University of Wisconsin-La Crosse (College of Business)
Iowa State University (Ivy College of Business)
North Dakota State University (College of Business)
Winona State University (College of Business)
```

---

## 4. Cache schema contract

Root object:

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | Yes | Must be `1` |
| `last_updated` | Yes | `YYYY-MM-DD` — bump on any cache edit |
| `rankings_source` | Yes | Global note (e.g. US News 2026) |
| `colleges` | Yes | Map of college name → entry |

Per-college entry:

| Block | Required | When to leave blank / null |
|-------|----------|----------------------------|
| `researched_at` | Yes on any change | `YYYY-MM-DD` |
| `rankings` | Yes | `entrepreneurship: null` if not in US News specialty list |
| `tuition` | Yes | `in_state`, `out_of_state`, `year`, `source_url` |
| `acceptance_rates` | Yes | `university_general` + `business_program`; use `display` text when no numeric rate |
| `deadlines` | Yes | `early_action`, `early_decision`, `regular`, `ed_available` |
| `admit_stats` | Optional | **Only** if official **program-level** mid-50% exists; omit block if not |
| `admit_profile` | Optional | Nested **under college**; overrides `program_admit.py` defaults |
| `business_program_note` | Recommended | Sheet column 27 |
| `business_program_secondary` | Rare | Secondary rate for display/fit; set `use_for_fit: true` only when matcher should use it |
| `research_method` | Optional | Pro audit: `backend`, `scope`, `researched_at`, `source_urls[]` — see [`PROFILE_AND_CONFIG.md`](PROFILE_AND_CONFIG.md) |

### Rankings object

```json
"rankings": {
  "national_university": 59,
  "undergrad_business": 19,
  "entrepreneurship": null,
  "notes": "Optional context"
}
```

- **National** ≠ **undergrad business** ≠ **entrepreneurship** — never swap types.
- Sheet column 3 uses major-aware rank via `college_research.program_rank_for_major()`.

### Acceptance rate block

Each of `university_general` and `business_program`:

```json
{
  "value": 0.366,
  "display": "36.6%",
  "label": "Human-readable scope",
  "source_url": "https://...",
  "source_note": "Who published it; program vs university scope"
}
```

- `value: null` is valid when only criteria or narrative exists (Kelley, Iowa Tippie business slot).
- `business_program_secondary`: optional third slot; Carlson uses `use_for_fit: true` for matcher fit rate.

### Admit stats (mid-50%)

```json
"admit_stats": {
  "scope": "Program or university — be explicit",
  "cycle": "Fall 2025",
  "gpa_mid50_low": 3.72,
  "gpa_mid50_high": 3.97,
  "sat_mid50_low": 1350,
  "sat_mid50_high": 1470,
  "act_mid50_low": 28,
  "act_mid50_high": 32,
  "source": "Page title",
  "source_url": "https://..."
}
```

- Omit individual GPA/SAT/ACT fields if not published (partial bands OK).
- **Blank mid-50% for ~15 schools is intentional** when no official program band exists — do not invent numbers.

### Admit profile (nested under college only)

```json
"admit_profile": {
  "display_mode": "direct_admit_criteria",
  "direct_admit": {
    "gpa_min": 3.60,
    "act_min": 26,
    "sat_min": 1230,
    "logic": "gpa_and_test",
    "guaranteed": true
  },
  "program_admit_notes": "Sheet column 9 override text"
}
```

Valid `display_mode` values (must match `program_admit.py`):

| Mode | Example schools |
|------|-----------------|
| `mid50_band` | Carlson, Purdue, UIUC Gies |
| `mid50_partial` | Wisconsin, UIC, St Thomas |
| `direct_admit_criteria` | Iowa Tippie |
| `holistic_no_stats` | Kelley, Bethel, Augsburg, CMU |
| `pathway` | Mankato, Iowa State |
| `university_only` | Winona, NDSU, UWEC |
| `not_applicable` | MIT, Stanford |

Defaults live in `program_admit.py` → `DEFAULT_ADMIT_PROFILES`. Cache `admit_profile` **merges over** defaults.

### Wrong vs right (orphan key)

**Wrong** — reserved key at `colleges` top level:

```json
"colleges": {
  "University of Iowa (Tippie College of Business)": { "..." },
  "admit_profile": { "display_mode": "direct_admit_criteria" }
}
```

**Right** — nested under the college:

```json
"colleges": {
  "University of Iowa (Tippie College of Business)": {
    "admit_profile": { "display_mode": "direct_admit_criteria", "..." }
  }
}
```

---

## 5. Source priority

1. **Official:** University admissions, business school site, Common Data Set (CDS) PDF  
2. **US News 2026:** National, undergrad business, entrepreneurship specialty; tuition when official page is unclear  
3. **Secondary:** Poets&Quants, news releases — **must** say so in `source_note`; never use for fit without user approval except documented cases (Carlson P&Q rate)

**Rules:**

- Never copy a stat from School A onto School B.
- Label scope in every rate: university-wide vs business program vs pre-business pathway.
- Prefer program-level mid-50% for business majors when published.
- Record `source_url` for every block you add or change.

---

## 6. Field-specific rules

### Rankings

- Verify **2026** US News edition when updating ranks.
- Entrepreneurship specialty: only schools on the list get a number; else `null`.
- Regional Midwest rank is fallback for sheet display only — note in `rankings.notes` if used.

### Tuition

- Store published in-state and out-of-state amounts for the current academic year.
- MN reciprocity (WI, ND, SD publics) is applied in **Python** (`scripts/college_finder.py`) — cache stores list prices; note reciprocity in `business_program_note` if relevant.

### Acceptance rates

- Column 22 = `university_general`; column 23 = `business_program`.
- Wisconsin `business_program_secondary` is for **current UW students** — do **not** set `use_for_fit: true` on that block.
- Carlson `business_program_secondary` has `use_for_fit: true` — official business rate is unpublished.

### Mid-50% and fit

- Matcher and sheet “Meets?” use cache mid-50% when present.
- Point estimates in `scripts/college_finder.py` are fallback for matching only — not shown on sheet when cache has bands.

### Deadlines

- Use short labels: `"Nov 1"`, `"Jan 15"`, or `null` if not offered.
- `ed_available`: boolean for Early Decision binding column.

---

## 7. Pre-write checklist (mandatory)

Before finishing any cache edit:

```
[ ] Scope command confirmed with user
[ ] Only data/college_research_cache.json changed (unless user asked otherwise)
[ ] College key matches catalog / cache name exactly
[ ] admit_profile nested under college (never top-level orphan)
[ ] source_url present for changed blocks
[ ] last_updated and per-school researched_at set to today (YYYY-MM-DD)
[ ] python3 scripts/validate_cache.py  → must pass (0 errors)
[ ] python3 scripts/college_finder.py && python3 scripts/build_selection_sheet.py
[ ] Spot-check that school’s row in students/<name>/output/<Name> - US College Selection.xlsx
[ ] Optional: set `research_method` on the college entry; append research log (see §7.1)
```

### 7.1 Research logging (Pro path)

After a scoped research session, record what happened for audit:

1. **`validate_cache.py`** auto-appends a `validate` event to `output/logs/research_log.jsonl` when logging is enabled in `config/pro.json`.
2. **Matcher/sheet** runs auto-append `matcher_run` / `sheet_build` events.
3. **Agents** should append a `research` event after merging cache data:

```bash
cd ~/Documents/college-compass/scripts
python3 -c "
from run_log import log_research
log_research(
    backend='cursor',
    school='Purdue University',
    scope='research school: Purdue University',
    source_urls=['https://www.purdue.edu/admissions/...'],
    validator_ok=True,
    validator_errors=0,
    validator_warnings=0,
)
"
```

Set `research_method` on the college entry when you change research data:

```json
"research_method": {
  "backend": "cursor",
  "scope": "research school: Purdue University",
  "researched_at": "2026-06-27",
  "source_urls": ["https://..."]
}
```

**Never log API keys.** Full contract: [`docs/PROFILE_AND_CONFIG.md`](PROFILE_AND_CONFIG.md).

---

## 8. Post-write summary

Tell the user:

1. Which schools and fields changed  
2. Source URLs used  
3. Validator result  
4. Anything left blank intentionally (and why)

---

## 9. Known gaps (do not “fix” without scoped research)

1. **Mid-50% blank** for ~15 schools — no official program band; not a bug.  
2. **`acceptance_rates.json`** legacy — cache is authoritative; merge optional.  
3. HS historical outcomes deferred — see [`ENHANCEMENT.md`](ENHANCEMENT.md).  
4. Do not re-research all schools unless user says `full refresh: all`.

---

## 10. Machine-readable validation

`scripts/validate_cache.py` enforces:

- `schema_version === 1`
- No reserved keys at `colleges` top level
- `researched_at` date format
- `acceptance_rates.*` shape (`value` + `display`)
- Valid `admit_profile.display_mode`
- Optional `research_method.backend` ∈ `cursor|openai|anthropic|local|manual`
- Cache ↔ matcher college name alignment (warnings for mismatches)

```bash
cd ~/Documents/college-compass
python3 scripts/validate_cache.py
```

---

## 11. Session starter prompts

**Update one field (cheapest):**

> Read `@docs/RESEARCH_AGENT.md`. `update cache only: University of Minnesota - Carlson School of Management tuition` — verify 2025-26 OOS from official Carlson site, update cache only, run validator, regenerate outputs.

**Research one school:**

> Read `@docs/RESEARCH_AGENT.md`. `research school: Purdue University` — refresh rankings, tuition, deadlines, accept rates, and mid-50% if published. Run validator and regenerate outputs.

**Research 12 recommended schools:**

> Read `@docs/RESEARCH_AGENT.md`. `research field: recommended tuition, deadlines, accept rates` — recommended schools only. Do not touch excluded schools. Leave mid-50% blank where no official program band exists.

**Full refresh (explicit only):**

> Read `@docs/RESEARCH_AGENT.md`. `full refresh: all` — all 21 matcher schools. Run validator and regenerate outputs when done.

---

## Related files

| File | Role |
|------|------|
| `data/college_research_cache.json` | Master research cache |
| `scripts/college_research.py` | Load cache, apply to matcher |
| `scripts/program_admit.py` | Program admit columns 6–9 |
| `scripts/validate_cache.py` | Schema gate |
| `scripts/run_log.py` | Append-only JSONL audit log |
| `config/pro.json` | Pro runtime settings (backend, logging) |
| `docs/PROFILE_AND_CONFIG.md` | Profile schema, config layout, logging contract |
