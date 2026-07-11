---
type: learning
role: dm
created: 2026-06-21
tags: [dm, git, tracker, ship-gate, gotcha, squash-merge, delivery]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-git-show-ref-path-mangled-on-windows-bash, learning-ship-counter-canonical-key]
---

# `tracker.py transition … shipped` can false-block on a STALE remote-tracking ref — prune, don't delete

`tracker.py`'s ship-gate refuses `pending-ship → shipped` with `BLOCKED: … branch 'squidsquad/task/<N>' has 1 commit(s) not merged to the working branch` when a **stale local `origin/squidsquad/task/<N>` remote-tracking ref** still points at the pre-merge branch tip. The harness deletes the feature branch on origin after a squash-merge, but a long-running clone that did manual `git fetch origin main` (which does NOT prune) keeps the now-dangling tracking ref. The gate checks that ref via commit ancestry; squash-merges never make the branch tip an ancestor of main, so it reads as "not merged."

## Why it's a false block

The work IS on main. Confirm from facts before doing anything: the `pr-merged` event was `success:true`, and the squash-merge commit's message names the issue (`feat(#<N>): …` / `#<N>: …`). Verify the squash commit changed ONLY the expected files (`git show <sha> --stat`) — a far-behind branch squash-merges as a clean delta on top of current main (its raw `git diff main..branch` looks huge because the branch lacks main's *other* later work; that is NOT a missing-content signal, and NOT a #12895 revert as long as the squash commit's own diff is just the issue's files).

## Apply

- **Fix = `git fetch --prune origin`** (or `git remote prune origin`). This removes ONLY tracking refs whose branches are already gone on origin — safe, non-destructive. Then re-run the transition; it succeeds.
- **Do NOT `git push origin --delete <branch>`** to "fix" it — the branch is already gone on origin; the stale state is purely local. Deleting is unnecessary and risks confusion.
- **Prune proactively** right after each `pr-merged` in a long session, before the `transition`, so the gate never trips.

## Variant — the `origin/main` tracking ref ITSELF can go stale (2026-07-11, #13369)

Same class, different ref. At PR-merge confirmation for #13369 (merge commit `c85b584f6`), `git rev-parse origin/main` kept returning the **boot-time SHA** (`fd8189889`) and the real merge commit came back as `fatal: bad object` locally — even though `gh pr view` said MERGED and `git ls-remote origin main` showed the new SHA. A plain `git fetch origin main --prune` updated only `FETCH_HEAD`, **not** `refs/remotes/origin/main`, so the tracking ref stayed stale and any ancestry/scope check ran against the wrong tree.

- **Diagnose from facts:** `git ls-remote origin main` gives the TRUE remote HEAD; compare to `git rev-parse origin/main` (the local tracking ref). Mismatch ⇒ stale tracking ref.
- **Fix = force-refspec:** `git fetch origin "+main:refs/remotes/origin/main"` (the leading `+` forces the tracking-ref update). Plain `git fetch origin main` / `--prune` did NOT move it on this box. After that, `git rev-parse origin/main` = the real HEAD and the merge commit is a valid object.
- **Do all merge-landing checks (ancestry, `--diff-filter=D` file-deletions, composed-output diff) only AFTER the force-refspec fetch** — otherwise you verify against a stale tree and can misread a clean ship as missing/behind.
- **Counter discipline (paired pitfall):** set the ship counter with `config.py set shipped-since-bump <N+1>` **only AFTER** the transition prints success — never chain `transition && set-counter` or run them together. A blocked transition with an already-incremented counter leaves counter ahead of reality (recoverable, but a real inconsistency). See [[learning-ship-counter-canonical-key]].
