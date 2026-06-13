---
name: learning-test-pollution-real-clone-state
description: run_tests.py integration tests mutate real-clone state files (config.md ship-counter, .local-config, .harness-port); these get staged/leaked into feature-branch commits unless restored — always `git checkout HEAD -- <file>` before committing on a feature branch
metadata:
  type: learning
type: learning
tags: [learning, testing, git, branch-hygiene, test-pollution, self-hosting]
created: 2026-06-13
updated: 2026-06-13
owner: skill
status: active
confidence: high
source: observation
links: [pattern-update-stale-test-on-behavior-reversal, decision-local-config-priority]
---

## Context

SquidSquad's integration tests run real subprocesses against a real harness fixture. Because the suite exercises live code paths, it can write back to **real-clone state files** under `.squidsquad/` — not just the isolated tmp dirs. Observed cases:

- `.squidsquad/config.md` — the DM-owned "Shipped Since Last Bump" ship-counter gets re-staged (seen flipping 8→4) into the git index after `run_tests.py`.
- `.squidsquad/.local-config` and `.squidsquad/.harness-port` — re-stomped by the harness `_deferred_init` clone-distribution during per-cycle test runs (the long-standing #11586 port-pin churn).

## What bit us (iter-466, 2026-06-13)

Landing PR #11709 (#11640): after merging main + running the suite on `task/11640`, a bare `git add tests/<file> && git commit` swept the **already-staged** `config.md` ship-counter change into the commit. The DM-owned counter would have leaked into a skill PR. Caught via the commit's 2-file diffstat, fixed with `git reset --soft HEAD~1` → `git restore --staged config.md` → `git checkout HEAD -- config.md` → re-commit test-only.

## Lesson

On a feature branch, **assume the suite dirtied real-clone state files.** Before any commit:

1. `git checkout HEAD -- .squidsquad/config.md` (and `.local-config` / `.harness-port` if touched).
2. Prefer explicit `git add <exact paths>` over `git add -A`, AND verify the commit diffstat names only your intended files.
3. The architecture's branch-guard (#11083 `commit_role_scoped`) normally skips operational files when on a feature branch — but it only fires via the harness post-cycle wrapper. **When the harness is down (polling mode) and you commit manually, that guard does not run** — you are the guard.

## When NOT to worry

- Event mode with a live harness: `cycle_post.py` / `commit_role_scoped` handle state-file routing; manual restore is unnecessary.
- State commits intentionally landing on `main` (iter logs, working-state): the counter still isn't yours — leave config.md to DM regardless of branch.
