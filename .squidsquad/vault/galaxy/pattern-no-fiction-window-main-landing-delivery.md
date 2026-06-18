---
type: pattern
tags: [delivery, dm, main-landing, branch-workflow, compose, no-fiction-window, dm-arch]
created: 2026-06-18
updated: 2026-06-18
owner: dm-lead
status: active
confidence: high
---

# Pattern: no-fiction-window main-landing delivery

When a refactor changes both source (in the PR) **and** install-local `.squidsquad/` state (config.md, L4 `project/<role>.md`, live `statusline.sh`, composed `CLAUDE.md`), the worker **strips the `.squidsquad/` state from the feature branch** and posts it as a verbatim "main-landing spec" in the issue Discussion. DM applies that state **on main in the same window as the merge** — never before (the docs would describe a system that isn't live = "fiction window"), never as a deferred follow-up (main would carry source that nothing wires up).

## DM procedure
1. Merge the PR → main (harness `/merge`, squash); `git pull`.
2. Apply the stripped state on main, in order: config changes (`config.py set …`) → L4 `project/<role>.md` diff → sync live `statusline.sh` from `references/` (it's a plain copy — they're identical when in sync) → `compose.py deploy-all`.
3. Verify the composed output matches the verifier's AC evidence (grep the composed `CLAUDE.md` for the expected anchors/sections) **before** committing.
4. One commit for all `.squidsquad/` state; push; then transition `pending-ship → shipped`.

## Gotchas
- `compose.py deploy-all` recomposes every role but only the roles whose sub-skills changed show a file delta — that's expected, not a miss. (DM-ARCH #12749: only dm + qa CLAUDE.md changed; pm/skill were no-ops.)
- The verifier states this as an explicit **ship-contingency** ("verdict holds only if the main-landing batch lands same window"). Treat each contingency line as a delivery checklist item.
- A `restart-required` event fired by `l4_file_watcher` on compose success is **advisory** — check the agent's harness *intent* (`/status`). `intent: running` ⇒ not an authoritative restart; honor any standing operator reboot-defer instead of self-restarting. See [[learning-restarting-intent-not-across-harness-restart]].

Verification-side complement: [[pattern-verify-composed-output-with-main-landing-state-applied]]. Bump/release semantics still gate on operator signal: [[feedback_bump_requires_pm_signal]].
