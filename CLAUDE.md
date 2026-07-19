# College Compass — Claude Code Context

Open-source Python CLI for US undergrad college admissions. Any family clones the repo, fills in a student Excel profile (and optionally drops in transcript/resume PDFs), runs one command, and gets a Safety/Target/Reach classification, a 26-column Excel selection sheet, and a printable gap analysis HTML.

**Two tiers — both ship in this repo:**
- **Free (Option A):** Ollama + open-source local model (~2 GB download, no API key)
- **Pro (Option B):** BYO API key — OpenAI or Anthropic

The matcher is deterministic Python. LLMs are used in three places only:

1. **Student doc extraction** — reads any .pdf, .docx, or .txt files in input/ → fills blank profile fields
2. **School name suggestions** — optional, only when `any_other_preference` is set
3. **College auto-research** — fetches each school's admissions page → extracts mid-50%, deadlines, program rates into cache

---

## Pipeline (what `college-compass run` does)

```
1. Load profile    Excel → profile dict
                   + PDF extraction (transcript/resume) → fills blank fields via LLM

2. Discover        College Scorecard API → catalog
                   + LLM school name suggestions (if any_other_preference set)

3. Research        US News scrape → rankings
                   + auto_research_colleges.py → fetches admissions pages → LLM extracts
                     mid-50% bands, deadlines, accept rates → saved to shared cache

4. Classify        college_finder.py → Safety / Target / Reach (pure Python)

5. Output          26-column Excel + gap analysis HTML (pure Python)
```

Cache is the smart layer — schools already fully researched are skipped on repeat runs.

---

## Before coding or doing research

Read these files first:

- `docs/ARCHITECTURE.md` — pipeline detail, data model, module map
- `docs/RESEARCH_AGENT.md` — cache research playbook and scope commands
- `docs/PROFILE_AND_CONFIG.md` — Excel profile fields + `config/pro.json` schema

---

## Key paths

| Path | Role |
|------|------|
| `students/<name>/input/student profile input.xlsx` | Student profile (Excel — primary input) |
| `students/<name>/input/transcript.pdf` (or any filename) | Optional — LLM extracts GPA, courses |
| `students/<name>/input/resume.pdf` (or any filename) | Optional — LLM extracts activities, awards |
| `data/college_research_cache.json` | Shared research cache — single source of truth |
| `students/<name>/data/colleges/catalog.json` | Discovered schools for this student (generated) |
| `config/pro.json` | Pro backend config (research_backend, logging) |
| `.env` | API keys only — never commit |
| `college-compass-free` / `college-compass-pro` | CLI entry points (installed via pip) |
| `college_compass_cli.py` | Cross-platform CLI entry point |
| `scripts/extract_student_docs.py` | PDF extraction — fills blank profile fields via LLM |
| `scripts/auto_research_colleges.py` | Admissions page fetch + LLM extraction per school |
| `scripts/run.py` / `scripts/pipeline.py` | Full pipeline entry |
| `scripts/college_finder.py` | Safety/Target/Reach matcher |
| `scripts/build_selection_sheet.py` | 26-column XLSX output |
| `scripts/build_gap_analysis.py` | Gap analysis HTML output |
| `scripts/validate_cache.py` | Schema + catalog cross-check |
| `scripts/discover_colleges.py` | Scorecard API + preferred schools → catalog |
| `research_assist/manual_cache_inject.py` | Manual override tool — correct stale cache data |
| `docs/ENHANCEMENT.md` | Deferred features — do not implement unless asked |

---

## Multi-student layout

```
students/
  alex-sample/       <- fictional OSS example (committed)
  <your-name>/       <- real student (gitignored — add to .gitignore)
data/
  college_research_cache.json   <- shared across all students
```

Run any student:
```bash
college-compass-free --student alex-sample run
college-compass-pro  --student <your-name> run
```

---

## LLM backends

Set `research_backend` in `config/pro.json`:

- `openai` — OpenAI API (OPENAI_API_KEY in .env)
- `anthropic` — Anthropic API (ANTHROPIC_API_KEY in .env)
- `local` — Ollama (free path, llama3.2:3b)
- `cursor` — no LLM automation (manual only)

---

## Research scope — honor these commands exactly

- `update cache only: <school> <field>` — JSON edit, no web research unless field is missing
- `research school: <name>` — one school, web research OK
- `full refresh: all` — all catalog schools, **only when user explicitly requests**

After any cache edit:
```bash
college-compass-free --student <your-name> validate
college-compass-free --student <your-name> run
```

---

## Session state (as of Session 11)

Phase 1 (student pipeline), Phase 2 (Pro + Free research assist), and Phase 3 (OSS) largely complete.
Architecture refactored: PDF extraction, college auto-research, and Ollama school suggestions all wired in.

**Session 11 remaining:**

- `LICENSE` (MIT)
- `CONTRIBUTING.md`
- Config-driven reciprocity (replace MN hardcode)

Do not break the `alex-sample` pipeline or any real student pipeline.

---

## Cost / scope discipline

- One task per session
- No full catalog re-research unless user explicitly asks
- Deferred features live in `docs/ENHANCEMENT.md` — leave them there
