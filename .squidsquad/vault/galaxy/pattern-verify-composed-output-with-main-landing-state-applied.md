---
type: pattern
tags: [verification, compose, l4, branch-workflow, main-landing, dm-arch]
created: 2026-06-18
updated: 2026-06-18
owner: verifier-lead
status: active
confidence: high
source: observation
links: [learning-l4-only-fix-skips-pr-flow, pattern-resolve-config-against-live-install-not-test-fixture]
---

## Context

#12749 (DM-ARCH layered DM refactor) verification. The ACs assert behavior of the **composed** DM
(`.squidsquad/dm/CLAUDE.md`): a generic L2 spine, L4 batch-10 release policy, L3 `dm/skill` package mechanics.
But the state those ACs depend on — `config.md` alias `dm/skill`, L4 `project/dm.md`, the live `statusline.sh`,
and the recomposed `.squidsquad/<role>/CLAUDE.md` — is **`.squidsquad/` state, stripped from the feature branch by
the state-guard** and intended to land on `main` only at merge ("no fiction window" — docs+code+state land together).
So on the feature branch the composed DM still reflects the OLD model, and a naive grep of the branch's composed
output would FALSE-FAIL every composed-output AC.

## Content

**When a feature's composed output depends on main-landing `.squidsquad/` state that the feature branch strips,
verify the real post-merge artifact by applying the worker's documented main-landing diff to the working tree,
recomposing, and inspecting the composed output — then revert before leaving the branch.**

Procedure:
1. Read the worker's durable `§main-landing` spec from the issue discussion (the exact config/L4/statusline diff).
2. Apply it to the working tree on the feature branch (`config.py set`, edit the L4 file, `cp references/X → .squidsquad/X`).
3. `compose.py deploy-all`; grep/inspect the composed `.squidsquad/<role>/CLAUDE.md` against each AC. Test BOTH the
   policy-present case AND the no-L4 default (move the L4 file aside, recompose → assert generic-default behavior).
4. For the same reason, expect 2 classes of branch test failures that are **artifacts, not gaps**:
   - statusline / `references-vs-live` byte-identical tests fail because the live `.squidsquad/` copy is main-landing →
     re-run after the documented live-copy sync; they pass.
   - Always re-confirm a suspicious failure on **clean origin/main** (via `git worktree add /tmp/x origin/main`) to
     separate pre-existing failures from real regressions before blocking.
5. **Revert all working-tree mutations** (`git checkout HEAD -- .squidsquad/...`) before switching branches — the
   main-landing state must NOT be committed to the feature branch (that recreates the fiction window).

The verdict stays evidence-based: it rests on YOUR inspection of the composed artifact, not the worker's claims. But
make the ship **contingent on the main-landing batch landing in the same window as the merge** explicit in the verdict
and QA-RESULTS — carry it to DM, since that's the only thing keeping the shipped docs honest.

See also [[learning-l4-only-fix-skips-pr-flow]] (why `.squidsquad/` composed output bypasses PR flow — the same
state/code split, from the worker's commit-routing side).
