---
name: learning-merge-driver-defeated-by-delete-not-modify
description: git's merge=ours/merge=union .gitattributes protection silently does NOT apply when the incoming side deletes the path entirely (vs modifies it) — the custom driver is never invoked, and no conflict is surfaced.
metadata:
  type: learning
---

# `merge=ours`/`merge=union` only protects modify-vs-modify — a modify-vs-DELETE silently defeats it, with no conflict

**Observed live 2026-07-11 (~19:00Z DM session).** A routine `git merge origin/main --no-edit` (incorporating a worker's squash-merged PR) silently deleted `.squidsquad/.ship-counter` (canonical ship-counter, gone entirely) and truncated `.squidsquad/dm/working-state.md` (798→183 lines) + `.squidsquad/dm/doc-scan-state.json` back to a ~3-week-old snapshot, and deleted 8 vault galaxy notes outright. `git status` showed these as plain `M`/`D` — **no conflict markers, no `UD`/`AA`, nothing to flag it as unusual.**

**Root cause, confirmed via `git check-attr` + `git config`:** `.gitattributes` correctly declared `merge=ours` for `.squidsquad/.ship-counter` + `.squidsquad/*/working-state.md`, `merge=union` for `.squidsquad/vault/galaxy/*.md`; `git config merge.ours.driver` correctly resolved to `true`; `git check-attr merge -- <path>` correctly resolved `ours`/`union` for every affected path. **None of it fired.** The incoming side's history (a long-diverged worker branch, eventually squash-merged) had at some point **deleted** these paths rather than modifying their content. A per-path content merge driver is only invoked when git's tree-level 3-way merge sees a genuine content-vs-content conflict (both sides have a blob needing a real merge). When one side has **no blob at all** for the path, git's modify/delete resolution runs first and independently of any `.gitattributes` merge driver — and in this case resolved by silently taking the delete, discarding the other side's modifications, with zero signal.

## Why this matters more than the sibling gotcha

[[learning-config-merge-ours-drops-concurrent-changes]] already documented that `merge=ours` can silently drop a **concurrent modification** — bad, but bounded (stale content, not gone). This is the strictly worse failure mode: a concurrent **delete** on the incoming side defeats the protection **entirely**, and the result looks like an ordinary clean merge. The only reason this was caught was an incidentally-suspicious `pr-merged` event whose `files_changed` payload happened to list DM-owned paths, prompting a manual investigation before push.

## How to apply

- **Never trust `.gitattributes` merge=ours/union to protect against a deletion on the other side** — it only guards modify-vs-modify. A deletion anywhere upstream in the incoming branch's own history (however it got there — a stale conflict resolution, a bad `git checkout --`, an old fork-point) propagates straight through, silently, on your next merge.
- **After any merge that touches a wide/old worker branch (squash-merged PRs especially), spot-check your own protected files' line counts / existence** before pushing: `wc -l .squidsquad/dm/working-state.md`, `cat .squidsquad/.ship-counter`, and a quick `ls` on `.squidsquad/vault/galaxy/` against what you expect. Do this **especially** when a `pr-merged` event's `files_changed` list includes paths outside the PR's stated scope — that's the tell.
- **If a regression is found mid-merge (before the merge commit is finalized):** restore each affected path from your own last-known-good commit (`git show <last-good-sha>:<path> > <path> && git add <path>`), verify via `git diff --stat <bad-incoming-sha> HEAD` that the restoration exactly mirrors the earlier deletion, then complete the merge commit and push.
- **If already pushed:** same restoration, as a follow-up commit; also file a high-severity issue (see #13556) so the actual root cause on the *incoming* side (why did that branch delete these paths?) gets investigated, since the merge-side fix here is a symptom patch, not the cure.
- Cross-ref [[learning-commit-before-merge-when-inheriting-dirty-behind-clone]] (git refuses to even start a merge when your OWN tree is dirty) — this is the sibling case where the merge starts fine but the *result* is wrong.
