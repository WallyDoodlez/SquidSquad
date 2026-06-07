Now I have all the information needed. Let me produce my findings.

---

### Finding 1

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 1070–1084 (the §7.6 flowchart) vs. 789–807 (§7.1 pseudocode) and 817–857 (§7.1 diagram)
- **Severity**: error
- **Issue**: The §7.6 flowchart was not updated when §7.1 was restructured to wrap everything in the `loop forever` and flow improvement-subloop output back to the top via `continue`. Two edges in the §7.6 flowchart now contradict §7.1:

  1. **`Subloop --> Idle`** (line 1083). §7.1 pseudocode line 803–804 says `run_one_improvement_subloop_task()` then `continue` (back to top, re-checks GET). §7.1 diagram line 849 says `loop continues — re-check`. The flowchart instead sends subloop output straight to idle, skipping the re-check.

  2. **`QEmpty -->|"no — more events past cursor"| Idle`** (line 1079). §7.1 lines 799–799 show that when a GET finds more events past cursor, the agent processes them and `continue`s back to the top — it does **not** go to idle. The flowchart shows the "more events" path going directly to idle, which would leave queued events unprocessed.

- **Evidence**: The §7.1 restructuring (per the diagram's "loop continues — re-check" notes on lines 844 and 849, and the pseudocode `continue` on lines 799 and 804) changed the improvement subloop from a terminal branch to a branch that re-enters the main loop at the GET. The §7.6 flowchart was not updated to match; it preserves the pre-restructuring assumption that the subloop is the last thing before idle.

- **Suggested fix**: Update the §7.6 flowchart edges:
  - Change `Subloop --> Idle` to `Subloop --> QEmpty` (re-check GET for events that may have arrived during subloop execution).
  - Change `QEmpty -->|"no — more events past cursor"| Idle` to point to a new or existing "process next event" node, or remove the `QEmpty --> Idle` edge altogether and redirect the `"no"` branch back toward event-processing logic (consistent with §7.1's `continue` back to the top of the eager main loop).

---

### Finding 2

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 849 (the §7.1 diagram `Note over A`)
- **Severity**: warning
- **Issue**: The diagram note says: `loop continues — re-check (subloop may have emitted a fresh assigned-to for this alias)`. This is misleading because:
  - §7.3 (self-assign invariant) states the harness forbids `assigned-to` where `target_alias == emitter_alias`. The improvement subloop runs under the agent's authority; the agent **cannot** emit an `assigned-to` for its own alias via `POST /work/assign`.
  - §7.6 line 1094 describes subloop output correctly: `Subloop output may emit a new assigned-to (e.g., pm-subloop files a bug and routes it). That nudges the owning alias into work` — i.e., the subloop typically assigns work to **other** aliases, not itself.

- **Evidence**: §7.3 self-assign rule: `Self-assign → forbidden by built-in invariant (the harness rejects any assigned-to where target_alias == emitter_alias)`. §7.6 prose correctly says the subloop nudges "the owning alias" (some other alias that should handle the bug). The indirect path via EAD (subloop writes to forge → EAD picks it up → EAD emits `assigned-to` with `emitter_alias="__ead__"`) is technically possible but delayed (EAD polls at 5–60s), making it an unlikely reason for an immediate re-check.

- **Suggested fix**: Reword the parenthetical to something accurate, e.g.: `loop continues — re-check (other agents may have assigned work during the subloop; subloop forge writes may have triggered EAD events for this alias)`.

---

### AC1 Verification (pseudocode + diagram consistent)

**Pass.** The §7.1 pseudocode (lines 789–807) and §7.1 diagram (lines 817–857) are now consistent on the post-subloop re-check:
- Pseudocode line 803–804: `run_one_improvement_subloop_task()` → `continue` (back to top, re-does GET).
- Diagram line 849: `loop continues — re-check`.
- Pseudocode lines 805–806: `idle_wait_for_next_nudge()` blocks, then loop naturally returns to top.
- Diagram lines 851–853: `idle wait`, then `EP->>M: next NUDGE` → `M->>A: wake — loop continues`.

All three paths (post-event, post-subloop, post-nudge-wake) re-enter at the GET. The *only* inconsistency is the §7.6 flowchart (Finding 1 above).

### AC2 Verification (boot step 4)

**Pass.** Boot step 4 (line 874) now reads: `Enter §7.1 eager main loop. Its first iteration's GET /events/for/{role}?since=cursor performs the initial drain: if events are queued they're processed per-event with their acks; if the queue is empty the loop falls through to the improvement-subloop check and then to idle-wait. No separate boot-time GET or branch is needed — §7.1 handles both cases natively.`

This is clean, unambiguous, and eliminates the former double-GET (R1 F2).

### AC4 Verification (Mermaid syntax)

**Pass.** The nested `loop > alt > alt` structure (lines 829–856) is syntactically valid:
- 4 opens: `loop` (829), outer `alt` (831), inner `alt` in if-branch (834), inner `alt` in else-branch (847).
- 4 closes: `end` (840), `end` (854), `end` (855), `end` (856).
- `alt` blocks are properly nested within both branches of the outer `alt`.
- All participant declarations, `autonumber`, arrow types (`->>`, `-->>`), `Note over`, and `<br/>` line breaks conform to Mermaid sequenceDiagram syntax.