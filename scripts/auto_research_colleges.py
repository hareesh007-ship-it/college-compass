"""Auto-research college admissions data for catalog schools.

For each school in the catalog that is missing mid-50% bands, deadlines, or
program-level accept rates, this module:
  1. Fetches the school's admissions page (from Scorecard URL or a search fallback)
  2. Passes the page text to the configured LLM backend
  3. Extracts structured data and merges it into the shared cache

Runs as part of the pipeline after cache_sync. Schools already fully researched
are skipped — so repeat runs are fast.

Backends:
  openai    → OpenAI API (OPENAI_API_KEY)
  anthropic → Anthropic API (ANTHROPIC_API_KEY)
  local     → Ollama (llama3.2:3b) — free path
  cursor    → no-op (user populates cache manually via manual_cache_inject.py)
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from _paths import DATA

CACHE_PATH = DATA / "college_research_cache.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SYSTEM_PROMPT = """\
You are a structured data extraction assistant. Extract college admissions data from the \
provided webpage text and return ONLY valid JSON — no markdown, no explanation.

Rules:
- Use null for any field not found in the text. NEVER invent or guess values.
- tuition values are integers (USD, no commas or $ signs). null if not found.
- acceptance_rate values are decimals between 0 and 1 (e.g. 0.35 for 35%). NEVER store whole numbers.
- gpa/sat/act fields are numeric (int or float). null if not found.
- ed_available is boolean: true ONLY if the school offers binding Early Decision. EA is NOT ED.
- deadlines use "Mon DD" format (e.g. "Nov 1", "Jan 15").
- research_method must be the string "auto_research".
- Return a single JSON object. Do NOT wrap in a list or add extra keys.
"""

SCHEMA_EXAMPLE = {
    "tuition": {
        "in_state": None,
        "out_of_state": None,
    },
    "admit_stats": {
        "gpa_mid50_low": None,
        "gpa_mid50_high": None,
        "sat_mid50_low": None,
        "sat_mid50_high": None,
        "act_mid50_low": None,
        "act_mid50_high": None,
    },
    "acceptance_rates": {
        "university_general": {
            "value": None,
            "display": None,
        },
        "business_program": {
            "value": None,
            "display": None,
        },
    },
    "deadlines": {
        "early_action": None,
        "early_decision": None,
        "regular": None,
        "ed_available": None,
    },
    "business_program_note": None,
}

# Admissions page URL patterns to try per school
ADMISSIONS_URL_PATTERNS = [
    "{base}/admissions",
    "{base}/admission",
    "{base}/apply",
    "{base}/undergraduate/admissions",
    "{base}/admissions/first-year",
]


@dataclass
class ResearchResult:
    researched: int = 0
    skipped: int = 0
    failed: int = 0


def _needs_auto_research(block: Dict[str, Any]) -> bool:
    """True if the block is missing mid-50% bands or deadlines."""
    stats = block.get("admit_stats") or {}
    has_mid50 = stats.get("gpa_mid50_low") is not None or stats.get("sat_mid50_low") is not None
    deadlines = block.get("deadlines") or {}
    has_deadline = deadlines.get("regular") is not None or deadlines.get("early_action") is not None
    return not (has_mid50 and has_deadline)


def _fetch_page(url: str) -> Optional[str]:
    """Fetch a webpage and return cleaned text. Returns None on failure."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:8000]
    except Exception:
        return None


def _find_admissions_page(school_url: str, school_name: str) -> Optional[str]:
    """Try common admissions URL patterns, return first that responds."""
    if not school_url:
        return None
    base = school_url.rstrip("/")
    if not base.startswith("http"):
        base = f"https://{base}"

    for pattern in ADMISSIONS_URL_PATTERNS:
        url = pattern.format(base=base)
        text = _fetch_page(url)
        if text and len(text) > 500:
            return text

    # Fallback: fetch the homepage and look for admissions links
    homepage = _fetch_page(base)
    if homepage and len(homepage) > 200:
        return homepage

    return None


def _build_prompt(school_name: str, page_text: str) -> str:
    schema_str = json.dumps(SCHEMA_EXAMPLE, indent=2)
    return (
        f"Extract admissions data for: {school_name}\n\n"
        f"Fill this JSON schema (use null for anything not found):\n"
        f"{schema_str}\n\n"
        f"Webpage text:\n{page_text}\n\n"
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
    except (urllib.error.URLError, KeyError, IndexError):
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
    except (urllib.error.URLError, KeyError, IndexError):
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


def _extract(school_name: str, page_text: str, backend: str) -> Optional[Dict[str, Any]]:
    prompt = _build_prompt(school_name, page_text)
    if backend == "openai":
        return _call_openai(prompt)
    if backend == "anthropic":
        return _call_anthropic(prompt)
    if backend == "local":
        return _call_ollama(prompt)
    return None


def _merge_extracted(block: Dict[str, Any], extracted: Dict[str, Any], school_url: str) -> bool:
    """Merge LLM-extracted data into existing cache block. Returns True if anything changed."""
    changed = False
    today = date.today().isoformat()

    # Tuition — only fill if missing
    tuition_ext = extracted.get("tuition") or {}
    tuition = block.setdefault("tuition", {})
    for key in ("in_state", "out_of_state"):
        if tuition_ext.get(key) is not None and tuition.get(key) is None:
            tuition[key] = tuition_ext[key]
            changed = True

    # Mid-50% bands — fill missing fields
    stats_ext = extracted.get("admit_stats") or {}
    stats = block.setdefault("admit_stats", {})
    for field in ("gpa_mid50_low", "gpa_mid50_high", "sat_mid50_low", "sat_mid50_high", "act_mid50_low", "act_mid50_high"):
        if stats_ext.get(field) is not None and stats.get(field) is None:
            stats[field] = stats_ext[field]
            changed = True
    if changed and not stats.get("source"):
        stats["source"] = "auto_research"

    # Acceptance rates — only fill if currently null/stub
    rates_ext = extracted.get("acceptance_rates") or {}
    rates = block.setdefault("acceptance_rates", {})
    for rate_key in ("university_general", "business_program"):
        ext_rate = rates_ext.get(rate_key) or {}
        if ext_rate.get("value") is not None:
            existing = rates.get(rate_key) or {}
            if existing.get("value") is None:
                rates[rate_key] = {
                    "value": ext_rate["value"],
                    "display": ext_rate.get("display") or f"{ext_rate['value']*100:.1f}%",
                    "label": rate_key.replace("_", " ").title(),
                    "source_url": school_url,
                    "source_note": "auto_research",
                }
                changed = True

    # Deadlines — fill missing
    dl_ext = extracted.get("deadlines") or {}
    dl = block.setdefault("deadlines", {})
    for field in ("early_action", "early_decision", "regular", "ed_available"):
        if dl_ext.get(field) is not None and dl.get(field) is None:
            dl[field] = dl_ext[field]
            changed = True

    # Business program note
    note = extracted.get("business_program_note")
    if note and not block.get("business_program_note"):
        block["business_program_note"] = note
        changed = True

    if changed:
        rm = block.setdefault("research_method", {})
        rm["backend"] = "auto_research"
        rm["researched_at"] = today
        if school_url and school_url not in (rm.get("source_urls") or []):
            urls = list(rm.get("source_urls") or [])
            urls.append(school_url)
            rm["source_urls"] = urls
        block["researched_at"] = today

    return changed


def _load_cache() -> Dict[str, Any]:
    if not CACHE_PATH.is_file():
        return {"colleges": {}}
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: Dict[str, Any]) -> None:
    cache["last_updated"] = date.today().isoformat()
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def auto_research_catalog(catalog: Dict[str, Any], backend: str) -> ResearchResult:
    """Auto-research admissions data for every catalog school that needs it.

    Skips schools already fully researched (has mid-50% + deadlines).
    Politely rate-limits web fetches to avoid being blocked.
    """
    if backend == "cursor":
        print("  [auto-research] Cursor backend — skipping auto-research (populate cache manually)")
        return ResearchResult()

    cache = _load_cache()
    colleges = cache.setdefault("colleges", {})
    result = ResearchResult()

    schools_to_research = [
        entry for entry in (catalog.get("colleges") or [])
        if _needs_auto_research(colleges.get(entry["cache_key"]) or {})
    ]

    if not schools_to_research:
        print("  [auto-research] All catalog schools already fully researched — skipping")
        return result

    print(f"  [auto-research] Researching {len(schools_to_research)} schools via {backend}...")

    for entry in schools_to_research:
        cache_key = entry["cache_key"]
        school_url = entry.get("school_url") or ""
        if school_url and not school_url.startswith("http"):
            school_url = f"https://{school_url}"

        print(f"  [auto-research] Fetching: {cache_key}")
        page_text = _find_admissions_page(school_url, cache_key)
        if not page_text:
            print(f"  [auto-research] WARNING: Could not fetch admissions page for {cache_key}")
            result.failed += 1
            continue

        extracted = _extract(cache_key, page_text, backend)
        if extracted is None:
            print(f"  [auto-research] WARNING: LLM extraction failed for {cache_key}")
            result.failed += 1
            continue

        block = colleges.setdefault(cache_key, {})
        if _merge_extracted(block, extracted, school_url):
            print(f"  [auto-research] Updated: {cache_key}")
            result.researched += 1
        else:
            print(f"  [auto-research] No new data extracted for {cache_key}")
            result.skipped += 1

        time.sleep(1.5)  # polite rate limit between schools

    _save_cache(cache)
    from college_research import reload_cache
    reload_cache()

    print(
        f"  [auto-research] Done: {result.researched} updated, "
        f"{result.skipped} no new data, {result.failed} failed"
    )
    return result
