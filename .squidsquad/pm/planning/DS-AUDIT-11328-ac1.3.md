Here are my findings after reviewing the §7.5 rewrite and cross-checking with the referenced sections:

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 64, 405, 780, 1030
- **Severity**: warning
- **Issue**: Batched-walk vocabulary remnants persist in sections outside §7.5, inconsistent with the eager per-event loop model established in §7.1.
- **Evidence**: 
  - **Line 64**: "during a **nudge-walk**; … if every event in the **batch** is filtered out" — The eager loop processes events one-at-a-time with per-event acks and re-GETs; there is no "walk" and no "batch" of events processed together. The term "nudge-walk" is undefined anywhere in the doc and inherits from the pre-D2 batched model.
  - **Line 405** (§4.3 Cursor model): "re-deliver on the next **walk**" — the cursor model describes at-least-once delivery. In the eager-loop model, re-delivery happens on "the next GET iteration" not a "walk."
  - **Line 780** (§7.0 Initial-queue ordering invariant): "processes these as the initial event **walk**" — should be "initial drain" or "initial event processing" to match the eager-loop vocabulary used in §7.2 step 4 ("performs the initial drain").
  - **Line 1030** (§7.4 EAD safety net diagram note): "Monitor → **walk**" — diagram note uses "walk" as shorthand for the agent's processing sequence. In the eager-loop model this is a continuous loop, not a discrete walk.
- **Suggested fix**: Replace "nudge-walk" on line 64 with "nudge-initiated drain" or "nudge-triggered loop iteration." Replace "batch" on line 64 with "returned events." Replace "walk" on line 405 with "iteration" or "loop cycle." Replace "initial event walk" on line 780 with "initial drain." Replace "Monitor → walk" on line 1030 with "Monitor → process" or "Monitor → loop."

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 1058
- **Severity**: warning
- **Issue**: The §7.5 crash-safety table row 3 recovery description states "Any single fresh post-restart nudge wakes the agent into §7.1" — implying a nudge is required for recovery. In fact, per §7.2 step 4, the agent's boot sequence directly enters §7.1, whose first iteration performs an initial GET that drains all events past cursor without waiting for any nudge.
- **Evidence**: 
  - §7.2 step 4 (line 874): "Enter §7.1 eager main loop. Its first iteration's `GET /events/for/{role}?since=cursor` performs the **initial drain**: if events are queued they're processed per-event with their acks; … No separate boot-time GET or branch is needed — §7.1 handles both cases natively."
  - The "multiple nudges arrived" scenario means events were queued at crash time. The cursor sits before those events. On restart, the initial drain's GET returns them immediately — no nudge is needed.
  - The text's framing "wakes the agent into §7.1" is doubly misleading: (a) the agent is already in §7.1 after boot, and (b) the initial GET at the top of the loop is what discovers the events, not a nudge. A nudge would only be relevant if the initial drain somehow found an empty queue and the agent reached idle_wait before the events appeared — which cannot happen when events were already queued at crash time.
- **Suggested fix**: Rewrite row 3 recovery to: "On restart, the agent enters §7.1 whose initial drain (per §7.2 step 4) processes every queued event in cursor order via the loop's drain-to-empty behavior. No nudge is required for the initial drain — the boot sequence handles it directly. If events arrive after the initial drain completes, the normal nudge path wakes the agent from idle_wait."

---

**Summary**: The §7.5 rewrite itself (lines 1040–1060) correctly implements all four AC1.3 requirements — the single-instruction procedure, §9 Q7 citation, eager-loop-reframed "Why no flag" bullets, and the three crash-safety table rows with D-Lock 3 framing. No contradictions were found with §7.1, §9 Q7, §4.3, or §5. The two findings above are cross-document consistency issues: stale "walk"/"batch" vocabulary in other sections (Finding 1) and a misstated recovery mechanism in the row 3 crash-safety cell (Finding 2).