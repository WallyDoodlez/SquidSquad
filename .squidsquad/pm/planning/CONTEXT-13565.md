# CONTEXT-13565 — Composed-prompt re-diet + sub-skill re-read discipline (15-20% target)

**Not light mode** — Medium size, cross-role impact, mandatory CQ specs for two of the three phases. Operator approved as part of "go ahead on all of context trimming" (2026-07-18), but this is flagged as **high-blast-radius work** (touches all 4 roles' composed `CLAUDE.md` + the cycle contract itself) and should get DS-review-per-change during implementation, not just a final-pass audit, per [[feedback_ds_review_per_change]].

**AC1 revised 2026-07-18 (PM, post-implementation)** — see the AC section below. The original "composed CLAUDE.md size reduced ≥15%" premise was factually wrong: `v2_link_stage.py` (`_is_sub_skill_body_in_instructions`, D2/Q-D2 design) deliberately excludes `references/sub-skills/` bodies from inlining into the composed instructions slot, so splitting `task-intake.md`/`verification.md` structurally cannot move composed boot size — verified directly against the source, not taken on skill's word alone. The AC is corrected to measure what this work actually controls: per-cycle re-read cost.

## Scope

Three phases:
- **Phase A (audit)**: re-run FEAT-SKILL-195-style per-include token accounting on today's composed output (pm 76KB / skill 86KB / qa 68KB / dm 77KB), identify duplicated content, prose that should be deterministic script, and dead branches. `event-mode-contract.md` (24KB) is a named suspect.
- **Phase B (hot/cold split)**: split `task-intake` (26KB) and `verification` (27KB) into a lean hot-path core (≤~8KB) + cold-path reference sections read only when the relevant branch triggers.
- **Phase C (re-read discipline)**: cycle-contract rule — skip re-Reading a sub-skill whose full text is already VISIBLE in current context from an earlier cycle this session. Worded against *visibility*, not memory, so post-compaction / post-restart the agent naturally re-reads (the text is genuinely gone from context).

## Locked Decisions (human decided)

- Proceed with all three phases as scoped in the issue body.
- **Risk acknowledgment**: Phase C changes live agent behavior (mine included) fleet-wide — every role's per-cycle sub-skill reads. This is exactly the kind of high-blast-radius, hard-to-reverse-if-wrong change the DS-review-per-change discipline exists for. Not asking the operator to re-confirm each phase individually (they already authorized the batch) — flagging it here so skill/verifier apply the heavier review posture without needing a separate ask.

## Worker Discretion (worker agent can choose)

- Exact split points within task-intake/verification for the hot/cold boundary, as long as hot-path cores land at ≤~8KB.
- Implementation approach for Phase A's mechanical-overhead reduction (prose → script), following the FEAT-PM-2070 precedent (60-80% reduction on similar work).

## Side Effect Mitigations (required)

- Phase C's re-read-discipline wording MUST be tied to "visible in current context," never "remembered from earlier" — the issue body is explicit about this to prevent an agent skipping a genuinely-needed re-read after compaction.
- Cold-path sections in the Phase B split must be comprehension-tested (a fresh agent must still find and use them when the triggering branch fires) — not just present in the file.
- CQ scenarios for Phase C must cover all three cases: second cycle same session (skip is correct), post-compaction (re-read is correct), post-restart (re-read is correct).

## Upgrade Path (required)

- N/A — no upgrade impact for existing installs beyond the compose-output size change itself (agents just get leaner instructions on next deploy/recompose).

## Out of Scope

- BRIEFING.md (#13563, already shipped), cycle-input diet (#13564, in progress), model/effort tiering (#13568).
