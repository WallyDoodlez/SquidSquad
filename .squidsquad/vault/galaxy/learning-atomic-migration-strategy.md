---
type: learning
tags: [migration, architecture, process]
created: 2026-04-02
updated: 2026-04-02
owner: skill
status: active
confidence: medium
source: observation
links:
  - "[[decision-sub-skill-architecture]]"
  - "[[squidsquad]]"
---

## Context

During the FEAT-SKILL-030 sub-skill architecture migration, the team faced the challenge of replacing the core instruction delivery mechanism while agents were potentially running. The human explicitly required all phases to ship atomically in a single dev cycle.

## Content

When migrating foundational infrastructure that running agents depend on, the entire migration must ship as a single atomic unit. Partial migrations -- where some agents run on old structures while others use new ones -- will break coordination. The FEAT-SKILL-030 migration succeeded by: (1) completing all research and planning phases first (RESEARCH, CONTEXT, TEST-PLAN), (2) implementing the full extraction and composition in one dev session, (3) verifying with 12 smoke tests before marking complete, and (4) diff-verifying the composed output against the original monolith (only 3 intentional differences). The entire cycle from planning approval to ship took under 7 hours.

## Rationale

This pattern works because SquidSquad agents coordinate through shared files and git. If the file structure changes mid-cycle, agents that pulled before the change will conflict with agents that pulled after. Atomic delivery eliminates this race condition entirely. The upfront investment in thorough planning (extended research, 8 open questions resolved, 40 test cases written before any code) paid off by enabling a clean single-pass implementation with no rework.

## Related

- [[decision-sub-skill-architecture]]
- [[squidsquad]]

---

### Changelog

- 2026-04-02 -- Created by QA agent. Observed from FEAT-SKILL-030 discussion timeline during vault-create testing.
