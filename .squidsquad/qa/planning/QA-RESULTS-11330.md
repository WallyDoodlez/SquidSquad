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

---

## Round 2 — Post-route-back (cycle 1037, 2026-06-07)

**Trigger**: Skill addressed the R1 reject at commit `dc4d34939` ("skill: #11330 R7 — update AC7 topic-coverage test to match canonical post-D1-D4 headers"). Per the R1 recipe, the two superseded parametrize cases were replaced with assertions pinning the new canonical headers:

- `r"atomic update protocol"` → **`r"POST.*ack-cursor|how to advance"`** (matches the new section `How to advance the cursor — POST /events ack-cursor`, which IS the mechanism that replaced the dropped `.tmp + mv` agent-side write).
- `r"per-event advance|per-batch"` → **`r"where the cursor lives"`** (matches the new section `Where the cursor lives`, which carries the harness-owned framing that replaced the agent-side atomicity contract).

R7 also added an inline comment in the test explaining the supersession with #11330 D1-D4 — the same kind of "why this changed" trail PM enforced on #11139.

### Re-verification

- **TestAc7TopicCoverage** sweep — **16/16 PASS** in 0.12s on the PR branch. Both R1-failing cases now PASS with the new parametrize values.
- **Wider sweep apples-to-apples** (`pytest tests/test_event_mode_fragments.py tests/test_compose_author_comments_11142.py tests/test_manifest.py -q`):
  - polish-session base @ `9ff6b8341`: **9 failed / 160 passed**
  - PR R2 branch @ `dc4d34939`: **9 failed / 160 passed**
  - **Net-new failures: 0.** The 9 pre-existing failures on polish-session base are pre-existing event-fragment manifest-wiring drift, out of scope for #11330.

### Content drift check (R1 rewrites still intact)

- `cursor-management.md` line 12 — harness-owned framing unchanged: "The cursor is **harness-owned**. It is persisted in `.squidsquad/.event-state.json`...". ✓
- `POST /events {event_type: "ack-cursor"...}` block still present in `cursor-management.md` (1 distinctive `event_type.*ack-cursor` match). ✓
- `.tmp + mv` discipline still dropped from `cursor-management.md` (zero matches). ✓
- `event-mode-contract.md` line 97 still reads: "Cursor advance is per-event and agent-initiated. You POST `ack-cursor {event_id, role}` after tending each event...". ✓
- `event-driven-workflow.md` line 8 still: "POST `ack-cursor` to the harness after each tended event so it advances your cursor in `.squidsquad/.event-state.json`". ✓

### DS audit trail (delta from R1)

R1 saw 6 audit rounds (`DS-AUDIT-11330.md` + `-r2/3/4/5/6`); R2 adds the R7 round implied by `dc4d34939`. The `R2-R5` commits between original `R1` and `R6` are DS-driven content fixes (cursor URL form, factual bugs, `current_head→oldest_id` leftover) that don't touch the verifier's R1 content checks — those still hold as listed above.

### Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Skill applied the exact fix recipe from the R1 reject (same shape PM enforced on #11139 and #11066). Zero net-new failures, content rewrites intact, test pinning the new canonical headers. R2 ships.
