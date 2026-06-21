Now I have all the evidence I need. Let me produce my findings.

---

```
### Finding 1

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 93
- **Severity**: warning
- **Issue**: The `stop-requested` handler tells the agent to "exit cleanly" — ambiguous language that could be interpreted as executing `/quit`. By contrast, the `deploy-signal` handler in the same file (line 97) uses explicit, unambiguous language: "**halt — cease output and end your turn**" and "You **cannot terminate your own process**." The `self-restart.md` file (line 22) likewise uses "**halt: start nothing new, cease output, end your turn.**" This inconsistency means the stop-requested handler is the one place in the three reviewed files that could still be read as implying the agent should self-/quit.
- **Evidence**: 
  - AC1: "agent does NOT terminate its own process" / "halt = cease output/end turn."
  - AC4: "/quit must NOT be framed as load-bearing."
  - The `deploy-signal` handler at event-mode-contract.md:97 explicitly states "You **cannot terminate your own process** — an LLM agent can only stop emitting output, not execute a real `/quit` (#13077)." The `stop-requested` handler at line 93 has no such caveat and uses the pre-#13077 language "exit cleanly."
  - The harness code at harness.py:4235-4245 documents the #13077 reality: "an LLM agent CANNOT execute /quit — it can only stop emitting output."
- **Suggested fix**: Replace "exit cleanly" with language consistent with the deploy-signal handler, e.g.: "then **halt — cease output and end your turn**. You cannot terminate your own process (an LLM agent can only stop emitting output, not execute a real `/quit` — #13077); the harness's 60-second force-kill net terminates your process." This makes the stop-requested handler self-contained and consistent with both the deploy-signal handler in the same file and self-restart.md.
```

```
### Finding 2

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 93
- **Severity**: warning
- **Issue**: The `stop-requested` handler does not instruct the agent to emit `ack-stop` with `result="stop-confirmed"`, while the `deploy-signal` handler (line 96) explicitly specifies `ack-stop` with `result="deploy-halted"`. The harness accepts `ack-stop` with `result="stop-confirmed"` (harness.py:3169-3179) and the instructions.md step:cycle/exit block (line 258) references "ack-stop can emit a coherent checkpointed / drained result." Leaving this out means the stop-requested path lacks the cooperative acknowledgement that the deploy-signal path provides.
- **Evidence**:
  - AC1: "agent's role on cooperative exit = finish atomic unit, emit ack-stop/exit-42 signal, then halt."
  - instructions.md line 258: "if intent=stopping was observed, finish the current event cleanly so ack-stop can emit a coherent checkpointed / drained result at the end of your drain."
  - The deploy-signal handler (event-mode-contract.md:96) explicitly includes: "emit `ack-stop` with `result='deploy-halted'`: `POST /events` with `event_type='ack-stop'`..."
  - harness.py:3169-3179 handles `ack-stop` with `result="stop-confirmed"` for the STOPPING intent path.
- **Suggested fix**: Add to the stop-requested handler: "At the boundary, emit `ack-stop` with `result='stop-confirmed'`: `POST /events` with `event_type='ack-stop'`, top-level `role=<your alias>`, payload `{event_id: <the stop-requested event's id>, result: 'stop-confirmed', role: <your alias>}`. Then halt — cease output and end your turn." This matches the structure of the deploy-signal handler and fulfills AC1's "emit ack-stop/exit-42 signal" requirement.
```

```
### Finding 3

- **File**: references/sub-skills/common-events/event-mode-contract.md
- **Line**: 93
- **Severity**: warning
- **Issue**: The `stop-requested` handler does not address whether to `ack-cursor` the stop-requested event. The `deploy-signal` handler (line 97) explicitly says "do NOT `ack-cursor` the deploy-signal" with a clear rationale. For `stop-requested`, the agent could default to POSTing `ack-cursor` after processing (the normal per-event contract in the eager loop), which would advance the cursor past the stop-requested event before the agent has actually halted — opening a narrow race window. The current text says "The cursor is harness-owned... and is preserved automatically across your exit — no agent-side cursor checkpoint to perform" but this addresses the cursor file, not the per-event `ack-cursor` POST.
- **Evidence**:
  - The per-nudge cycle in instructions.md (lines 79-100) shows `ack-cursor` is POSTed for every event after processing.
  - The deploy-signal handler explicitly says "do NOT `ack-cursor` the deploy-signal" and explains why (re-halt loop).
  - The stop-requested handler's "no agent-side cursor checkpoint to perform" refers to the `.event-state.json` file, not the per-event `POST ack-cursor`.
  - An agent following the normal eager-loop contract might POST `ack-cursor` for the stop-requested event before halting, since nothing tells it not to.
- **Suggested fix**: Add after the existing cursor note: "Do NOT `ack-cursor` the stop-requested event — the harness preserves your cursor across the stop." This mirrors the deploy-signal handler's explicit prohibition and eliminates ambiguity.
```

---

## Dispositions (skill)

Review by real DeepSeek (model_router, not the degenerate-fallback this time). All 3 findings concern the `stop-requested` handler's inconsistency with the now-corrected `deploy-signal` handler.

- **Finding 1 — FIXED.** "exit cleanly" is pre-#13077 language with the same `/quit` ambiguity #13134 targets, and the issue explicitly names "exit-42/**stop-requested**" as sharing the can't-self-`/quit` reality → in scope. Reconciled the stop-requested handler to "**halt — cease output and end your turn**; you cannot terminate your own process (#13077); the harness's 60-second force-kill net (armed on the `stopping` intent flip) terminates you." (event-mode-contract.md:93).
- **Finding 2 — JUSTIFIED-IGNORE → filed #13136.** Adding a manual `ack-stop(stop-confirmed)` instruction is a *new mechanic*, not `/quit`-drift, and is unsafe to assert without first resolving whether `cycle_post.py` already emits the stop ack-stop on exit-42 (if so, the agent must NOT). Out of #13134 scope; captured as low-sev follow-up **#13136** for PM/verifier triage.
- **Finding 3 — JUSTIFIED-IGNORE → filed #13136.** The `ack-cursor`-on-stop-requested guidance is likewise a separate correctness/precision question (verify against harness.py + AGENT-RUNTIME §5.2 before editing), not `/quit`-drift. Folded into **#13136**.

Net: 1 in-scope finding fixed; 2 out-of-scope observations preserved as #13136. No residual `/quit`-load-bearing framing in any of the 4 touched handlers (deploy-signal, stop-requested, self-restart, instructions Step 7).