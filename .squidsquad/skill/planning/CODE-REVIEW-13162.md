# CODE-REVIEW — #13162 Config-gated Verbose Mode (boot-read narration toggle)

**Reviewer:** Claude/Sonnet subagent (DeepSeek model_router unavailable — 402, fleet-wide; [[feedback_model_router_auto_fallback]]).
**Date:** 2026-06-21
**Scope (high-blast-radius, LLM-consumed):** `references/roles/SOUL.md` (User-Facing Communication — both postures) + `references/roles/instructions.md` (boot-read selector + per-nudge no-action-wake callout). SOUL.md composes into all 4 role agents.

## Verdict: 1 BLOCKING + 1 LOW — both FIXED, re-reviewed clean

### FINDING 1 — BLOCKING (FIXED)
The per-nudge-cycle callout `> Telling the user about a no-action wake.` (instructions.md) carried an **unconditional** "Use plain language only — the prohibited internal terms and the template live in that Soul rule." That contradicts the new verbose posture (which lifts the jargon-ban) for every no-action wake in verbose mode.
**Fix:** Scoped the callout explicitly — "In **quiet mode** … use plain language only and follow the one-liner template … In **verbose mode** … narrate the wake in full internal detail per the verbose posture instead. Either way the mechanics still run unchanged." Now posture-gated, no contradiction.

### FINDING 2 — LOW (FIXED)
The two SOUL posture blocks co-reside with no conditional frame; an agent reading the Soul in isolation (skipping the boot selector) could read both as active.
**Fix:** Added an explicit preamble line — "**Exactly one of the two postures below is live for the session — the boot-read selects it and the other does not apply** (never both at once)." Headings already labelled "Verbose Mode OFF/ON"; this makes the conditionality self-evident without the boot step.

## Confirmed SOUND (no change)
- **AC4 (verbose ON):** verbose posture narrates every cycle step + event, internal terms allowed/expected.
- **AC5 (verbose OFF):** comprehensive ban incl. `acknowledgment`/`acknowledge`/`ack`/`acked` (AC5 calls these out by name) + positive plain-outcome substitution; no default-install regression.
- **D1 stickiness:** once-at-boot, no mid-session re-check path; mirrors the wake-mode "Loaded mode is sticky" rule; stated in both SOUL (overview) + instructions.md (imperative).
- **PM role-adaptation survival:** the L1 one-liner `🦑 Checked the latest activity…` survives verbatim — PM's "No-action-wake reporting — brief summary only" refinement (which depends on it) is intact.
- **Boot-selector cross-reference:** `config.py get verbose-mode` → `yes`/`no` maps cleanly to the SOUL's labelled postures; "Right after mode selection" is the correct boot ordering (wake mode first, then narration posture).

## Gates
config.py/wizard.py deterministic; AC1 covered by tests/test_config.py::TestVerboseMode (7) + test_config_functions FIELD_MAP coverage + test_wizard verbose section. Full static gate PASS 4916/0/0 (pre-fix run; re-run post-fix confirmed). Composed output verified: boot selector + both postures reach skill AND qa CLAUDE.md (AC3). No new `references/` files → no installer-files.txt change (AC9). AC8 CQ spec = verifier-derived per project practice (coverage in PR body; lane flagged to PM).
