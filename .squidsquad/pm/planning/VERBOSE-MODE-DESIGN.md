# Verbose Mode — Design & Plan

_PM planning artifact. Feature requested by operator 2026-06-21 (inline). Intake: Research ✓ → Discussion ✓ (4 decisions locked with operator) → Planning (this doc) → human-approve gate → Execution._

## Summary

A config-gated **Verbose Mode** that controls how much of SquidSquad's internal operation each agent narrates to its terminal. **ON** = the agent talks through every step and every event (drains, acks, cursor advances, care-filter decisions, cycle steps, transitions) so the operator sees exactly how SquidSquad runs. **OFF (shipped default)** = today's behavior: plain high-level one-liners, no internal jargon. This install (SquidSquad-on-SquidSquad) ships with verbose **ON**; every other deployment defaults **OFF**.

## Locked decisions (Phase 2 discussion, operator 2026-06-21)

- **D1 — Mechanism: boot-read, session-sticky.** The agent reads `config.md`'s Verbose Mode flag **once at session boot** and the posture is **fixed for the whole session** (re-read only on the next restart — mirrors the existing "wake-mode is sticky" boot rule). NOT compose-time-baked (so toggling needs only an edit + restart, no recompose) and NOT a per-cycle read.
- **D2 — Depth: full firehose.** Narrate every drained event, every ack/cursor advance, every care-filter decision, and every cycle step. Token cost is the operator's explicit, accepted tradeoff when they turn it on.
- **D3 — Role scope: all agents.** pm, skill, qa, dm each narrate their own internals when on.
- **D4 — Operator-facing doc: `README.md`** (the DM-maintained operator surface; DM-ARCH is an internal TRD).

## Design

### Config (skill lane)
- `config.md` gains:
  ```
  ## Verbose Mode
  - **Enabled**: no
  ```
  Shipped/template default `no`. `config.py` parses it (getter returning bool; **graceful default `no`** when the section is absent, per the existing config-parse pattern).
- This install's `.squidsquad/config.md` sets `Enabled: yes`.

### Boot-read mechanism (skill lane — boot-bootstrap)
- The agent boot sequence (`references/sub-skills/common/boot-bootstrap.md` and/or the SOUL User-Facing Communication rule) gains a step: **at session start, read `config.md` Verbose Mode; adopt verbose or quiet posture for the session.** Sticky — do not re-check mid-session (operator toggles take effect on next restart, exactly like wake-mode).
- The composed `CLAUDE.md` carries **both** posture contracts + the boot-read selector. (This is why it's boot-read not compose-baked: one composed artifact serves both modes; the boot read selects.)

### Behavior (skill lane — `references/roles/SOUL.md` "User-Facing Communication")
- **Verbose OFF (default)** = today's rule unchanged: plain one-liner on no-action wakes (`🦑 Checked the latest activity…`), internal jargon **banned** (`ack`/`cursor`/`event id`/`GET`/`POST`/`no-op`/`nudge`/`drain`…), brief summaries.
- **Verbose ON** = overrides that rule for the session: narrate every cycle step and every event with full internal detail; internal terms are **allowed** (the operator wants them). The jargon-ban and one-liner-brevity rules are lifted while verbose is on.

### Docs
- **AGENT-RUNTIME.md** (PM lane): document the Verbose Mode config, the boot-read/session-sticky mechanism, and both-mode behavior.
- **README.md** (DM lane): operator-facing section — what verbose mode shows, how to turn it on/off (edit `config.md` + restart), default off.

## Acceptance Criteria

1. **Config schema** — `config.md` template gains `## Verbose Mode → - **Enabled**: no` (default off). `config.py` exposes a getter returning bool; returns `False` (off) when the section is absent. Test: parse `yes` → true, `no` → false, absent → false.
2. **This install ON** — `.squidsquad/config.md` (this repo) has `Verbose Mode > Enabled: yes`. Verify value is `yes`.
3. **Boot-read consumed** — composed `CLAUDE.md` (post `compose.py deploy-all`) contains the boot-read selector step AND both posture contracts. Verify via the composed output for ≥1 role (compose-pipeline consumption, not just source-file existence).
4. **Verbose ON behavior** — given a verbose-on session, all agents narrate every cycle step + every event (drain/ack/cursor/care-filter/transition) with internal terms allowed. Verified by comprehension test (AC8).
5. **Verbose OFF default preserved** — given verbose-off (default), behavior is exactly today's: plain one-liner on no-action wakes, jargon banned, brief. No regression to default installs. Verified by comprehension test (AC8).
6. **AGENT-RUNTIME doc** (PM) — AGENT-RUNTIME.md documents config + boot-read/sticky + both-mode behavior. Lands coupled to ship.
7. **README operator doc** (DM) — README.md gains the operator-facing verbose section (on/off + restart + default off). Lands coupled to ship.
8. **Comprehension test** (per CQ-required-for-agent-instruction-changes) — a CQ spec: a fresh agent given verbose-on composed CLAUDE.md exhibits firehose narration; given verbose-off, exhibits the quiet default. Both postures verified from the composed instructions.
9. **Compose/installer hygiene** — `compose.py deploy-all` regenerates cleanly; if new source files are added under `references/`, `installer-files.txt` is updated.

## Lane split
- **skill** (lead): AC1, AC2, AC3, AC4, AC5, AC8, AC9 — config schema + boot-read + SOUL behavior source + comprehension test + compose hygiene (all compose-consumed / code).
- **PM**: AC6 — AGENT-RUNTIME.md doc (PM authors, cross-pair consistency pass, lands coupled).
- **DM**: AC7 — README.md operator section (DM authors, lands coupled).

## Risks / notes
- Token cost under verbose-on is significant (4 agents firehosing) — accepted operator tradeoff; off by default protects everyone else.
- The boot-read must be genuinely sticky (no mid-session re-check) to avoid posture flips mid-cycle; mirror the existing "Loaded mode is sticky" boot rule.
- Verbose-on lifts the L1 jargon-ban — the two rules must be composed so they don't contradict (the ban applies only in quiet mode).
