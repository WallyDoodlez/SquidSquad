Now I have enough context to issue my findings.

---

### Finding 1

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 56
- **Severity**: error
- **Issue**: Model-A residual in blockquote — "For each event delivered by `event_poll.py`" contradicts the updated model where `event_poll.py` delivers only bare `NUDGE` (no payload) and the agent fetches events itself via `GET /events/for/{role}?since=<cursor>`.
- **Evidence**: The same file's Monitor section (line 50, updated by this diff) says: "`event_poll.py` writes a single literal `NUDGE\n` line (no payload) to stdout… A `NUDGE` is a wake signal only — it never carries event data." Case B step 1 (line 62, also updated) says: "The `NUDGE` woke you — `GET /events/for/{role}?since=<cursor>` to fetch the event(s)." But the blockquote at line 56 was not touched by the diff and still claims `event_poll.py` delivers events — directly contradicting the two surrounding sections that were updated. This blockquote sits between the Monitor section (line 50) and Case B (line 60), making the contradiction visible to any reader.
- **Suggested fix**: Change "For each event delivered by `event_poll.py`" to "For each event returned by your `GET /events/for/{role}?since=<cursor>`" (or equivalent phrasing matching the model-B agent-fetches-events model).

---

### Finding 2

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 58
- **Severity**: warning
- **Issue**: The "Case precedence" blockquote still uses model-A phrasing: "When an event arrives, evaluate Case E (special events) first." In the new model, what "arrives" via the Monitor is a bare NUDGE — individual events are fetched by the agent via GET. The phrasing suggests events travel through the Monitor stream, which is the old model.
- **Evidence**: Same file positioning as Finding 1 — the blockquote at line 58 was not included in any diff hunk. While the operational logic described (check Case E first per event before state-based case) remains correct, the phrase "When an event arrives" is a model-A framing that sits oddly between the updated Monitor section (which correctly describes NUDGE-only delivery) and the updated Case B (which correctly instructs the agent to GET-fetch events after a NUDGE).
- **Suggested fix**: Replace "When an event arrives" with "For each event from your GET response" or "When you take the next event from your GET."

---

**Additional note on the `since=None` change (correctness confirmed)**: The `cycle_pre.py` change at line 1391 (`_query_events(since=None, limit=100)`) is correct. `event_bus_reader.query()` line 77 gates on `if since and since != "none"` — when `since=None`, the parameter is omitted and the harness endpoint `GET /events/for/{role}?limit=100` returns the 100 most recent events (newest-first ordering, per harness.py line 2199). This matches the documented intention: "read the recent window each cycle — the mechanical reactions below are idempotent (#5622), so re-reading the window is harmless." No consumers of `_read_working_state()` access `last_processed_event_id` after the removal (confirmed by grep of all `references/` and `tests/` directories). The `vault_remember.py` file has its own independent `_read_working_state` that returns raw string content, not a parsed dict — unaffected.