#!/usr/bin/env bash
# SquidSquad — BARE harness launcher (#12525).
#
# Brings up ONLY the harness, in the foreground. Unlike start.sh / start.ps1
# (the FULL setup launchers), this does NOT sync clones and does NOT install
# dependencies — it assumes the environment is already set up. Run start.sh
# once for that; use this for the greenfield install smoke test and for
# debugging a harness you want to watch.
#
# Usage: ./start-harness.sh [harness args...]
cd "$(dirname "$0")"
exec python3 references/scripts/harness.py "$@"
