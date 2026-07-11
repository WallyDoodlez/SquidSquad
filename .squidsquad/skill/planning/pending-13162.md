Skill lane complete → pending-test. **PR #13171** (branch squidsquad/task/13162).

**Delivered (skill: AC1,2,3,4,5,9 + AC8 coverage):**
- AC1 — config.py `verbose-mode` (FIELD_MAP + `_FIELD_DEFAULTS` no + `is_verbose()` graceful-off getter); wizard.py `## Verbose Mode` template (default no). Tests: TestVerboseMode (7) + FIELD_MAP coverage + wizard section-order/default.
- AC2 — `.squidsquad/config.md` Verbose Mode Enabled: **yes** (this install), committed **direct to main** (config.md is main-only per #11511; effective next restart via the boot-read).
- AC3 — boot-read selector in instructions.md after "Loaded mode is sticky" (session-sticky, no mid-session re-check). **Verified consumption**: composed `.squidsquad/{skill,qa}/CLAUDE.md` (post deploy-all) carry the selector + the `config.py get verbose-mode` boot command + BOTH posture contracts.
- AC4/AC5 — SOUL.md "User-Facing Communication" carries both postures: quiet (OFF, default) bans all internal mechanics in ANY operator output incl. `acknowledg*` + plain-outcome substitution; verbose (ON) lifts the ban, firehose. L1 one-liner survives verbatim → no default-install regression; PM's no-action-wake refinement intact.
- AC9 — compose deploy-all clean; no new references/ files → no installer-files.txt change.

**Gates:** Full static gate **PASS 4921/0/0** (post-merge of origin/main). Sonnet DS-review (DeepSeek 402 fleet-wide): 1 BLOCKING (per-nudge no-action-wake callout was unconditional "plain language only" — now posture-gated) + 1 LOW (exactly-one-posture-live preamble), both fixed + re-reviewed clean (`.squidsquad/skill/planning/CODE-REVIEW-13162.md`). Source-only commit; composed regen post-merge via harness deploy-signal (#12853 pattern).

**@PM / @verifier — AC8 lane question:** the lane split puts AC8 (the CQ spec) in skill's lane, but my `step:cycle/skill-cq` rule says "Do NOT self-generate CQ specs — verifier's job per TEST-PLAN," and project practice (#13147) is verifier-derives. I defaulted to **verifier-derives** `tests/comprehension/13162_spec.json` (coverage is fully described by AC5/AC8: both postures verifiable from the composed instructions, incl. an explicit check that `acknowledg*` never appears in OFF-mode output). If you'd rather skill author the spec file (as an approved-AC override of the default), say so and I'll add it.

**Coupled cross-lane (land together):** AC6 AGENT-RUNTIME doc (PM), AC7 README operator section (DM).