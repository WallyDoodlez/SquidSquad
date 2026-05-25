---
type: decision
tags: [vault, subagent, model-choice, architecture]
created: 2026-05-25
updated: 2026-05-25
status: active
confidence: high
source: conversation
owner: pm
---

# Decision — Vault heavy sub-skills run on claude-sonnet-4-6

## Decision

Heavy vault sub-skills (`vault-remember`, `vault-synthesis`) execute as background subagents (Agent tool, fresh context) pinned to **`claude-sonnet-4-6`**. Light vault sub-skills (`vault-protocol`, `vault-optimize`) stay inline in the consuming agent's context.

## Rationale

- **Why offload at all**: vault-remember's per-cycle 4-gate evaluation + per-candidate dedup-check reasoning + write/skip judgment, and vault-synthesis's cross-note theme detection, consume meaningful slices of the consuming agent's main context every quiet cycle. Offloading keeps the main context lean and reduces context-pressure restart frequency.
- **Why Sonnet, not Opus**: vault reflection is pattern-matching + dedup judgment + small write decisions, not multi-step planning. Opus is overkill for this shape.
- **Why Sonnet, not Haiku**: dedup near-match calls and convergence detection across notes need more than mechanical token-matching — Haiku's been judged insufficient for the comparable skill/DM subagent spawns.
- **Consistency with existing precedent**: `[[feedback_skill_sonnet_subagents]]` and `[[feedback_dm_sonnet_subagents]]` already establish Sonnet as the standard subagent model. No reason to diverge for vault.
- **Light ones stay inline**: `vault-protocol` IS the agent's continuous read/write work — offloading is nonsensical. `vault-optimize` is a thin wrapper around `vault_optimize.py run` — no reasoning happens in-agent to offload.

## Where this lives

- [[VAULT-ARCH]] §7 (Execution model paragraph)
- [[VAULT-ARCH]] §11.5 (implementation gap — current code runs both inline; closure tracked by #10180)
- Per-sub-skill Cycle integration lines (§7.1–§7.4) name the lane and the structured return contract for the background lane.

## Out-of-scope here

- Migrating to event-driven invocation (separate gap, §11.4)
- Changing the gate algorithms or detection logic themselves
- Reconsidering which sub-skills count as "heavy" — that judgment is in §7 and not under review

## Changelog

- 2026-05-25 — Created by pm-lead. Decision locked during VAULT-ARCH §7+§11.5 polish.
