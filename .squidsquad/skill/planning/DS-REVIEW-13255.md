# Code Review — #13255 (exclude self-emitted events from /events/for/{role})

Reviewer: Sonnet subagent (model_router/DeepSeek returned a degenerate sub-threshold
output → auto-fallback to Claude/Sonnet per feedback_model_router_auto_fallback).

## Verdict: NO_BLOCKING_FINDINGS

### Verified
1. **No cross-agent regression.** verifier-reject (role=qa, no target_alias) → emitter "qa" != "skill" → worker still receives it. assigned-to/deploy-signal are harness-emitted (role="harness"): if target_alias is set the unconditional first branch catches them; otherwise "harness" != requesting role passes the guard. Self-emitted reacts-to (own git-commit, role=self) → suppressed.
2. **Cursor/eviction/skim-then-advance unchanged** — the emitter guard is confined to the filter loop; since/get_since_with_eviction and the [:limit]/[-limit:] ordering are untouched.
3. **Empty emitter default** `e.get("role","")` → "" != any real role → always included (conservative-correct; an unattributable event can't be ascribed to the requester).
4. **Explicit target wins** even when self-emitted (first branch unconditional) — preserves any self-assign-via-target_alias case.

### LOW (addressed)
- No explicit test for a missing top-level `role` field (emitter=""). Behavior is trivially correct (included) but a test documents the spec. → Added `test_self_emit_filter_includes_event_with_missing_emitter_13255`.
