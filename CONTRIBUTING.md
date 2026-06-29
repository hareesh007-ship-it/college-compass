# Contributing to College Finder

Thank you for your interest in contributing. This document covers how the project works, what you can contribute, and how to submit changes safely.

---

## What you can contribute

- **Bug fixes** — matcher logic, sheet column calculations, discovery filters
- **New profile fields** — extending the Excel schema and pipeline to use them
- **Research cache entries** — adding or improving school data for the shared cache
- **New admit display modes** — modeling program admit logic for schools not yet covered
- **Documentation** — quickstarts, examples, accuracy corrections
- **Install script improvements** — Windows support, reliability fixes
- **Reciprocity rules** — config-driven multi-state reciprocity (Phase 3 priority)

---

## Getting started

```bash
git clone <repo-url> college-finder
cd college-finder
bash install-pro.sh          # or install-free.sh

# Run the sample student to verify everything works
college-finder --student alex-sample run
```

See [`README.md`](README.md) and [`docs/TECHNICAL.md`](docs/TECHNICAL.md) for architecture context.

---

## The cache workflow (most common contribution)

The research cache (`data/college_research_cache.json`) is the shared library of school data. Contributing accurate, well-sourced cache entries is one of the highest-value contributions.

### Rules

1. **Validate before committing.** Every cache edit must pass `validate_cache.py`:
   ```bash
   college-finder --student alex-sample validate
   ```
   Do not submit a PR with cache changes that fail validation.

2. **Keys must match exactly.** Cache keys must match catalog `cache_key` values exactly — no trailing school names, no parenthetical suffixes. Check `students/alex-sample/data/colleges/catalog.json` after a run to see the expected keys.

3. **Nest `admit_profile` under the college entry.** It must be a key inside the college object, not a sibling at the `colleges` top level.

4. **Cite your sources.** Include `source_url` or `source_note` on acceptance rates and rankings. Include `research_method` (`"manual"`, `"ollama"`, `"openai"`, etc.) and `last_updated` (e.g. `"2026-06"`).

5. **Leave fields blank rather than guessing.** A missing field falls back to seed defaults. A wrong value produces a bad match. If you can't find an official source for a mid-50% range or acceptance rate, leave it out.

6. **Do not add real student data.** The cache stores school data only — no student profiles, no personal information.

### Cache entry template

```json
"School Name": {
  "tuition": {
    "in_state": 18000,
    "out_of_state": 35000,
    "source_url": "https://school.edu/tuition",
    "as_of": "2025-26"
  },
  "admit_stats": {
    "gpa_range": [3.4, 3.8],
    "sat_range": [1200, 1400],
    "act_range": [26, 32],
    "source_url": "https://school.edu/admissions/stats",
    "as_of": "Class of 2028"
  },
  "acceptance_rates": {
    "university_general": {
      "rate": 0.62,
      "source_url": "https://school.edu/admissions",
      "source_note": "Fall 2024 entering class"
    }
  },
  "deadlines": {
    "early_action": "Nov 1",
    "early_decision": null,
    "regular": "Feb 1",
    "ed_available": false
  },
  "rankings": {
    "national_university": 150,
    "business_undergraduate": 55
  },
  "research_method": "manual",
  "last_updated": "2026-06"
}
```

See [`docs/RESEARCH_AGENT.md`](docs/RESEARCH_AGENT.md) for the full cache schema and scope commands.

---

## Code contributions

### Branch naming

```
fix/<short-description>
feat/<short-description>
docs/<short-description>
```

### Before submitting a PR

1. Run the sample student end-to-end and confirm it produces outputs:
   ```bash
   college-finder --student alex-sample run
   ```
2. Run cache validation:
   ```bash
   college-finder --student alex-sample validate
   ```
3. If you changed matcher logic (`college_finder.py`, `program_admit.py`, `acceptance_data.py`): manually verify that Safety/Target/Reach categories are sensible for the sample student.
4. If you changed `build_selection_sheet.py`: open the output XLSX and check that columns are in the right order and data looks correct.
5. Do not commit `.env`, `config/pro.json`, or any real student folder.

### Adding a new profile field

1. Add the field name constant to `scripts/profile_fields.py`
2. Read it in `scripts/load_profile.py`
3. Use it in the pipeline stage where it applies
4. Update `docs/PROFILE_AND_CONFIG.md` with the field description
5. Add an example value to `students/alex-sample/input/student profile input.xlsx`

### Adding a new admit display mode

1. Add the mode key and default behavior to `DEFAULT_ADMIT_PROFILES` in `scripts/program_admit.py`
2. Add the display label to `DISPLAY_MODE_LABELS`
3. Set `admit_profile.display_mode` in the cache for relevant schools
4. Validate and run

---

## What we do not accept

- Real student data of any kind (PII)
- Hardcoded school lists replacing dynamic discovery
- Cache entries without a cited source
- Auto-merged LLM output that has not been reviewed and validated
- Hosted/SaaS infrastructure — this tool is intentionally local-first

---

## Questions

Open a GitHub issue describing what you want to change or add. For cache research questions, see [`docs/RESEARCH_AGENT.md`](docs/RESEARCH_AGENT.md). For architecture questions, see [`docs/TECHNICAL.md`](docs/TECHNICAL.md).
