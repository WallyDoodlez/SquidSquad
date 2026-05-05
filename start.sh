#!/usr/bin/env bash
# SquidSquad — ensure deps, sync clones, run harness.
# Usage: ./start.sh

set -e
cd "$(dirname "$0")"
REPO_ROOT="$(pwd)"

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

# --- Sync all clones to main ---
echo "Syncing clones..."
# Primary repo
git checkout main 2>/dev/null && git pull --ff-only 2>/dev/null && echo "  primary: OK" || echo "  primary: WARN (could not sync)"

# Agent clones from .local-config
if [ -f ".squidsquad/.local-config" ]; then
    while IFS= read -r line; do
        role=$(echo "$line" | sed -n 's/^- \*\*\([^*]*\)\*\*: *\(.*\)/\1/p')
        path=$(echo "$line" | sed -n 's/^- \*\*\([^*]*\)\*\*: *\(.*\)/\2/p')
        [ -z "$role" ] && continue
        [ "$path" = "." ] && continue
        # Resolve relative path
        if [[ "$path" != /* ]]; then
            path="$REPO_ROOT/$path"
        fi
        if [ -d "$path" ]; then
            (cd "$path" && git checkout main 2>/dev/null && git pull --ff-only 2>/dev/null && echo "  $role: OK") || echo "  $role: WARN (could not sync $path)"
        else
            echo "  $role: MISSING ($path)"
        fi
    done < ".squidsquad/.local-config"
fi

# --- Go ---
exec python3 references/scripts/harness.py "$@"
