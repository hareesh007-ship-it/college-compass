#!/usr/bin/env python3
"""Run the full college compass pipeline (recommended single command)."""

import os
from _paths import load_env_file

load_env_file()

# Warn once here — after .env is loaded — so the warning is accurate
if not os.environ.get("SCORECARD_API_KEY", "").strip() and not os.environ.get("COLLEGE_SCORECARD_API_KEY", "").strip():
    print(
        "\n  ⚠️  WARNING: SCORECARD_API_KEY is not set in your .env file.\n"
        "     School discovery will use a shared demo key that is heavily rate-limited.\n"
        "     You may see very few schools, empty results, or HTTP 429 errors.\n"
        "     Get a free key in 30 seconds: https://api.data.gov/signup/\n"
        "     Then add SCORECARD_API_KEY=your_key to your .env file.\n"
    )
    # Suppress duplicate warning from scorecard_api.py
    import scorecard_api
    scorecard_api._scorecard_key_warned = True

from pipeline import run_pipeline

if __name__ == "__main__":
    raise SystemExit(run_pipeline(write_matches=True, write_sheet=True))
