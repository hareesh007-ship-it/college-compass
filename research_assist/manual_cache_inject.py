#!/usr/bin/env python3
"""
manual_cache_inject.py — Manual research data injection tool.

Use this ONLY to correct or override auto-researched college data.
The pipeline (college-finder run) populates the cache automatically.
This tool is for power users who need to fix a specific data point —
e.g. a deadline changed, a ranking is stale, or a program rate is wrong.

It never writes to the cache directly — output is draft JSON for human review.
After reviewing, merge manually into data/college_research_cache.json and validate:
    college-finder --student <name> validate

Usage:
    # Pipe text from clipboard or a file
    echo "<admissions page text>" | python3 research_assist/manual_cache_inject.py --college "Purdue University"
    python3 research_assist/manual_cache_inject.py --college "Purdue University" --file data/purdue_text.txt

    # Choose a different model (default: llama3.2:3b)
    python3 research_assist/manual_cache_inject.py --college "Carlson" --model qwen2.5:3b

    # Show the prompt only (no Ollama call)
    python3 research_assist/manual_cache_inject.py --college "Purdue" --dry-run < text.txt

Requirements:
    pip install ".[free]"   (see pyproject.toml)
    ollama pull llama3.2:3b (or run install-free.sh)

Ollama must be running:
    ollama serve            (or it auto-starts on macOS after brew install)
"""

import argparse
import json
import sys
from datetime import date


# ---------------------------------------------------------------------------
# Cache schema template — drives the extraction prompt.
# Fields marked null are acceptable blanks; model must not invent values.
# ---------------------------------------------------------------------------
SCHEMA_EXAMPLE = {
    "researched_at": str(date.today()),
    "rankings": {
        "national_university": None,
        "undergrad_business": None,
        "entrepreneurship": None,
        "notes": None
    },
    "tuition": {
        "in_state": None,
        "out_of_state": None,
        "year": None,
        "source_url": None
    },
    "admit_stats": {
        "scope": None,
        "cycle": None,
        "gpa_mid50_low": None,
        "gpa_mid50_high": None,
        "sat_mid50_low": None,
        "sat_mid50_high": None,
        "act_mid50_low": None,
        "act_mid50_high": None,
        "source": None,
        "source_url": None
    },
    "acceptance_rates": {
        "university_general": {
            "value": None,
            "display": None,
            "label": None,
            "source_url": None,
            "source_note": None
        },
        "business_program": {
            "value": None,
            "display": None,
            "label": None,
            "source_url": None,
            "source_note": None
        }
    },
    "deadlines": {
        "early_action": None,
        "early_decision": None,
        "regular": None,
        "ed_available": None
    },
    "business_program_note": None,
    "research_method": "local_assist"
}

SYSTEM_PROMPT = """\
You are a structured data extraction assistant. Extract college admissions data from the provided text and return ONLY valid JSON — no markdown, no explanation, no commentary.

Rules:
- Use null for any field not found in the text. NEVER invent or guess values.
- tuition values are integers (USD, no commas or $ signs).
- acceptance_rates.*.value MUST be a decimal between 0 and 1 (e.g. 0.35 for 35%, 0.57 for 57%). NEVER store a whole number like 57 or 23.
- acceptance_rates.*.display is a string like "35%" or "35.4%".
- gpa/sat/act fields are numeric (int or float). null if not found.
- ed_available is boolean: true ONLY if the school offers a binding Early Decision program. Early Action is NOT Early Decision — if only EA exists, ed_available is false.
- deadlines use "Mon DD" format (e.g. "Nov 1", "Jan 15"). Do NOT include the day of week — just month abbreviation and day number.
- research_method must be the string "local_assist".
- Return a single JSON object matching the schema — do NOT wrap in a list or add extra keys.
"""


def build_prompt(college_name: str, text: str) -> str:
    schema_str = json.dumps(SCHEMA_EXAMPLE, indent=2)
    return (
        f"Extract data for: {college_name}\n\n"
        f"Target JSON schema (fill in values, keep null where not found):\n"
        f"{schema_str}\n\n"
        f"Source text:\n{text.strip()}\n\n"
        f"Return only the filled-in JSON object."
    )


def call_ollama(model: str, system: str, user_prompt: str) -> str:
    try:
        import ollama  # type: ignore
    except ImportError:
        sys.exit(
            "ERROR: ollama Python package not installed.\n"
            "Run: pip install \".[free]\" from the repo root\n"
            "     (or: pip install ollama)"
        )

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0},
        )
    except Exception as exc:
        sys.exit(
            f"ERROR: Ollama call failed: {exc}\n"
            "Is Ollama running? Try: ollama serve\n"
            f"Is the model pulled? Try: ollama pull {model}"
        )

    return response.message.content or ""


def clean_json(raw: str) -> dict:
    """Strip markdown fences if the model added them, then parse."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening ```json or ``` line and closing ``` line
        text = "\n".join(
            line for line in lines
            if not (line.strip().startswith("```"))
        )
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual cache injection — extract college data from text for manual review and merge."
    )
    parser.add_argument("--college", required=True, help="College name (as it appears in catalog/cache)")
    parser.add_argument("--file", help="Path to input text file (defaults to stdin)")
    parser.add_argument("--model", default="llama3.2:3b", help="Ollama model to use (default: llama3.2:3b)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt only, do not call Ollama")
    args = parser.parse_args()

    # Read source text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            source_text = fh.read()
    else:
        if sys.stdin.isatty():
            print("Paste text then press Ctrl+D (or pipe text via stdin / use --file):", file=sys.stderr)
        source_text = sys.stdin.read()

    if not source_text.strip():
        sys.exit("ERROR: No input text provided. Pipe text or use --file.")

    prompt = build_prompt(args.college, source_text)

    if args.dry_run:
        print("=== SYSTEM ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER PROMPT ===")
        print(prompt)
        return

    print(f"[manual_cache_inject] Model: {args.model}  College: {args.college}", file=sys.stderr)
    print("[manual_cache_inject] Calling Ollama... (this may take 10-30s on first run)", file=sys.stderr)

    raw = call_ollama(args.model, SYSTEM_PROMPT, prompt)

    try:
        draft = clean_json(raw)
    except json.JSONDecodeError as exc:
        print(f"\n[manual_cache_inject] WARNING: Model returned non-JSON. Raw output below.", file=sys.stderr)
        print(f"JSON parse error: {exc}", file=sys.stderr)
        print("\n--- RAW MODEL OUTPUT ---")
        print(raw)
        return

    # Wrap in college key so output can be copy-pasted directly into cache
    output = {args.college: draft}

    print(json.dumps(output, indent=2))

    print("\n[manual_cache_inject] DRAFT ONLY — not written to cache.", file=sys.stderr)
    print("[manual_cache_inject] Review output, merge manually into data/college_research_cache.json, then:", file=sys.stderr)
    print("    college-finder --student <name> validate", file=sys.stderr)
    print("    college-finder --student <name> run", file=sys.stderr)


if __name__ == "__main__":
    main()
