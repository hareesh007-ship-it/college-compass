# Quickstart — Pro path (Option B, BYO API key)

**Works on macOS, Linux, and Windows. Requires an OpenAI or Anthropic API key.**

Auto-research runs via your API key. No Ollama, no model download. Matcher and sheet generation are pure Python.

---

## 1. Install Python dependencies

**macOS / Linux:**

```bash
git clone <your-repo-url> college-finder
cd college-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[pro]"
```

**Windows (Command Prompt):**

```bat
git clone <your-repo-url> college-finder
cd college-finder
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[pro]"
```

> **Every time you open a new terminal**, activate the venv first:  
> macOS/Linux: `source .venv/bin/activate`  
> Windows: `.venv\Scripts\activate`

---

## 2. Configure your API key

```bash
cp .env.example .env
# edit .env:
ANTHROPIC_API_KEY=sk-ant-...    # preferred
# or
OPENAI_API_KEY=sk-...
```

The pipeline auto-detects whichever key is present. If both are set, Anthropic is used.

Get a key:

- Anthropic: [console.anthropic.com](https://console.anthropic.com)
- OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

---

## 3. Add a free Scorecard key (recommended)

School discovery uses the College Scorecard API. Add a free key for reliable results:

```bash
# add to .env:
SCORECARD_API_KEY=your_key_from_api.data.gov
```

Get a key: [api.data.gov/signup](https://api.data.gov/signup/)

---

## 4. Run the sample student

```bash
college-finder-pro --student alex-sample run
```

**Outputs:**

| File | Path |
| --- | --- |
| Selection sheet | `students/alex-sample/output/Alex - US College Selection.xlsx` |
| Gap analysis | `students/alex-sample/output/Alex - College Prep Gap Analysis.html` |
| Match report | `students/alex-sample/data/college_matches.json` |

Open both files to confirm everything worked.

---

## 5. Add your own student

```bash
cp -r students/alex-sample students/<your-name>
# edit students/<your-name>/input/student profile input.xlsx

college-finder-pro --student <your-name> run
```

Add real student folders to `.gitignore`:

```text
students/<your-name>/
```

See [`docs/PROFILE_AND_CONFIG.md`](PROFILE_AND_CONFIG.md) for all Excel profile fields.

---

## What the pro path does automatically

When the pipeline runs, it:

1. Reads your Excel profile (and optionally extracts data from transcript/resume PDFs)
2. Discovers matching schools via College Scorecard
3. **Auto-researches** any schools missing mid-50% bands or deadlines — fetches their admissions pages and uses your API key to extract the data into the shared cache
4. Classifies each school as Safety / Target / Reach
5. Generates Excel + gap analysis HTML

Schools already in the cache are skipped on repeat runs — so subsequent runs are fast.

---

## PDF extraction (optional)

Drop transcript and resume PDFs into `students/<your-name>/input/`:

```text
students/<your-name>/input/transcript.pdf
students/<your-name>/input/resume.pdf
```

The pipeline reads them automatically and fills any blank fields in your Excel profile. Excel values always take precedence — PDFs only fill fields you left empty.

---

## Manually correcting cache data

If auto-research extracted something wrong, use the manual override tool:

```bash
python research_assist/manual_cache_inject.py --college "School Name"
```

Then validate and re-run:

```bash
college-finder-pro --student <your-name> validate
college-finder-pro --student <your-name> run
```

Full cache playbook: [`docs/RESEARCH_AGENT.md`](RESEARCH_AGENT.md)

---

## Audit log

All research and pipeline events are logged to:

```text
students/<name>/data/logs/research_log.jsonl
```

No API keys or personal data are ever written to the log.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'college_finder_pro'` | Venv not active — run `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows), then retry |
| `No student selected` | Add `--student <name>` to the command |
| `No API key found` | Add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to `.env` |
| HTTP 429 on discovery | Set `SCORECARD_API_KEY` in `.env` |
| Auto-research warnings | Normal if network blocks some university sites — pipeline still completes |
| Catalog has few schools | Add preferred schools in Excel; check budget and regions |
| Validator errors after cache edit | Fix JSON schema; keys must match catalog `cache_key` |

---

**Principle:** *Python decides. Models draft. Humans validate.*
