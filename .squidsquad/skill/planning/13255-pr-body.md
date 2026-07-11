## #13255 — exclude self-emitted events from `GET /events/for/{role}`

(qa-filed improvement-scan; directly evidenced this session — I drained ~6 of these benign self-wakes while idle.)

### Root cause
`get_events_for_role` (harness.py) returned events where `payload.target_alias == role` **OR** `event_type` ∈ the role's reacts-to list — but never excluded events the requesting role **emitted itself**. An agent's own `git-commit` / `status-transition` events carry top-level `role=<that agent>` and no `target_alias`, are in its reacts-to list, so they came back through its own `event_poll`, woke it via Monitor, and drained to a guaranteed care-filter no-op. ~8 wasted wakes/session on a busy clone (each = a GET + ack round-trip + a slice of agent turn/context) — noise against AGENT-RUNTIME §8.4's "queue is pre-filtered, almost every event is cared" contract.

### Fix
Add `and emitter != role` (where `emitter = e.get("role", "")`) to the **reacts-to branch only**:
- Explicit `target_alias == role` still wins **unconditionally** (preserves any self-assign-via-target case).
- Self-emitted **broadcast** reacts-to events are suppressed → no self-wake.

### Why it's safe (no cross-agent regression)
- A **verifier reject** is qa-emitted → a worker (different emitter) still receives it.
- `assigned-to` / `deploy-signal` are **harness-emitted** (`role="harness"`) → never excluded for any agent.
- A **missing emitter** (`""`) → `"" != role` → always included (conservative: an unattributable event can't be ascribed to the requester).

### Verification
- +2 tests: self-emitted excluded / cross-agent included / explicit-target-self included; missing-emitter included.
- Full static gate: **4969 passed, 0 failures, 0 errors** (nothing relied on self-emitted delivery).
- Review: model_router/DeepSeek returned a degenerate sub-threshold output → **Sonnet fallback** (per the auto-fallback rule): **NO_BLOCKING_FINDINGS** + 1 LOW (missing-emitter test) addressed. DS-REVIEW-13255.md on main.
- No CQ (deterministic harness code, not LLM-consumed). No manifest (no new files).
