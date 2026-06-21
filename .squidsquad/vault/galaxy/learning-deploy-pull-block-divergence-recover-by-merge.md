---
name: learning-deploy-pull-block-divergence-recover-by-merge
description: When deploy-error stage=pull fires with a CLEAN working tree but diverged main, recover by merging origin/main (not discarding, not rebasing).
metadata:
  type: project
---

A `deploy-error` with `stage=pull` ("Diverging branches can't be fast-forwarded") has **two distinct root causes** that need **different recoveries** — diagnose by the working tree before acting:

- **DIVERGENCE variant (this note)** — working tree is CLEAN of modified tracked files, but local `main` is N-ahead/M-behind `origin/main`. Cause: the harness committed this clone's per-session doc/state work to local main, then a teammate (e.g. dm recompose) pushed to origin before this clone's push landed → legitimate non-overlapping divergence. The harness deploy-pull is FF-only and fatals. **Recovery: `git merge origin/main --no-edit` then `git push`.** Files are non-overlapping so the merge is clean (0 conflicts). Verify `git rev-list --left-right --count HEAD...origin/main` reads `0	0` after. NEVER rebase (see [[feedback_never_rebase_merge_instead]]); NEVER discard local commits (they are real harness-committed work).

- **DIRTY-TREE variant** — working tree has modified tracked composed CLAUDE.md/.linked.md left by an agent-manual `compose.py deploy-all`. If `git diff origin/main` on those files is empty (byte-identical), discard them via `git checkout` (zero loss). See [[learning-deploy-pull-block-recover-by-discarding-composed-artifacts]].

PM is permitted to reconcile **main** (merge only) — this is not a worker-branch op. Both variants block the recompose/deploy path fleet-wide and recur every deploy-signal until reconciled. Systemic fixes: #13158 (give the harness deploy-pull a merge strategy, mirroring the #12526 launcher fix) for divergence; #13030 (retire agent-manual recompose) for dirty-tree.
