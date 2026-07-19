"""Project root paths — import from any script under scripts/.

Student isolation
-----------------
Per-student paths (INPUT, CONFIG, OUTPUT, LOGS, COLLEGES_DIR) resolve under a
*student root* directory.  Set one of these to select the active student:

  COLLEGE_COMPASS_STUDENT=sid          → <repo>/students/sid/
  COLLEGE_COMPASS_STUDENT_DIR=/abs/path → that absolute path

The shared data directory (DATA) always points to <repo>/data/ and is never
per-student — the research cache and reference files are shared across all
students.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Shared reference data — cache, rankings, acceptance rates.
DATA = ROOT / "data"


def _resolve_student_root() -> Path:
    """Return the active student's root directory."""
    abs_dir = os.environ.get("COLLEGE_COMPASS_STUDENT_DIR", "").strip()
    if abs_dir:
        return Path(abs_dir)
    name = os.environ.get("COLLEGE_COMPASS_STUDENT", "").strip()
    if name:
        return ROOT / "students" / name
    # Legacy fallback: old flat layout (input/ at repo root).
    if (ROOT / "input" / "student profile input.xlsx").is_file():
        return ROOT
    raise EnvironmentError(
        "No student selected.\n"
        "  Run:  college-compass-free --student <name> run\n"
        "  Or:   college-compass-pro  --student <name> run\n"
        "  Or:   export COLLEGE_COMPASS_STUDENT=<name>\n"
        "  Example student folder: students/alex-sample/"
    )


STUDENT_ROOT = _resolve_student_root()

# Per-student paths.
INPUT = STUDENT_ROOT / "input"
OUTPUT = STUDENT_ROOT / "output"
STUDENT_DATA = STUDENT_ROOT / "data"       # intermediate data (catalog, match report, logs)
COLLEGES_DIR = STUDENT_DATA / "colleges"   # per-student discovered school list
LOGS = STUDENT_DATA / "logs"               # operational logs — not a deliverable

# Shared tool config (research_backend, logging) — lives at repo root, not per-student.
CONFIG = ROOT / "config"


def load_env_file() -> None:
    """Load ROOT/.env into os.environ (does not override existing vars)."""
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
