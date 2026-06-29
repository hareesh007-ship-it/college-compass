"""Optional LLM-assisted school name suggestions.

Respects research_backend from config/pro.json:
  openai     → calls OpenAI Chat Completions (requires OPENAI_API_KEY)
  anthropic  → calls Anthropic Messages API (requires ANTHROPIC_API_KEY)
  local      → calls Ollama (llama3.2:3b — best-effort, free path)
  cursor     → no-op (Cursor users research manually via RESEARCH_AGENT.md)

Only runs when "Any other preference" is filled in the Excel profile.
Note: local (Ollama 3B) suggestions are best-effort — quality is lower than
pro models but better than nothing for users without an API key.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List

MAX_SUGGESTIONS = 12


def _build_prompt(profile: Dict[str, Any]) -> str:
    prefs = profile.get("preferences") or {}
    extra = prefs.get("any_other_preference") or ""
    return (
        "Return ONLY a JSON array of US college names (official institution names) that fit this student. "
        "No markdown, no explanation.\n"
        f"Major: {profile.get('intended_major')}\n"
        f"State: {profile.get('state_of_residence')}\n"
        f"Regions: {', '.join(prefs.get('regions') or [])}\n"
        f"Budget max tuition/year USD: {profile.get('budget_max_tuition_per_year')}\n"
        f"Public OK: {prefs.get('public_ok', True)}; Private OK: {prefs.get('private_ok', True)}\n"
        f"Other preferences: {extra}\n"
        f"Already interested in: {', '.join(profile.get('schools_interested_in') or [])}\n"
        f"Suggest up to {MAX_SUGGESTIONS} additional schools not already listed."
    )


def _parse_names(text: str) -> List[str]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        names = json.loads(text)
        if isinstance(names, list):
            return [str(n).strip() for n in names if str(n).strip()]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def _openai_suggest(profile: Dict[str, Any]) -> List[str]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return []
    body = json.dumps({
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": _build_prompt(profile)}],
        "temperature": 0.2,
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
        return _parse_names(payload["choices"][0]["message"]["content"])
    except (urllib.error.URLError, KeyError, IndexError):
        return []


def _anthropic_suggest(profile: Dict[str, Any]) -> List[str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return []
    body = json.dumps({
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
        "max_tokens": 512,
        "messages": [{"role": "user", "content": _build_prompt(profile)}],
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
        return _parse_names(payload["content"][0]["text"])
    except (urllib.error.URLError, KeyError, IndexError):
        return []


def _ollama_suggest(profile: Dict[str, Any]) -> List[str]:
    try:
        import ollama  # type: ignore
    except ImportError:
        return []
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": _build_prompt(profile)}],
            options={"temperature": 0.2},
        )
        return _parse_names(response.message.content or "")
    except Exception:
        return []


def suggest_school_names(profile: Dict[str, Any]) -> List[str]:
    """Return LLM-suggested school names, or [] if not applicable."""
    if not (profile.get("preferences") or {}).get("any_other_preference"):
        return []

    try:
        from pro_config import load_pro_config
        backend = load_pro_config().get("research_backend", "cursor")
    except Exception:
        backend = "cursor"

    if backend == "openai":
        return _openai_suggest(profile)
    if backend == "anthropic":
        return _anthropic_suggest(profile)
    if backend == "local":
        return _ollama_suggest(profile)
    # cursor → manual research
    return []
