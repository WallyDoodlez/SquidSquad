Now let me trace every relevant mention of the cursor's semantics across all four sections:

- **§4.1 Principle 1 (line 252)**: "the cursor is the work-completed indicator at event-delivery granularity, not forge-level workflow tracking"
- **§4.1 Principle 3 (line 254)**: "Agent owns work completion."
- **§4.1 Principle 4 (line 255)**: "ack-cursor fires after the agent has finished processing an event … it carries *event-completion* semantics; the cursor advance IS the completion signal."
- **§4.2 ack-cursor row (line 266)**: "Agent has finished processing this event (cared or skipped); cursor advances"
- **§4.2 line 269**: "ack-cursor advances the delivery cursor per event"
- **§4.3 line 379**: "The cursor IS the canonical work-completed indicator."
- **§4.3 line 385**: "one ack per tended event"
- **§5 line 575**: "Harness owns delivery state"
- **§5 line 579**: "cursor is harness-owned for event-delivery dedup"
- **§7.5 line 1046**: "harness owns delivery state (cursor)"

Now the full analysis:

**1. The original clash has been resolved.** The pre-R3 §4.1 text said "delivery state, not work-completion state" — which directly contradicted §4.3's "cursor IS the canonical work-completed indicator." The current §4.1 text (line 252) now says "the cursor is the work-completed indicator at event-delivery granularity, not forge-level workflow tracking." Both sections now agree the cursor *is* a work-completed indicator. The qualifier "at event-delivery granularity" distinguishes the cursor's scope from forge-level workflow tracking without denying its completion-semantics nature.

**2. Cross-section consistency holds.** Every section consistently describes the cursor as advancing after the agent *finishes processing* (not on delivery/receipt):

| Section | What it says about cursor advancement |
|---|---|
| §4.1 Principle 4 | "fires after the agent has finished processing an event" |
| §4.2 ack-cursor row | "finished processing this event (cared or skipped); cursor advances" |
| §4.3 line 379 | "advances only after the agent has finished processing an event" |
| §5 line 579 | cursor is "event-delivery dedup" (dedup happens at the *completion* boundary, not at receipt) |

**3. The apparent tension between §5's "delivery state" and §4.1/§4.3's "work-completed indicator" is not a clash.** The §5 "Why" column describes the ownership domain ("the harness owns the delivery subsystem's state") — it's not making a claim about whether the cursor tracks delivery vs. completion. The old §4.1 phrasing "delivery state, **not** work-completion state" had an explicit negation ("not") that created the clash. That negation is gone. Without it, "delivery state" and "work-completed indicator at event-delivery granularity" are compatible framings of the same thing: the cursor belongs to the harness's event-delivery infrastructure and its advancement means the agent finished processing an event.

**4. No regressions in the principle architecture.** The D1/D4 refinements referenced in §4.1 (lines 250, 252, 255) are applied consistently: D1 established that the cursor is the work-completed indicator at event-delivery granularity, and D4 established that ack-cursor and ack-stop are separate state machines. Both are reflected faithfully across all four sections.

**Conclusion: The R3 fix resolves the R2 clash without introducing new conflicts. All four sections (§4.1, §4.2, §4.3, §5) are now consistent on the cursor's semantics.**

```
NO_FINDINGS
```