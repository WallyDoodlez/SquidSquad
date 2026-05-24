I've completed a thorough re-review of `docs/AGENT-RUNTIME.md`. All 12 round-1 fixes are confirmed applied. However, I found **6 new issues** — contradictions introduced by incomplete updates, stale diagrams, and underspecified edge cases in the locked routing table.

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 1013 (glossary)
- **Severity**: MED
- **Issue**: Glossary defines "Improvement subloop" as "token-throttled self-care work" but §7.6 line 884 explicitly says "time-based, NOT token-counting." Round-1 fix #12 relabeled the throttle but the glossary was not updated.
- **Evidence**: Line 1013: `- **Improvement subloop**: token-throttled self-care work…` vs line 884: `**Throttle** (time-based, NOT token-counting)`.
- **Suggested fix**: Change line 1013 to read "time-throttled self-care work the agent runs when its queue is empty (event mode only)."

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 324–347 (cursor model sequence diagram)
- **Severity**: MED
- **Issue**: The cursor model diagram still shows the pre-migration architecture where cursor lives in `working-state.md`. Participant `WS` is `working-state.md`, the note says "Last Processed Event ID: a1b2c3d4" (line 331), `CP->>WS: Read cursor (loop mode)` (line 333), and `H-->>WS: cursor advances to g7` (line 343). But §4.3 line 316 says cursor was "migrated to harness" and §5 line 494 says cursor is in `.event-state.json`, owned by harness.
- **Evidence**: The text at line 316 explicitly states: "Per-role, owned by harness (was per-agent in `working-state.md` pre-`#9873-A`; migrated to harness)." The diagram participants and arrows contradict this migration.
- **Suggested fix**: Replace participant `WS` with a harness-state representation (e.g., `.event-state.json`), remove the note about "Last Processed Event ID" in working-state, and route the cursor-advance arrow to harness state, not `working-state.md`.

---

### Finding 3

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 777–778, 781 (tracker.py auto-routing table)
- **Severity**: MED
- **Issue**: The routing table's `pending-ship → in-progress` (line 778) and `planned → approved` (line 781) rows specify `target_role` = `assigned role` (from `role:*` label) but provide no fallback when the label is missing. The `pending-test → in-progress` row (line 777) has an explicit fallback: `if none, route to pm with event_context="unowned-rejection"`. The other two "assigned role" rows lack equivalent guardrails.
- **Evidence**: Line 777: `assigned role from role:* label; if none, route to pm…` vs line 778: `assigned role` (no fallback) and line 781: `assigned role` (no fallback). In production, a missing `role:*` label on a `pending-ship → in-progress` transition (DM merge-conflict rejection) or `planned → approved` transition (PM approving) would produce an undefined or failed `/work/assign` call.
- **Suggested fix**: Add fallback to PM for both rows, e.g.: `assigned role from role:* label; if none, route to pm with event_context="unowned-rejection"` for line 778, and `assigned role from role:* label; if none, route to pm with event_context="unowned-approval"` (or similar) for line 781.

---

### Finding 4

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 586 (event_poll polling cadence)
- **Severity**: LOW
- **Issue**: The event_poll adaptive backoff rule says "N consecutive empty polls? → step up to 30s" without specifying N. The EAD cadence (§4.4 line 393) specifies "3 consecutive empty polls." An implementer cannot determine when event_poll should back off.
- **Evidence**: Line 586: `N consecutive empty polls? → step up to 30s` vs line 393: `3 consecutive empty polls? → step up to 30s`. Neither §9 Q4 nor any other section defines N for event_poll.
- **Suggested fix**: Either specify N (e.g., "3 consecutive empty polls") to match EAD, or document that N is intentionally different and provide the value.

---

### Finding 5

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 210 (signal catalog `assigned-to` payload) vs 747, 825 (wire diagrams)
- **Severity**: LOW
- **Issue**: The `assigned-to` signal catalog entry lists `title` as a payload field (`{issue_number, title, target_role, event_context, payload}`), but no concrete wire diagram shows `title` being populated — not the `/work/assign` diagram at line 747 nor the EAD safety-net diagram at line 825.
- **Evidence**: Line 210: `{issue_number, title, target_role, event_context, payload}`. Line 747: `{issue_number:9926, target_role:verifier, event_context:"verification-needed", payload:{pr_number:9943}}` — no `title`. Line 825: `assigned-to(target_role=verifier,...)` — no `title`. Either the catalog is overspecified or the diagrams are underspecified.
- **Suggested fix**: Either drop `title` from the catalog payload shape, or add `title` to the wire-diagram examples showing where it is populated (EAD would have it from the forge issue; `/work/assign` callers may or may not pass it).

---

### Finding 6

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 871 (§7.6 improvement-subloop flowchart)
- **Severity**: LOW
- **Issue**: The flowchart decision node reads "cursor at deque head?" but the agent has no API to directly observe the deque's head position. The actual check an agent can perform is "does GET /events/for/{role}?since=cursor return an empty list?" The label is misleading for implementers.
- **Evidence**: Line 871: `QEmpty{cursor at<br/>deque head?}`. The harness exposes `GET /events/for/{role}?since=cursor` but no endpoint for "am I at head?" The agent can only infer drained-queue state from an empty GET response.
- **Suggested fix**: Change the flowchart node label to "GET returns empty?" or "no events past cursor?" to match the agent's actual observable condition.