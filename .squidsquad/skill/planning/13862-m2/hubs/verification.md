---
type: system
tags: [testing, verification, qa]
created: 2026-09-26
updated: 2026-09-26
status: active
owner: shared
community:
subcommunity:
last_optimized:
---

# Verification

_Hub note (VAULT-ARCH 3.2): connective anchor for this subsystem. Keep it a
map, not an essay -- galaxy leaves carry the knowledge; this note carries
the links._

## What It Is

The verifier lane and the test machinery that gates it: AC-derived test plans, the full static gate, comprehension (CQ) specs and their staleness baseline, and test hygiene (isolation from live state and the live harness).

## Key Files

`tests/run_tests.py`, `tests/comprehension/`, `references/scripts/comprehension_staleness.py`, `references/sub-skills/roles/verifier/`

## Knowledge Map

- [[decision-comprehension-test-pipeline]]
- [[decision-deterministic-testing]]
- [[decision-tui-headless-render-verification]]
- [[learning-audit-scope-and-source-of-truth]]
- [[learning-background-verification-pipe-truncation-masks-verdict]]
- [[learning-bare-run-tests-mutates-real-tracker-verify-after-taskstop]]
- [[learning-branch-checkout-mid-background-test-corrupts-results]]
- [[learning-canonical-verifier-merge-is-harness-post-merge]]
- [[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]]
- [[learning-confirm-merge-landed-before-pending-ship-transition]]
- [[learning-cq-applies-to-launcher-injected-prompts]]
- [[learning-cq-artifacts-commit-after-pr-merges-not-before]]
- [[learning-create-test-environments]]
- [[learning-default-port-fallback-is-live-egress-trap-in-tests]]
- [[learning-edit-shared-fragment-run-full-static-gate]]
- [[learning-fail-open-claims-need-real-reader-tests]]
- [[learning-fix-inverting-an-invariant-is-a-regression]]
- [[learning-gate-collection-abort-masks-reds]]
- [[learning-gh-pr-edit-broken-use-gh-api-patch]]
- [[learning-git-ops-run-pins-repo-root-ignores-chdir]]
- [[learning-git-ops-tests-patch-repo-root-not-chdir]]
- [[learning-git-show-ref-path-mangled-on-windows-bash]]
- [[learning-in-process-handler-daemon-os-exit-kills-test-suite]]
- [[learning-in-process-import-resolution-test-contaminates-suite]]
- [[learning-merge-mechanism-fix-cannot-protect-its-own-landing-commit]]
- [[learning-prove-regression-test-fails-pre-fix]]
- [[learning-push-branch-before-triggering-harness-merge]]
- [[learning-qa-boot-pickup-must-not-transition-pending-test-to-in-progress]]
- [[learning-quarantine-clear-triage-stale-vs-blocked]]
- [[learning-raw-pytest-shows-known-failures-use-run-tests-static]]
- [[learning-read-all-comments-before-merge-not-just-transition]]
- [[learning-recompose-and-config-carry-across-checkout]]
- [[learning-reexecute-evidence-after-verifier-session-loss]]
- [[learning-reverify-transition-blocked-by-own-prior-reject]]
- [[learning-shared-fragment-reword-stales-specs-beyond-the-issue]]
- [[learning-shell-out-provisioning-has-three-sharp-edges]]
- [[learning-sibling-pr-additive-test-conflict-keep-both]]
- [[learning-silent-gate-inertness-masks-format-drift]]
- [[learning-single-static-gate-red-may-be-flake-rerun-before-reject]]
- [[learning-squash-drops-newest-commits-of-ahead-branch]]
- [[learning-suite-exit-code-not-proof-of-all-pass]]
- [[learning-test-pollution-real-clone-state]]
- [[learning-tests-must-not-mutate-shared-live-state]]
- [[learning-trivial-append-conflicts-still-route-to-worker]]
- [[learning-verifier-verdict-may-be-off-forge-confirm-before-routeback]]
- [[learning-verify-absent-claims-need-fresh-fetch-all-refs]]
- [[learning-verify-combined-state-when-branch-behind-main-shares-files]]
- [[learning-verify-deletion-task-by-repo-wide-consumer-sweep]]
- [[learning-verify-instruction-premises-against-code-not-just-comprehension]]
- [[learning-verify-squash-diff-additions-only-behind-branch]]
- [[pattern-model-router-architecture]]
- [[pattern-parallel-axis-audit]]
- [[pattern-prove-side-effect-absence-via-live-state-snapshot]]
- [[pattern-replay-fix-against-real-incident-not-just-mocks]]
- [[pattern-resolve-config-against-live-install-not-test-fixture]]
- [[pattern-retroactive-verify-emergency-fixes-on-main]]
- [[pattern-trace-data-reads-not-just-grep-literal-strings-for-leakage-claims]]
- [[pattern-update-stale-test-on-behavior-reversal]]
- [[pattern-verify-composed-output-with-main-landing-state-applied]]
- [[pattern-verify-egress-guard-on-the-wire]]
- [[pattern-verify-liveness-lifecycle-with-independent-runtime-probe]]
- [[pattern-verify-new-shipped-file-in-installer-manifest]]
- [[pattern-verify-unmocked-paths-stubbed-by-units]]
- [[pattern-windows-utf8-subprocess]]

## Changelog

- **2026-09-26** — hub authored at vault v2 distillation (#13862).
