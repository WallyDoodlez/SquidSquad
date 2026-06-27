# ARCH-DOC-RECONCILE-13298 — planning + ground truth

Task: #13298 (role:pm). Reconcile TRDs with the SEV-1 (#13271) merge-safety + sync-discipline cluster. Doc-first + DS-audit. Pure docs.

## Ground truth (cross-checked vs code, 2026-06-27 — NOT memory)

### #13271 — pre-merge behind-count guard (git_ops.py)
- Lives in `git_ops.pr_merge` (the agent-invoked merge path: verifier auto-merge / DM ship), NOT the harness `/merge` endpoint. Distinct code paths — document the guard where it lives + note relationship to HARNESS-ARCH §4.5 `/merge`.
- `MERGE_MAX_BEHIND_DEFAULT = 50`; env override `SQUIDSQUAD_MERGE_MAX_BEHIND` (non-negative int).
- `_pr_behind_by(pr)` uses GitHub compare API `behind_by` field (authoritative).
- Refuse squash-merge when branch behind base > threshold. **Refuse-only**, fires BEFORE any `gh pr merge` (main never mutated). **Fail-OPEN** when behind_by undeterminable (proceeds). **Squash-strategy only** (other merge strategies unguarded).
- Motivation: #13271 SEV-1 — squash from ~154-behind clone reverted ~155 commits / 194 files.

### #13285 — post-merge scope-audit (git_ops.py `_post_merge_scope_audit`)
- Runs AFTER a successful merge. Computes `deleted - declared`: files the squash commit DELETED (`git show --diff-filter=D`) that the PR never declared (`gh pr view --json files`). Non-empty = stale-tree mass-revert signature.
- **ALWAYS**: detect + (on violation) print loud SCOPE VIOLATION + post append-only incident comment with evidence + exact remediation (`git revert --no-edit <sha> && git push`).
- **Auto-revert is OPT-IN, DEFAULT OFF** (`SQUIDSQUAD_MERGE_AUTO_REVERT=1`). Shipped "defused" so detection runs in production before the destructive action is trusted. (CORRECTION vs task body's loose "auto-revert on mismatch".)
- **FAIL-SAFE**: any audit uncertainty (gh/git error, unresolved merge SHA, undeterminable declared set) → warn + return WITHOUT reverting. Never raises (never breaks merge flow).
- **GitHub-only**: uses gh + GitHub fields; pr_merge returns early on non-GitHub forge backends before this runs.
- **SCOPE LIMIT (document honestly):** this is the file-DELETION net (the #13271 mass-revert class). The **ahead-DROP variant (#13280** — a squash that omitted the branch's newest ADDITIONS) is a missing-addition, not a deletion → OUT of this audit's scope; tracked separately. So a residual gap remains.

### Relationship / layering (the corrected model from this session)
- L1 universal norm (#13291, SHIPPED): every agent commits to shared git repo → be-current-before-integrate; merge, never overwrite. The git-repo sibling of the already-universal forge-read-before-acting rule (AGENT-RUNTIME §6).
- Dev mechanics (#13286, SHIPPED): sync-before-start + sync-before-merge on feature branches (dev-specific specialization).
- Mechanical backstops (#13271 + #13285, SHIPPED): agent-agnostic in git_ops merge path.
- Developer-domain sub-layer (#13287, PARKED): "a worker isn't always a dev" — possible tier between L2 worker-role and L3 stack-variant. Open/undecided.

## Edit plan (per doc)
1. **HARNESS-ARCH.md** — extend §4.5 (PR merge endpoint) with a subsection on the git_ops.pr_merge safety guards (#13271 behind-count + #13285 scope-audit), being explicit that they live in the agent merge path (git_ops), the auto-revert default-OFF, fail-open/fail-safe semantics, GitHub-only, and the #13280 deletion-only scope gap. Update §1 changelog/version banner.
2. **AGENT-RUNTIME.md** — add the L1 universal sync/merge norm near §6 (forge source of truth) + git-activity (§ ~330). Note dev mechanics (#13286). #13291 is SHIPPED so document as landed.
3. **COMPOSE-ARCHITECTURE.md** — light note: developer domain sub-layer open question (#13287, parked).

## Gates
- DS-audit: internal-consistency + cross-pair HARNESS-ARCH<->AGENT-RUNTIME → verdict artifact REVIEW-13298-DEEPSEEK.md.
- No new drift; update cross-refs + changelog banners.
- Pure docs (PM lane).

## Status
- [x] Ground truth gathered (code cross-checked)
- [ ] HARNESS-ARCH §4.5 edit
- [ ] AGENT-RUNTIME L1-norm edit
- [ ] COMPOSE-ARCH dev-domain note
- [ ] DS-audit + cross-pair
- [ ] changelog/version banners
