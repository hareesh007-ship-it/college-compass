# Research Assist — Free / Local Tier

Offline-first research helper using [Ollama](https://ollama.com) to extract college data from pasted admissions text into cache-schema JSON drafts.

**This module produces drafts only.** It never writes to `data/college_research_cache.json` directly. You review the output, merge manually, and run `validate_cache.py`.

---

## Model choice: Ollama vs HuggingFace

| | Ollama | HuggingFace `transformers` |
|---|---|---|
| Install | `brew install ollama` | `pip install transformers torch` (~5 GB) |
| RAM (3B model) | ~3 GB | ~4–6 GB |
| Apple Silicon | Yes (Metal, fast) | Yes (MPS, slower) |
| First inference | Fast after pull | Slow (model load) |
| JSON extraction | Good with 3B instruct | Good with Phi/Qwen instruct |
| License | Model-dependent (mostly Apache/MIT) | Model-dependent |
| Complexity | Low | High |

**Verdict: Ollama** is the default for this project. Simpler install, faster inference on Mac, smaller disk footprint.

---

## Quick start

```bash
# 1. One-time setup (installs Ollama + pulls model + pip deps)
bash install-free.sh

# 2. Paste admissions page text and extract
pbpaste | python3 research_assist/extract_college_draft.py --college "Purdue University"

# 3. Or read from a saved text file
python3 research_assist/extract_college_draft.py --college "Carlson School of Management" \
    --file data/carlson_admissions.txt

# 4. Review the draft JSON, merge into cache manually, then validate
college-finder --student <your-name> validate
college-finder --student <your-name> run
```

---

## Recommended models

| Model | Pull command | RAM | Best for |
|---|---|---|---|
| `llama3.2:3b` *(default)* | `ollama pull llama3.2:3b` | ~3 GB | General extraction, fast |
| `qwen2.5:3b` | `ollama pull qwen2.5:3b` | ~3 GB | Slightly better JSON |
| `llama3.1:8b` | `ollama pull llama3.1:8b` | ~5 GB | More accurate, slower |
| `phi3.5` | `ollama pull phi3.5` | ~2.5 GB | Low-RAM laptops |

All models are quantized GGUF (Q4). Apple Silicon uses Metal automatically.

---

## Usage

```
extract_college_draft.py --college NAME [--file FILE] [--model MODEL] [--dry-run]

  --college   College name exactly as it should appear as the cache key (required)
  --file      Path to text file (default: stdin)
  --model     Ollama model tag (default: llama3.2:3b)
  --dry-run   Print the prompt only — do not call Ollama
```

### Examples

```bash
# Pipe from clipboard (macOS)
pbpaste | python3 research_assist/extract_college_draft.py --college "Iowa State University"

# From a saved HTML-to-text scrape
python3 research_assist/extract_college_draft.py \
    --college "University of Minnesota Twin Cities" \
    --file /tmp/umn_admissions.txt

# Use a bigger model for better accuracy
python3 research_assist/extract_college_draft.py \
    --college "Indiana University Bloomington" \
    --model llama3.1:8b \
    --file /tmp/iu_text.txt

# Inspect the prompt without calling Ollama
python3 research_assist/extract_college_draft.py \
    --college "Purdue University" \
    --dry-run < /tmp/purdue.txt
```

---

## What the model extracts

From the source text, the model attempts to fill these cache fields:

| Section | Fields |
|---|---|
| `rankings` | national_university, undergrad_business, entrepreneurship, notes |
| `tuition` | in_state, out_of_state, year, source_url |
| `admit_stats` | scope, cycle, gpa/sat/act mid-50% bands, source, source_url |
| `acceptance_rates` | university_general and business_program (value, display, label, source) |
| `deadlines` | early_action, early_decision, regular, ed_available |
| `business_program_note` | Short description of business school |

Fields not found in the source text are `null` — the model is instructed not to invent values.

---

## Workflow

```
1. Copy admissions page text (Ctrl+A, Ctrl+C) or save as .txt
2. Run extract_college_draft.py — prints JSON draft to stdout
3. Review every field — check source accuracy
4. Paste the college block into `data/college_research_cache.json`
5. `college-finder --student <name> validate`    ← required gate
6. `college-finder --student <name> run`       ← regenerate outputs
```

---

## What this does NOT do

- Does **not** fetch live URLs (use Cursor Agent for live web research)
- Does **not** write to the cache
- Does **not** look up US News rankings (paste the ranking text manually if available)
- Does **not** replace `college_finder.py` logic — matcher stays Python-only

---

## Ollama setup notes

Start Ollama before running extractions:

```bash
ollama serve          # starts the local server (http://localhost:11434)
```

On macOS after `brew install ollama`, it may auto-start. Check with:

```bash
ollama list           # lists downloaded models
```

If you get a connection error, run `ollama serve` in a separate terminal tab.

---

## Adding a new model

Any Ollama instruct model works. Try:

```bash
ollama pull mistral:7b
python3 research_assist/extract_college_draft.py --college "Purdue" --model mistral:7b < text.txt
```

Compare JSON quality across models on a known school (e.g. one already in cache) and pick the best for your hardware.
