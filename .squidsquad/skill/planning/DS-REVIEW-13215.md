# Code Review — #13215 (deploy-pull survives a dirty clone tree)

Reviewer: Sonnet subagent (DeepSeek degenerate sub-threshold all session → Sonnet per auto-fallback). Fleet-critical deploy-path lens (#13158/#13167/#13197/#13036/#12906 history).

## Verdict: NO_BLOCKING_FINDINGS

### Verified clean
- **#13167 no-op-stash guard** faithfully replicated (_stash_ref before/after; only pop a stash we created) — no ancient-stash splatter.
- **#13045 conflict-marker handling** faithful (diff --diff-filter=U → checkout HEAD per path → drop) — no markers leak into the tree to break the subsequent compose.
- **Genuine merge conflict** still fails → (False) → §11 recovery (not swallowed).
- **--no-rebase pre-merge abort** reasoning holds: a dirty-tree "would be overwritten" abort happens BEFORE merge start (no MERGE_HEAD), so stash+retry is correct; a first-pull genuine conflict leaves MERGING → `git stash` refuses → (False, "stash-failed") → recovery.
- **Option A** (replicate in harness via _git_in_clone) correctly chosen over parameterizing git_ops.pull with a cwd — keeps blast radius off the every-agent pull path. Replication faithful across every seam.

### MEDIUM (FIXED)
On the genuine-conflict RETRY path, the retry pull leaves the clone in MERGING state (MERGE_HEAD + markers); _safe_stash_pop_in_clone would then misread the merge's unmerged files as a stash-pop conflict, DROP our stash, and leave MERGE_HEAD → next deploy's `checkout main` fails → recurring deploy-error loop until manual `git merge --abort`. **Fix:** added `git merge --abort` on the retry-failure branch BEFORE restoring the stash (harmless no-op when no merge in progress). Test updated to assert abort is called and precedes the stash pop.

### LOW (accepted, docstring-mitigated)
Replication drift risk: a future fix to git_ops._safe_stash_pop must be ported to _safe_stash_pop_in_clone. Docstrings name the mirror relationship; no automated guard. Acceptable for the blast-radius win of Option A.

### Follow-up (out of scope, to file)
The reviewer noted the identical MERGING-state-after-failed-pull gap exists in **git_ops.pull** (the every-agent path) — pre-existing, not introduced here. Fixing it is a separate slice (higher blast radius); noting on #13215 for triage rather than folding in.
