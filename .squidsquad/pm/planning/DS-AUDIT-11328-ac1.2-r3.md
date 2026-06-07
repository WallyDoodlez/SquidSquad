Now I have all the information needed. Let me compile the findings.

---

## Review Summary

**R2 F1 (flowchart consistency)**: RESOLVED. The §7.6 flowchart (lines 1070–1087) now correctly mirrors §7.1's eager per-event loop:
- `Process --> Start` matches the `continue` back to top-of-loop after event processing + ack
- `Subloop --> Start` (not Idle) matches `continue` after subloop task
- `Idle -->|NUDGE wakes agent| Start` correctly represents `idle_wait_for_next_nudge()` blocking → wake → re-enter loop
- Start node label "per-event ack just emitted; top of §7.1 eager loop" correctly captures the state for all three incoming edges

**R2 F2 (self-assign parenthetical)**: RESOLVED. The parenthetical at line 849 now reads: "other agents may have assigned work during subloop; subloop forge writes can trigger EAD-emitted assigned-to for this alias" — this correctly identifies the indirect EAD-mediated path (forge writes → EAD poll → `assigned-to` emission), not a self-assign claim.

However, there is one residual issue:

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 1068
- **Severity**: error
- **Issue**: The prose uses batched-walk vocabulary "on the last walk" that contradicts the per-event eager-loop model shown in the §7.6 flowchart and described in §7.1. In the eager loop, the GET that returns `[]` is the *current* iteration's check — there is no "last walk" to observe. The flowchart correctly shows this as an inline decision (node `QEmpty` checks the current GET result), but the prose describes it as a historical observation from a completed prior traversal.
- **Evidence**: 
  - §7.1 pseudocode (lines 801–806) shows the GET-empty branch executing immediately on the current iteration: "No events past cursor — queue is drained" → check throttle → subloop or idle. No "last walk" indirection.
  - §7.6 flowchart (lines 1070–1087) shows `Start --> QEmpty` as a direct, live check of the current GET response, not a check of a historical result.
  - The task context (verification point 4) explicitly flags this risk: "Are §7.6 prose paragraphs still consistent with the new flowchart (they may still reference 'last walk' or similar batched-walk vocab)?"
- **Suggested fix**: Replace line 1068:
  ```
  The improvement subloop fires when the agent's queue is observably drained — `GET /events/for/{role}?since=cursor` returned `[]` on the last walk (no events past cursor).
  ```
  with:
  ```
  The improvement subloop fires when the agent's queue is observably drained — `GET /events/for/{role}?since=cursor` returns `[]` (no events past cursor).
  ```
  (Simply delete "on the last walk" — the present-tense "returns" or simple past "returned" is correct; "on the last walk" is the stale qualifier.)