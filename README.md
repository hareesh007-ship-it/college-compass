# College Finder

**A free, open-source tool that helps high school juniors and seniors — and their parents — find the right colleges.**

College admissions research is time-consuming and expensive. This tool does the research for free, on your own computer, with no data leaving your machine.

Fill in a student profile — grades, test scores, budget, state, preferred majors, and any schools you already have in mind. Run one command. The tool searches thousands of US colleges, researches each school's admissions data, and delivers:

- A **Safety / Target / Reach classification** for every matching school
- A **26-column Excel selection sheet** with rankings, tuition, acceptance rates, deadlines, and fit scores
- A **printable gap analysis report** showing exactly where the student stands against each school's admit profile

**How it works under the hood:**

- **Python scripts** handle all matching and classification — deterministic, explainable, no surprises
- **Web scraping** pulls live data from the College Scorecard API (free US government data) and university admissions pages
- **LLMs** (local Ollama model or your own API key) read those admissions pages and extract structured data — mid-50% bands, deadlines, acceptance rates — into a shared research cache
- Once a school is researched, it stays in the cache — repeat runs are instant

**Free to use. No subscription. No data sent to any service. You own everything.**

> *Python decides. Models draft. Humans validate.*

---

## What it does

Fill in a student Excel profile. Run one command. Get:

- A **Safety / Target / Reach classification** for each matching school
- A **26-column Excel selection sheet** (rankings, tuition, fit, deadlines, acceptance rates)
- A **printable gap analysis HTML** showing where the student stands vs. each school's admit profile

The matcher is deterministic Python — no LLM is called on every run. LLMs are used only to help research and populate the shared `data/college_research_cache.json` once per school.

---

## How it works

| Step | What happens |
| --- | --- |
| 1. **Fill your profile** | Enter GPA, test scores, budget, state, major, and any schools you're interested in into an Excel file |
| 2. **Discover schools** | Python queries the free College Scorecard API to find matching schools nationwide |
| 3. **Research each school** | LLM fetches each school's admissions page and extracts mid-50% bands, deadlines, and acceptance rates into a local cache |
| 4. **Classify** | Pure Python compares your profile to each school's data → Safety, Target, or Reach |
| 5. **Output** | 26-column Excel sheet + printable gap analysis HTML saved to your computer |

The research cache is shared across runs — once a school is researched, it's saved locally and skipped on future runs.

---

## Requirements

| Requirement | Detail |
| --- | --- |
| **OS** | macOS, Linux, or Windows |
| **Python** | 3.9+ |
| **Setup time** | ~15 minutes |
| **School discovery** | Free [College Scorecard API key](https://api.data.gov/signup/) |
| **Free path** | [Ollama](https://ollama.com/) + ~2 GB local model |
| **Pro path** | OpenAI or Anthropic API key |

---

## Install — pick one path

### Option A — Free (local AI, no API key)

Uses [Ollama](https://ollama.com/) to auto-research schools locally. No OpenAI or Anthropic account needed.

**macOS / Linux:**

```bash
git clone <your-repo-url> college-finder
cd college-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[free]"
```

**Windows (Command Prompt):**

```bat
git clone <your-repo-url> college-finder
cd college-finder
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[free]"
```

**Windows (PowerShell):**

```powershell
git clone <your-repo-url> college-finder
cd college-finder
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
pip install -e ".[free]"
```

Install Ollama and pull the model (one time, ~2 GB):

```bash
# macOS
brew install ollama

# Windows / Linux: download from https://ollama.com/download
ollama pull llama3.2:3b
```

### Option B — Pro (bring your own API key)

Use your existing OpenAI or Anthropic subscription.

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

**Windows (PowerShell):**

```powershell
git clone <your-repo-url> college-finder
cd college-finder
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
pip install -e ".[pro]"
```

Add your key to `.env` at the repo root:

```bash
cp .env.example .env
# edit .env:
ANTHROPIC_API_KEY=sk-ant-...    # preferred
# or
OPENAI_API_KEY=sk-...
```

> **Every time you open a new terminal**, activate the venv first:  
> macOS/Linux: `source .venv/bin/activate`  
> Windows Command Prompt: `.venv\Scripts\activate`  
> Windows PowerShell: `.venv\Scripts\Activate.ps1`

---

## Add a free Scorecard key (both paths)

Required for reliable school discovery. Add to `.env`:

```bash
SCORECARD_API_KEY=your_key_from_api.data.gov
```

Get a free key: [api.data.gov/signup](https://api.data.gov/signup/)

---

## Try it — sample student included

The repo ships with a fictional student (`alex-sample`) so you can verify your install before entering real data.

**Free path:**

```bash
ollama serve                                          # terminal 1 — keep open
college-finder-free --student alex-sample run        # terminal 2
```

**Pro path:**

```bash
college-finder-pro --student alex-sample run
```

**Output lands at:**

| File | Description |
| --- | --- |
| `students/alex-sample/output/Alex - US College Selection.xlsx` | 26-column selection sheet |
| `students/alex-sample/output/Alex - College Prep Gap Analysis.html` | Printable gap report |
| `students/alex-sample/data/college_matches.json` | Full match report (S/T/R) |

Open the Excel and gap HTML in your browser to confirm everything worked.

See [`students/alex-sample/README.md`](students/alex-sample/README.md) for the sample profile details.

---

## Add your own student

```bash
cp -r students/alex-sample students/<your-name>
# edit students/<your-name>/input/student profile input.xlsx

college-finder-free --student <your-name> run   # free path
college-finder-pro  --student <your-name> run   # pro path
```

Add real student folders to `.gitignore` so personal data is never committed:

```text
students/<your-name>/
```

See [`docs/PROFILE_AND_CONFIG.md`](docs/PROFILE_AND_CONFIG.md) for all Excel profile fields.

---

## Outputs

All paths are under `students/<name>/`:

| File | Description |
| --- | --- |
| `output/{FirstName} - US College Selection.xlsx` | 26-column sheet: rankings, tuition, fit, deadlines, accept rates |
| `output/{FirstName} - College Prep Gap Analysis.html` | Printable gap report — open in browser → Print → PDF |
| `data/college_matches.json` / `.md` | Full Safety / Target / Reach report |
| `data/colleges/catalog.json` | Discovered school list for this run (generated) |

When `alternate_major` is set in the profile, a second Excel tab and second gap HTML are generated automatically.

---

## Key files

| Path | Role |
| --- | --- |
| `students/<name>/input/student profile input.xlsx` | Student profile |
| `data/college_research_cache.json` | Shared research cache (rankings, tuition, mid-50%, deadlines) |
| `.env` | API keys — never committed |
| `college_finder_free.py` | Entry point for free path |
| `college_finder_pro.py` | Entry point for pro path |

---

## Cost

| Activity | Free path | Pro path |
| --- | --- | --- |
| Matcher, sheet, validator | Free (Python only) | Free (Python only) |
| School discovery (Scorecard) | Free (government API) | Free (government API) |
| Auto-research cache population | Free (local Ollama) | Your OpenAI / Anthropic API credits |
| Maintainer hosting | None | None |

---

## Documentation

| Doc | Audience |
| --- | --- |
| [`docs/Quickstart-free.md`](docs/Quickstart-free.md) | Free path — full setup walkthrough |
| [`docs/Quickstart-pro.md`](docs/Quickstart-pro.md) | Pro path — full setup walkthrough |
| [`docs/TECHNICAL.md`](docs/TECHNICAL.md) | Developers — pipeline, data model, module reference |
| [`docs/PROFILE_AND_CONFIG.md`](docs/PROFILE_AND_CONFIG.md) | Excel profile fields + config schema |
| [`docs/RESEARCH_AGENT.md`](docs/RESEARCH_AGENT.md) | Cache editors — scope commands, validation gate |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contributors |
