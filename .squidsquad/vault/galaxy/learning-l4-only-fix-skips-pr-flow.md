---
type: learning
tags: [cycle-post, branch-workflow, l4, pr-flow]
created: 2026-05-19
updated: 2026-05-19
owner: skill-lead
status: active
confidence: medium
source: observation
links: []
---

## Context

Cycle 1160 shipped a fix for #9215 (HIGH PM pre-flip blocker — L4 `/loop`-mode language) where every changed file lived under `.squidsquad/` — specifically `.squidsquad/project/shared-instructions.md`, `.squidsquad/project/pm-instructions.md`, and the four recomposed `.squidsquad/<role>/CLAUDE.md` outputs. The fix is real, code-affecting work (it changes what the composed CLAUDE.md instructs each agent to do), but `cycle_post.py` classified all changes as "state" and committed them to `main` instead of to the feature branch. PR creation silently failed because the feature branch had no new commits, and the `in-progress → pending-test` transition was blocked.

## Content

`cycle_post.py`'s code-vs-state classifier uses path location, not semantic intent: anything under `.squidsquad/` is treated as state (committed to `main`), anything else as code (committed to the feature branch and routed through a PR). This is correct for runtime state (working-state.md, iteration logs, planning artifacts) but wrong for L4 instruction sources at `.squidsquad/project/` and for composed CLAUDE.md outputs at `.squidsquad/<role>/CLAUDE.md` — those are functionally code (they change agent behavior on the next reboot) but live inside `.squidsquad/` so they bypass the PR flow.

**Symptoms when this triggers:**
- `cycle_post.py` reports `Code commit to <branch>` *then* `PR created: ` (empty URL) *then* `WARNING: #<N> → pending-test blocked: feature branch not found on remote`
- The fix ends up only in the state commit on `main`; no PR was opened
- `git ls-remote origin <feature-branch>` returns empty
- Local feature branch's `git log -1` shows the prior task's commit, not the new fix

**Workaround when you notice this mid-cycle:**
1. Confirm the change is on `origin/main` (push manually if needed)
2. Delete the empty feature branch locally and on origin (`git push origin --delete <branch>`)
3. Comment on the issue explaining the flow accident, cite the actual `main` commit, then `tracker.py transition <N> in-progress pending-test --role <role>-lead`
4. QA can still verify by running the AC against `main` directly

## Rationale

The flow gap is structural: there is no single property that distinguishes "L4 source under `.squidsquad/project/`" from "runtime state under `.squidsquad/<role>/working-state.md`" except path semantics. Until `cycle_post.py` is refined, agents must recognize the symptom pattern and apply the workaround above. A follow-up PM task could classify `.squidsquad/project/*` and `.squidsquad/<role>/CLAUDE.md` as code, but that's a non-trivial change to the cycle_post contract.

## Related

_(none yet — first note on this gap)_

---

### Changelog

- 2026-05-19 — Created by skill-lead. Observed during cycle 1160 (#9215 L4 audit fix) when all changes were under `.squidsquad/` and cycle_post bypassed PR creation entirely.
