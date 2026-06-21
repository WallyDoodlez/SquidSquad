## #13162 — Config-gated Verbose Mode (boot-read, session-sticky narration toggle)

Implements the skill lane (AC1,2,3,4,5,9 + AC8 coverage) of the operator-approved Verbose Mode feature. Per PM design `.squidsquad/pm/planning/VERBOSE-MODE-DESIGN.md`.

### What changed (source-only; composed regen post-merge per #12853)
- **AC1 config schema** — `config.py`: `verbose-mode` in FIELD_MAP + `_FIELD_DEFAULTS` (`no`); new `is_verbose()` bool getter (graceful `False` when section absent). `wizard.py`: `config.md` template gains `## Verbose Mode → - **Enabled**: no`.
- **AC3 boot-read** — `instructions.md`: boot-read selector (`config.py get verbose-mode`) right after "Loaded mode is sticky"; session-sticky, no mid-session re-check (mirrors wake-mode stickiness). Composes into all 4 role boot blocks.
- **AC4 verbose ON / AC5 verbose OFF** — `SOUL.md` "User-Facing Communication" rewritten to carry BOTH postures, gated by the boot-read:
  - **Quiet (OFF, default)**: zero internal mechanics in ANY operator-facing output — comprehensive ban (`acknowledgment`/`ack`, cursor, event, drain, care-filter, nudge, transition, GET/POST, no-op) + positive plain-OUTCOME substitution. Strengthens today's L1 jargon-ban; **no default-install regression** (the `🦑 Checked the latest activity…` one-liner survives verbatim — PM's no-action-wake refinement stays intact).
  - **Verbose (ON)**: lifts the ban for the session; firehose every cycle step + event with internal terms allowed.
- **AC9 compose/installer hygiene** — `compose.py deploy-all` regenerates clean; no new `references/` files → no `installer-files.txt` change.

### Verification
- **AC1**: `tests/test_config.py::TestVerboseMode` (7: yes→True, no→False, absent→False, case/ws-tolerant, defaults registry, FIELD_MAP) + `test_config_functions` FIELD_MAP-coverage fixture + `test_wizard` section-order/default.
- **AC3 (consumption, not existence)**: composed `.squidsquad/{skill,qa}/CLAUDE.md` (post deploy-all) verified to contain the boot selector + BOTH posture contracts + the `config.py get verbose-mode` boot command.
- **Full static gate**: PASS 4916/0/0.
- **DS-review** (high-blast-radius; Sonnet fallback, DeepSeek 402): 1 BLOCKING + 1 LOW, both fixed (posture-gated the per-nudge no-action-wake callout; added exactly-one-posture-live preamble). `CODE-REVIEW-13162.md`.

### Coupled / cross-lane (land together)
- **AC2 (this install ON)**: `.squidsquad/config.md` set `Verbose Mode > Enabled: yes` committed **direct to main** (config.md is main-only per #11511 state-guard; takes effect next restart via the boot-read).
- **AC6 (AGENT-RUNTIME doc)**: PM lane. **AC7 (README operator section)**: DM lane.
- **AC8 (CQ)**: comprehension coverage is described in AC5/AC8 (both postures verifiable from composed instructions; explicit check that `acknowledg*` never appears in OFF-mode output). Per project practice (#13147) the `tests/comprehension/13162_spec.json` file is **verifier-derived** during verification — flagged to PM/verifier in the issue (lane split puts AC8 in skill; skill-cq rule says verifier authors the spec — I defaulted to verifier-derives; will author it if PM prefers).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
