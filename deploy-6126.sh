#!/bin/bash
# Deploy script for #6126 — Harness owns PR merge + compose
# Conflicts already resolved. Run from repo root.

set -e

echo "=== Step 1: Stop all agents ==="
python references/scripts/start_team.py --stop --all 2>/dev/null || echo "  (agents may not be running — continuing)"
echo ""

echo "=== Step 2: Merge the PR ==="
git checkout main
git pull
gh pr merge 6201 --squash --delete-branch
echo ""

echo "=== Step 3: Pull merged code ==="
git pull
echo ""

echo "=== Step 4: Recompose all agent templates ==="
python references/scripts/compose.py deploy-all
echo ""

echo "=== Step 5: Start harness + agents ==="
python references/scripts/start_team.py --all
echo ""

echo "=== Step 6: Remove blocked label ==="
gh issue edit 6126 --remove-label blocked:human-action
echo ""

echo "=== Done ==="
echo "QA will verify the 13 runtime TCs automatically."
