Now I have sufficient context. Let me compile my findings systematically.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8695.md`
- **Line**: TC-N6 (lines ~168–176)
- **Severity**: error
- **Issue**: The regex sentinel patterns are overbroad and will produce false positives on legitimate negative documentation. `"dispatch.*gate"` matches any comment containing the string "dispatch" followed by "gate", including `# No dispatch gate — this is informational only` or the CONTEXT.md-mandated `# No dispatch gate, no per-role queue`. Similarly, `"before.*bootup-complete"` matches comments like `# Events are not held before bootup-complete`. The `.*` wildcard spans across words, so negative-form documentation triggers the test.
- **Evidence**: The existing CONTEXT.md §2 thin-harness lock requires code comments/documentation stating the harness has *no* dispatch gating. Those comments necessarily contain the tokens the regex targets. The regex `dispatch.*gate` matches the substring `dispatch gate` in `"No dispatch gate"`. The test would fail on compliant code that correctly documents the thin-harness property.
- **Suggested fix**: Anchor patterns to positive assertions, not mere substring presence. For example: `dispatch_gate\s*=\s*True`, `_pending_dispatch\[`, `def\s+_hold_event`, `queue_pending_events`, `flush_pending`. Alternatively, restrict the grep to exclude comment lines: `grep -v '^\s*#' | grep -v '^\s*//'` before applying patterns. Document that TC-N6 is a soft sentinel with known false-positive tolerance for negative-form comments.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8695.md`
- **Line**: TC-I1 step 1 (lines ~100–102)
- **Severity**: warning
- **Issue**: The test says `GET /agents/skill — assert bootup_complete: false (or agent absent)`. The parenthetical `(or agent absent)` is ambiguous and contradictory. If the agent is absent, `GET /agents/{role}` returns `{"role": "skill", "status": "unknown", "message": "No health data yet"}` (harness.py line 656), which does NOT contain the key `bootup_complete`. The assertion `bootup_complete: false` cannot be satisfied from this response. The test implementer could interpret this as either (a) assert the key exists with value false, or (b) handle the 200 with missing key as equivalent. These are different test behaviors.
- **Evidence**: Current `get_agent` at harness.py:649–657 returns `{"role": role, "status": "unknown", "message": "No health data yet"}` when `agent is None` — no `bootup_complete` key. An assertion for `bootup_complete: false` would raise KeyError or assertion failure on this response.
- **Suggested fix**: Remove the ambiguity. Either (a) require the test setup to ensure the AgentState exists before step 1 (e.g., pre-seed via `state.set_agent` or POST a cycle-start event first), or (b) split into two explicit sub-cases: "if agent absent, assert 200 with no bootup_complete key; if agent present, assert `bootup_complete: false`." The cleaner approach: ensure agent exists in the precondition so step 1 always gets a `to_dict()` response with `bootup_complete: false`.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8695.md`
- **Line**: §5 Negative Tests / §3 Unit Tests (coverage gap)
- **Severity**: warning
- **Issue**: No test covers POSTing a `bootup-complete` event where the `role` field is missing. `_update_agent_from_event` (harness.py:752) reads `role = event.get("role")` — if `None`, `state.get_agent(None)` returns `None`, and line 759 creates `AgentState(None)`. This produces a nameless agent in the state that would pollute `all_agents()` output and is unreachable via `GET /agents/{role}`. While CONTEXT.md §5.2 doesn't explicitly require role validation for this event, the thin-harness principle means silent garbage-state creation is a defect.
- **Evidence**: `_update_agent_from_event` at harness.py:757-760 creates a new AgentState for any role key present in the event, including `None`. No guard clause checks that `role` is a non-None, non-empty string. A `bootup-complete` event without a `role` field would create `AgentState(None)` in the state dict — invisible via the role-keyed endpoints but present in `all_agents()`.
- **Suggested fix**: Add a test case: `POST /events` with `{"event_type": "bootup-complete", "payload": {"listener_active": true}}` (no role field). The expected behavior should be either (a) 400 rejection with a clear error, or (b) event logged and discarded with no AgentState mutation. Assert that no new agent appears in `GET /agents` or `GET /status`. Add this as TC-U9 in §3 or TC-N8 in §5. Also validate that empty-string role is handled equivalently.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8695.md`
- **Line**: TC-N1 verification block (lines ~138–145)
- **Severity**: warning
- **Issue**: The exact-substring grep for `_pending_dispatch` and similar tokens will match negative-form comments like `# No _pending_dispatch — thin harness`. This is the same class of false-positive risk as TC-N6 but for exact substring matches rather than regex. A developer documenting that dispatch gating has been *removed* or *is not present* will inadvertently trigger the sentinel.
- **Evidence**: The assertion `assert token not in src` on `inspect.getsource(harness)` for tokens like `_pending_dispatch` would fail if any comment, docstring, or log message contains that literal string — even in a negative context. The CONTEXT.md §5.2 deliverable explicitly says `No queue flushing. No _pending_dispatch[role]` — a developer faithfully transcribing this as a code comment would break the test.
- **Suggested fix**: Add a pre-filter step that strips Python comments (`# ...` and triple-quoted strings) before token matching, similar to the TC-N6 fix. Or restrict the check to attribute-access patterns: `self._pending_dispatch`, `state._pending_dispatch`, `_pending_dispatch[`, `_pending_dispatch =`. This narrows the match to actual code usage rather than prose.