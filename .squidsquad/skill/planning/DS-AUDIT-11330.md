Now I have all the evidence needed. Let me compile my findings.

---

### Finding 1

- **File**: references/sub-skills/common-events/cursor-management.md
- **Line**: 52
- **Severity**: error
- **Issue**: In the "Dropped scenario (#9265)" callout, the event-fetching endpoint is written as `GET /events?since=<cursor>`, missing the `role` parameter. This contradicts line 50 (eviction gap) which correctly uses `GET /events/for/{role}?since=<old>`. The two lines describe querying the same deque but use different URL forms — one path-based with `/for/{role}`, one query-based and missing the `role` filter.
- **Evidence**: The harness defines both `GET /events?role=<role>&since=<cursor>` (harness.py line 2088) and `GET /events/for/{role}?since=<cursor>` (harness.py line 2141). The eviction-gap line 50 correctly uses the `/for/{role}` form. The dropped-scenario line 52 uses `GET /events?since=<cursor>` with no `role` at all — a URL that would return unfiltered events from all roles, not the role-scoped query the agent needs. An agent copying this URL literally would get wrong results.

- **Suggested fix**: Change line 52 to `GET /events/for/{role}?since=<cursor>` to match the eviction-gap form on line 50, or add the missing `&role=<role>` query parameter: `GET /events?since=<cursor>&role=<role>`.

---

### Finding 2

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 98
- **Severity**: error
- **Issue**: The Always-On Rules claim "`event_poll.py` only emits NUDGE lines on stdout and does not touch `working-state.md`." The actual `event_poll.py` script (line 6, lines 113–148, line 302) **does** touch `working-state.md` — it reads the `Last Processed Event ID` line from it and writes cursor advances to it using a `.tmp`+`mv` atomic protocol after every event. This claim is factually false for the current implementation.
- **Evidence**: `event_poll.py` line 6: `"advances the cursor in .squidsquad/<role>/working-state.md"`. Lines 113–148: `_write_cursor_atomic()` function with `.tmp`+`os.replace`. Line 302: `_write_cursor_atomic(role, str(event_id))` called per event. The transitional note at line 298–299 acknowledges this code path is due for replacement by #9873-B, but until that lands, `event_poll.py` actively writes to `working-state.md`. An agent following the sub-skill literally would be surprised when `working-state.md` contains a cursor line written by `event_poll.py`.

- **Suggested fix**: Either (a) qualify the claim with a transitional note: "`event_poll.py` currently writes a `Last Processed Event ID` line to `working-state.md` (pre-#11329 behavior); #11329 will retire this. For now, treat that line as `event_poll.py`'s internal state — do not read, write, or rely on it for cursor decisions." Or (b) if #11329 has already landed in `event_poll.py`, then the `event_poll.py` docstring and implementation need updating to match.

---

### Finding 3

- **File**: references/sub-skills/common-events/cursor-management.md
- **Line**: 56
- **Severity**: warning
- **Issue**: The crash-recovery section says "the boot bootstrap routes you back into the §7.1 eager loop, which fetches the events past `GET /events/cursor` and walks them with per-event acks." Two problems: (a) the endpoint is written as `GET /events/cursor` without the required `/{role}` path segment (contrary to line 21 which correctly uses `GET /events/cursor/{role}`, and the harness route at harness.py line 2211 `@app.get("/events/cursor/{role}")`); (b) the phrasing "fetches the events past GET /events/cursor" is misleading — `GET /events/cursor/{role}` returns the cursor value (a single event_id or null), not the events themselves. The events are fetched via `GET /events/for/{role}?since=<cursor>`, a different endpoint.
- **Evidence**: Line 21 correctly documents `GET /events/cursor/{role}` returns `{cursor: <event_id> | null, role}` — a cursor value, not a list of events. Line 56 collapses this to `GET /events/cursor` (missing role) and implies it's the event-fetching endpoint. An agent could reasonably interpret line 56 as "make a GET to /events/cursor to get the events."

- **Suggested fix**: Rewrite as: "...which reads your cursor via `GET /events/cursor/{role}`, fetches events past it via the event stream, and walks them with per-event acks."

---

### Finding 4

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 31 (step 4)
- **Severity**: warning
- **Issue**: Boot drain step 4 instructs the agent to "Skim events from cursor forward" and "Skim-then-ack each event individually" but does not specify the mechanism or endpoint for fetching those events. The Monitor tool / `event_poll.py` is not started until step 5. No GET endpoint for fetching events is formally documented in any of the four changed files — the only hints are in cursor-management.md's eviction-gap scenario (line 50, `GET /events/for/{role}?since=<old>`) and dropped-scenario callout (line 52), neither of which is presented as "the endpoint to use to fetch events."
- **Evidence**: Step 4 says "Skim events from cursor forward" — the agent needs to fetch events from the harness via some HTTP endpoint. Step 5 then starts `event_poll.py` for steady-state listening. The gap between "fetch events during boot drain" and the documented tools is unfilled. An agent reading step 4 has no instruction for which URL to GET, whether to use `event_poll.py` temporarily, or whether to make direct HTTP calls.

- **Suggested fix**: Add a sentence specifying the mechanism: e.g., "Issue `GET /events/for/{role}?since=<cursor>` repeatedly (or invoke `event_poll.py` with `--since <cursor>` in single-shot mode) until the deque is drained, acking each event as you go." Or explicitly state that step 4 uses the same `event_poll.py` mechanism as step 5 but invoked temporarily for the drain.

---

### Finding 5

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 31 vs cursor-management.md line 49
- **Severity**: warning
- **Issue**: Step 4 of the boot sequence says boot-drain events are "Informational only — the forge already has current state." But cursor-management.md line 49 (long-lag gap scenario, which is equivalent to boot drain) says "the only requirement is that each one passes through the same care-filter + per-event-ack discipline as a normal walk." These two descriptions are in tension: "informational only" suggests the agent should NOT run the cycle wrapper (just ack), while "same care-filter discipline as a normal walk" suggests running the full care-filter decision (and potentially the cycle wrapper for cared events). An agent could interpret step 4 as "skip the cycle wrapper for all events during boot drain" while cursor-management.md could be read as "run the care filter + wrapper as normal."
- **Evidence**: event-mode-contract.md line 31: "Informational only — the forge already has current state. Skim-then-ack each event individually." The word "skim" reinforces "don't act." cursor-management.md line 49: "the only requirement is that each one passes through the same care-filter + per-event-ack discipline as a normal walk." The "same discipline" wording implies the agent should classify each event as cared/skipped and potentially act on cared ones. An agent that runs the cycle wrapper on cared boot-drain events would duplicate work the forge already reflects; an agent that skips the wrapper would violate the "same discipline" instruction.

- **Suggested fix**: Clarify whether the care filter during boot drain should (a) still classify cared/skipped but never fire the cycle wrapper (i.e., ack-only mode), or (b) fire the wrapper for cared events (which risks duplication). If (a), update cursor-management.md line 49 to say "passes through the same care-filter classification (cared vs skipped) and per-event-ack discipline, but without firing the cycle wrapper." If (b), remove "Informational only" from event-mode-contract.md step 4.

---

### Finding 6

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 98 vs line 50
- **Severity**: warning
- **Issue**: Terminology inconsistency within the same file. Line 50 says `event_poll.py` "writes one JSON object per line to stdout." Line 98 says `event_poll.py` "only emits NUDGE lines on stdout." The term "NUDGE lines" is undefined in any of the four changed files. An agent encountering "NUDGE lines" only at line 98 (after having read line 50's "JSON object per line") cannot know whether these are the same thing or distinct formats.
- **Evidence**: The word "NUDGE" appears only once across all four changed files (event-mode-contract.md line 98). The term originates from `references/roles/instructions.md` (lines 78, 113) where `NUDGE` is the Monitor-level abstraction for a line that wakes the agent. But within the four sub-skill files — which event-driven-workflow.md line 10-16 instructs the agent to read as the primary contract — "NUDGE" is never defined. The shift from the concrete "JSON object" (line 50) to the abstract "NUDGE lines" (line 98) is jarring.

- **Suggested fix**: Either (a) replace "NUDGE lines" with "JSON event lines" at line 98 for self-contained clarity, or (b) add a brief parenthetical at first use: "NUDGE lines (JSON event objects, one per line)."

---

### Finding 7

- **File**: references/sub-skills/common/agent-lifecycle.md
- **Line**: 1–51 (entire file)
- **Severity**: warning
- **Issue**: AC5 requires "agent-lifecycle.md has zero cursor mentions" — this is verified clean. However, the file references `cycle_post.py` (line 12) and `cycle_pre.py` (line 14) as the agents' per-cycle git pull/branch and commit/push handlers. This contradicts event-mode-contract.md line 100: "The harness owns git — pull, commit, and push are managed at boot and shutdown by the harness. You do not run mechanical pre/post steps in event mode."
- **Evidence**: agent-lifecycle.md line 13: "`cycle_post.py` queries `GET /agents/{role}` at cycle end, sees the intent, and exits with code 42." Line 14: "`cycle_pre.py` handles git pull/branch per cycle." These describe per-cycle mechanical steps that run inside the agent session. But event-mode-contract.md line 100 says agents in event mode do NOT run these steps — the harness manages git. In the post-#11328 event-mode model with per-event acks, there is no "cycle" wrapper — each event is processed atomically. The `cycle_pre.py`/`cycle_post.py` references in agent-lifecycle.md describe a per-cycle wrapper model that may only apply to polling/loop mode, not event mode. This is a contradiction between agent-lifecycle.md (which describes a cycle-wrapper model) and event-mode-contract.md (which says the harness manages git, no agent-side pre/post steps in event mode).

- **Suggested fix**: Add a qualification that `cycle_pre.py` and `cycle_post.py` apply to polling/loop mode only, or clarify that these are harness-internal steps not run by the agent in event mode. Alternatively, if agent-lifecycle.md is intentionally mode-agnostic, add a note that "in event mode, git operations are harness-managed; the cycle wrappers described here apply to polling mode."

---

### Finding 8

- **File**: references/sub-skills/common-events/cursor-management.md
- **Line**: 47
- **Severity**: warning
- **Issue**: Cross-reference `(CONTEXT.md §2)` for gap scenarios may be a broken link. The canonical documentation is `docs/AGENT-RUNTIME.md` (referenced throughout these files as the authority for the cursor model). `CONTEXT.md` is not one of the four documented canonical sources. If `CONTEXT.md` does not exist or does not have a §2 about cursor gaps, an agent following this reference would be blocked.
- **Evidence**: The file references `docs/AGENT-RUNTIME.md` §4.3 (line 8) and §7.1 (line 41) as canonical. `CONTEXT.md` appears only at line 47. There is no `CONTEXT.md` in the repository root or in a standard documentation location obvious from these files. This is likely an internal design-document reference (CONTEXT-8694 is referenced at line 52 in the same file) that leaked into agent-facing instructions.

- **Suggested fix**: Replace `(CONTEXT.md §2)` with a self-contained summary (the two gap types are already described inline at lines 49–50, so the cross-reference is redundant) or reference the canonical `docs/AGENT-RUNTIME.md` if it covers gap scenarios.