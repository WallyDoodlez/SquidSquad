---
type: style
tags: [operator-comms, style, user-facing, plain-language, 13162]
created: 2026-06-21
updated: 2026-06-21
owner: pm
status: active
confidence: high
source: conversation
---

**Operator-facing communication value** (operator, emphasized 2026-06-21 while specing #13162 verbose mode). In the default (non-verbose) posture, agents must expose **zero internal mechanics** — never a term that requires SquidSquad-internal knowledge to parse: `acknowledgment`/ack, cursor, event, drain, care-filter, nudge, transition, GET/POST, etc. "No operator knows what 'acknowledgment' means."

Instead, describe **outcomes** in plain language: "Activity detected — nothing needs attention" rather than "acked 4 events / queue drained". The operator should never see a word they'd need to understand the framework's internals to follow.

This is the principle behind the L1 "User-Facing Communication" jargon-ban and the [[#13162]] verbose-mode feature (ON = full internal narration for operators who WANT the mechanics; OFF/default = mechanics-free outcome language). Applies to all operator-facing surfaces (terminal output, README, status lines), not just the no-action-wake one-liner. When designing any operator-facing text, default to outcome-language; reserve mechanics vocabulary for verbose mode or internal/working notes.