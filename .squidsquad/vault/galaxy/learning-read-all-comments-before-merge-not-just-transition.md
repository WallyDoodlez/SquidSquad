---
type: learning
tags: [verification, merge, operator-hold, process]
created: 2026-06-27
author: qa
---

# Read ALL recent comments (esp. operator holds) BEFORE merging — the unread-feedback guard only gates the transition

The verifier's flow on a pending-test item is: pick up → verify → **squash-merge the PR** → **transition to pending-ship**. The tracker's unread-feedback guard fires on the **transition** (`tracker.py transition` refuses if there are unread comments from another role) — but it does **NOT** gate the **merge**. So a merge can land on `main` before the guard ever surfaces a directive that should have stopped it.

**Observed**: 2026-06-27, #13291 (L1 universal norm). An operator HOLD ("nothing from this cluster lands in main; QA do not verify or ship") landed on the issue *after* skill shipped it to pending-test but *before* I picked it up. At pickup I read the issue body + skill's ship comment, verified, and squash-merged PR #13292 — **then** the transition guard blocked pending-ship and surfaced the HOLD. I had already violated "nothing lands in main." Corrective: git-reverted both the squash and my QA-RESULTS commit (non-destructive), pushed, confirmed the cluster left no trace on `main`, and parked the issue at pending-human-review.

**How to apply** (verifier, every pickup):
- At pickup, **read the issue's recent comment history end-to-end**, not just the latest skill/ship comment — specifically scan for **operator/PM directives** (HOLD, "do not ship", "do not verify", parking at pending-human-review, scope changes). An operator hold can land in the window between the worker's ship and your pickup.
- Treat **the merge** as the point of no easy return, not the transition. If any recent comment says hold/do-not-ship, STOP before merging — do not rely on the transition guard to catch it.
- If you discover the directive only after merging: **revert promptly and non-destructively** (`git revert` the squash + any of your own commits on top, never force-push — exactly the "merge, never overwrite" L1 norm), push, verify the change is absent from `origin/main`, then park the issue per the directive and acknowledge transparently (what you did, the revert SHA, the root cause).

Related: [[learning-verify-squash-diff-additions-only-behind-branch]], [[feedback_verify_against_planning_artifacts]], [[feedback_verify_fresh_fetch_all_refs]].
