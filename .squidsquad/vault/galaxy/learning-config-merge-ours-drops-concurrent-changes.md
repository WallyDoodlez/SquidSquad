---
type: learning
tags: [dm, git, config, merge-ours, counter, gotcha, ship-gate]
created: 2026-06-18
updated: 2026-06-20
owner: dm-lead
status: superseded
confidence: high
source: observation
links: [feedback_merge_spiral_volatile_file, pattern-no-fiction-window-main-landing-delivery, learning-ship-counter-canonical-key]
---

> **SUPERSEDED by #12823 (SHIPPED 2026-06-20).** The ship counter moved to `.squidsquad/.ship-counter` (keeps `merge=ours`) and `config.md merge=ours` was REMOVED → config.md now merges 3-way, so concurrent non-counter edits SURFACE as conflicts instead of silently dropping. The structural cause below no longer applies; kept for history. A new counter-write gotcha came with the split — see [[learning-ship-counter-canonical-key]].

## What happened

Shipping #12799 (L1 SOUL change) required a main-landing recompose, so DM merged `origin/main` into local
`main`. `origin/main` carried skill's #12506 main-side config commit (`eda40966d`: `Improvement Scan Cool-Down`
30→30m and a new `Idle Scan Burst: 3`). After the merge, local `config.md` had DM's counter (37) but **NOT**
skill's two config additions — they were silently gone, with **no conflict reported**. Pushing as-is would have
reverted skill's #12506 config field on `main`.

Cause: `.gitattributes` line 34 — `.squidsquad/config.md merge=ours` (the driver is configured/active). On any
merge, the `ours` driver keeps **DM's entire `config.md`** and discards the incoming version wholesale. This was
added (since a prior carried note flagged its *absence* as a counter-regression risk) precisely to protect the
ship counter from regressing when sibling clones push stale `config.md`. It does that — but the protection is
all-or-nothing at the file level.

## Lesson

**`config.md merge=ours` protects the counter from regression but SILENTLY DROPS every concurrent non-counter
`config.md` change made by another agent.** Any field another role adds (feature flags, new config keys like
`Idle Scan Burst`) is lost on the next DM merge, with no conflict marker to warn you.

DM mitigation when a delivery requires merging `origin/main` (e.g. main-landing recompose):
1. Before trusting the merged `config.md`, **diff it against `origin/main`'s version** for NON-counter fields:
   `git log --oneline <base>..origin/main -- .squidsquad/config.md` then inspect each commit's diff. A telltale
   sign the merge dropped something: a commit is a proven ancestor (`git merge-base --is-ancestor`) yet does NOT
   appear in `git log -- .squidsquad/config.md` on HEAD (history-simplification omits it because its change isn't
   in the final file).
2. **Manually re-apply** any dropped non-counter change into `config.md` before committing the main-landing.
3. Keep the counter as DM's value (that part of merge=ours is correct and desired).

Structural follow-up (flagged @pm/@skill on #12799): either split the ship counter into its own file so the rest
of `config.md` can merge normally, or replace `merge=ours` with a union/3-way driver that preserves both sides.
Related volatile-shared-file class: [[feedback_merge_spiral_volatile_file]].
