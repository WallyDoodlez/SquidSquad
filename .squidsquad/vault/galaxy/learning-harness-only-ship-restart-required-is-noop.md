---
type: learning
role: dm
created: 2026-06-19
tags: [delivery, harness, restart, recompose, gotcha]
owner: dm-lead
status: active
confidence: high
source: observation
---

# A harness.py-only ship triggers a restart-required that is usually a NO-OP

## Context

Delivering a ship whose diff is **`harness.py` (+ tests) only** — e.g. #12837 (eviction-marker bug), #12906 (recompose ensure-main). Two restart concerns get conflated at ship time; they are different and must be reasoned separately.

## The two restarts are NOT the same

1. **Harness restart — genuinely needed.** The *running* harness predates the merged fix, so harness-code changes only take effect after a harness relaunch. This folds into the pending harness-restart window (operator/supervised-launcher), deferred per standing operator directive. Note it in the ship comment; do NOT self-trigger.
2. **`l4-recompose` restart-required (target=dm) — usually a spurious NO-OP.** The harness emits a recompose `restart-required` after a merge regardless of whether composed output changed (the `l4_file_watcher` over-emit, #12895). A harness.py-only ship changes **no** L4/template/sub-skill source, so your composed `CLAUDE.md` does not change — there is nothing to pick up.

## How to tell it's a no-op (gate before any self-restart)

- `git status --short .squidsquad/dm/CLAUDE.md` → **empty** (composed output unchanged; cross-check `git log -1` shows last touch was an earlier unrelated commit), AND
- `/status` shows your `intent: running` (NOT flipped to restarting/stopping) → the signal is **advisory**, not a forced exit-42.

If both hold: treat as no-action, stay up, defer per operator. Do **not** self-restart. Confirmed twice (2026-06-14 no-op; 2026-06-19 #12837). The 2026-06-14 run also found `/quit` is itself a no-op in a live event-mode session — another reason not to chase the restart.

## Apply

Scope-gate every ship: harness.py-only / runtime-loaded-fragment / test-only diffs need **no recompose and no agent reboot** (see [[pattern-runtime-loaded-subskill-change-no-recompose]]); config.md/template/sub-skill-source diffs do. Distinguish the spurious recompose `restart-required` from a real one via the git-clean + intent-running gate above. Distinct failure from [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] (which is a behind-clone pushing a revert, not a benign no-op).
