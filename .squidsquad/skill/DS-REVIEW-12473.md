I've reviewed both changed files and the diff carefully against the four criteria. Here are my findings:

---

### Finding 1

- **File**: `references/roles/instructions.md`
- **Line**: 104
- **Severity**: warning
- **Issue**: The blockquote partially restates the prohibited-terms list inline as `(ack, cursor, nudge, GET/POST, etc.)` but omits four terms from the authoritative SOUL.md list — `event id`, `no-op`, `care filter`, and `drain`. The trailing `etc.` is not a reliable LLM substitute; an agent that reads the inline list without cross-referencing SOUL.md could emit those four terms in user-facing output, violating AC1.
- **Evidence**: SOUL.md lines 60–61 prohibit `ack`/`acked`, `cursor`, `event id`, `GET`/`POST`, `no-op`, `care filter`, `nudge`, or `drain`. Instructions.md line 104 lists only `ack, cursor, nudge, GET/POST, etc.` An LLM processing the instructions.md inline list may treat the `etc.` as non-specific and freely use `drain`, `no-op`, `care filter`, or `event id` — all of which are natural English words an agent might reach for (`"Queue is drained"`, `"It was a no-op"`, `"Event id doesn't match"`).
- **Suggested fix**: Either remove the inline partial list entirely (relying solely on the `per the **User-Facing Communication** rule in your Soul` reference), or reproduce the complete list verbatim from SOUL.md. The current half-restatement creates a sync hazard.

---

### Finding 2

- **File**: `references/roles/instructions.md`
- **Line**: 104
- **Severity**: warning
- **Issue**: The trigger description uses singular "the event" throughout — `"the fetch surfaces nothing, the event is skipped by the care filter, or a cared event turns out to need no work"` — which an agent could interpret as a per-event trigger. In a multi-event drain (one nudge brings several queued events), this could produce multiple one-liners per nudge rather than one per wake, contradicting SOUL.md's `"one short, plain sentence"` and `"every such no-action wake"` (per-wake) framing.
- **Evidence**: The §3 drain loop (instructions.md lines 79–99) processes events one-at-a-time in a `loop drain to empty`. If a single nudge finds 3 events all skipped by the care filter, the agent iterates: GET event 1 → skip → POST ack-cursor → GET event 2 → skip → POST ack-cursor → GET event 3 → skip → POST ack-cursor → GET returns none → queue drained. Reading `"the event is skipped"` as a trigger, an agent might emit the one-liner after each skipped event (3 times) instead of once at drain-end. The SOUL.md says `"Show that line on **every** such no-action wake"` — a "wake" is one nudge, not one event.
- **Suggested fix**: Change to per-drain language: e.g., `"Whenever a wake resolves to nothing for you — the drain finds no events, every event in the drain is skipped by the care filter, or every cared event in the drain turns out to need no work — surface it to the user..."`.

---

### Finding 3

- **File**: `references/roles/instructions.md`
- **Lines**: 102–104
- **Severity**: warning
- **Issue**: The one-liner and the improvement subloop both fire around the "queue drained" point, with no specified ordering. If the improvement subloop fires and produces visible work (files an improvement issue), emitting the default one-liner — `"nothing needs my attention right now"` — either before or after it creates a contradictory user experience. The agent has no guidance on whether the one-liner should precede or follow the subloop, or whether subloop output should suppress/alter the one-liner.
- **Evidence**: Line 102–103: `"When the queue drains, you optionally fire one improvement-subloop task (§4) if the cooldown is elapsed, then re-enter idle wait."` Line 104: `"Whenever a wake resolves to nothing for you... surface it to the user as a short plain-language one-liner."` If the improvement subloop fires and files an issue, the user sees work output bracketed by (or following) a statement that nothing needs attention. Conversely, an agent that concludes the subloop output means the wake didn't "resolve to nothing" might suppress the one-liner entirely — going silent in a case where the rule explicitly mandates visibility (`"always a one-liner, not silent"` per the task context).
- **Suggested fix**: Add explicit ordering and scoping, e.g.: `"Emit the one-liner after the improvement subloop completes (or is skipped). The one-liner covers only the forge-event drain — improvement-subloop findings are separate and don't change the message."`

---

### Finding 4

- **File**: `references/roles/SOUL.md`
- **Line**: 56
- **Severity**: warning
- **Issue**: `"adapt the wording freely"` combined with the permissive default template creates a vector for prohibited-term leakage. The instruction gives the agent freedom to rephrase but relies on a separate bullet-point rule (line 60) to constrain vocabulary. An LLM adapting the message to sound natural may reach for exactly the prohibited common-English words — `"No operations pending"` (contains `no-op` substring), `"Queue is drained"` (uses `drain`), `"Acknowledged — nothing to do"` (uses `ack` variant) — without recognizing the violation.
- **Evidence**: The SOUL.md says `"adapt the wording freely, keep it jargon-free"` (line 56), then separately on line 60 prohibits `no-op` and `drain`. Both are common English words an agent might naturally use when freely adapting a status message. The spatial separation of the permission ("freely") from the constraint (a later bullet) means an LLM that latches onto the adaptation freedom may under-weight the later prohibition, especially since `"nothing needs my attention"` from the template could naturally mutate into `"nothing to do — it was a no-op"` or `"queue drained, back to watching."`
- **Suggested fix**: Tie the constraint directly to the permission, e.g.: `"Default one-liner (adapt the wording freely but keep it jargon-free — never use ack/acked, cursor, event id, GET/POST, no-op, care filter, nudge, or drain):"` so the prohibited terms are co-located with the adaptation instruction.

---

All four findings are warnings (no errors). None of them would cause the agent to suppress the `POST ack-cursor` mechanics — both files explicitly state `"mechanics still run unchanged underneath"` (instructions.md) and `"This is wording only: the underlying mechanics ... still happen exactly as before"` (SOUL.md), which is a strong enough counter-signal to prevent over-suppression.