# #13862 M2 distillation manifest — operator review (M3 gate)

Nothing in the live vault has changed yet. Approving this manifest lets the skill agent run M1 (the mechanical frontmatter transform) and M3 apply, as one atomic step. Retirement is a status flip in place (`archived` / `superseded`), never a deletion, so every item is reversible.

**Totals:** 185 notes: 170 keep, 5 merge, 10 prune. There are 3 new hubs, and the 7 existing hubs get extended knowledge maps. 49 dangling wikilinks get fixed; almost all point at Claude-memory `feedback_*` names or doc names, and they are unlinked with the text kept.

**Rehearsal (scratch copy): PASSED.** The M0 count of 185 equals the sum of the dispositions. `vault_check validate` is clean, with zero broken links. See `m3-rehearsal-reconcile.json`.

**Distillation was lighter than "aggressive".** The per-cluster reviewers judged that most learnings generalize. If you want deeper pruning, name the notes (or a rule, e.g. "prune every single-incident learning older than N days that nothing cites") and the manifest will be re-cut.

## Prune (status → archived)

- `decision-pid-primary-liveness` — Self-declared ARCHIVED/SUPERSEDED by #12492 progress-based liveness; mechanism no longer runtime behavior.
- `decision-reboot-kills-child` — Wrapper/.pid/.restart-sentinel model superseded by harness intent API and thin_launcher; deprecation tracked #4792.
- `learning-comprehension-staleness-refresh-cli-silent-failure` — Single CLI-arg mistake (bare issue# vs spec filename); narrow, root-cause bug already filed as #13710.
- `learning-config-merge-ours-drops-concurrent-changes` — Explicitly superseded by #12823; config.md merge=ours removed so the described mechanism no longer exists.
- `learning-git-cat-file-ref-path-false-negative-use-ls-tree` — Single-incident, uncited tool quirk; the cross-check-surprising-git-facts lesson is already covered by other kept notes.
- `learning-harness-port-59999-is-deliberate-loop-pin` — Narrow, situational ops workaround tied to an unresolved bug; single-clone incident, doesn't generalize.
- `learning-migration-6274-cutover` — One-off completed rename migration (dev->worker, qa->verifier); cutover date passed, dual-shim mechanism retired.
- `learning-powershell-start-job-cwd` — Narrow, uncited single-incident Windows Start-Job cwd quirk from an old (2026-04-18) boot-wrapper fix.
- `learning-qa-branch-merge-workaround` — Single-incident workaround for a since-tracked QA clone branch-discovery bug (#3361); the mechanism it patches around is stale.
- `learning-trd-v2-rewrite-crossref-drift-dominant-defect` — Single-incident TRD-rewrite audit finding; niche doc-hygiene lesson not tied to any hub domain, low reuse likelihood.

## Merge (source → superseded; target body gets the merged draft in `drafts/`)

- `decision-local-config-priority` → `decision-clone-isolation-architecture` — Sub-case of clone-isolation: same #2750 clone-path incident, narrower _parse_local_config priority-order detail.
- `decision-phase-4-event-ack-lifecycle-deferred` → `decision-event-bus-architecture-redesign` — Historical deferral this decision explicitly supersedes; unique history folded into target's origin section.
- `learning-deploy-error-pull-block-recover-by-discarding-composed-artifacts` → `learning-deploy-pull-block-divergence-recover-by-merge` — Sub-case (dirty-tree variant) of the broader deploy-error stage=pull recovery family; folded into target.
- `learning-git-ops-helpers-pin-repo-root-not-cwd` → `learning-git-ops-tests-patch-repo-root-not-chdir` — Duplicate REPO_ROOT-patching technique; folds unique #13373 example and the no-op diagnostic heuristic into the target.
- `learning-tail-truncation-hides-pytest-failures-from-review` → `learning-background-verification-pipe-truncation-masks-verdict` — Sub-case of the same pipe/tail-truncation family; folds in the reviewer-blind-spot nuance and the lastfailed recovery tip.

## New hubs (`hubs/*.md`)

- `verification`
- `delivery`
- `agent-runtime`

## Also in the M1 transform (mechanical)

- The style note folds into a pattern: `style-operator-comms-no-internal-mechanics` → `pattern-operator-comms-no-internal-mechanics`. `.squidsquad/pm/planning/PLAN-STATUSLINE-V2.md` mentions the old slug; it is flagged, not rewritten.
- Drops `confidence`/`source`/`links`/`name`/`metadata`. Owner labels become their role-class. Missing status/type/created/updated are filled. `.relevance-index.json` is deleted.

## How to respond

- **Approve as-is:** say so (comment on #13862 or tell PM). The skill agent then applies it.
- **Veto items:** list the slugs and the disposition you want. Every note is vetoable.
- The vault write freeze (`Writes Per Cycle: 0`) holds until M4 unfreezes it.
