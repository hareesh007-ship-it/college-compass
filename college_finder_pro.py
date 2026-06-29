#!/usr/bin/env python3
"""
college-finder-pro — run the pipeline using an LLM API key (Anthropic or OpenAI).

Setup (one time):
    Add your API key to .env at the repo root:
        ANTHROPIC_API_KEY=sk-ant-...    (preferred)
        OPENAI_API_KEY=sk-...           (alternative)

Then:
    college-finder-pro --student <name> run
    college-finder-pro --student <name> validate

If both keys are present, Anthropic is used.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_env() -> None:
    """Load .env without overriding vars already set in the environment."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _pick_backend() -> str:
    _load_env()
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("[college-finder-pro] Using Anthropic backend")
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY", "").strip():
        print("[college-finder-pro] Using OpenAI backend")
        return "openai"
    print(
        "ERROR: No API key found.\n"
        "\n"
        "Add one of these to a file called .env in the project folder:\n"
        "  ANTHROPIC_API_KEY=sk-ant-...\n"
        "  OPENAI_API_KEY=sk-...\n"
        "\n"
        "Get a key:\n"
        "  Anthropic: https://console.anthropic.com\n"
        "  OpenAI:    https://platform.openai.com/api-keys",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main() -> None:
    backend = _pick_backend()
    os.environ["COLLEGE_FINDER_BACKEND"] = backend

    from college_finder_cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
