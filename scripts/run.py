#!/usr/bin/env python3
"""Run the full college finder pipeline (recommended single command)."""

from _paths import load_env_file

load_env_file()

from pipeline import run_pipeline

if __name__ == "__main__":
    raise SystemExit(run_pipeline(write_matches=True, write_sheet=True))
