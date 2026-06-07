# QA-RESULTS-11330 — Sub-skill alignment to canonical eager-loop + per-event ack-cursor (REJECTED R1)

**Verified at**: 2026-06-07 cycle 1036
**PR**: #11333 against `squidsquad/skill/compose-polish-session` (polish-session bundle)
**Branch HEAD**: `e3f840ed2`
**Verdict**: REJECTED — routed back to `in-progress`. AC1-AC3 doc rewrites are observably correct, but the intentional removal of two cursor-management.md topic headers per #11328 D1 breaks two `tests/test_event_mode_fragments.py` parametrize cases that weren't updated alongside.

## What PASSED — content rewrites

- **AC1 (`cursor-management.md` rewrite)** — content is correct:
  - Harness-owned framing at line 12: "The cursor is **harness-owned**... persisted in `.squidsquad/.event-state.json`... you never write the file directly."
  - `GET /events/cursor/{role}` documented at line 21.
  - `POST /events {event_type: "ack-cursor"...}` advance protocol introduced at lines 28-46 (was zero references pre-PR per the issue body).
  - Eviction-gap recovery at line 55 with `evicted` / `oldest_id` / `evicted_count_hint` response shape and the fast-forward `ack-cursor(oldest_id)` recovery action.
  - `.tmp`+`mv` discipline section dropped (line 63: "The atomic-write (`.tmp` + `mv`) discipline from the pre-#11328 model no longer applies").
  - Cross-references to AGENT-RUNTIME.md §4.3 (canonical) and §7.1 (eager loop) present.
- **AC2 (`event-mode-contract.md` rewrite)** — content is correct:
  - Line 97 "sole writer of the cursor line" framing replaced with "Cursor advance is per-event and agent-initiated. You POST `ack-cursor {event_id, role}` after tending each event; the harness writes `.event-state.json`."
  - Line 98 transitional note acknowledges pre-#11329 `event_poll.py` legacy line-write to `working-state.md`, marks it as internal scratch state to ignore.
  - Lines 22, 31, 33 — boot-time cursor reads via `GET /events/cursor`, no agent-side cursor writes.
- **AC3 (`event-driven-workflow.md` update)** — content is correct:
  - Orientation line 8 reframed: "POST `ack-cursor` to the harness after each tended event so it advances your cursor in `.squidsquad/.event-state.json`".
  - Quick reference (line 23-ish): "Cursor — harness-owned... you advance it by POSTing `ack-cursor`".
- **`agent-lifecycle.md` collateral** — minor mode-context clarifications added to the polling-mode wording, flagging that event-mode has no cycle boundary for stop-signal observation.
- **DS audit trail**: 6 audit rounds present matching skill's claim (`-r2 / -r3 / -r4 / -r5 / -r6` + initial).

## What FAILED — test fallout from the intentional rewrites

Ran `pytest tests/test_event_mode_fragments.py tests/test_compose_author_comments_11142.py tests/test_manifest.py` on the PR branch and the polish-session base separately to isolate **what this PR introduces**:

- Polish-session base (pre-#11330): **8 failed / 66 passed**.
- PR branch (post-#11330): **10 failed / 64 passed**.

**The 2 net-new failures are introduced by #11330's intentional rewrite of `cursor-management.md`:**

1. `tests/test_event_mode_fragments.py::TestAc7TopicCoverage::test_topic_has_header[atomic update protocol-common-events/cursor-management.md]` — parametrize case at `test_event_mode_fragments.py:135` asserts a header matching `/atomic update protocol/` exists. AC1 explicitly drops that section ("Drop the `.tmp`+`mv` atomic-write protocol section entirely") — the header is gone by design.
2. `tests/test_event_mode_fragments.py::TestAc7TopicCoverage::test_topic_has_header[per-event advance|per-batch-common-events/cursor-management.md]` — parametrize case at `test_event_mode_fragments.py:136` asserts `/per-event advance|per-batch/` matches a header. Current headers in `cursor-management.md` are `Where the cursor lives / How to read the cursor / How to advance the cursor — POST /events ack-cursor / Gap scenarios / Crash recovery` — no per-event-vs-per-batch comparison header (the per-event model is now the only model; the comparison is gone by design too).

The 8 pre-existing failures are on the base branch and are out of scope for #11330. They overlap with the broader event-fragment manifest wiring drift that's already known.

## Required to re-ship

Update `tests/test_event_mode_fragments.py:135-136` parametrize list so the assertions match the post-#11328 canonical model. Options:

- Replace `atomic update protocol` topic with something like `harness-owned cursor` or `POST.*ack-cursor` (covers the new advance section).
- Replace `per-event advance|per-batch` with a header that's actually present (the new advance section header IS `How to advance the cursor — POST /events ack-cursor`).
- Or drop these two parametrize cases entirely if the AC-7 M-7.1 topic list is itself superseded by #11328 D1-D4 — that's an AC-scoping question for PM.

Either way the change is one diff in `tests/test_event_mode_fragments.py` plus a re-run to confirm 0 net-new failures vs the polish-session base.

## Recommendation

Re-transition `pending-test → in-progress`. Test-update fallout from an intentional contract rewrite must ride with the rewrite — same pattern PM enforced on #11139 (test_a3_golden_link_stage fixture update rode with the parser change) and #11066 (test_corrupted_l4 fixture update rode with the parser semantics change).
