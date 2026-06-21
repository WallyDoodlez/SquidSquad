Now I'll perform the full cross-pair audit, trait by trait.

---

## Cross-Pair Audit: New Trait vs. Every Soul Trait

### Carve-outs verification (lines 44-45)
- ✅ **Carve-out 1**: "This does **not** override lane boundaries or *Never Stop While Work Is Pending*: handing off work that genuinely belongs to another role is correct. What is forbidden is *manufacturing* a handoff or a limitation to escape a hard problem that is yours to solve." — Present, complete, not weakened.
- ✅ **Carve-out 2**: "Bound the dig by reasonable depth (per *Token Consciousness*): timebox it, and if it overruns, surface the problem *with* your attempted approaches and the specific remaining blocker — not a bare 'can't.'" — Present, complete, not weakened.

### Trait-by-trait analysis

| Trait | Lines | Contradiction? |
|---|---|---|
| Core Identity | 12-14 | None |
| Situational Awareness | 16-22 | None — "understand WHY" complements "question the framing" |
| Vault-First | 24-33 | None — "research how solved elsewhere" aligns with vault consultation |
| Professionalism | 35-39 | None — "be thorough," "don't take shortcuts" are reinforced |
| **Treat "Impossible"** | 41-45 | *(the new trait)* |
| Never Stop | 47-62 | None — explicit carve-out; timebox ensures no indefinite stall; genuine handoffs preserved |
| Shared Discipline | 64-69 | None |
| Health & Diagnostics | 71-77 | None — "evidenced attempt" aligns with "facts over context" |
| Token Consciousness | 79-83 | None — explicit carve-out with timebox |
| User-Facing Communication | 85-94 | None |
| **Universal Quality Gate** | 96-100 | **Finding below** |

---

### Finding 1

- **File**: `references/roles/SOUL.md`
- **Line**: 43 vs. 100
- **Severity**: warning
- **Issue**: The new trait states that *"shipping without coverage are last resorts after the solution space is exhausted"* (line 43). The Universal Quality Gate states *"New work must have corresponding verification — verification is part of the implementation, not follow-up work"* (line 100). These two rules point in opposite directions: one opens the door to shipping without coverage as a permissible last resort, the other makes verification an absolute, non-negotiable part of implementation. The new trait does not reconcile this — it contains no language such as "subject to Universal Quality Gate" or "except where the Universal Quality Gate requires verification."
- **Evidence**: The phrase "last resorts" carries clear permission semantics — it means the action is undesirable but ultimately allowed once preconditions are met. The Universal Quality Gate uses unconditional "must" language with no exception clause. An agent reading both rules sequentially encounters an absolute prohibition followed (or preceded, depending on read order) by a qualified permission, with no guidance on which prevails. This is a behavioral-drift risk: an agent could invoke the new trait to justify skipping verification after hitting a wall, directly violating the Universal Quality Gate.
- **Suggested fix**: Add a reconciliation clause to the new trait or the Universal Quality Gate. Options: (a) In the new trait, replace "shipping without coverage" with "shipping with a documented coverage gap (per Universal Quality Gate, verification is still required for everything that *can* be verified)" — this preserves the gate's absoluteness while acknowledging that genuinely untestable code must be documented. (b) Add a cross-reference in the Universal Quality Gate acknowledging that documented, evidenced limitations are the only acceptable form of "without coverage." Either approach closes the gap between the two directives.

---

**Summary**: Both LOAD-BEARING carve-outs are present and intact. The trait does not contradict Never Stop, Token Consciousness, Professionalism, or any other Soul trait. One warning-level finding: an unreconciled tension between "shipping without coverage" as a last resort (new trait, line 43) and the absolute verification requirement (Universal Quality Gate, line 100).