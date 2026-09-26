
# Harness

_Hub note (VAULT-ARCH 3.2): connective anchor for this subsystem. Keep it a
map, not an essay -- galaxy leaves carry the knowledge; this note carries
the links._

## What It Is

The Python supervisor that owns agent lifecycle: spawn/restart via the intent state machine, health polling, the event bus, and the REST API on :7373. Lifecycle authority lives here -- no sentinel files.

## Key Files

`references/scripts/harness.py`, `references/scripts/thin_launcher.py`, `.squidsquad/.harness-state.json`, `docs/HARNESS-ARCH.md`

## Knowledge Map

- Liveness/PID: [[decision-pid-primary-liveness]], [[pattern-verify-liveness-lifecycle-with-independent-runtime-probe]]
- Restart/supervision: [[decision-watchdog-supervisor]], [[decision-reboot-kills-child]], [[decision-self-healing-sentinel]]
- Merge gating: [[learning-harness-merge-gate-caches-git-ops-module]], [[learning-harness-only-ship-restart-required-is-noop]]

## Distilled leaves (vault v2)

- [[decision-agents-never-stop-while-work-pending]]
- [[decision-class-vs-alias-routing-model]]
- [[decision-clone-isolation-architecture]]
- [[decision-event-bus-architecture-redesign]]
- [[human-profile]]
- [[learning-activity-liveness-redispatch-must-not-reset-grace]]
- [[learning-claude-code-http-hooks-block-only-command-hooks-async]]
- [[learning-default-port-fallback-is-live-egress-trap-in-tests]]
- [[learning-deploy-pull-block-divergence-recover-by-merge]]
- [[learning-doc-first-for-architecture-changes]]
- [[learning-ead-status-routing-and-back-transition-dedup]]
- [[learning-fail-open-claims-need-real-reader-tests]]
- [[learning-graceful-restart-grace-timer-on-wedged-agent]]
- [[learning-guarding-a-status-machine-death-decision-needs-hold-resume-and-ceilinged-signals]]
- [[learning-harness-pr-merge-does-not-sync-local-clone]]
- [[learning-in-process-handler-daemon-os-exit-kills-test-suite]]
- [[learning-in-process-import-resolution-test-contaminates-suite]]
- [[learning-intent-clear-on-transition-not-liveness]]
- [[learning-polling-agent-reads-as-inert-on-status]]
- [[learning-requirements-txt-is-harness-runtime-scoped]]
- [[learning-restarting-intent-not-across-harness-restart]]
- [[learning-runtime-resolves-by-alias-not-role-class]]
- [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]]
- [[learning-singleton-must-refuse-not-fallback-when-canonical-port-held]]
- [[learning-stale-activity-not-dead-rule-out-limit-and-inline]]
- [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]]
- [[learning-stall-vs-deepwork-before-nudging]]
- [[learning-tests-must-not-mutate-shared-live-state]]
- [[learning-wire-format-specs-triplicated-across-trds]]
- [[pattern-model-router-architecture]]
- [[pattern-prove-side-effect-absence-via-live-state-snapshot]]

## Changelog

- **2026-09-26** — migrated to vault v2 (#13862).
