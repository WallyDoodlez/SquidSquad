Now I have enough evidence. Let me compile my findings.

---

### Finding 1

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: New sub-bullet under Case E `stop-requested` (line 94 in the diff)
- **Severity**: error
- **Issue**: The diff claims AGENT-RUNTIME §10 Q11 is an "unsettled design question", but Q11 is **Closed (2026-05-30)** with the `ack-stop.result` enum already locked to `'checkpointed' | 'aborted' | 'drained'`.
- **Evidence**:
  - Diff text: "(Whether a cooperative stop-confirm `ack-stop` should be added — and which `result` value it would carry — is an unsettled design question, AGENT-RUNTIME §10 Q11; until that lands, emit nothing here.)"
  - `docs/AGENT-RUNTIME.md` line 1326: `| Q11 | \`ack-stop.result\` enum values | **Closed (2026-05-30)** — \`'checkpointed'\` (working-state.md flushed; safe to SIGTERM), \`'aborted'\` (graceful stop failed; harness should escalate), \`'drained'\` (no in-flight work; exiting clean). Documented in §5.2 catalog row. |`
  - `docs/AGENT-RUNTIME.md` line 301 (the §5.2 catalog row): `\`{event_id, result}\` where \`result\` is one of \`'checkpointed'\` ... \`'aborted'\` ... \`'drained'\` ... \`'deploy-halted'\``
  - The enum is settled; referencing Q11 as "unsettled" is a factual error.
- **Suggested fix**: Rewrite the parenthetical to reflect reality — the enum is settled but no agent-side code (outside tests) calls `event_bus.ack_stop()` on the stop path today, so agents should emit nothing until that emission is implemented. For example: "(The `ack-stop.result` enum is settled per AGENT-RUNTIME §10 Q11, but no agent-side code calls `event_bus.ack_stop()` on the stop path today — until that invocation is implemented, emit nothing here.)"

---

### Finding 2

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: Case E `stop-requested` entry body; Always-On Rules context-pressure line (lines 93, 116 in the diff)
- **Severity**: warning
- **Issue**: The new text instructs agents to honor the stop "ONLY at a task boundary" and says "Honor the stop at the next task boundary." But the mechanism described — `cycle_post.py` exit 42 — occurs at cycle end, which is inherently a task boundary (the agent has just completed a cycle). The instruction to "honor only at a task boundary" is vestigial from the old event-driven model where a `stop-requested` event could arrive mid-cycle and sit unread. In the intent-driven model, the stop signal arrives via `cycle_post.py` exit 42 *at cycle end* — the agent cannot encounter it mid-task (it only sees it when `cycle_post.py` runs, which is at cycle end). The mid-task vs. boundary distinction is meaningless for this mechanism but remains in the text.
- **Evidence**:
  - `references/scripts/cycle_post.py` lines 877-890 show `_do_stop_after_cycle_check()` runs at cycle end only.
  - `references/sub-skills/common/self-restart.md` lines 16-22: the exit-42 flow is exclusively a cycle-end event.
  - The old text's "mid-task: read the event, ignore" made sense when a deque event could arrive mid-cycle via Monitor/nudge; the new text removes that explicit mid-task clause but retains "Honor it ONLY at a task boundary" — which cannot be violated under the intent-driven mechanism.
- **Suggested fix**: Replace "Honor it ONLY at a task boundary" with language reflecting that the stop arrives at cycle end (via exit 42) and the only action is to checkpoint and halt — there is no mid-task scenario to guard against. Or simply drop "ONLY at a task boundary" and state the required action directly: "When `cycle_post.py` exits 42, checkpoint `working-state.md` and halt."

---

### Finding 3

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: Always-On Rules, Context pressure line (line 116 in diff)
- **Severity**: warning
- **Issue**: The text says "the post-cycle wrapper (`cycle_post.py`) exits the session for a harness-managed restart." `cycle_post.py` does not "exit the session" — it exits with code 42, which is a signal to the agent to halt output. The agent then halts, and the harness's 60s force-kill net terminates the process. Attributing session exit to `cycle_post.py` is imprecise and contradicts `self-restart.md` which correctly states "You then halt — cease output and end your turn" and "The harness's 60-second force-kill net... terminates your still-running process."
- **Evidence**:
  - `references/sub-skills/common/self-restart.md` lines 17-18: "You then halt — cease output and end your turn... The harness's 60-second force-kill net... terminates your still-running process"
  - `cycle_post.py` exiting 42 is a signal, not a session exit; the harness terminates the session.
- **Suggested fix**: Change to: "the post-cycle wrapper (`cycle_post.py`) exits with code 42, signalling the agent to halt for a harness-managed restart" or similar language that attributes termination to the harness force-kill, not to `cycle_post.py`.

---

### Finding 4

- **File**: `references/sub-skills/common-events/event-driven-workflow.md`
- **Line**: Context pressure section (line 35 in diff)
- **Severity**: warning
- **Issue**: The text says "when a restart is needed it flips `intent` to `stopping`/`restarting` and `cycle_post.py` detects that." This describes the operator-initiated restart path (harness flips intent → cycle_post detects → exits 42) but does not match the context-pressure-initiated restart path, where `cycle_post.py` detects pressure first, then POSTs `/restart` to the harness (which flips intent), and then exits 42 in the same run — cycle_post.py does NOT "detect" a pre-existing intent flip for context pressure. The two paths have opposite causality. Since this section is specifically about "Context pressure," the description should match that path.
- **Evidence**:
  - `references/sub-skills/common/self-restart.md` lines 11-17: "Step 1b detects context pressure exceeds threshold... At cycle end, `cycle_post.py` checks the `context_pressure` field... If exceeded, it POSTs `/agents/[ROLE]/restart` to the harness so intent flips to `restarting`... then exits with code 42."
  - `references/scripts/cycle_post.py` lines 906-921: context pressure check runs AFTER the harness intent query, and only triggers the POST when intent is NOT already stopping/restarting.
- **Suggested fix**: Rewrite to match both paths. For example: "For operator-initiated restarts the harness flips `intent` and `cycle_post.py` detects it; for context pressure, `cycle_post.py` detects the pressure, notifies the harness (which flips intent), and exits 42. In both cases there is no `stop-requested` event..."