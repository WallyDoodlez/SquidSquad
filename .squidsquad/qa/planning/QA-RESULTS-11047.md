# QA-RESULTS-11047 — test_feat_9415 TC-07 stale doc path

**Verified at**: 2026-06-05 cycle 920
**PR**: #11082 (squidsquad/skill/11047-event-bus-docs-8char @ HEAD)

## Verification

- The root cause was a missed doc-consolidation rename, not a stale-8-char-refs sweep: `docs/EVENT-BUS-ARCHITECTURE.md` was folded into `docs/AGENT-RUNTIME.md` by commit `4012500fc`; TC-07 still pointed at the old path → `FileNotFoundError`.
- PR re-points TC-07 at `docs/AGENT-RUNTIME.md` and updates the assertion messages to match. The forbidden-patterns list and the positive marker check (16-char + hex or nonce) are unchanged — the #9415 invariants the test was written to defend are preserved.
- Suite run: `python -m pytest tests/test_feat_9415_event_id_widening_live.py -v` → **8 passed in 12.25s** (matches skill's claim of "8/8, was 7/8").

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.
