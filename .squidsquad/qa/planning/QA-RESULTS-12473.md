# QA-RESULTS-12473

**Task**: #12473 — L1 plain-language user comms on no-action event wakes (suppress ack/cursor jargon)
**Verified**: 2026-06-15 20:11 (qa cycle 213, POLLING) · **Branch**: squidsquad/task/12473 · **PR**: #12474
**Verdict**: ✅ **PASS → pending-ship.** All 6 ACs pass incl. compose-consumption (AC4) and the required comprehension gate (AC6). Zero gaps.

## AC walk

| AC | Statement | Result | Evidence |
|----|-----------|--------|----------|
| 1 | L1 source has the rule: prohibits internal-mechanics terms in user-facing output + mandates plain one-liner | ✅ PASS | SOUL.md new `### User-Facing Communication` section: explicit ban on `ack`/`acked`, `cursor`, `event id`, `GET`/`POST`, `no-op`, `care filter`, `nudge`, `drain` ("even where they read as natural English"); mandates one short plain sentence on every no-action wake. |
| 2 | Concrete one-liner template, NONE of the prohibited terms, reads naturally | ✅ PASS | `🦑 Checked the latest activity — nothing needs my attention right now.` — zero prohibited terms; natural. |
| 3 | Authored in exactly ONE L1 location; cycle steps reference (no dup) | ✅ PASS | Rule lives only in SOUL.md. instructions.md ADDS a reference ("per the **User-Facing Communication** rule in your Soul … the prohibited internal terms and the template live in that Soul rule") + clarifies per-wake-not-per-event timing — no restated prose. |
| 4 | `compose.py deploy-all` → rule present in EVERY role's composed CLAUDE.md | ✅ PASS | Ran deploy-all (regenerated dm/pm/qa/skill — qa IS the verifier alias). grep: pm=3, dm=3, qa=3, skill=3 matches each (heading + reference + template). All install roles covered. |
| 5 | installer-files.txt updated iff a new source file added | ✅ PASS | Edits in-place (SOUL.md + instructions.md) → installer-files.txt correctly UNTOUCHED. |
| 6 | Comprehension test (required — changes agent instructions) | ✅ PASS | Fresh sonnet agent given ONLY the SOUL.md rule: S1 produced the jargon-free one-liner (zero prohibited terms); S2 correctly answered "one line per wake, not per event" AND refused "drain"/"acked" even where natural. Spec: tests/comprehension/12473_spec.json. |

## Comprehension spec
`tests/comprehension/12473_spec.json` — REQUIRED (changes agent character/instructions). Generative test (agent produces the line); PASS = plain one-liner, zero prohibited terms.

## Decision
- All 6 ACs PASS. Transitioned `pending-test → pending-ship`.
- **Merge deferred to DM** (delivery boundary). Counter NOT bumped (DM owns).
- Note: deploy-all regenerates composed CLAUDE.md at deploy time — the rule reaches live agents when the deploy step runs (ship/restart), consistent with AC4's "run deploy-all" verification model.
