#!/usr/bin/env bash
# College Compass — Option B (Pro / BYO LLM) installer
# No Ollama, no model download. See docs/Quickstart-pro.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${ROOT}/.venv"
PY="${PY:-python3}"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

echo "College Compass — Pro install (Option B)"
echo "Repo: ${ROOT}"
echo

if ! command -v "${PY}" >/dev/null 2>&1; then
  die "Python 3 not found. Install Python 3.9+ and re-run."
fi

PY_VERSION="$("${PY}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Using Python ${PY_VERSION} (${PY})"

if ! "${PY}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
  die "Python 3.9+ required (found ${PY_VERSION})."
fi

if [[ ! -d "${VENV}" ]]; then
  echo "Creating virtual environment at ${VENV} ..."
  "${PY}" -m venv "${VENV}"
else
  echo "Virtual environment already exists at ${VENV}"
fi

# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo "Installing Python packages ..."
pip install --upgrade pip >/dev/null
pip install "${ROOT}[pro]"

if [[ ! -f "${ROOT}/.env" ]]; then
  cp "${ROOT}/.env.example" "${ROOT}/.env"
  echo "Created .env from .env.example — add your API keys before discovery."
else
  echo ".env already exists (not overwritten)"
fi

if [[ ! -f "${ROOT}/config/pro.json" ]]; then
  cp "${ROOT}/config/pro.json.example" "${ROOT}/config/pro.json"
  echo "Created config/pro.json from example"
else
  echo "config/pro.json already exists (not overwritten)"
fi

mkdir -p "${ROOT}/students/alex-sample/output" \
         "${ROOT}/students/alex-sample/data/logs" \
         "${ROOT}/students/alex-sample/data/colleges"

echo
echo "Install complete."
echo
echo "Next steps:"
echo "  1. Edit ${ROOT}/.env"
echo "     Set SCORECARD_API_KEY (free: https://api.data.gov/signup/)"
echo "     Optional: OPENAI_API_KEY / ANTHROPIC_API_KEY for LLM-assisted discovery"
echo "  2. Try the sample student:"
echo "       cd ${ROOT}"
echo "       college-compass-pro --student alex-sample run"
echo "  3. Add your own student:"
echo "       cp -r students/alex-sample students/<your-name>"
echo "       # edit students/<your-name>/input/student profile input.xlsx"
echo "       college-compass-pro --student <your-name> run"
echo
echo "Research gaps in Cursor: college-compass-pro cursor-prompt"
echo "Docs: docs/Quickstart-pro.md"
