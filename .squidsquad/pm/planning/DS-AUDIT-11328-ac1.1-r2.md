Here are my findings:

---

### Finding 1

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 252 vs 379
- **Severity**: warning
- **Issue**: The F1 inline qualifier at line 252 says the harness's cursor is "delivery state, **not work-completion state**" — but the §4.3 Cursor model section at line 379 opens with "The cursor IS the canonical **work-completed indicator**." These two statements directly contradict each other. A reader who sees the Principle 1 qualifier ("not work-completion state") and then encounters the cursor model headline ("work-completed indicator") will find them irreconcilable.
- **Evidence**: Line 252: `that's delivery state, not work-completion state.`  Line 379: `The cursor IS the canonical work-completed indicator.` The F1 fix sharpened the distinction in Principle 1 without updating the §4.3 cursor model section that uses the conflicting term "work-completed." The surrounding text at line 379 clarifies that "work-completed" means "events this alias has tended" (i.e., event-tending work), but the heading's choice of "work-completed indicator" is the exact phrase Principle 1 now says the cursor is *not*.
- **Suggested fix**: Align the §4.3 cursor model language with the Principle 1 qualifier. Change line 379 from `The cursor IS the canonical work-completed indicator.` to something like `The cursor IS the canonical event-tending indicator.` or `The cursor IS the canonical delivery-completion indicator.` — matching the "delivery state" terminology established in Principle 1.

---

## Assessment of F1–F4 resolutions

All four R1 findings are resolved in the text:

- **F1** (line 252): The parenthetical qualifier `(Per D1, the harness DOES track the per-alias event-tending cursor ... — that's delivery state, not work-completion state. See §4.3.)` is present and correctly distinguishes forge-level work state from the event-tending cursor.
- **F2** (line 255): Principle 4 has been rewritten to split `ack-cursor` (event-tending confirmation / event-completion semantics) from `ack-stop` (lifecycle confirmation / stop-intent progress). The rewrite is thorough and internally consistent with the §4.2 signal catalog.
- **F3** (line 403): The cross-reference no longer claims §7.1 has a "per-event eager loop"; it now says "the agent's loop" and adds an explicit forward-pointer: `(AC1.2 of #11328 rewrites §7.1 to the canonical per-event eager-loop form)`. §7.1 (line 806) still accurately describes the current batched-ack model — no misrepresentation.
- **F4** (line 250): The header now reads `Principles 1 and 4 refined by #11328 D1/D4 as noted inline:` — acknowledging that these two principles were amended rather than locked without modification. The section header "Architectural commitments (locked principles)" remains, but the inline qualifier makes the exception explicit.

## Coherence of §4.1

The five principles read as a coherent list. Principles 1 and 4 have parenthetical refinements that clarify rather than disrupt the original claims. Principle 2 (forge as truth), Principle 3 (agent owns completion), and Principle 5 (no completion endpoint) are untouched and remain consistent. The only coherence issue is the Finding 1 terminological conflict between Principle 1's new qualifier and §4.3's cursor model language, which lives outside §4.1 proper but is cross-referenced by it.