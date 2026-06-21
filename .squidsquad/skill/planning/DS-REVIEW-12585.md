# Review record — #12585 L1 Soul "Health & Diagnostics — Facts Over Context"

**Change**: new `### Health & Diagnostics — Facts Over Context` subsection in `references/roles/SOUL.md`, placed after `### Shared Discipline`. High-blast-radius (L1 ⇒ composed into all 4 roles' CLAUDE.md).

**Review path**: `model_router code-review` (DeepSeek) self-aborted exit 1 — "Output below minimum length threshold (11 < 200)". Per step:cycle/ds-review + feedback_model_router_auto_fallback, fell back to a Sonnet subagent for the same review prompt (no human ask).

**Verdict: SHIP** (Sonnet fallback).

- Coverage: all 5 spec ideas present and unambiguous (own+team health first-class; facts-not-memory esp. for humans; cross-check ≥1 independent source on surprising readings; doctor-style RCA proven-vs-inferred; fix-as-filed-issue).
- Prohibited jargon: clean (no ack/cursor/event id/GET/POST/no-op/care filter/nudge/drain).
- Behavioral regression/contradiction: none — coheres with Shared Discipline (facts-from-script), Universal Quality Gate, User-Facing Communication, Token Consciousness.
- Token bloat: lean for payload; intro paragraph carries the Shared-Discipline tie-in; 3 bullets map 1:1 to ideas 3/4/5.

**Optional nits — considered and declined, with rationale:**
1. "telemetry field" → "data point": KEPT. Faithful to PM's draft wording and the literal motivating incident (a misrepresented harness `/status` telemetry field). More precise than the generic alternative.
2. "iteration logs" → "cycle logs": KEPT. Established SquidSquad vocabulary (`.squidsquad/<role>/iterations/iter-N.md`), not novel jargon.
