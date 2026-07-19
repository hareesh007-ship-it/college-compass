#!/usr/bin/env bash
# install-free.sh — Set up the free/offline local model tier (Ollama + Python client)
#
# Usage:
#   bash install-free.sh                  # installs default model (llama3.2:3b)
#   OLLAMA_MODEL=qwen2.5:3b bash install-free.sh
#   OLLAMA_MODEL=llama3.1:8b bash install-free.sh
#
# After setup, run extractions with:
#   pbpaste | python3 research_assist/extract_college_draft.py --college "Purdue University"

set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${SCRIPT_DIR}/.venv"
PY="${PY:-python3}"

echo "=== College Compass — Free / Local Tier Setup ==="
echo "Model: $OLLAMA_MODEL"
echo ""

# ------------------------------------------------------------------
# 0. Python version check + virtual environment (mirrors install-pro.sh)
# ------------------------------------------------------------------
if ! command -v "${PY}" >/dev/null 2>&1; then
  echo "ERROR: Python 3 not found. Install Python 3.9+ and re-run." >&2
  exit 1
fi

if ! "${PY}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
  PY_VERSION="$("${PY}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  echo "ERROR: Python 3.9+ required (found ${PY_VERSION})." >&2
  exit 1
fi

if [[ ! -d "${VENV}" ]]; then
  echo "[0/3] Creating virtual environment at ${VENV} ..."
  "${PY}" -m venv "${VENV}"
else
  echo "[0/3] Virtual environment already exists at ${VENV}"
fi

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
echo ""

# ------------------------------------------------------------------
# 1. Install Ollama
# ------------------------------------------------------------------
if command -v ollama &>/dev/null; then
    echo "[1/3] Ollama already installed: $(ollama --version 2>/dev/null || echo 'version unknown')"
else
    echo "[1/3] Installing Ollama..."
    if command -v brew &>/dev/null; then
        brew install ollama
    else
        echo "  Homebrew not found. Installing via official script..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    echo "  Ollama installed."
fi
echo ""

# ------------------------------------------------------------------
# 2. Pull the model
# ------------------------------------------------------------------
echo "[2/3] Pulling model: $OLLAMA_MODEL"
echo "      (This may take a few minutes on first run — ~2 GB for llama3.2:3b)"

# Start Ollama in background if not already running.
# OLLAMA_NUM_GPU=0 forces CPU-only mode — avoids Metal GPU failures on some Macs.
if ! curl -sf http://localhost:11434 &>/dev/null; then
    echo "      Starting Ollama server (CPU mode)..."
    OLLAMA_NUM_GPU=0 ollama serve &>/dev/null &
    OLLAMA_PID=$!
    sleep 4
    STARTED_OLLAMA=true
else
    STARTED_OLLAMA=false
fi

ollama pull "$OLLAMA_MODEL"
echo "  Model ready: $OLLAMA_MODEL"
echo ""

# Stop background Ollama if we started it
if [ "${STARTED_OLLAMA:-false}" = true ]; then
    kill "$OLLAMA_PID" 2>/dev/null || true
fi

# ------------------------------------------------------------------
# 3. Install Python dependencies (base + local model client)
# ------------------------------------------------------------------
echo "[3/3] Installing Python dependencies..."
pip install --upgrade pip >/dev/null
pip install "${SCRIPT_DIR}"[free]
echo "  Done."
echo ""

mkdir -p "${SCRIPT_DIR}/students/alex-sample/output" \
         "${SCRIPT_DIR}/students/alex-sample/data/logs" \
         "${SCRIPT_DIR}/students/alex-sample/data/colleges"

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Set SCORECARD_API_KEY in .env (free: https://api.data.gov/signup/)"
echo "  2. Run the sample student:"
echo "       college-compass-free --student alex-sample run"
echo "  3. Add your own student:"
echo "       cp -r students/alex-sample students/<your-name>"
echo "       college-compass-free --student <your-name> run"
echo ""
echo "Before extracting, make sure Ollama is running (CPU mode recommended on Mac):"
echo "    OLLAMA_NUM_GPU=0 ollama serve"
echo ""
echo "Extract college data from clipboard text:"
echo "    pbpaste | python3 research_assist/extract_college_draft.py --college \"College Name\""
echo ""
echo "After reviewing the draft JSON:"
echo "    college-compass-free --student <your-name> validate"
echo "    college-compass-free --student <your-name> run"
echo ""
echo "Docs: docs/Quickstart-free.md · research_assist/README.md"
