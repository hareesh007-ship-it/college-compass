# Quickstart — Free path (Option A, local Ollama)

**Works on macOS, Linux, and Windows. No API key needed.**

Research assist runs locally via [Ollama](https://ollama.com/). No OpenAI or Anthropic subscription required. Matcher and sheet generation are pure Python.

---

## 1. Install Python dependencies

**macOS / Linux:**

```bash
git clone https://github.com/hareesh007-ship-it/college-compass college-compass
cd college-compass
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[free]"
```

**Windows (Command Prompt):**

```bat
git clone https://github.com/hareesh007-ship-it/college-compass college-compass
cd college-compass
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[free]"
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/hareesh007-ship-it/college-compass college-compass
cd college-compass
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
pip install -e ".[free]"
```

> **Every time you open a new terminal**, activate the venv first:  
> macOS/Linux: `source .venv/bin/activate`  
> Windows Command Prompt: `.venv\Scripts\activate`  
> Windows PowerShell: `.venv\Scripts\Activate.ps1`

---

## 2. Install Ollama and pull the model (one time, ~2 GB)

**macOS:**

```bash
brew install ollama
ollama pull llama3.2:3b
```

**Windows / Linux:** download from [ollama.com/download](https://ollama.com/download), then:

```bash
ollama pull llama3.2:3b
```

To use a different model, set `OLLAMA_MODEL` in `.env`:

```bash
OLLAMA_MODEL=qwen2.5:3b
```

---

## 3. Add a free Scorecard key (recommended)

School discovery uses the College Scorecard API. Without a key it falls back to a shared demo key that is heavily rate-limited — broad discovery queries may return few or no results, or fail with HTTP 429 errors. A free personal key takes 30 seconds to get and removes that limit:

```bash
cp .env.example .env
# edit .env:
SCORECARD_API_KEY=your_key_from_api.data.gov
```

Get a key: [api.data.gov/signup](https://api.data.gov/signup/)

---

## 4. Run the sample student

Start Ollama in one terminal and keep it open:

```bash
ollama serve
```

In a second terminal, run the pipeline:

```bash
college-compass-free --student alex-sample run
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

college-compass-free --student <your-name> run
```

Add real student folders to `.gitignore`:

```text
students/<your-name>/
```

See [`docs/PROFILE_AND_CONFIG.md`](PROFILE_AND_CONFIG.md) for all Excel profile fields.

---

## What the free path does automatically

When the pipeline runs, it:

1. Reads your Excel profile
2. Discovers matching schools via College Scorecard
3. **Auto-researches** any schools missing mid-50% bands or deadlines — fetches their admissions pages and uses Ollama to extract the data into the shared cache
4. Classifies each school as Safety / Target / Reach
5. Generates Excel + gap analysis HTML

Schools already in the cache are skipped on repeat runs — so subsequent runs are fast.

---

## Manually correcting cache data

If auto-research extracted something wrong, use the manual override tool:

```bash
python research_assist/manual_cache_inject.py --college "School Name"
```

Then validate and re-run:

```bash
college-compass-free --student <your-name> validate
college-compass-free --student <your-name> run
```

Full docs: [`research_assist/README.md`](../research_assist/README.md)

---

## Free vs. Pro comparison

| Task | Free (Ollama) | Pro (API key) |
| --- | --- | --- |
| Matcher + Excel sheet | Same | Same |
| Auto-research from admissions pages | Good | Stronger (larger models) |
| School name suggestions from preferences | Yes (local model) | Yes (API model) |
| Cost | Free | API credits |

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'college_compass_free'` | Venv not active — run `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows), then retry |
| `No student selected` | Add `--student <name>` to the command |
| `Ollama is not running` | Run `ollama serve` in a separate terminal |
| HTTP 429 on discovery | Set `SCORECARD_API_KEY` in `.env` |
| Auto-research warnings | Normal if network blocks some university sites — pipeline still completes |
| Model too slow | Try `llama3.2:3b` (default, fastest) or see model options at [ollama.com/library](https://ollama.com/library) |

---

**Principle:** *Python decides. Models draft. Humans validate.*
