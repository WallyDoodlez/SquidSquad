---
type: decision
tags: [pipeline, sentinel, self-healing, process-gaps]
created: 2026-04-18
updated: 2026-04-18
owner: pm
status: active
confidence: high
source: conversation
links: [human-profile]
---

## Context

Human discovered orphaned PR #1327 — tracker items shipped but PR never merged. Pipeline sentinel didn't catch it. Discussion revealed the sentinel only covers narrow stuck states and doesn't auto-remediate.

## Content

Pipeline sentinel must use a **two-tier self-healing response** when detecting stuck tasks:

- **Tier 1 (immediate)**: Nudge/unstick the specific item right now (close orphaned PR, transition task back, ping stalled agent)
- **Tier 2 (root cause)**: Detect that the stuck state reveals a process gap, then auto-file a bug against the responsible component so the gap gets fixed permanently

This creates a closed loop: detect stuck state → unstick → file root-cause bug → agent fixes gap → sentinel verifies fix in future cycles.

The sentinel should cover **every** pipeline state where a task can get stuck — not just specific known scenarios.

## Rationale

Human's design philosophy: the system should self-heal. When a process gap is found, don't just patch the symptom — file a bug so the root cause gets fixed. This compounds: each bug fix makes the pipeline more robust, and the sentinel keeps finding new gaps.

## Related

- [[human-profile]]

---

### Changelog

- 2026-04-18 — Created by pm. Human-directed decision after orphaned PR #1327 discovery.
