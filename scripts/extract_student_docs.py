"""Extract student profile fields from PDF documents (transcript, resume, test reports).

Reads any PDF files found in the student's input/ folder alongside the Excel profile.
Uses LLM to extract structured data and merges it into the profile dict — Excel values
always take precedence (PDF fills only blank fields).

Supported backends (same as the rest of the pipeline):
  openai    → OpenAI API (OPENAI_API_KEY)
  anthropic → Anthropic API (ANTHROPIC_API_KEY)
  local     → Ollama (llama3.2:3b or configured model)
  cursor    → no-op (user fills Excel manually)

Called from load_profile.py after Excel is loaded.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

PDF_FILENAMES = ("transcript.pdf", "resume.pdf", "test_scores.pdf", "test_report.pdf")

SYSTEM_PROMPT = """\
You are a structured data extraction assistant. Extract student academic and activity data \
from the provided document text and return ONLY valid JSON — no markdown, no explanation.

Rules:
- Use null for any field not found in the text. NEVER invent or guess values.
- gpa_unweighted and gpa_weighted are floats on a 4.0 scale (e.g. 3.82).
- sat_total is an integer (400–1600). act_composite is an integer (1–36).
- act subscores (english, math, reading, science) are integers (1–36).
- courses, ap_courses, awards, activities, work are arrays of strings.
- graduation_year is a 4-digit integer (e.g. 2027).
- Return null for any field you are not confident about.
"""

SCHEMA_EXAMPLE = {
    "gpa_unweighted": None,
    "gpa_weighted": None,
    "gpa_source": None,
    "graduation_year": None,
    "sat_total": None,
    "act_composite": None,
    "act_english": None,
    "act_math": None,
    "act_reading": None,
    "act_science": None,
    "key_coursework_summary": None,
    "ap_courses": None,
    "business_coursework": None,
    "awards": None,
    "activities": None,
    "work": None,
    "high_school": None,
    "high_school_ceeb": None,
    "class_rank": None,
}


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF. Returns empty string if pypdf not installed or PDF is image-only."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
        return "\n".join(pages)
    except Exception:
        return ""


def _collect_pdf_texts(input_dir: Path) -> Dict[str, str]:
    """Return {filename: text} for every readable PDF in input_dir."""
    texts: Dict[str, str] = {}
    for fname in PDF_FILENAMES:
        path = input_dir / fname
        if path.is_file():
            text = _read_pdf(path)
            if text.strip():
                texts[fname] = text
                print(f"  [student docs] Read {fname} ({len(text)} chars)")
            else:
                print(f"  [student docs] {fname} found but no extractable text (image-only PDF?)")
    return texts


def _build_prompt(doc_name: str, text: str) -> str:
    schema_str = json.dumps(SCHEMA_EXAMPLE, indent=2)
    return (
        f"Document: {doc_name}\n\n"
        f"Extract student data into this JSON schema (fill values found, keep null otherwise):\n"
        f"{schema_str}\n\n"
        f"Document text:\n{text[:6000]}\n\n"
        f"Return only the filled-in JSON object."
    )


def _call_openai(prompt: str) -> Optional[Dict[str, Any]]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    body = json.dumps({
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return _parse_json(payload["choices"][0]["message"]["content"])
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
        return None


def _call_anthropic(prompt: str) -> Optional[Dict[str, Any]]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    body = json.dumps({
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return _parse_json(payload["content"][0]["text"])
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
        return None


def _call_ollama(prompt: str) -> Optional[Dict[str, Any]]:
    try:
        import ollama  # type: ignore
    except ImportError:
        return None
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0},
        )
        return _parse_json(response.message.content or "")
    except Exception:
        return None


def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_one(doc_name: str, text: str, backend: str) -> Optional[Dict[str, Any]]:
    prompt = _build_prompt(doc_name, text)
    if backend == "openai":
        return _call_openai(prompt)
    if backend == "anthropic":
        return _call_anthropic(prompt)
    if backend == "local":
        return _call_ollama(prompt)
    return None


def _merge_into_profile(profile: Dict[str, Any], extracted: Dict[str, Any]) -> int:
    """Merge extracted fields into profile — Excel values take precedence. Returns count of fields filled."""
    filled = 0

    def _fill(profile_path: str, value: Any) -> None:
        nonlocal filled
        if value is None:
            return
        parts = profile_path.split(".")
        node = profile
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        if node.get(parts[-1]) in (None, "", []):
            node[parts[-1]] = value
            filled += 1

    _fill("gpa_unweighted", extracted.get("gpa_unweighted"))
    _fill("gpa_weighted", extracted.get("gpa_weighted"))
    _fill("gpa_source", extracted.get("gpa_source"))
    _fill("class_of", extracted.get("graduation_year"))
    _fill("sat", extracted.get("sat_total"))
    _fill("high_school", extracted.get("high_school"))
    _fill("high_school_ceeb", extracted.get("high_school_ceeb"))

    act_composite = extracted.get("act_composite")
    if act_composite is not None:
        act = profile.setdefault("act", {})
        if act.get("composite") is None:
            act["composite"] = act_composite
            filled += 1
        for sub in ("english", "math", "reading", "science"):
            val = extracted.get(f"act_{sub}")
            if val is not None and act.get(sub) is None:
                act[sub] = val
                filled += 1

    highlights = profile.setdefault("academic_highlights", {})
    _fill_list(highlights, "key_coursework_summary", extracted.get("key_coursework_summary"))
    _fill_list_field(highlights, "ap_completed_or_in_progress", extracted.get("ap_courses"))
    _fill_list_field(highlights, "business_coursework", extracted.get("business_coursework"))
    if extracted.get("class_rank") and not highlights.get("class_rank"):
        highlights["class_rank"] = extracted["class_rank"]
        filled += 1

    activities = profile.setdefault("activities_summary", {})
    _fill_list_field(activities, "awards", extracted.get("awards"))
    _fill_list_field(activities, "other", extracted.get("activities"))
    _fill_list_field(activities, "work", extracted.get("work"))

    return filled


def _fill_list(node: Dict[str, Any], key: str, value: Any) -> None:
    if value is None or node.get(key):
        return
    if isinstance(value, list):
        node[key] = ", ".join(str(v) for v in value if v)
    elif isinstance(value, str) and value.strip():
        node[key] = value.strip()


def _fill_list_field(node: Dict[str, Any], key: str, value: Any) -> None:
    if value is None or node.get(key):
        return
    if isinstance(value, list) and value:
        node[key] = [str(v).strip() for v in value if str(v).strip()]
    elif isinstance(value, str) and value.strip():
        node[key] = [v.strip() for v in value.split(",") if v.strip()]


def extract_and_merge(profile: Dict[str, Any], input_dir: Path, backend: str) -> int:
    """Read PDFs from input_dir, extract student data, merge into profile.

    Returns total number of profile fields filled from documents.
    Excel values always take precedence — only blank fields are filled.
    """
    if backend == "cursor":
        return 0

    texts = _collect_pdf_texts(input_dir)
    if not texts:
        return 0

    total_filled = 0
    for doc_name, text in texts.items():
        print(f"  [student docs] Extracting from {doc_name} via {backend}...")
        extracted = _extract_one(doc_name, text, backend)
        if extracted is None:
            print(f"  [student docs] WARNING: Could not extract data from {doc_name} — skipping")
            continue
        n = _merge_into_profile(profile, extracted)
        print(f"  [student docs] {doc_name}: filled {n} profile fields")
        total_filled += n

    return total_filled
