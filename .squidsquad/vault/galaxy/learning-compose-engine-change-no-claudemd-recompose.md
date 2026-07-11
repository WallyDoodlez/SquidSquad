---
type: learning
role: dm
created: 2026-06-26
tags: [delivery, compose, settings-json, hooks, reboot, scope-classification]
owner: dm-lead
status: active
confidence: high
source: observation
---

# A compose.py engine change that emits .claude/settings.json does NOT recompose CLAUDE.md — it rides the next per-clone deploy/restart

When a shipped task changes `compose.py` itself (the compose ENGINE) — e.g. the hooks-emission lane `_ensure_activity_hooks` that writes each clone's `.claude/settings.json` hooks block — classify it as **code, not a CLAUDE.md source change**:

- The composed `.squidsquad/<role>/CLAUDE.md` is **byte-identical** (the change is to settings.json emission, not instruction text) → **no `compose.py deploy` recompose of CLAUDE.md, no CLAUDE.md-reboot**.
- BUT the new settings.json behavior only materializes in a clone when compose re-runs there, which happens on that clone's **next deploy/restart**. So the effect (the new hook in `.claude/settings.json`) **rides the next per-clone restart** — fold it into the already-pending team-restart window; do NOT call it "live now."
- Do **NOT** force a `compose.py deploy` from a behind/dirty clone to push settings.json early — that is the [[learning-config-merge-ours-drops-concurrent-changes]] / stale-source-recompose hazard. Defer to the per-clone restart, which composes pull-first.

This sits between two known cases: it is not a CLAUDE.md-source recompose (which needs the isolated-worktree-at-origin/main deploy dance), and it is not a pure no-reboot code ship either — its *output artifact* (settings.json) does change, gated on restart. Example: #13213 (wire `UserPromptSubmit` activity hook), scope = compose.py + 2 tests, shipped 2026-06-26.

Related: [[learning-harness-only-ship-restart-required-is-noop]] (harness.py-only ships need a harness restart, not a recompose).
