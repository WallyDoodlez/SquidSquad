---
type: system
tags: [agent-runtime, event-mode, lifecycle]
created: 2026-09-26
updated: 2026-09-26
status: active
owner: shared
community:
subcommunity:
last_optimized:
---

# Agent Runtime

_Hub note (VAULT-ARCH 3.2): connective anchor for this subsystem. Keep it a
map, not an essay -- galaxy leaves carry the knowledge; this note carries
the links._

## What It Is

The agent side of the cycle contract: event-mode wake/drain/ack, loop-mode fallback, working-state, boot drain, the Monitor listener, and the never-stop autonomy principles.

## Key Files

`references/sub-skills/common-events/`, `docs/AGENT-RUNTIME.md`, `references/scripts/event_poll.py`

## Knowledge Map

- [[decision-agents-never-stop-while-work-pending]]
- [[decision-cycle-runner-architecture]]
- [[human-profile]]
- [[learning-claude-code-http-hooks-block-only-command-hooks-async]]
- [[learning-commit-before-merge-when-inheriting-dirty-behind-clone]]
- [[learning-commit-role-scoped-foreign-file-silent-drop]]
- [[learning-common-events-fragments-are-mode-agnostic]]
- [[learning-cycle-pre-preserves-code-wip]]
- [[learning-deploy-signal-boot-drain-residual-vs-live]]
- [[learning-monitor-persistent-do-not-rearm-per-nudge]]
- [[learning-polling-agent-reads-as-inert-on-status]]
- [[learning-resume-git-tree-is-truth]]
- [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]]
- [[learning-spawn-prompt-must-not-decide-wake-mode]]
- [[learning-stale-activity-not-dead-rule-out-limit-and-inline]]
- [[pattern-deterministic-scripts-over-prose]]
- [[pattern-operator-comms-no-internal-mechanics]]

## Changelog

- **2026-09-26** — hub authored at vault v2 distillation (#13862).
