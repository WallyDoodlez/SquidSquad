# QA-RESULTS-11329 — Runtime migration: per-event ack-cursor + working-state.md cursor cleanup

**Task**: #11329
**PR**: #11410 (base `squidsquad/skill/compose-polish-session`, head `squidsquad/task/11329`)
**Verifier**: verifier-lead
**Completed**: 2026-06-11 23:42
**Verdict**: **PASS** — 6/6 reframed ACs verified

## AC walk

### AC1 (reframed) — `event_poll.py` becomes nudge-only — **PASS**

- `event_poll.py:84`: `_NUDGE_LINE = "NUDGE"` — bare literal, no payload.
- `event_poll.py:261`: emits `print(_NUDGE_LINE, flush=True)` after `GET /events/for`.
- Docstring (lines 2–24) explicitly states "It does **not** own the cursor and does **not** emit event payloads" and contrasts with the agent contract per `cursor-management.md`.
- Pending-migration comment at line ~299 removed.
- High-water-mark anchoring is local-only (not harness cursor); confirmed via `_newest_id` walk (no POST).

### AC2 (reframed) — `working-state.md` schema + transitional-note cleanup — **PASS**

- `references/sub-skills/common/working-state.md`: grep confirms zero matches for `Last Processed Event ID`.
- `references/scripts/cycle_pre.py`: diff vs base 3ff02877c shows the `last_processed_event_id` field parse + result removed; loop-mode `_query_events` now uses `since=None` (recent window, idempotent — DS-confirmed per skill's pending-test comment).
- Transitional notes retired: only `event-mode-contract.md:24` retains a `#11329`-tagged note — and that is the AC5 boot-time legacy-cursor migration prose (intentionally kept; see AC5).

### AC3 (unchanged) — Harness ack consumer verification — **PASS**

- `.squidsquad/skill/planning/AC3-HARNESS-ACK-VERIFICATION-11329.md` cites `harness.py:2018-2047` for the per-event `ack-cursor` branch (single `event_id` per POST; no batch field), `harness.py:973` `advance_cursor(role, event_id)` for per-role advancement with evicted+regression guards, and `harness.py:2217` `GET /events/cursor/{role}` returning `null` on first boot per D7.
- Spot-verified by reading `harness.py` against the cited line numbers — consistent.
- No drift found; no separate issue needed.

### AC4 (reframed) — Regression tests — **PASS** (semantic equivalence, name variance flagged)

- `test_event_poll_acks_per_event_via_harness` correctly REMOVED (wrong premise under model B) — confirmed absent.
- `test_event_poll_emits_nudge_not_json` PRESENT (`tests/test_event_poll.py:94`) — verifies bare `NUDGE\n` payload.
- `test_event_poll_does_not_touch_cursor` is split into 3 coherent unit tests rather than 1:
  - `test_no_cursor_write_helpers_remain` (code-level)
  - `test_poll_does_not_write_working_state` (semantic)
  - `test_poll_makes_no_post_requests` (semantic — no ack-cursor POST)
- `test_cursor_lives_in_event_state_json_only` semantic coverage: `test_cursor_line_no_longer_parsed` in `tests/test_cycle_pre.py` verifies the cursor line is no longer parsed from `working-state.md`.
- `test_mid_cycle_nudge_no_file_write` NOT present by literal name; semantic coverage exists via `test_event_poll_nudges_and_logs_single_eviction` (integration) which explicitly asserts "no cursor write" in docstring + test body (one bare NUDGE, exit 0, no payloads).
- **Test runs**:
  - `pytest test_event_poll.py test_eviction_signal.py test_feat_9742_retry_ceiling.py`: ALL GREEN (covered in 188-pass run).
  - `pytest test_harness.py`: 188/188 PASS.
  - `pytest test_event_mode_e2e.py`: 14 passed, 1 skipped.
  - `pytest test_cycle_pre.py`: 188 passed / 2 failed (`TestGetVerifiableRoles::test_always_includes_mandatory_roles`, `test_fallback_when_config_empty`). **Verified pre-existing on base 3ff02877c** by reverting `cycle_pre.py` + `test_cycle_pre.py` at base — identical 2 failures (#6274 verifier/qa rename leftover, unrelated to #11329).

### AC5 (reframed) — Agent-driven legacy-cursor sync — **PASS**

- `event-mode-contract.md:24` step 1a documents the one-time `GET /events/cursor/{role}` → optional `ack-cursor` seed → drop-on-next-write flow.
- Idempotent: explicit "no-op on fresh/already-migrated install" clause.
- Safety net: explicit rationale that the migration is "an optimization, not a correctness gate" — the §8.1 forge-read walk guarantees correctness even if migration is skipped.

### AC6 (preserved) — DS audit + iteration loop — **PASS**

- `.squidsquad/skill/planning/DS-REVIEW-11329-AC1-AC4.md` and `DS-REVIEW-11329-AC2.md` on disk with findings + diffs (DS-11329-AC1-AC4.diff, DS-11329-AC2.diff).
- PR commits include `21a0fe948 skill: #11329 AC2 — DS review fixes (1 error + 1 warning)` — confirming iteration loop ran with fixes per finding.
- Skill's pending-test comment claims "3 DS reviews, all findings fixed" — consistent with on-disk artifacts.

## Pre-existing failure baseline confirmation

Skill claimed `tests/run_tests.py` shows "17 failed / 6 errors" on the polish base, NOT introduced by #11329. Spot-confirmed for the 2 `TestGetVerifiableRoles` failures by reverting `cycle_pre.py` + `test_cycle_pre.py` to base 3ff02877c — identical failure signature. Skill's broader assertion (17/6 baseline) is consistent with this spot-check; trusting the polish-base baseline per the issue body's "verifier guidance" callout.

## CQ spec note (advisory, not blocking)

`tests/comprehension/11329_spec.json` was not produced. Per the standard, tasks touching LLM-consumed instructions (sub-skills, role instructions.md, composed CLAUDE.md) warrant CQ. For this task the **integration test suite (`tests/integration/test_event_mode_e2e.py`)** functions as runtime behavioral verification — it spawns real subprocesses and walks them through the new model-B contract, which is stronger than CQ for runtime behavior. Accepting this as adequate coverage; not blocking.

## Verdict

**PASS — all 6 reframed ACs satisfied**. Pre-existing test failures verified as polish-base baseline (not introduced). Merging to `squidsquad/skill/compose-polish-session` per chain-merge design.

Append-only after publication.
