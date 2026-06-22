Now I have a thorough understanding of the full system context. Let me synthesize my findings.

---

### Finding 1

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: 79
- **Severity**: warning
- **Issue**: Case C step 4 introduces a `current-state` marker-write on work pickup (`status-bar-self <phase> "<description>"`) that is not mirrored in Case B (line 70), Boot Sequence step 2 (line 33), or the idle-cooldown-loop `absorb-work` path — all of which perform the identical operation ("pick up the top item from `work_queue()`") without writing a `current-state` marker. This creates a behavioral divergence across work-pickup paths within the same contract that an LLM agent must resolve at runtime.
- **Evidence**: 
  - Case C step 4 (line 79): "Pick up the next item — **writing the new task's marker as you start it** (`python references/scripts/cycle.py status-bar-self <phase> "<short description>"`)"
  - Case B step 3 (line 70): "Run `work_queue(<role>)` against the forge — pick up the top item if available" — no marker write mentioned.
  - Boot step 2 idle branch (line 33): "pick up the top item — transition it to `status:in-progress`, write the issue number to the Task field in `working-state.md`, and begin work" — no marker write.
  - Idle-cooldown-loop Step B `absorb-work` (`idle-cooldown-loop.md` line 52): "pick up the top item (transition it `in-progress`, write the Task field in `working-state.md`), do the work" — no marker write.
  - The health check from PR #13131 uses `current-state` for staleness detection. When work is picked up via Case B or the driver tick, `current-state` remains `idle` (or whatever was last written), producing a false impression that the agent is idle when it is actually working.
- **Suggested fix**: Either (a) add `current-state` marker writes to Case B, Boot Sequence, and the idle-cooldown-loop `absorb-work` path for consistency, or (b) add a scope note to Case C step 4 clarifying that the marker-write-on-start is specific to the task-chaining path and that other work-pickup paths are addressed in a follow-on slice. Option (b) is lower-risk for this S2 change.

---

### Finding 2

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: 77
- **Severity**: warning
- **Issue**: The phrase "every task close, hand-off, or task change" in Case C step 2 over-promises relative to what Case C actually covers. Case C fires only when the agent itself performs a `tracker.py transition` (step 1). But a "task change" can also occur externally — e.g., another agent reassigns or closes the task — in which case the agent discovers it via Case B's forge-read, and Case B has no idle-marker write instruction. The `current-state` would still name the externally-changed task, recreating the #12854 lingering-stale-content defect for that path.
- **Evidence**: 
  - Line 77: "Write the marker **on the transition** — every task close, hand-off, or task change"
  - Case C header (line 74): "After completing work" — scoped to agent-initiated completion.
  - Case B (lines 66-70): handles events when idle — would catch externally-driven task changes, but writes no idle marker.
  - The always-on rule (line 107): "Forge-read before acting. Every decision consults the forge." — an agent discovering via forge-read that its task was reassigned would clear `working-state.md`'s Task field but has no instruction to clear `current-state`.
- **Suggested fix**: Either (a) constrain the language to match Case C's actual scope: "every task close, hand-off, or task change **that you perform**" — or (b) add an idle-marker write to the Case B path for the sub-case where the forge-read reveals the agent's task is no longer its own (keeping it consistent with the always-on rule that the agent clears the Task field in that scenario). Option (a) is a one-word fix and aligns the text with the actual mechanics.

---

### Finding 3

- **File**: `references/sub-skills/common-events/event-mode-contract.md`
- **Line**: 77
- **Severity**: warning
- **Issue**: The parenthetical "(The `idle` marker is distinct from the `inline` operator-session marker you self-write during a human turn; don't conflate them.)" references a concept — "inline operator-session marker" — that is not defined anywhere in this file. An event-mode agent reads this fragment at boot (ordinal 11); the inline-marker definition lives in `references/roles/instructions.md` (line 151), which may or may not have been read yet depending on compose ordering. The instruction to "not conflate" is therefore underspecified: the agent knows what to DO (write `idle`) but cannot verify it is avoiding confusion with a pattern it hasn't been formally introduced to.
- **Evidence**: 
  - The only definition of "inline operator-session marker" in the repo is in `references/roles/instructions.md` line 151: `python references/scripts/cycle.py status-bar-self inline ""`.
  - The event-mode-contract.md has no link, footnote, or cross-reference to where the inline marker is defined.
  - AC8c requires the idle marker to be distinct — which it is (`idle|` vs `inline|`) — but the instruction's prohibition against conflation is unenforceable if the agent doesn't know what it's supposed to not conflate with.
- **Suggested fix**: Add a brief inline definition, e.g.: "(The `idle` marker — writing `idle` as the phase — is distinct from the `inline` operator-session marker — `python references/scripts/cycle.py status-bar-self inline ""` — that you self-write during a human turn; don't conflate them.)" This makes the distinction self-contained and actionable at boot without requiring the agent to have read `instructions.md` first.