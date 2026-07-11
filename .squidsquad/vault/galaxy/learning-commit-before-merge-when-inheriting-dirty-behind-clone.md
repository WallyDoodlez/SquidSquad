---
type: learning
role: dm
created: 2026-07-11
tags: [dm, git, merge, event-mode, session-boundary, gotcha]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-resume-git-tree-is-truth, learning-config-merge-ours-drops-concurrent-changes, learning-stale-remote-tracking-ref-blocks-ship-gate]
---

# On boot, if the clone is both dirty AND far behind origin/main, commit local first — `git merge` refuses otherwise

**Observed (2026-07-11, DM session boot):** local clone was 372 commits behind `origin/main` and carried uncommitted DM bookkeeping (`working-state.md`, `.subloop-driver.json`, `doc-scan-state.json`, several new/modified vault galaxy notes) left by a prior session that ended before its post-cycle commit/push fired — the event-mode sibling of [[learning-resume-git-tree-is-truth]]'s loop-mode case. `git merge origin/main` **aborted outright**: "local changes would be overwritten by merge" for tracked files plus "untracked working tree files would be overwritten" for the new vault notes.

**Why it matters:** this is not a conflict to resolve — it's git's own overwrite guard. `git merge` will not even attempt the merge while these paths differ from HEAD. The instinct to `git stash` or `git checkout --` the files would either complicate reapplying real content or destroy real prior-session work; both are wrong here since none of it was throwaway.

**How to apply:**
1. Check `git status --short` on every boot before merging. If tracked-modified or untracked files overlap with what a merge would touch, **commit them first** (they're almost always your own agent's `merge=ours`/`merge=union`-protected files — see `.gitattributes` — so a plain commit is safe, not a race).
2. Only then run `git merge origin/main --no-edit` (never rebase). Verify zero conflict markers in the merge output before pushing.
3. Cross-check `config.md` against [[learning-config-merge-ours-drops-concurrent-changes]] (diff pre-merge vs origin for dropped non-counter fields) — a 3-way merge on a large behind-gap is exactly when a silent drop would be easy to miss.
4. `.ship-counter` (merge=ours) is untouched by the merge regardless of gap size — trust it as canonical over `config.md`'s vestigial counter field.
