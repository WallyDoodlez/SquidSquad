---
type: system
tags: [harness, lifecycle, architecture]
created: 2026-07-20
updated: 2026-07-20
status: active
owner: shared
---

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
