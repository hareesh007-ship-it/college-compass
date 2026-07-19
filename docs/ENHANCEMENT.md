# Enhancements — out of current scope

**Status:** Deferred  
**Last updated:** 2026-06-27

Features documented here are **not** in the selection sheet or pipeline today. Revisit after Pro install and generic OSS ship if users ask for them.

---

## HS historical outcomes (Maia / Naviance)

### Fields it would add

School-specific context: how many students from **this high school** applied to and were admitted by each college — separate from national accept rates (columns 22–23 on the sheet).

| Proposed column | Meaning |
| --------------- | ------- |
| HS Applied (historical) | Applicants from the student's HS in past cycles |
| HS Admitted (historical) | Admits from the same HS |
| HS Admit % (historical) | HS-specific admit rate |
| HS Outcomes Source | e.g. Maia Learning export, Naviance report |

### Reason for deferral

- Not available to most families (no counselor platform, privacy limits, homeschool, small HS).
- Does not affect Safety / Target / Reach matching.
- Every platform exports differently — no standard import path yet.
- Empty columns added noise to the sheet without helping the core workflow.

### If implemented later

**Input (proposed):** `input/high_school_outcomes.json`

```json
{
  "source": "Maia Learning export, Chanhassen HS, 2026-06",
  "colleges": {
    "University of Minnesota-Twin Cities (Carlson)": {
      "applied": 42,
      "admitted": 28
    }
  }
}
```

College keys must match catalog / cache college names.

**Possible work:**

1. Counselor export guide (Maia, Naviance, CSV)
2. `scripts/import_hs_outcomes.py` or manual JSON edit
3. Optional second tab or columns on the selection sheet (or separate `HS Outcomes` report)
4. Tool-neutral column names for OSS

---

## Urban Institute Education Data Portal

**API:** `https://educationdata.urban.org/documentation/`  
**Auth:** None required. Free, open license (ODC-By v1.0).

### Data it would add

The portal aggregates multiple federal datasets (IPEDS, College Scorecard, Civil Rights Data Collection) and exposes fields not available in the Scorecard API we currently use:

| Potential field | Use |
| --------------- | --- |
| Graduation rate by major / program | Stronger fit signal for intended major |
| Acceptance rate trend (multi-year) | Identify schools getting harder/easier to get into |
| Enrollment breakdown (full-time vs part-time) | Campus character signal |
| Financial aid disbursement data | Supplement average net price |

### Why it is deferred

- Core Safety/Target/Reach matching works well without it — no gap today.
- Adds depth, not accuracy; users can validate output without it.
- Integration work needed to map Urban school IDs to our Scorecard-based catalog.

### Implementation notes

1. Add `research_backend: urban` option or use as a supplemental enrichment step after Scorecard discovery.
2. Map `unitid` (IPEDS ID) — already returned by Scorecard — to Urban portal school IDs.
3. Add optional columns to selection sheet: graduation rate, acceptance rate trend.

---

## Other candidates (not planned)

Add items here as they are explicitly deferred from core scope.

| Idea | Notes |
|------|-------|
| Maia / Naviance CSV import | See above |
| Generic reciprocity config (YAML) | Today MN → WI/ND/SD hardcoded in matcher |
| College Scorecard bulk IPEDS enrich | Discovery uses Scorecard; deeper program stats optional |
| API Ninjas University API | Free tier too limited (5 results, premium fields paywalled); Scorecard covers same data for free |

---

## References

| File | Role |
| ---- | ---- |
| `input/high_school_outcomes.json` | Placeholder schema only — **not read by pipeline** |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Active 26-column sheet map |
