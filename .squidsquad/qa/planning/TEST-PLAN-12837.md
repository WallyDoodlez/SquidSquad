# TEST-PLAN-12837 — Harness emits anchorless eviction marker → kills event listener

Bug (type:issue, auto-approved). Filed by qa (verifier). PR #12959, branch
`squidsquad/task/12837`. No explicit AC list → ACs derived from the bug report's
evidenced root-cause + suggested remediation. Code-only harness fix → **no CQ**.
Verified in isolated worktree `D:\Dev\Dev\sq-12837-verify`.

**Self-relevant:** this is the exact bug that killed THIS verifier session's Monitor
(event_poll exit 2). Picked up via the idle-driver cron safety-net forge-read after
the Monitor death (the missed-nudge backstop working as designed).

## Derived ACs
- **AC1 (root-cause fix):** the harness eviction path no longer emits the fatal
  triple `evicted:true` + `events:[]` + `oldest_id:null`. When the cursor predates
  the window AND the deque is EMPTY (cold-start / fully-churned, no anchor),
  `get_since_with_eviction` returns `([], None)` — a benign empty result, no marker.
- **AC2 (marker integrity):** whenever a marker IS emitted, `oldest_id` is a real
  retained id, never None.
- **AC3 (endpoint propagation):** `/events` and `/events/for/{role}` set
  `response["evicted"]=True` ONLY when the marker is non-None → a None marker yields
  a plain `{events:[], total}` with no `evicted`/`oldest_id` keys.
- **AC4 (recoverable variant intact):** non-empty deque + stale cursor still emits a
  marker with a real `oldest_id` (the recoverable eviction-gap path agents handle at boot).
- **AC5 (guard preserved):** `event_poll.py`'s fatal guard for the genuinely-
  unrecoverable case is unchanged (PR touches harness.py + test only) — defense-in-depth.
- **AC6 (regression test):** a test reproduces the original empty-deque+stale-cursor
  condition and asserts marker suppression; would have caught the original defect.

## Test cases
- **TC1 (AC1)** — live repro on branch: `EventStream(maxlen=10).get_since_with_eviction('stale')` → `([], None)`.
- **TC2 (AC2/AC4)** — live: non-empty deque + stale cursor → marker with `oldest_id` real.
- **TC3 (AC3)** — inspect /events (h.py ~3052) + /events/for (~3131): both `if eviction is not None:` gate.
- **TC4 (AC5)** — confirm event_poll.py not in diff (guard unchanged).
- **TC5 (AC6)** — test_eviction_signal.py (test_empty_deque_with_evicted_cursor_suppresses_marker, test_eviction_marker_oldest_id_is_never_none).
- **TC6 (no-reg)** — full `run_tests.py static`.

## Evidence (live)
- Independent repro: A) empty+stale → `events=[] marker=None` (fatal triple impossible); B) non-empty+stale → `marker={'oldest_id':'e0',...}` (recoverable intact). PASS.
- test_eviction_signal.py → 16 passed.
- Endpoints both gate on `if eviction is not None` (h.py:3052 /events, h.py:3131 /events/for).
- event_poll.py NOT in PR diff → fatal guard preserved.
- Static gate: (pending — see QA-RESULTS).
