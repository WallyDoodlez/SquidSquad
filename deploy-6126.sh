#!/bin/bash
# Deploy script for #6126 — Harness owns PR merge + compose
# Run this from the SquidSquad repo root.
# The PR has merge conflicts — this script resolves them, merges, and restarts.

set -e

echo "=== Step 1: Stop all agents ==="
python references/scripts/start_team.py --stop --all 2>/dev/null || echo "  (agents may not be running — continuing)"
echo ""

echo "=== Step 2: Ensure we're on main and up to date ==="
git checkout main
git pull
echo ""

echo "=== Step 3: Resolve merge conflicts on the PR branch ==="
git checkout squidsquad/task/6126
git merge main
echo ""
echo ">>> If merge conflicts appear above, resolve them manually, then run:"
echo ">>>   git add -A && git commit && git push"
echo ">>>   Then re-run this script from Step 4 (comment out steps 1-3)."
echo ">>> If no conflicts, continuing..."
echo ""

echo "=== Step 4: Push resolved branch ==="
git push
echo ""

echo "=== Step 5: Return to main ==="
git checkout main
echo ""

echo "=== Step 6: Merge the PR ==="
gh pr merge 6201 --squash --delete-branch
echo ""

echo "=== Step 7: Pull merged code ==="
git pull
echo ""

echo "=== Step 8: Recompose all agent templates ==="
python references/scripts/compose.py deploy-all
echo ""

echo "=== Step 9: Start harness + agents ==="
python references/scripts/start_team.py --all
echo ""

echo "=== Done ==="
echo "QA will now verify the 13 runtime TCs automatically."
echo "Remove blocked:human-action label:"
echo "  gh issue edit 6126 --remove-label blocked:human-action"
