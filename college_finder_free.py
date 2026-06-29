#!/usr/bin/env python3
"""
college-finder-free — run the pipeline using Ollama (no API key needed).

Setup (one time):
    Install Ollama: https://ollama.com/download
    ollama pull llama3.2:3b
    ollama serve                 # keep running in a separate terminal

Then:
    college-finder-free --student <name> run
    college-finder-free --student <name> validate
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request


def _check_ollama() -> None:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
    except (urllib.error.URLError, OSError):
        print(
            "ERROR: Ollama is not running.\n"
            "\n"
            "Start it first:\n"
            "  ollama serve\n"
            "\n"
            "If you haven't pulled the model yet:\n"
            "  ollama pull llama3.2:3b",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main() -> None:
    _check_ollama()

    import os
    os.environ["COLLEGE_FINDER_BACKEND"] = "local"

    from college_finder_cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
