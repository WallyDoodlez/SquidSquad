#!/usr/bin/env bash
# SquidSquad — ensure deps are installed, then run the harness.
# Usage: ./start.sh

set -e
cd "$(dirname "$0")"

# --- Python 3 ---
if ! command -v python3 &>/dev/null; then
    if command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv python-is-python3
    elif command -v brew &>/dev/null; then
        brew install python3
    else
        echo "Install Python 3 and re-run." >&2; exit 1
    fi
fi

# --- pip ---
python3 -m pip --version &>/dev/null || {
    if command -v apt &>/dev/null; then
        sudo apt install -y python3-pip
    else
        python3 -m ensurepip --upgrade
    fi
}

# --- fastapi + uvicorn ---
python3 -c "import fastapi; import uvicorn" 2>/dev/null || pip3 install fastapi uvicorn

# --- claude CLI ---
command -v claude &>/dev/null || echo "WARNING: 'claude' not on PATH (npm i -g @anthropic-ai/claude-code)"

# --- Go ---
exec python3 references/scripts/harness.py "$@"
