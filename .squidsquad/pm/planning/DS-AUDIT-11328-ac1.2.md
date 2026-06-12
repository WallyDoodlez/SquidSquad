Now I have a complete picture. Here are my findings:

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 789–806 (pseudocode) vs 817–857 (diagram)
- **Severity**: error
- **Issue**: The pseudocode and the sequence diagram diverge on what happens after the improvement subloop fires. The pseudocode (lines 802–804) runs `run_one_improvement_subloop_task()` then executes `continue`, which re-enters the top of `loop forever` — causing a re-check for events past cursor before idling. The diagram (lines 850–856) places the improvement `alt` after the `loop drain to empty` has exited, then falls directly into `"re-enter idle wait"` — no re-check for events occurs after the subloop.

- **Evidence**: §7.6 (line 1095) states: *"Subloop output may emit a new `assigned-to` (e.g., pm-subloop files a bug and routes it)."* If an improvement subloop emits an `assigned-to` targeting the same agent, the pseudocode picks it up immediately via the `continue`-driven re-check. The diagram goes straight to idle, forcing the agent to wait for `event_poll` to detect the new event and deliver a fresh nudge — adding up to 60s of idle-backoff latency (§7.0 cadence). This contradicts the D2 "drain-to-empty outer behavior" principle which says events arriving during processing should be picked up in the same wake-up.

- **Suggested fix**: Add a re-check path after the improvement subloop in the diagram. Either: (a) wrap the entire body (drain loop + improvement alt) in an outer `loop forever` frame so the improvement branch naturally re-enters the drain loop; or (b) add an explicit `A->>H: GET /events/for/{role}?since=cursor` arrow after the improvement `alt` end, with a conditional re-entry to the drain loop if events exist.

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 869–875 (§7.2 boot steps) and 789–798 (§7.1 start of loop)
- **Severity**: warning
- **Issue**: The boot sequence describes a two-step hybrid flow that does not cleanly enter the §7.1 `loop forever`. Boot step 4 (line 874) performs an explicit `GET /events/for/{role}?since=cursor` as a gate-check. Boot step 5 (line 875) then says *"process queued events per §7.1 walk, then idle-wait."* But §7.1's `loop forever` starts with its own `GET /events/for/{role}?since=cursor` (line 791). This means at boot the agent executes two consecutive GETs against the same cursor before processing begins — the step 4 GET and the §7.1-initial GET return identical results since the cursor hasn't advanced yet. The redundant GET is ambiguous in spec terms: if an implementer feeds step 4's result into step 5 bypassing §7.1's initial GET, they violate §7.1; if they invoke §7.1 literally, they do a double-fetch.

- **Evidence**: Nothing breaks functionally (same events returned twice, cursor hasn't moved), but the boot flow is underspecified about HOW step 5 enters §7.1. §7.0 (line 782) frames it as *"the agent processes these as the initial event walk"* — implying §7.1 entry — but doesn't address the duplicate GET. An implementer following the spec literally writes a boot-time GET followed by a §7.1 loop that immediately GETs again. Additionally, the step 4 alternative path (*"or wait for nudge if queue is empty"*) bypasses the improvement-subloop check that §7.1 performs when queue is drained (line 802). At first boot the `.subloop-last-run` file doesn't exist, so `improvement_cooldown_elapsed()` would return true if it were reached.

- **Suggested fix**: Either (a) remove step 4's explicit GET and have step 5 unconditionally enter the §7.1 `loop forever` — the loop's own first GET handles both the "events waiting" and "queue empty" cases, and the improvement-subloop check fires naturally on the empty-queue path; or (b) keep step 4 as a boot-only condition check but specify that step 5 enters §7.1 at line 791 (the GET) regardless, and the duplicate fetch is intentional (harmless at boot, and required for the loop's cursor-based re-fetch semantics on subsequent iterations).

---

### No additional findings

- **§4.2/§4.3 cursor consistency**: Verified. §4.2 (line 266) says `ack-cursor` fires *"after the agent has finished processing"*; §4.3 (line 379) says cursor *"advances only after the agent has finished processing an event — whether cared or skipped."* §7.1 pseudocode places `POST /events ack-cursor` at line 798 after the `if event passes` block (outside it, so it fires for both cared and skipped). Diagram places the ack at lines 841–843 after the inner `alt cared`/`else skipped` `end`. All four are mutually consistent: ack fires after processing, for both cared and skipped events, per-event rather than batched. ✓

- **§7.4 care filter**: The pseudocode (`if event passes my role's care filter`) and diagram (`care filter (target_alias == my_alias?) → alt cared/else skipped`) are consistent. ✓

- **§7.5 nudge-while-busy**: Step 2 states *"Emits ack-cursor for current event"* which is D2-consistent (per-event ack). Step 3 references §7.1 for subsequent processing. No batching conflict detected — the reference to §7.1 now points at the eager per-event loop. The crash-safety table's *"Between ack and walk"* row is consistent with the D2 model where ack-cursor and next GET are adjacent. No contradictions to flag. ✓

- **§7.6 improvement subloop branch**: The trigger (queue drained, GET returned []) matches both pseudocode line 801 and diagram line 844. The throttle mechanism and role-class catalog are consistent. The only inconsistency is the post-subloop re-check documented in Finding 1 above. ✓

- **Mermaid syntax**: `autonumber` is valid. Nesting of `loop > alt > alt` (lines 829–848) is syntactically correct — the inner `alt cared/else skipped` closes with `end` at line 840, the outer `alt event exists/else queue drained` closes with `end` at line 847, and the `loop` closes with `end` at line 848. The `alt improvement cooldown elapsed` at line 850 is correctly outside the loop. No parse-level issues. ✓

- **§§1-3 cursor cross-refs**: Sections 1–3 contain no cursor references that contradict §7.1. The only cursor mention in §2 is the loop-mode exclusion (*"No cursor maintained while in fallback"*), which is orthogonal. ✓

- **Idle-wait as only exit path**: Both pseudocode (line 806) and diagram (line 856) end the flow at `idle_wait_for_next_nudge()` / Monitor block. The `continue` paths (lines 799, 804) re-enter the loop rather than exiting; the only blocking/waiting exit is idle-wait. ✓