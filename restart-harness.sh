#!/usr/bin/env bash
# SquidSquad — SUPERVISED harness launcher (#12825).
#
# Runs the harness in an auto-relaunch loop so the harness itself can be
# restarted without an operator at the terminal. This is the SUPERVISOR layer
# ABOVE the harness: the harness owns agent lifecycle; this wrapper owns harness
# lifecycle (it is mechanism, not a parallel control path).
#
# Exit-code contract (mirrors the agent self-restart exit-42 convention):
#   42    → RESTART: relaunch immediately. `POST /restart` makes the harness
#           exit with this code.
#   0     → clean STOP (`POST /shutdown`) or operator Ctrl+C → do NOT relaunch.
#   other → CRASH: relaunch, but a crash-loop guard gives up after
#           CRASH_THRESHOLD crashes so a broken harness never respawns forever.
#
# Use this (not start-harness.sh, the one-shot) to run the harness for any
# install that needs self-healing harness restart.
#
# Usage: ./restart-harness.sh [harness args...]
set -u
cd "$(dirname "$0")"

RESTART_CODE="${SQUIDSQUAD_HARNESS_RESTART_CODE:-42}"
CRASH_THRESHOLD="${SQUIDSQUAD_HARNESS_CRASH_THRESHOLD:-3}"
CRASH_WINDOW="${SQUIDSQUAD_HARNESS_CRASH_WINDOW:-60}"
# Overridable so installs can pick a python and tests can point at a stub.
HARNESS_CMD="${SQUIDSQUAD_HARNESS_CMD:-python3 references/scripts/harness.py}"

stop=0
# Operator Ctrl+C reaches both the harness and this wrapper; record it so we
# don't relaunch after an interactive interrupt.
trap 'stop=1' INT TERM
crash_count=0

while true; do
    start=$(date +%s)
    # shellcheck disable=SC2086  # HARNESS_CMD is intentionally word-split.
    $HARNESS_CMD "$@"
    code=$?
    end=$(date +%s)

    if [ "$stop" -eq 1 ]; then
        echo "[restart-harness] operator interrupt - not relaunching."
        exit 0
    fi
    if [ "$code" -eq 0 ]; then
        echo "[restart-harness] harness exited cleanly (0) - not relaunching."
        exit 0
    fi
    if [ "$code" -eq "$RESTART_CODE" ]; then
        echo "[restart-harness] restart requested (exit $code) - relaunching..."
        crash_count=0   # intentional restart — reset crash accounting
        continue
    fi

    # Abnormal exit → crash-loop guard. A run that lasted at least CRASH_WINDOW
    # seconds was healthy (not a boot loop), so it FORGIVES prior crashes — the
    # crash that ended it then starts a fresh streak at 1 (we still count it; a
    # boot loop is rapid *consecutive* crashes, which is what this catches).
    if [ $((end - start)) -ge "$CRASH_WINDOW" ]; then
        crash_count=0
    fi
    crash_count=$((crash_count + 1))
    echo "[restart-harness] harness exited abnormally (code $code) - crash ${crash_count}/${CRASH_THRESHOLD}."
    if [ "$crash_count" -ge "$CRASH_THRESHOLD" ]; then
        echo "[restart-harness] crash-loop detected ($crash_count crashes) - giving up." >&2
        echo "[restart-harness] inspect the harness output above and .squidsquad/harness-errors.log." >&2
        exit 1
    fi
    sleep 1
done
