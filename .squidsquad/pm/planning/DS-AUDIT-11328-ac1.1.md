Now I have all the evidence needed. Let me compile the findings.

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 252
- **Severity**: error
- **Issue**: §4.1 Principle 1 states the harness "does NOT track work completion, ticket state, or workflow status." This directly contradicts §4.3 line 379 ("The cursor IS the canonical work-completed indicator") and §5 line 575 (cursor is harness-owned in `.event-state.json`). Under D1, the harness DOES track work completion — the cursor is the single source of truth for "events this alias has tended" and lives in harness state.
- **Evidence**: The D1 decision (CONTEXT-11328 body-v3, line 24): "The cursor IS the work-completed indicator. Single source of truth." §4.3 line 379 repeats this verbatim and §4.3 line 383 says "Per-alias, owned by harness. Persisted in `.squidsquad/.event-state.json`." §4.1 line 252 was not updated and still carries the pre-D1 framing from vault note `decision-event-bus-architecture-redesign` (2026-05-21).
- **Suggested fix**: Replace §4.1 Principle 1 with wording that distinguishes between forge-level work completion (which the harness does NOT track) and event-tending-level cursor state (which the harness DOES track, per D1). Or add a bracketed amendment to the principle noting it is qualified by D1: the harness does not track *forge* work completion but does own the cursor as the work-completed indicator for event delivery.

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 255
- **Severity**: error
- **Issue**: §4.1 Principle 4 states "Ack = receipt confirmation, NOT completion confirmation" and defines ack as "the signal was delivered to the agent's session." This is a direct semantic conflict with §4.2 line 266 (ack-cursor = "Agent has finished processing this event (cared or skipped); cursor advances") and §4.3 line 379 (cursor IS work-completed indicator, advance after processing). The D1 decision explicitly removes the ambiguity: there is no separate "I received this" signal — finishing the event IS the cursor commit.
- **Evidence**: D4 (CONTEXT-11328 body-v3) says ack-cursor is "Delivery state advance" that fires "Per event after processing (cared or skipped)." §4.2 line 266 implements this: the ack fires *after* processing. §4.3 line 379: "there is no separate 'I received this' signal." But §4.1 line 255 still says ack means "the signal was delivered to the agent's session" — the exact "I received this" framing D1 rejects.
- **Suggested fix**: Rewrite §4.1 Principle 4 to distinguish between the pre-D1 generic "ack" concept and the post-D1 split: `ack-stop` is lifecycle receipt (stop-intent accepted), but `ack-cursor` IS work-completed confirmation — it fires after the agent has finished processing, not on delivery. Or add a parenthetical noting the principle predates D1/D4 and that `ack-cursor` specifically carries completion semantics.

---

### Finding 3

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 403
- **Severity**: warning
- **Issue**: §4.3 line 403 describes the cursor-advance diagram as the mechanism "the agent's per-event eager loop calls" and cross-references §7.1. But §7.1 (§§7.1 pseudocode at lines 789-804, sequence diagram at lines 808-840, and line 806 "The batched ack at the end signals…") currently describes the **old batched-ack-at-end model**, not a per-event eager loop. The cross-reference text was written anticipating AC1.2's §7.1 rewrite but the current §7.1 has not been updated yet.
- **Evidence**: Line 403: "see §7.1 for how the agent's per-event eager loop calls it." But §7.1 line 789-804 pseudocode iterates a for-loop, accumulates `last_tended`, then batch-POSTs a single `ack-cursor` at the end. §7.1 line 806: "The **batched ack at the end** signals 'I've handled or skipped everything up to last_tended; advance my cursor.'" No per-event eager loop exists in §7.1 yet.
- **Suggested fix**: Either (a) if AC1.1 ships before AC1.2, reword line 403 to describe the current batched model ("see §7.1 for how the agent's batched walk calls it") and update after AC1.2 lands, or (b) if the two sub-ACs are expected to ship in a single commit, ensure §7.1 is rewritten before line 403 ships with the phrase "per-event eager loop."

---

### Finding 4

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 252–256 (collectively, §4.1 Principles 1-4)
- **Severity**: warning
- **Issue**: §4.1 is sourced from vault note `decision-event-bus-architecture-redesign` (locked cycles 1541–1542, dated 2026-05-21), but that vault note predates the D1–D4 decisions. The vault note itself encodes "Ack = receipt confirmation, NOT completion confirmation" as a locked principle. D1 explicitly overrides this: the cursor IS the work-completed indicator. §4.1 Principles 1 and 4 are now semantically stale but are presented as active "locked principles" with no qualification that D1/D4 have partially superseded them.
- **Evidence**: The vault note at `.squidsquad/vault/galaxy/decision-event-bus-architecture-redesign.md` line 24 encodes precisely the pre-D1 ack semantics. The doc's §4.2/§4.3 encode post-D1 semantics. The §4.1 header (line 248) presents these as intact locked principles with no amendment or cross-reference to D1/D4. A reader arriving at §4.1 first will internalize a mental model that §4.2/§4.3 immediately contradict.
- **Suggested fix**: Add a brief amendment block after the 5 principles (after line 256) noting that Principles 1 and 4 are qualified by D1 (the cursor IS a work-completed indicator, and `ack-cursor` specifically carries completion semantics). Alternatively, note that the vault note `decision-event-bus-architecture-redesign` encodes the pre-D1 framing and that the final semantics are in §4.2/§4.3 per the #11328 D1/D4 decisions. This also implies the vault note itself should eventually be updated to reflect the new architecture.