#!/usr/bin/env bash
# SquidSquad — THE single Unix launcher (#13318).
#
# Consolidates the former start.sh + start-harness.sh + restart-harness.sh into
# one script. Running it brings up ALL of SquidSquad:
#   deps → clone-sync → harness (supervised, detached) → agent fleet → TUI.
#
# This script lives in .squidsquad/ (NOT repo root). It resolves the project
# repo root as its own parent directory and operates from there.
#
# Usage:
#   .squidsquad/start.sh                 full bring-up: deps + sync + harness + TUI
#   .squidsquad/start.sh --bare          harness only (no deps/sync/TUI), foreground
#   .squidsquad/start.sh --no-setup      alias for --bare
#   (any other args are passed through to harness.py)
#
# Behaviors folded in:
#   - deps + clone-sync           (former start.sh)
#   - supervised auto-relaunch    (former restart-harness.sh, #12825 — exit-42
#                                  relaunch / exit-0 stop / crash-loop guard)
#   - bare/no-setup path          (former start-harness.sh, #12525)
#   - TUI bundling                (references/tui/app.py, #12801/#13277)
set -u

# --- Repo-root resolution (script is in .squidsquad/, repo root is its parent) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# --- Parse flags (everything non-flag is a harness pass-through arg) ---
BARE=0
HARNESS_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --bare|--no-setup) BARE=1 ;;
        *) HARNESS_ARGS+=("$arg") ;;
    esac
done

# --- Supervised-loop knobs (overridable; tests point SQUIDSQUAD_HARNESS_CMD at a stub) ---
RESTART_CODE="${SQUIDSQUAD_HARNESS_RESTART_CODE:-42}"
CRASH_THRESHOLD="${SQUIDSQUAD_HARNESS_CRASH_THRESHOLD:-3}"
CRASH_WINDOW="${SQUIDSQUAD_HARNESS_CRASH_WINDOW:-60}"
HARNESS_CMD="${SQUIDSQUAD_HARNESS_CMD:-python3 references/scripts/harness.py}"

# --- Harness port + liveness probe (singleton-safety: never double-start) ---
harness_port() {
    local p=7373
    if [ -f .squidsquad/.harness-port ]; then
        local raw
        raw="$(tr -dc '0-9' < .squidsquad/.harness-port 2>/dev/null)"
        [ -n "$raw" ] && p="$raw"
    fi
    echo "$p"
}
harness_up() {
    # Probe via python3 (guaranteed present in full mode after ensure_deps) so
    # the singleton check does not silently fail on hosts without curl (#13318
    # review M1 — a false "down" would double-start the harness).
    python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$(harness_port)/status', timeout=3)" >/dev/null 2>&1
}

# --- Supervised harness loop (folds restart-harness.sh #12825) ---
#   42    → RESTART: relaunch immediately (POST /restart exits with this code).
#   0     → clean STOP (POST /shutdown / operator Ctrl+C) → do NOT relaunch.
#   other → CRASH: relaunch, but a crash-loop guard gives up after
#           CRASH_THRESHOLD rapid consecutive crashes.
run_supervised() {
    local stop=0 crash_count=0 start end code
    # Operator Ctrl+C reaches both harness and wrapper; record it so we don't
    # relaunch after an interactive interrupt.
    trap 'stop=1' INT TERM
    while true; do
        start=$(date +%s)
        # shellcheck disable=SC2086  # HARNESS_CMD is intentionally word-split.
        $HARNESS_CMD "${HARNESS_ARGS[@]}"
        code=$?
        end=$(date +%s)

        if [ "$stop" -eq 1 ]; then
            echo "[start] operator interrupt - not relaunching."
            return 0
        fi
        if [ "$code" -eq 0 ]; then
            echo "[start] harness exited cleanly (0) - not relaunching."
            return 0
        fi
        if [ "$code" -eq "$RESTART_CODE" ]; then
            echo "[start] restart requested (exit $code) - relaunching..."
            crash_count=0   # intentional restart — reset crash accounting
            continue
        fi

        # Abnormal exit → crash-loop guard. A run that lasted at least
        # CRASH_WINDOW seconds was healthy (not a boot loop), so it forgives
        # prior crashes; the crash that ended it then starts a fresh streak at 1.
        if [ $((end - start)) -ge "$CRASH_WINDOW" ]; then
            crash_count=0
        fi
        crash_count=$((crash_count + 1))
        echo "[start] harness exited abnormally (code $code) - crash ${crash_count}/${CRASH_THRESHOLD}."
        if [ "$crash_count" -ge "$CRASH_THRESHOLD" ]; then
            echo "[start] crash-loop detected ($crash_count crashes) - giving up." >&2
            echo "[start] inspect the harness output above, .squidsquad/harness-supervisor.log (detached full-mode output), and .squidsquad/harness-errors.log." >&2
            return 1
        fi
        sleep 1
    done
}

# --- Setup: deps + clone-sync (folds start.sh; skipped in --bare) ---
ensure_deps() {
    # Python 3
    if ! command -v python3 &>/dev/null; then
        if command -v apt &>/dev/null; then
            sudo apt update && sudo apt install -y python3 python3-pip python3-venv python-is-python3
        elif command -v brew &>/dev/null; then
            brew install python3
        else
            echo "Install Python 3 and re-run." >&2; exit 1
        fi
    fi
    # pip
    python3 -m pip --version &>/dev/null || {
        if command -v apt &>/dev/null; then
            sudo apt install -y python3-pip
        else
            python3 -m ensurepip --upgrade
        fi
    }
    # Runtime deps (#11613): import probe covers every runtime dep so a partial
    # environment triggers a full reinstall from requirements.txt.
    python3 -c "import fastapi, uvicorn, starlette, watchdog, yaml" 2>/dev/null || pip3 install -r requirements.txt
    # TUI dep (#12801/#13318): full mode launches references/tui/app.py, which
    # imports `textual` — kept in requirements-tui.txt, separate from the harness
    # runtime set (test_runtime_requirements drift guard). Without this, full mode
    # would pass the harness-dep probe then crash at TUI launch on a fresh machine.
    python3 -c "import textual" 2>/dev/null || pip3 install -r requirements-tui.txt
    # claude CLI
    command -v claude &>/dev/null || echo "WARNING: 'claude' not on PATH (npm i -g @anthropic-ai/claude-code)"
}

sync_clones() {
    echo "Syncing clones..."
    git checkout main 2>/dev/null && git pull --no-rebase 2>/dev/null && echo "  primary: OK" || echo "  primary: WARN (could not sync)"
    if [ -f ".squidsquad/.local-config" ]; then
        while IFS= read -r line; do
            local role path
            role=$(echo "$line" | sed -n 's/^- \*\*\([^*]*\)\*\*: *\(.*\)/\1/p')
            path=$(echo "$line" | sed -n 's/^- \*\*\([^*]*\)\*\*: *\(.*\)/\2/p')
            [ -z "$role" ] && continue
            [ "$path" = "." ] && continue
            if [[ "$path" != /* ]]; then
                path="$REPO_ROOT/$path"
            fi
            if [ -d "$path" ]; then
                (cd "$path" && git checkout main 2>/dev/null && git pull --no-rebase 2>/dev/null && echo "  $role: OK") || echo "  $role: WARN (could not sync $path)"
            else
                echo "  $role: MISSING ($path)"
            fi
        done < ".squidsquad/.local-config"
    fi
}

# --- BARE mode (#12525): harness only, no deps/sync/TUI, foreground supervised ---
# This is also the path the full-mode launch re-invokes (backgrounded) to own the
# harness lifecycle, and the path #12527's greenfield smoke test uses.
if [ "$BARE" -eq 1 ]; then
    echo "[start] bare mode (#12525): harness only (no deps/sync/TUI)."
    run_supervised
    exit $?
fi

# --- FULL mode: deps + sync, then detached supervised harness + foreground TUI ---
ensure_deps
sync_clones

if harness_up; then
    echo "[start] harness already running on port $(harness_port) — attaching TUI (singleton-safe)."
else
    echo "[start] launching harness (supervised, detached background)..."
    # Re-invoke self in --bare mode, detached, so the supervised loop (#12825)
    # survives this script exiting AND the TUI quitting (AC4/AC6). nohup detaches
    # from the controlling terminal (portable: Linux + macOS).
    nohup "$SCRIPT_DIR/start.sh" --bare "${HARNESS_ARGS[@]}" \
        >> .squidsquad/harness-supervisor.log 2>&1 &
    disown 2>/dev/null || true
    # Wait (≤30s) for the harness to answer /status before launching the TUI.
    for _ in $(seq 1 60); do
        harness_up && break
        sleep 0.5
    done
    harness_up || echo "[start] WARNING: harness not reachable yet; TUI will keep retrying."
fi

# TUI in foreground (#12801). Quitting it (q / Ctrl-C) leaves the detached
# harness + agent fleet running in the background (AC6); re-running this script
# re-attaches the TUI without double-starting the harness.
exec python3 references/tui/app.py --url "http://127.0.0.1:$(harness_port)"
