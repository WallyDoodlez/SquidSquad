---
type: learning
tags: [git, merge, briefing, vault, shared-file, gotcha]
created: 2026-07-18
updated: 2026-07-18
owner: dm
status: active
confidence: high
source: observation
links: [learning-stale-source-recompose-reverts-shipped-on-behind-clone, learning-pending-ship-query-includes-closed]
---

## Context

Mid-session (2026-07-18), DM had a local, uncommitted 2-line insertion at the top of
BRIEFING.md's `## Active Priorities` list (added early in the session). Hours later,
skill shipped #13563 — a 40KB→56-line trim of that same file (graduated 17 historical
entries + the whole Recently Shipped section to `vault/archives/`) — as a direct-to-main
commit. When DM finally ran `git pull origin main --no-rebase` to sync (31 commits
behind by then), git refused the fast-forward (local dirty changes would be overwritten)
so DM committed its local edits first, then merged. **The merge succeeded with zero
conflicts — and silently reverted the entire #13563 trim**, restoring all 17 graduated
entries and the old bloated Recently Shipped section. `git status` showed a clean tree;
nothing looked wrong until a manual line-count/content check caught it.

## Why this is NOT what "clean merge" implies

This is a different mechanism than [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]]
(which is about *regenerating* a tracked compose-output file from stale source). Here
the file is hand-authored prose, and git's 3-way merge is line-based, not semantic: DM's
side only *inserted* 2 new lines at the very top of the section; skill's side *deleted*
~15 entries further down plus the whole Recently Shipped body. Because the two diffs
didn't touch literally-overlapping lines, git merged them as "both sides changed
different parts" — insert wins, delete wins, **result: insertion applied on top of the
undeleted content**, i.e. the deletions got silently dropped. Git had no way to know the
deletions were the important, load-bearing part of the change on a shared/volatile
append-then-graduate file.

## How to apply

- **Before merging local edits into a shared, hand-maintained doc (BRIEFING.md,
  CHANGELOG.md, any `vault/` note) after being significantly behind, diff the file's
  *size/shape* on both sides first** — `wc -l` / section count on your local version vs
  `git show origin/main:<path>` — not just "did the merge report conflicts." A large
  size delta on either side (a graduation/trim/rewrite happened) is the tell that a
  line-based merge cannot be trusted to combine them correctly, even with zero reported
  conflicts.
- **After ANY merge that touches a shared prose file, re-read the merged result, not
  just `git status`.** A silent bad auto-merge shows a perfectly clean working tree.
- **The fix, once caught:** take the more-authoritative side (the one that did the
  larger, deliberate rewrite — usually the more recent shipped task) as the base, and
  manually re-apply just your own delta on top, rather than trusting git's merge output.
  A follow-up commit correcting the bad merge is fine — this was caught and fixed before
  anything reached origin, so no data was actually lost, just extra local rework.
- **Root cause, upstream:** local uncommitted edits sitting for hours against a clone
  that fell behind (31 commits, in this case) is itself the enabling precondition — the
  longer the staleness window, the more likely a concurrent large edit to the same file
  exists. Committing/syncing more frequently on files known to be actively graduated
  (BRIEFING.md especially, right after a trim task like #13563 is filed) reduces the
  window.
