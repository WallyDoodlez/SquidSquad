# TEST-PLAN-13327 — surface L4-customization affordance (discoverability)

**Issue**: #13327 (type:task, priority:medium) — PM-specced UX.
**PR**: #13427 `squidsquad/task/13327`, head 85c3e275a.
**Derived from**: issue ACs (independent).

## ACs
- AC1: wizard customize-later answer + What's-Next summary surface the talk-to-PM / L4 affordance in plain language (no jargon).
- AC2: PM (and worker) recognize a GENERIC customize request and route into l4-curation elicitation.
- AC3: l4-curation safety-gate pipeline unchanged (entry-point only).
- AC4 (comprehension): fresh agent quiz confirms PM recognizes BOTH specific-directive and generic-invitation triggers.

## Test cases
- TC-1 (AC1): read INSTALLER-RUNTIME.md §7 diff — both moments, plain benefit language, no "L4"/"compose".
- TC-2 (AC2): read pm + worker instructions.md diffs — generic trigger recognized, ask-one-question, route to l4-curation, no re-run-setup.
- TC-3 (AC3): diff scope — no l4-curation sub-skill/gate-script change; in-text "gates unchanged".
- TC-4 (AC4 CQ): 13327_spec review; fresh Sonnet agent on pm '### Project customization' only; zero misreads (both triggers + one-off exclusion).
- TC-5 (gate+landing): combined-state static gate (branch behind main, shares INSTALLER-RUNTIME.md with #13339); local merge + gate; §7 and §4/§9 coexist.

CQ REQUIRED — pm/worker instructions.md + INSTALLER-RUNTIME.md are LLM-consumed (AC4 explicit).
