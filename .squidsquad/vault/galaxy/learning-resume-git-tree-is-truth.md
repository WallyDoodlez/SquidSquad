---
type: learning
tags: [resume, working-state, loop-mode, harness-down, cycle-post, git, 11640]
created: 2026-06-13
updated: 2026-06-13
owner: skill-lead
status: active
confidence: high
source: observation
links: [learning-pr-conflicting-flag-can-be-cosmetic, decision-branch-per-feature-workflow]
---

# On resume, the git working tree is truth — not working-state.md

**Observed (#11640, cycle 452):** booted into loop-mode (harness down). `working-state.md` said "none active — on main", but the git tree was on `squidsquad/task/11640` with **complete, uncommitted** WIP (boot_remote.py + harness.py + 9 tests) for an in-progress issue. The prior session had finished the implementation but never committed it.

**Root cause:** in loop-mode with the harness down, the `cycle_post.py` wrapper (which normally commits/pushes/writes working-state at cycle end) **does not fire** — there is no scheduler driving it. So a session can end with finished work uncommitted AND working-state un-updated. Both the commit and the state-write are wrapper responsibilities that silently no-op.

**Why it matters:** trusting working-state.md on resume would have missed shipped-but-uncommitted work, risking re-implementation or loss. The forge/issue status (in-progress) + the git tree together are the real state; working-state is a hint that may be stale.

**How to apply:**
- On every resume, reconcile `git branch --show-current` + `git status --short` against working-state.md. If they disagree, the **git tree wins** — investigate the diff before acting.
- In any harness-down / loop-mode session, do the commit + push + working-state write **manually** at cycle end; do not assume the wrapper ran.
- Before attributing a red full-suite test to your own change, isolate it (`git stash` your WIP, re-run) and grep the tracker for an existing issue — the failure may be pre-existing and already fixed/pending-ship elsewhere (here: #11657/PR #11683). See [[learning-pr-conflicting-flag-can-be-cosmetic]] for the sibling "the obvious-looking failure isn't yours" pattern.
