# Profile, config, and logging

**Last updated:** 2026-06-28  
**Related:** [`Quickstart-pro.md`](Quickstart-pro.md) · [`RESEARCH_AGENT.md`](RESEARCH_AGENT.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## 1. File layout

Each student has an isolated folder under `students/<name>/`. Tool config and secrets live at the repo root.

| Path | Purpose | Secrets? |
| ------ | --------- | ---------- |
| **`students/<name>/input/student profile input.xlsx`** | **Student profile** — one-tab form with comments | No |
| `students/<name>/output/` | Deliverables — XLSX, gap HTML | No |
| `students/<name>/data/` | Intermediate — match report, catalog, logs | No |
| `students/<name>/data/academic_record.json` | Optional transcript reference (not wired to matcher today) | No |
| `data/college_research_cache.json` | **Shared** research cache across all students | No |
| `config/pro.json` | Runtime settings (backend preference, logging) | No |
| `config/pro.json.example` | Template for `pro.json` | No |
| `.env` | `SCORECARD_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | **Yes** |
| `.env.example` | Placeholder keys only | No |
| `students/<name>/data/logs/research_log.jsonl` | Append-only audit trail (when logging enabled) | No |

**Rule:** Never put API keys in the profile Excel or `config/pro.json`.

---

## 2. Student profile schema

Profile file: **`students/<name>/input/student profile input.xlsx`**

Loader: `scripts/load_profile.py` reads Excel via field map in `scripts/profile_fields.py`. Excel is the **only** supported format.

### Required for matcher + sheet

| Field | Type | Used by |
| ------- | ------ | --------- |
| `name` | string | Sheet header, match report title |
| `grade` | number | Sheet header |
| `intended_major` | string | Rank column label, program admit, business filter |
| `gpa_unweighted` | number | Fit scoring, program admit (direct-admit schools) |
| `state_of_residence` | string | Tuition (in-state / reciprocity), region filter |
| `budget_max_tuition_per_year` | number | Budget filter, Within Budget column |
| `preferences.regions` | string[] | Region filter when `prefer_local` logic applies |

### Strongly recommended

| Field | Type | Notes |
| ------- | ------ | ------- |
| `sat` | number \| null | At least one of `sat` or `act` needed for test fit |
| `act` | number \| `{composite, …}` \| null | Effective score = max(SAT, ACT-equiv) |
| `preferences.surrounding_states` | string[] | Expands allowed states beyond `regions` |
| `preferences.public_ok` / `private_ok` | boolean | Default true if omitted |
| `schools_interested_in` | string[] | Priority flag on matches; always kept in catalog |
| `application_cycle.applying_fall` | number | Apply Fall column |
| `preferences.any_other_preference` | string | Open text for LLM-assisted discovery (not used by matcher math) |

### Optional (research prompts + sheet display)

`class_of`, `high_school`, `high_school_ceeb`, `gpa_weighted`, `gpa_source`, `citizenship`, `gender`, `financial_aid_needed`, `early_decision_ok`, `academic_highlights`, `activities_summary`, `notes`.

These do **not** change Safety/Target/Reach math today. They help LLM agents draft richer cache notes.

### Regenerate outputs

```bash
college-compass --student <name> run
```

---

## 3. Runtime config (`config/pro.json`)

Shared tool config at the repo root (not per-student). Created by `install-pro.sh` from `config/pro.json.example`.

```json
{
  "research_backend": "cursor",
  "logging": {
    "enabled": true,
    "path": "data/logs/research_log.jsonl",
    "level": "info"
  }
}
```

| Field | Values | Notes |
| ------- | -------- | ------- |
| `research_backend` | `cursor` \| `openai` \| `anthropic` \| `local` | `local` reserved for Free path |
| `logging.enabled` | boolean | `false` disables all `run_log` writes |
| `logging.path` | path | Relative to **active student folder** (`students/<name>/`) or absolute |
| `logging.level` | `debug` \| `info` \| `warn` \| `error` | Reserved for future CLI verbosity |

With the default path, logs write to `students/<name>/data/logs/research_log.jsonl`.

---

## 4. Logging contract

**Format:** One JSON object per line (JSONL), append-only, UTF-8.

**Default location:** `students/<name>/data/logs/research_log.jsonl` (override `logging.path` in `config/pro.json`).

**Never logged:** API keys, tokens, passwords, or fields whose names match `*key*`, `*secret*`, `*token*`, `*password*`.

### Event types

| `event` | When | Typical fields |
| --------- | ------ | ---------------- |
| `research` | Agent/API completes scoped research | `backend`, `school`, `scope`, `source_urls[]`, `validator_ok`, `validator_errors`, `validator_warnings`, `notes` |
| `validate` | After `validate_cache.py` | `ok`, `errors`, `warnings`, `cache_path`, `backend` |
| `matcher_run` | After `college_finder.py` | `profile_path`, `safety`, `target`, `reach`, `excluded` |
| `sheet_build` | After `build_selection_sheet.py` | `profile_path`, `rows`, `outputs[]` |

### Example lines

```json
{"ts": "2026-06-27T18:30:00+00:00", "event": "research", "backend": "cursor", "school": "University of Iowa (Tippie College of Business)", "scope": "research school: University of Iowa (Tippie College of Business)", "source_urls": ["https://tippie.uiowa.edu/..."], "validator_ok": true, "validator_errors": 0, "validator_warnings": 0}
{"ts": "2026-06-27T18:31:02+00:00", "event": "validate", "backend": "cursor", "ok": true, "errors": 0, "warnings": 0, "cache_path": "data/college_research_cache.json"}
{"ts": "2026-06-27T18:31:05+00:00", "event": "matcher_run", "backend": "cursor", "profile_path": "students/alex-sample/input/student profile input.xlsx", "safety": 8, "target": 4, "reach": 0, "excluded": 9}
```

### After cache edits

1. Run `college-compass --student <name> validate`
2. Optionally append a `research` log entry via `scripts/run_log.py`
3. Run `college-compass --student <name> run` if validation passed

---

## 5. Cache metadata — `research_method`

Optional per-college field in `data/college_research_cache.json`:

```json
"research_method": {
  "backend": "cursor",
  "scope": "research school: Purdue University",
  "researched_at": "2026-06-27",
  "source_urls": ["https://www.purdue.edu/admissions/..."]
}
```

| `backend` | Meaning |
| ----------- | --------- |
| `cursor` | Cursor agent + `RESEARCH_AGENT.md` |
| `openai` | User OpenAI API |
| `anthropic` | User Anthropic API |
| `local` | Ollama / local model (Free path) |
| `manual` | Human-entered, no LLM |

Validator accepts this block; it is **optional** and does not affect matcher output.
