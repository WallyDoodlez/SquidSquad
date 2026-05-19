# TEST-PLAN-8694 — Event-Mode L1 Base Agent Definition

**Issue**: #8694 (lead of Phase 5 event-driven architecture bundle)
**Date**: 2026-05-17
**Status**: Phase 3 draft for human/QA review
**Inputs**: `CONTEXT.md` §3, §5.1, §11 · `RESEARCH-harness-events.md` · `tracker.py:437-510` · `run_comprehension_test.py`
**Bundle siblings**: #8692 (singleton, prereq), #8695, #8697, #8700, #8701, #8704

## Revision Log

- **2026-05-17** — Revised per deepseek R1 review (7 findings) + 4 PM-locked gap resolutions (TUI separate process, mode-gated validator, `_advance_event_cursor` removal, hard-coded 5s status-line refresh).
  - F1 (error, dead "4.x" ref): added §4.8 IT-StopRequested integration test for `stop-requested` mid-task; traceability matrix repointed.
  - F2 (warning, Case B gap): added §4.8b IT-CaseB for idle + event arrival.
  - F3 (warning, duplicate grep guard): removed duplicate; consolidated into §6.6.
  - F4 (warning, gap scenarios): added §4.9 IT-CursorGapInStream and §4.10 IT-CursorLongLag.
  - F5 (warning, M-2.1 boot ambiguity): M-2.1 restated with explicit idle-boot precondition and verified branch.
  - F6 (error, CQ asymmetry): removed `pr-merge-wait.md` from CQ spec `files`; Q5/Q6 answerable from `l1-base.md` + `comment-handling.md`; per-role events fragment locking noted under open questions.
  - F7 (error, Probe A automatic reconnect): rephrased per CONTEXT §11 degraded-mode glossary (manual-recovery scenario).

This plan describes what must be testable for the #8694 deliverable bundle:

- `references/scripts/event_poll.py` (new executable)
- `references/sub-skills/common-events/` + per-role `events/` fragments containing the event-mode L1 base agent definition (Cases A–E, cursor mgmt, forge-read pattern, idle-cooldown loop, comment handling + DM exception, transition-on-handoff, eviction-gap handling, improvement-scan crash recovery)

---

## 1. Acceptance Criteria

Verbatim from `CONTEXT.md` §5.1, each followed by a measurable refinement (M-#).

### AC-1 — CQ spec covers required scenarios (§5.1 Acceptance, bullet 1)

> "CQ spec (`tests/comprehension/8694_spec.json`) covers: how the agent reacts to a mid-task event; how the agent handles an unknown event; what fires when `work_queue()` returns empty; what DM does after a PR merges while it was waiting; what an agent does if a comment on its issue requests a route-back; what the agent does on boot when working-state shows an improvement-scan with `Status: running`."

- **M-1.1** — `tests/comprehension/8694_spec.json` exists and validates as JSON with the schema `{issue:int, title:str, files:list[str], questions:list[{id,question,expected}]}`.
- **M-1.2** — The spec contains questions covering all six scenarios above, plus the additional CONTEXT-mandated topics enumerated in §5 below (≥8 questions total).
- **M-1.3** — `python references/scripts/run_comprehension_test.py tests/comprehension/8694_spec.json` exits 0 against the as-shipped fragments.

### AC-2 — Failsafe: agent works with harness fully down (§5.1 Acceptance, bullet 2)

> "Agent boots and works correctly with the harness fully down — completes forge scan, enters retry loop, operates in degraded mode against the forge directly, does not crash or hang."

- **M-2.1** — **Precondition: working-state.md pre-seeded to idle (no in-progress task, no scan `Status: running`).** With `127.0.0.1:<harness-port>` refusing connections, a fresh agent session must (a) load `working-state.md`, (b) call `tracker.py work-queue <role>` exactly once before any harness call, (c) emit no uncaught exception, (d) attempt `POST /events` for `bootup-complete` and observe failure, (e) schedule a retry with backoff bounded by 5 minutes (§3.1 step 5).
  - **Boot-with-in-progress variant (measurable refinement):** if working-state shows an in-progress tracker task, the agent boots → calls `tracker.py get-state <number>` to verify against forge BEFORE starting work. If forge state has changed (different role assigned, status != in-progress, etc.), the boot drops the task and falls through to fresh `work_queue()`. In this branch, `work_queue()` is NOT necessarily invoked first — the forge verification call is.
- **M-2.2** — While the harness stays down, the agent picks up the top forge item and runs the task end-to-end (writing a status transition via `tracker.py`).
- **M-2.3** — When the harness comes back, the next retry of `bootup-complete` succeeds (HTTP 200) and `event_poll.py` enters the listening loop within one retry interval.

### AC-3 — `event_poll.py` unit/integration coverage (§5.1 Acceptance, bullet 3)

> "`event_poll.py` unit/integration tests cover cursor-based polling, timeout behavior, and retry on transient harness errors."

- **M-3.1** — Unit tests assert (a) cursor parsed from `--since N` or stdin, (b) `GET /events?since=<cursor>` invoked with that value, (c) JSON-line stdout (one event per line, valid JSON), (d) `--wait N` translates to HTTP timeout, (e) retry on 5xx / connection error / timeout uses capped exponential backoff with a 300-second ceiling matching the boot retry policy (§5.1 deliverables note).
- **M-3.2** — Integration test: with a stub harness emitting 3 events, `event_poll.py <role>` writes exactly 3 JSON lines and the cursor advance behavior (per-event atomic `.tmp` + `mv`) is observed against `working-state.md`.

### AC-4 — Fresh-agent comprehension pass (§5.1 Acceptance, bullet 4)

> "Comprehension test passes with a fresh agent given only the new fragments."

- **M-4.1** — Spec `files` list MUST contain only fragments under `references/sub-skills/common-events/` and per-role `references/sub-skills/roles/<role>/events/` (no project-level L4, no SOUL, no `CONTEXT.md`). A fresh agent reading only those files must answer all questions.
- **M-4.2** — The CQ runner must exit 0 in CI (cache may shortcut subsequent runs).

### AC-5 — No mode-conditional language inside any fragment (§5.1 Acceptance, bullet 5)

> "No mode-conditional language inside any fragment (`if event-driven is yes, ...` is banned in fragment bodies)."

- **M-5.1** — Grep across `references/sub-skills/common-events/**` and `references/sub-skills/roles/*/events/**` for `event-driven:` and `if /loop` returns zero matches.
- **M-5.2** — Grep for "cycle_pre" / "cycle_post" / "30-minute" / "/loop" returns zero matches inside the event-mode fragment bodies (these belong to loop-mode tree only).

### AC-6 — No instructions outside the L1–L4 compose stack (§5.1 Acceptance, bullet 6)

> "No agent instructions live outside the L1–L4 compose stack. No standalone `l1-boot.md` fragment."

- **M-6.1** — There is no `references/sub-skills/**/l1-boot.md` file.
- **M-6.2** — The boot sequence text appears inside the event-mode L1 base fragment (e.g. `common-events/l1-base.md`) and is rendered into the composed `.squidsquad/<role>/CLAUDE.md` by `compose.py deploy <role>` when `event-driven: yes`.

### AC-7 — Heavy instruction-design content surface (§5.1 Acceptance, bullet 7)

> "Heavy instruction-design task — primary content surface for Phase 5."

- **M-7.1** — Coverage check: each topic in §5.1 "Deliverables" (cursor format, atomic update protocol, forge-read protocol, idle cooldown loop, comment handling + DM exception, transition-on-handoff, eviction gap, improvement-scan crash recovery, event_poll.py invocation instructions) has at least one section header in the event-mode L1 base or a sibling fragment.

---

## 2. Test Categories Map

| Acceptance | Measurable | Category | Owner |
|------------|------------|----------|-------|
| AC-1 | M-1.1 | unit | dev (skill) |
| AC-1 | M-1.2 | unit | dev (skill) |
| AC-1 | M-1.3 | comprehension | QA |
| AC-2 | M-2.1 | integration (negative — harness down) | QA |
| AC-2 | M-2.2 | integration | QA |
| AC-2 | M-2.3 | integration | QA |
| AC-3 | M-3.1 | unit | dev (skill) |
| AC-3 | M-3.2 | integration | dev (skill) → QA verifies |
| AC-4 | M-4.1 | unit (grep / file-list audit) | dev (skill) |
| AC-4 | M-4.2 | comprehension | QA |
| AC-5 | M-5.1, M-5.2 | negative (grep guard) | dev (skill) |
| AC-6 | M-6.1 | negative (file existence) | dev (skill) |
| AC-6 | M-6.2 | integration (compose round-trip) | dev (skill) |
| AC-7 | M-7.1 | unit (coverage grep) | dev (skill) |
| — Cross-cutting | Crash-recovery during scan | integration | QA |
| — Cross-cutting | Eviction gap | integration | QA |
| — Cross-cutting | Cool-down sleep cancelled by event | manual smoke | PM/QA |

---

## 3. Unit Tests

All under `tests/test_event_poll.py` unless noted. Each test name encodes the behavior tested.

### 3.1 `event_poll.py` cursor parsing

- **`test_event_poll_cursor_from_arg`** — `event_poll.py skill --since 42` issues `GET /events?since=42&role=skill`.
- **`test_event_poll_cursor_from_working_state`** — When `--since` is omitted, the script reads `Last Processed Event ID: <n>` from `.squidsquad/<role>/working-state.md` and uses it.
- **`test_event_poll_cursor_missing_defaults_to_zero`** — If neither flag nor working-state has a cursor, default `since=0` and log a warning to stderr.

### 3.2 Retry & backoff math

- **`test_event_poll_backoff_doubles_until_cap`** — Simulated `requests.ConnectionError` → assert sleeps follow `[1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, ...]` (capped at 300s per §5.1 deliverables).
- **`test_event_poll_backoff_resets_on_success`** — After a successful response, the next failure starts the backoff sequence at 1s again.
- **`test_event_poll_retries_on_5xx`** — HTTP 500/503 → retried with backoff.
- **`test_event_poll_retries_on_timeout`** — `requests.Timeout` → retried.
- **`test_event_poll_does_not_retry_on_4xx`** — HTTP 400/404 → exits non-zero, no retry (caller fault).

### 3.3 JSON-line streaming

- **`test_event_poll_one_json_line_per_event`** — Stub harness returns `[{e1}, {e2}, {e3}]`; stdout has exactly 3 lines, each parsable JSON, in order.
- **`test_event_poll_flushes_per_event`** — stdout is line-buffered (write/flush after each event). Verified with `sys.stdout.flush` mock or by reading from a pipe.
- **`test_event_poll_empty_response_yields_no_lines`** — Stub returns `[]`; stdout is empty (the script still loops/waits, but writes nothing).

### 3.4 Timeout handling

- **`test_event_poll_wait_flag_translates_to_http_timeout`** — `--wait 5` ⇒ `requests.get(..., timeout=5)`.
- **`test_event_poll_returns_on_wait_expiry`** — When wait elapses with no events, the script either keeps polling (long-running mode) or exits 0 cleanly if `--once` (whichever is documented).

### 3.5 Cursor advancement semantics

- **`test_event_poll_atomic_cursor_write`** — When advancing the cursor, the script writes `<working-state>.tmp` then `mv` (or `os.replace`) — verified by intercepting filesystem calls.
- **`test_event_poll_cursor_advances_per_event_not_per_batch`** — A batch of 3 events ⇒ 3 separate writes (one per event), each persisting before the next event is emitted on stdout.

### 3.6 Spec file integrity (AC-1, AC-4, AC-7)

Under `tests/test_comprehension_8694.py`:

- **`test_8694_spec_valid_json`** — File parses; required keys present.
- **`test_8694_spec_files_only_event_fragments`** — Every path in `files` starts with `references/sub-skills/common-events/` or `references/sub-skills/roles/<role>/events/`.
- **`test_8694_spec_covers_required_topics`** — At least one question matches each of: mid-task event, unknown event, empty work_queue, DM end-of-task comments, comment-driven route-back, scan-running boot.

### 3.7 Compose round-trip (AC-6)

- **`test_event_mode_compose_includes_l1_base`** — Set `event-driven: yes` in a test config, run `compose.py deploy <role>` in a tmpdir, assert the produced CLAUDE.md contains the boot sequence header (e.g. `## Boot Sequence (Event Mode)`) AND no `l1-boot.md` was emitted as a standalone fragment.
- *(Mode-conditional grep guard is owned exclusively by §6.6 — see `test_no_mode_conditional_in_event_fragments`. Removed duplicate from this section per review F3.)*

---

## 4. Integration Tests

Add under `tests/integration/test_event_mode_e2e.py` (skip with `@pytest.mark.integration` when harness deps absent).

### 4.1 Happy-path end-to-end (AC-3 M-3.2, AC-2 M-2.3)

1. Start a real `harness.py` on a random port.
2. Seed a forge stub (or use a sandboxed `tracker.py` against a test repo) with one open issue assigned to `skill`.
3. Spawn agent shell that reads composed event-mode CLAUDE.md and is allowed to: read working-state, call `tracker.py`, invoke `event_poll.py`, POST events.
4. Assert sequence: working-state read → `work_queue()` call → `bootup-complete` posted (harness `GET /agents/skill` flips `bootup_complete=true`) → `event_poll.py` running.
5. Push a synthetic `status-transition` event for the picked-up item via `POST /events`.
6. Assert agent does NOT call forge again until the current task ends (atomicity rule §2 / §3.4), then re-runs `work_queue()` after task completion.

### 4.2 Crash recovery — mid-task (AC-2 / Cross-cutting)

1. Spawn agent on a tracker task; let it begin work and write `Status: in-progress` to working-state.
2. Kill the agent process mid-task (SIGKILL).
3. Inspect `.squidsquad/<role>/working-state.md` — must contain cursor + in-progress task fields preserved (atomicity rule for cursor writes).
4. Restart agent (fresh session, harness alive).
5. Assert agent (a) reads working-state, (b) **verifies against forge** the item is still `status:in-progress` AND still assigned to its role, (c) resumes (or drops if forge says otherwise per §3.1 step 2 first branch).

### 4.3 Crash recovery — improvement scan (§3.6 / §11 glossary)

1. Force agent into idle and start an improvement scan; ensure `working-state.md ## Improvement Scan` shows `Status: running`.
2. Kill the agent.
3. Restart agent.
4. Assert agent (a) skips forge verification step for the scan, (b) restarts the scan from scratch (idempotency), (c) on completion writes `Status: idle`, `Last completed`, `Next scan after` — values from `config.md` cooldown read at completion (NOT stored).

### 4.4 Eviction gap (§2 third bullet · CONTEXT §3.1 step 3) — IT-EvictionGap

**DEFERRED — blocked on precondition #9331.** Step 4(a)/(b) require the agent to receive an eviction signal from the harness and log a warning naming the oldest available id and the count of evicted events. Code reality (skill investigation cycle 1179):
- `harness.EventStream.get_since` returns the oldest retained events with no eviction marker when the cursor is not in the deque.
- `event_poll.py` has no eviction-detection or warning logic.

#9331 (skill, medium) lands the precondition: harness response shape carries `evicted: true, oldest_id, evicted_count_hint` when cursor not found; event_poll.py emits the stderr warning + advances cursor. Once #9331 ships, this scenario is testable as written and #8999 picks it back up. Same DEFERRED pattern as §4.9 / #9265.

Original spec (preserved for traceability, restore once #9331 ships):

1. Start harness; let it accumulate >1000 events (or simulate by setting `maxlen=10` in test config) until the deque rolls.
2. Pre-set agent `Last Processed Event ID` to a cursor that predates the oldest retained event.
3. Boot agent.
4. Assert agent: (a) calls `GET /events?since=<old>` and observes empty/eviction signal, (b) logs an eviction warning naming the oldest available id and the count of evicted events, (c) advances cursor to the oldest available id, (d) does NOT crash, (e) proceeds to forge-read for current state.

### 4.5 Harness-down boot (AC-2 M-2.1, M-2.2, M-2.3)

1. Ensure harness is **not** running. Pre-seed `working-state.md` to idle.
2. Boot agent.
3. Assert: (a) `work_queue()` is invoked, (b) `POST /events` for `bootup-complete` fails (connection refused), (c) agent does NOT crash, (d) agent picks up forge top item and proceeds, (e) retry timer is scheduled with backoff bounded by 5 minutes.
4. Start harness mid-task.
5. Assert eventual `bootup-complete` success and entry into `event_poll.py` listening loop (without interrupting the in-flight task — atomicity).

### 4.6 Transition-on-handoff (§5.1 deliverables)

1. Force agent to reach a point where it would assign work to a different role (e.g. PM transitions `in-progress → planning` mid-task to halt a worker, or skill routes a bug to QA).
2. Assert the handoff is implemented as a `tracker.py transition` (status change), NOT a bare comment.
3. Assert the resulting `status-transition` event appears on the event stream and is observable by `event_poll.py` on the receiving role.

### 4.7 Comment handling + DM exception (§3.7)

1. **Non-DM**: Add a comment to a non-active issue. Assert agent does NOT wake; only reads the comment when it next picks the issue up.
2. **DM**: Place DM in PR-merge wait. Add a comment to that issue during the wait. Assert DM does NOT enter a sub-loop, completes the merge wait, and only re-reads comments at task completion (end of merge wait).

### 4.8 `stop-requested` mid-task (CONTEXT §3.5) — IT-StopRequested

1. Spawn agent on a tracker task; let it begin work and write `Status: in-progress` to working-state.
2. Mid-task: POST `stop-requested` event to the harness.
3. Assert the agent reads the event at cursor+1, advances the cursor atomically, but does NOT act on it (atomicity rule). The current task continues to run.
4. Allow the task to reach its boundary (completion or natural stopping point).
5. Assert at task boundary: agent **checkpoints `working-state.md`** (preserves cursor + final state) and **exits cleanly** (no dangling work, no half-written outputs).
6. Restart the agent. Assert the boot path (§3.1) loads the checkpointed working-state and proceeds correctly.

### 4.8b Idle + event arrival (CONTEXT §3.2 Case B) — IT-CaseB

1. Drive the agent into idle: ensure `work_queue()` returns empty so the agent enters the improvement-scan cool-down loop. Verify `working-state.md ## Improvement Scan` shows `Status: idle`, `Next scan after: <future ts>`.
2. While the agent is sleeping with timeout = remaining cool-down, POST a `status-transition` event to the harness for an item now assigned to this role.
3. Assert: cool-down sleep is cancelled before `Next scan after`, the agent reads the event at cursor+1, runs `work_queue()` against the forge, picks up the next item (or stays idle if empty), and advances the cursor atomically.
4. Verify cursor is monotonically advanced and the agent does NOT skip events between the prior cursor and the wake-causing event.

### 4.9 In-stream gap (CONTEXT §2 first gap scenario) — IT-CursorGapInStream

**DEFERRED — not implementable as written.** Event ids in `harness.py` are `os.urandom(4).hex()` (random 8-char hex, see harness.py:1920) — there is no monotonic sequence, so an agent has no way to detect that "event 4" is missing between observed ids. Only eviction gaps (deque rollover, §4.4) are detectable.

Resolution required before this scenario can ship — handled out-of-band on a follow-up task:
- **Option A**: Update CONTEXT-8694.md §2 to remove the in-stream gap scenario (only eviction-gap remains). Simpler; aligns with current id model.
- **Option B**: Switch harness event ids to monotonic ints, then implement gap-detection in event_poll.py. Larger change; gives the agent a stronger guarantee but adds harness complexity.

This scenario is dropped from #8999's scope. A follow-up task tracks the CONTEXT-vs-code decision.

### 4.10 Long cursor lag (CONTEXT §2 second gap scenario) — IT-CursorLongLag

1. Pre-seed agent `Last Processed Event ID` to a cursor that is far behind the current head, but still within the retained window (e.g., 24h+ of idle accumulation; deque has NOT rolled).
2. Accumulate 50+ events in the harness deque ahead of the cursor.
3. Boot agent.
4. Assert: agent **skims events sequentially** (does not jump-to-latest), cursor advances **incrementally** event-by-event (per-event atomic `.tmp` + `mv` write observed), no event is silently dropped, agent eventually reaches the current head, and forge-read on next decision absorbs any state that mattered.

---

## 5. Comprehension Test Specs (AC-1, AC-4)

Per memory rule `feedback_comprehension_tests_required`, this section is mandatory and must drop into `tests/comprehension/8694_spec.json` as-is.

### 5.1 Spec format

`run_comprehension_test.py` expects:

```json
{
  "issue": <int>,
  "title": "<str>",
  "files": ["<repo-relative path>", ...],
  "questions": [
    {"id": "<str>", "question": "<str>", "expected": "<str>"}
  ]
}
```

The pipeline spawns a fresh Claude that may only `Read` the listed files, writes answers, then a second Claude grades them against the `expected` field for behavioral correctness.

### 5.2 `tests/comprehension/8694_spec.json` (complete, drop-in)

> Note: file paths use the illustrative naming from `CONTEXT.md` §5.1. Implementation can rename per #8697; the spec must then be updated to match shipped paths.
>
> **Per-role fragments deliberately omitted (review F6):** the CQ spec validates the role-agnostic event-mode L1 base contract. Per-role events fragments (skill / pm / qa / dm) for role-specific behavior on top of the common contract are not yet locked (see §10 open questions) and are excluded from this spec to avoid asymmetric coverage. Questions Q5 (DM end-of-task) and Q6 (comment-driven route-back) are answerable from `l1-base.md` and `comment-handling.md` alone — the DM exception is documented in `comment-handling.md` as the role-agnostic contract.

```json
{
  "issue": 8694,
  "title": "Event-mode L1 base agent definition (boot, reactions, cursor, idle cooldown, comments, transitions)",
  "files": [
    "references/sub-skills/common-events/l1-base.md",
    "references/sub-skills/common-events/cursor-management.md",
    "references/sub-skills/common-events/forge-read-pattern.md",
    "references/sub-skills/common-events/idle-cooldown-loop.md",
    "references/sub-skills/common-events/comment-handling.md"
  ],
  "questions": [
    {
      "id": "1",
      "question": "An agent boots and its working-state.md shows an in-progress tracker task. What exactly must the agent do before resuming that task, and under what conditions does it drop the task instead of resuming?",
      "expected": "The agent must verify the in-progress task against the forge via tracker.py: confirm the item is still labelled for this role AND still status:in-progress. If both checks pass, resume. If either fails, drop the task and run work_queue() to pick the next item. The verification step is mandatory — agents do not trust working-state alone."
    },
    {
      "id": "2",
      "question": "An event arrives in the event stream while the agent is in the middle of running a tracker task. How does the agent react? Does it process the event payload immediately?",
      "expected": "The agent reads the event at cursor+1 and advances the cursor atomically, but does NOT act on the event. The current task runs to completion (atomicity rule). When the task ends, the agent re-runs work_queue() against the forge — current forge state subsumes any mid-task events. Event payloads are never trusted as state; they are triggers only."
    },
    {
      "id": "3",
      "question": "An agent receives an event with an event_type it does not recognize. What should it do?",
      "expected": "Log a warning, advance the cursor past the event, and continue. Unknown event types must not block the agent. Forge-read on the next decision will recover any state that mattered."
    },
    {
      "id": "4",
      "question": "An agent runs work_queue() against the forge and the result is empty. What happens next? Where is the cool-down timestamp stored, and where does the cool-down value itself come from?",
      "expected": "The agent enters idle: run an improvement-scan as an atomic task, then sleep on the event stream until the cool-down elapses. The Improvement Scan section of .squidsquad/<role>/working-state.md stores Status (idle | running), Last completed, and Next scan after timestamps. The cool-down value itself is NOT in working-state — it is read from config.md at scan-completion time, default 30 minutes, so config changes take effect on the next scan boundary."
    },
    {
      "id": "5",
      "question": "DM has been waiting for a PR to merge. During the wait, three comments are posted on the issue requesting changes. How and when does DM respond to those comments?",
      "expected": "DM does not enter a sub-loop during the wait. The PR-merge wait is one atomic task. DM re-reads the issue comments at task completion (end of merge wait) before the next pickup. Comments arriving during the wait are honored when the wait ends. Senders who need a faster reaction must use a status transition or label change, not a bare comment."
    },
    {
      "id": "6",
      "question": "A comment is posted on an open issue asking the agent to route the work back to a different role. The issue is not currently in progress. How does the agent see this comment, and what is the rule about comments as triggers?",
      "expected": "Comments are NOT standalone event triggers. The agent only reads the comment when it next picks up that issue. Urgent inter-agent signaling must ride a status transition or label change, not a bare comment. Bare comments will not wake anyone."
    },
    {
      "id": "7",
      "question": "On boot, working-state.md shows the Improvement Scan with Status: running (not a tracker item). What does the agent do, and why?",
      "expected": "The agent SKIPS forge verification (the scan is not a tracker item) and restarts the improvement scan from scratch. Improvement scans are idempotent — a fresh scan subsumes a partial one. This is the crash-recovery semantics for the scan."
    },
    {
      "id": "8",
      "question": "An agent decides to hand work off to a different role (or to a human). What is the correct mechanism for the handoff, and what mechanism is forbidden?",
      "expected": "The handoff MUST be a status transition via tracker.py (e.g. transition to a role label change, or to a pending-human-* status). This appears on the event stream and wakes the recipient. Bare comments are NOT a valid handoff mechanism — they will not wake the recipient role."
    },
    {
      "id": "9",
      "question": "How does the agent advance its Last Processed Event ID cursor, and why must this write be atomic?",
      "expected": "The cursor is advanced one event at a time: write the new value to working-state.md.tmp, then mv/rename onto working-state.md. No batching — one atomic write per processed event. Atomicity prevents partial writes if the agent or OS crashes; combined with the forge-read pattern, this gives idempotent replay (re-processing an event yields the same action because action is computed from current forge state, not payload)."
    },
    {
      "id": "10",
      "question": "The agent boots and tries to emit bootup-complete, but the harness is unreachable. What happens to the agent's work, and what is the retry policy?",
      "expected": "The agent does NOT hang. bootup-complete emission is best-effort, not blocking. The agent operates in degraded mode: works directly from the forge via work_queue(), retries bootup-complete with exponential backoff capped at 5 minutes. When the harness becomes reachable, bootup-complete is emitted and the agent enters the event-listening loop via event_poll.py."
    }
  ]
}
```

Topic coverage (cross-check against §5.1 and AC-1):

| # | Topic | Spec Q |
|---|-------|--------|
| Boot resume rule (forge verification) | Q1 |
| Work pickup order / atomicity | Q2 |
| Unknown event handling | Q3 |
| Cool-down schema fields + config source | Q4 |
| DM end-of-task comment exception | Q5 |
| Comment-handling rule (not standalone triggers) | Q6 |
| Improvement-scan crash recovery | Q7 |
| Transition-on-handoff rule | Q8 |
| Cursor advancement + atomicity | Q9 |
| Harness-down degraded boot + retry cap | Q10 |

### 5.3 Pytest harness skeleton (no test code yet)

Drop in `tests/test_comprehension_8694.py`:

```python
"""Comprehension test wrapper for #8694 event-mode L1 base.

Skeleton only — the run is delegated to run_comprehension_test.py.
"""

# import pathlib
# import pytest
# import subprocess
# import sys
#
# REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
# SPEC = REPO_ROOT / "tests" / "comprehension" / "8694_spec.json"
# RUNNER = REPO_ROOT / "references" / "scripts" / "run_comprehension_test.py"
#
#
# @pytest.mark.comprehension
# def test_event_mode_l1_base_comprehension():
#     """Fresh agent reads only event-mode fragments and answers correctly."""
#     # TODO: invoke runner; assert exit code 0.
#     # TODO: optionally pass --force when fragments change.
#     ...
#
#
# @pytest.mark.unit
# def test_spec_paths_only_event_fragments():
#     """AC-4 M-4.1 guard: spec.files only references event-mode fragments."""
#     # TODO: load SPEC; assert every path starts with the allowed prefixes.
#     ...
#
#
# @pytest.mark.unit
# def test_spec_covers_required_topics():
#     """AC-1 M-1.2 guard: required topics each appear in at least one question."""
#     # TODO: load SPEC; for each topic keyword set, find ≥1 matching question.
#     ...
```

---

## 6. Negative Tests

Each guards an explicit "MUST NOT" property from §2/§3.

### 6.1 Mid-task event side-effects (CONTEXT §3.4)

- **`test_agent_does_not_act_on_mid_task_event`** — During an in-flight task, push a `status-transition` event for an unrelated issue. Assert NO new `tracker.py work-queue` invocation and NO new `tracker.py transition` call until the in-flight task ends.

### 6.2 Forge-poll discipline (CONTEXT §3.3, §3.4)

- **`test_agent_does_not_forge_read_on_every_event`** — Push 5 events while the agent is mid-task. Assert exactly one forge-read at task completion (not 5 — events are triggers only).

### 6.3 No runtime degraded mode (CONTEXT §11 glossary "Degraded mode" + §5.1)

- **`test_agent_does_not_pivot_to_forge_after_bootup_complete`** — Once `bootup-complete` is emitted, force the harness to drop. Assert agent retries `event_poll.py` with capped backoff and does NOT switch to forge-direct dispatch. (Mid-operation harness failure is an operator-recovery scenario; degraded mode is boot-only.)

### 6.4 Cursor on processing failure (CONTEXT §2 "Cursor advancement = per-event, atomic")

- **`test_cursor_does_not_advance_when_processing_fails`** — Inject a processing error (e.g. `tracker.py` 500). Assert cursor remains at pre-event value; the agent retries from the same cursor on the next pass. (Atomic write must follow successful processing — otherwise replay is unsafe.)

### 6.5 Boot forge-verify is mandatory (CONTEXT §3.1 step 2)

- **`test_boot_with_in_progress_does_not_skip_forge_verify`** — Pre-seed working-state with an in-progress task. Assert `tracker.py get-state <number>` (or equivalent) is called BEFORE the agent resumes. Resuming without the verify step is a fail.

### 6.6 No mode-conditional language (AC-5)

- **`test_no_mode_conditional_in_event_fragments`** — Grep guard. The string `event-driven:` must not appear as a branching instruction inside any event-mode fragment body.

### 6.7 No standalone l1-boot fragment (AC-6)

- **`test_no_standalone_l1_boot_md`** — `glob('references/sub-skills/**/l1-boot.md')` is empty.

---

## 7. Manual Smoke Tests

These are operator/PM checklists, run during the per-role pre-flip review (§6.3). Tracked in TEST-PLAN.md so QA can re-execute when needed.

1. **Single-agent happy path**
   - Start harness on a fresh checkout. Set `event-driven: yes` for one role in a test `.squidsquad/config.md` and `compose.py deploy <role>`.
   - Boot the agent. Observe: working-state read → `tracker.py` queue call → `bootup-complete` emitted → `event_poll.py` listening. Visible in the harness TUI when #8700 ships.
   - Confirm the agent picks up the top forge item, executes one transition, then re-runs `work_queue()` without waiting for the bounce-back event (CONTEXT §3.3).
2. **working-state shape**
   - After each transition, manually `cat .squidsquad/<role>/working-state.md`. Verify the cursor incremented exactly by the number of events processed, and the `Last Processed Event ID` value is monotonically increasing.
3. **Cool-down cancellable by event**
   - Empty the work queue. Observe `Status: idle`, `Last completed`, `Next scan after` populated under `## Improvement Scan`.
   - Confirm the agent is sleeping with timeout = remaining cool-down.
   - Trigger a relevant event (e.g. assign a new issue to the role). Confirm the agent wakes immediately (before `Next scan after`) and runs `work_queue()`.
4. **Improvement-scan after empty queue**
   - With work queue empty, allow cool-down to elapse with no events. Confirm the agent runs the improvement scan exactly once per cool-down tick (not a tight loop), writes `Status: running` at start and `Status: idle` + new timestamps at completion.

---

## 8. Gating Conditions

### Hard prereqs (block ship of #8694)

- **#8692 — singleton enforcement** MUST be shipped before any role flips `event-driven: yes` in `config.md` (CONTEXT §6.1). #8694 fragments may be authored and merged in parallel, but the per-role flip waits on #8692.
- **#8699 (absorbed into #8697)** — the `event-driven-workflow` source fragment migration must exist before `compose.py deploy <role>` can produce a clean events-mode CLAUDE.md (CONTEXT §6.2). Therefore #8697 must ship to land #8694's fragments in a useful deployed output.
- **#8695 — `bootup_complete` flag** — informational only, but the boot sequence references the field. Recommend shipping #8695 in the same release window so TUI/operators can observe boot status.

### Standard tracker.py transition gates

- Plan-checker gate (Phase 3B): the planning PR for #8694 must be approved by a human before status moves `Planned → Approved`.
- Status authority per `tracker.py:transition` legal-flow map (PM-instructions §"Status Transitions"). PM/QA cannot bypass.

### Pre-flip checklist enforcement (CONTEXT §6.3, per role)

Before flipping `event-driven: yes` for any role:

1. #8692 shipped.
2. #8697 shipped (events-mode tree exists, no `/loop` residue in any fragment body for this role).
3. L4 audit passed for the role's project instructions.
4. #8694 fragments deployed for the role.
5. #8695 deployed.
6. `compose.py deploy <role>` produces a CLAUDE.md with zero `/loop` language and the events-mode boot sequence at L1.

---

## 9. Post-Ship Validation

### 9.1 Soak validation

- One role flipped to `event-driven: yes`. Agent runs ≥ N consecutive task cycles in event mode without falling back to `/loop`. Recommended initial N: 5 cycles per role (operator/PM judgment; §7 says PM picks soak duration).
- Monitor (a) `bootup_complete=true` in `GET /agents/<role>`, (b) no `event_poll.py` crash log, (c) cursor advances monotonically, (d) no orphaned `Status: running` in working-state after each task.

### 9.2 Failure-mode probes

- **Probe A — Harness kill mid-operation** (per CONTEXT §11 "Degraded mode" glossary: mid-operation harness failure is a **manual-recovery** scenario, not auto-reconnect): stop the harness while a role is mid-task. Confirm:
  - (a) Agent does NOT pivot to forge-direct (negative test 6.3 in production).
  - (b) `event_poll.py` retries with capped 5-minute backoff (verifiable from stderr log).
  - (c) Agent completes or checkpoints its current task and logs state to the forge.
  - (d) After harness restart **AND agent restart (if needed)**, the agent boots via the L1 failsafe (§3.1) and recovers state from the forge. Automatic reconnection is **not** guaranteed by the architecture; this probe verifies the documented manual-recovery boundary.
- **Probe B — Forced eviction gap**: pre-seed cursor before oldest retained event. Confirm agent logs eviction details, advances to oldest available id, does NOT crash.
- **Probe C — Mid-task SIGKILL on agent**: working-state preserves cursor + in-progress fields. Restart agent. Confirm forge-verify path runs and the task resumes (or drops correctly).
- **Probe D — Improvement-scan crash**: kill agent mid-scan. Confirm fresh boot restarts the scan idempotently and does not double-write `Last completed`.

### 9.3 Roll-back plan

- For a single role: edit `.squidsquad/config.md` → `event-driven: no` for that role.
- Run `compose.py deploy <role>` — `compose.py` reads the flag, swaps to `includes-loop.yml`, and re-renders CLAUDE.md from the loop-mode tree (CONTEXT §4.3).
- Restart that role via `start_team.py --reboot <role>`. Confirm the agent re-enters `/loop` boot (Step 1c "Resume From Working State").
- No code revert required — the rollback is a config flip + recompose, exercising the dual-tree failsafe isolation property (CONTEXT §4.4).
- For full rollback across all roles, repeat per-role.

---

## 10. Open Questions / Gaps Surfaced During Planning

These are forwarded to the human/PM rather than answered here.

1. **Final fragment file naming.** CONTEXT §5.1 lists illustrative names (`common-events/l1-base.md`, `cursor-management.md`, etc.) but defers final naming to #8697 (CONTEXT §10 open Q1). The CQ spec `files` list MUST be updated to track whatever #8697 ships. Recommend: PM publishes the locked filenames before this TEST-PLAN goes to dev pickup, or dev updates the spec atomically when fragments land.
2. **`event_poll.py` invocation surface.** CONTEXT §5.1 says "instructions to invoke `event_poll.py` are composed into the event-mode L1 base." Should the invocation be (a) a direct bash command shown in the fragment, (b) wrapped by `cycle_pre.py`/`cycle_post.py` in events mode (overlapping with #8701), or (c) a thin wrapper script that handles re-launching? Not specified in CONTEXT. Recommend dev raises this in #8694's Discussion before implementing.
3. **`--once` vs long-running.** CONTEXT §5.1 specifies cursor-based polling with stdout JSON-lines but does not lock whether `event_poll.py` exits after first batch (`--once`) or stays resident. Unit test 3.4 references both options. Suggest PM/dev align before writing the script's flag surface.
4. **Cool-down config key.** CONTEXT §2/§3.6 says the cool-down value is read from `config.md` at scan-completion time but does not name the key. Recommend `improvement-scan-cooldown: 30m` (or numeric minutes); confirm with #8697 author since `_read_config_value()` is shared.
5. **Per-role events-mode fragment depth.** §5.1 lists `roles/{pm,skill,qa,dm}/events/*.md` but only DM has a specific deliverable (`pr-merge-wait.md`). Whether PM/QA/skill need their own role-specific events fragments at all (or can rely on `common-events/`) **is not yet locked — deferred to implementation**. Per review F6, the CQ spec (§5.2) excludes per-role fragments to keep coverage symmetric across roles; Q5/Q6 must be answerable from the role-agnostic `l1-base.md` + `comment-handling.md`. When per-role fragments are locked, the spec's `files` list may be extended symmetrically across all four roles.
6. **`event_poll.py` retry semantics on partial JSON.** What happens if the harness returns malformed JSON mid-stream (network truncation)? CONTEXT does not specify. Conservative default: log and retry from current cursor; do not advance. Flag for dev to confirm.

---

## 11. Traceability Matrix

| CONTEXT.md citation | Section here |
|---------------------|--------------|
| §3.1 (Case A — Boot) | AC-2, 4.5, 4.2, 6.5, CQ Q1, Q10 |
| §3.2 (Case B — Idle/event) | 4.8b (IT-CaseB), CQ Q4 |
| §3.3 (Case C — After completion) | 4.1 (step 6), §7 smoke 1 |
| §3.4 (Case D — Mid-task event) | 6.1, 6.2, CQ Q2 |
| §3.5 (Case E — Special events: stop-requested) | 4.8 (IT-StopRequested), CQ Q3 (unknown) |
| §3.6 (Idle cooldown loop) | 4.3, §7 smokes 3-4, CQ Q4, Q7 |
| §3.7 (Comments + DM exception) | 4.7, CQ Q5, Q6 |
| §5.1 deliverables (transition-on-handoff) | 4.6, CQ Q8 |
| §2 (cursor atomic write) | 3.5, 6.4, CQ Q9 |
| §2 (in-stream gap) | 4.9 (deferred — see §4.9 note) |
| §2 (long cursor lag) | 4.10 (IT-CursorLongLag) |
| §2 (eviction gap) | 4.4, §9.2 Probe B |
| §11 (degraded mode boot-only) | 6.3, §9.2 Probe A |
| §5.1 (event_poll.py spec) | 3.1-3.5, 4.1 |
| §6.3 (pre-flip checklist) | §8 gating, §9.3 rollback |

---

*End of TEST-PLAN-8694.md*
