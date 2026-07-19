#!/usr/bin/env python3
"""
Cross-platform CLI entry point for College Compass.

All platforms (Windows / macOS / Linux) after `pip install -e .`:
    college-compass-free --student <name> run
    college-compass-pro  --student <name> run

Or run directly with Python:
    python college_compass_cli.py --student <name> <command>

Commands: run | validate | help
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

def _find_repo_root() -> Path:
    """Find the repo root whether running from the repo directly or via pip install.

    When installed with `pip install -e .` the CLI lives at the repo root alongside
    pyproject.toml, so __file__ parent IS the repo root.

    When installed with plain `pip install .` the CLI is copied into site-packages.
    In that case walk up from cwd until we find pyproject.toml, falling back to cwd.
    """
    # Editable install or direct invocation: __file__ parent has pyproject.toml
    candidate = Path(__file__).resolve().parent
    if (candidate / "pyproject.toml").is_file():
        return candidate

    # Plain pip install: search from cwd upward
    for parent in [Path.cwd()] + list(Path.cwd().parents):
        if (parent / "pyproject.toml").is_file() and (parent / "scripts").is_dir():
            return parent

    # Last resort: cwd
    return Path.cwd()


ROOT = _find_repo_root()
SCRIPTS = ROOT / "scripts"


def _bootstrap() -> None:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from _paths import load_env_file
    load_env_file()


def _cmd_run() -> None:
    _bootstrap()
    from pipeline import run_pipeline
    raise SystemExit(run_pipeline(write_matches=True, write_sheet=True))


def _cmd_validate() -> None:
    _bootstrap()
    import json
    from validate_cache import CACHE_PATH, validate_cache
    from college_finder import catalog_college_names

    with open(CACHE_PATH, encoding="utf-8") as f:
        cache_data = json.load(f)
    errors, warnings = validate_cache(cache_data, catalog_college_names())
    for msg in warnings:
        print(f"WARN: {msg}")
    for msg in errors:
        print(f"ERROR: {msg}")
    raise SystemExit(1 if errors else 0)


def _cmd_cursor_prompt() -> None:
    print(
        "Copy into a new Cursor chat (attach @docs/RESEARCH_AGENT.md):\n\n"
        "> Read @docs/RESEARCH_AGENT.md and @docs/PROFILE_AND_CONFIG.md. "
        "Follow scope commands exactly.\n"
        "> `research school: <School Name>` — refresh rankings, tuition, deadlines, "
        "acceptance rates, and mid-50% only if officially published for the business "
        "program. Write only to data/college_research_cache.json. After edits: validate "
        "cache, then run the pipeline. Do not re-research other schools unless I ask.\n\n"
        "Cheaper one-field update:\n\n"
        "> Read @docs/RESEARCH_AGENT.md. `update cache only: <School Name> <field>` — "
        "verify from official .edu sources, update cache only, run validator, regenerate outputs.\n\n"
        "Scope rules: update cache only | research school | research field | "
        "full refresh: all (explicit only)."
    )


def _print_usage() -> None:
    print(f"""\
College Compass — Safety / Target / Reach matcher + selection sheet

Usage:
  college-compass [--student NAME] run              Full pipeline (discover → match → sheet)
  college-compass [--student NAME] validate         Validate data/college_research_cache.json
  college-compass cursor-prompt                     Print Cursor research chat starter
  college-compass help                              Show this help

Student folders live under students/<name>/  (input/, data/, output/)
Shared data (cache + rankings) stays in data/ at the repo root.

Examples:
  college-compass --student alex-sample run
  college-compass --student <your-name> run
  COLLEGE_COMPASS_STUDENT=alex-sample college-compass run

Windows:
  python college_compass_cli.py --student alex-sample run

Repo:  {ROOT}
Docs:  docs/Quickstart-pro.md  ·  docs/RESEARCH_AGENT.md
""")


def main() -> None:
    parser = argparse.ArgumentParser(prog="college-compass", add_help=False)
    parser.add_argument("--student", metavar="NAME",
                        help="Student folder name under students/")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("-h", "--help", action="store_true")
    args, _ = parser.parse_known_args()

    if args.student:
        os.environ["COLLEGE_COMPASS_STUDENT"] = args.student

    cmd = args.command or "help"

    if args.help or cmd == "help":
        _print_usage()
        raise SystemExit(0)

    if cmd == "run":
        _cmd_run()
    elif cmd == "validate":
        _cmd_validate()
    elif cmd in ("cursor-prompt", "cursor_prompt"):
        _cmd_cursor_prompt()
    else:
        print(f"Unknown command: {cmd}\n", file=sys.stderr)
        _print_usage()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
