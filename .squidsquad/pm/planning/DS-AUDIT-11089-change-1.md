I have reviewed the change in `docs/COMPOSE-ARCHITECTURE.md` at §3.0. Here are my findings.

---

## Verification of the four locked claims

All four claims from #11089 §'Locked decisions' #1 are **observable** in the new prose (lines ~130-134):

| # | Claim | Text |
|---|-------|------|
| (a) | unconditional | "**The §4.6 assemble pass is unconditional.**" |
| (b) | every non-forced-verbatim slot rewritten by the assemble subagent on every compose run | "Every non-forced-verbatim slot is rewritten by the assemble subagent on every compose run." |
| (c) | per-slot subagent task bounded by orchestrator-content rule (bounded prose reconciliation, not full-content authorship) | "This is feasible because the orchestrator-content rule (§4.6) keeps slots small and goal-shaped — the per-slot subagent task is bounded prose reconciliation against the precedence rule, not full-content authorship." |
| (d) | length-floor + forced-verbatim slot set are compose-time constants; assemble model + per-slot overrides configurable via `assemble-slots:` | "The length-floor and forced-verbatim slot set are compose-time constants; the assemble model and per-slot model overrides are configurable via `assemble-slots:` (see §4.6)." |

---

## Surrounding prose regression check

The new text sits between two existing sentences in the `.squidsquad/config.md` bullet:

- **Before**: "It declares install-level parameters: `Workers:` (the roster), `Iteration Interval`, `Improvement Scanning:`, other feature toggles, and the `squidsquad_version:` install-time stamp (read at upgrade time per INSTALLER-ARCH §10 step 2)."
- **After**: "Compose reads `config.md` to make compose-time *decisions* — what placeholder values to substitute, which aliases exist for `compose.py deploy-all`, etc. **Wake mode is NOT a config.md field**: …"

The new text integrates naturally: it follows the enumeration of what config.md *does* declare by clarifying what it does *not* control (assemble opt-out) and what it *does* control (model choice via `assemble-slots:`). The surrounding prose is unchanged and the paragraph's logical arc is preserved. **No regression.**

---

## Cross-reference resolution

The §4.6 section exists (line ~970 onward). The cross-reference resolves as a section target. However, the referenced concepts are **not yet present** in §4.6 — see Finding 1 below.

---

## Contradiction check

No contradiction with the rest of §3.0 was found. The new text is consistent with:

- Config.md being "the install's **configuration**, not a content layer"
- The mental-model table showing what config.md drives vs L1-L4 content
- The framing that "both feed compose; neither is a layer of the other"

The known contradiction with current §4.6 (model described as "compose-time constant — operators do not configure this per install" vs Change 1's "configurable via `assemble-slots:`") is correctly scoped to Changes 2-9 per the task instructions.

---

## Findings

### Finding 1

- **File**: `docs/COMPOSE-ARCHITECTURE.md`
- **Line**: ~133 (within the `.squidsquad/config.md` bullet, §3.0)
- **Severity**: FLAG
- **Issue**: Three forward-references point to content in §4.6 that does not yet exist at this change boundary: (i) "orchestrator-content rule", (ii) `assemble-slots:` config field, and (iii) "forced-verbatim" as a defined slot classification. A reader who follows the `(see §4.6)` or `(§4.6)` cross-references today will not find these concepts.
- **Evidence**: Grep of the file for `orchestrator-content` returns only the new §3.0 sentence; the term is absent from §4.6. Similarly, `assemble-slots` and `forced-verbatim` appear only in §3.0. The task context confirms §4.6 "has not yet been rewritten to match" and that Changes 2-9 will address this.
- **Suggested fix**: No fix required at this Change boundary — this is an inherent documentation-sequencing artifact. Note in the PR discussion that Changes 2-9 must add: (i) the orchestrator-content rule definition in §4.6, (ii) the `assemble-slots:` schema and parsing rules, and (iii) a definition of "forced-verbatim" slots (replacing the current "skipped" terminology). Consider whether the `assemble-slots:` cross-reference should also appear in the `config.md` schema listing earlier in the same bullet (the paragraph currently lists fields like `Workers:`, `Iteration Interval`, `Improvement Scanning:` — `assemble-slots:` is conspicuously absent from that enumeration).

### Finding 2

- **File**: `docs/COMPOSE-ARCHITECTURE.md`
- **Line**: ~131 ("Every non-forced-verbatim slot")
- **Severity**: NIT
- **Issue**: The term "forced-verbatim" is introduced without definition. The §13 Glossary defines "Slot" but not "forced-verbatim slot." The current §4.6 uses the term "skipped" for slots that bypass the assemble pass. A reader encountering "non-forced-verbatim slot" for the first time must infer the meaning from context.
- **Evidence**: §13 Glossary contains ~12 entries (Slot, Ordinal, Op, Target, Step ID, Sub-slot, Sub-procedure, Sub-skill, Composed output, Compose pipeline). No "forced-verbatim" entry. The term appears exactly once in the entire document.
- **Suggested fix**: When Changes 2-9 land, add "forced-verbatim slot" to §13 Glossary. This is optional at Change 1; the term is inferable. If the PR discussion wants to reduce forward-reference debt, a brief parenthetical could be added here: "non-forced-verbatim slot (i.e., every slot except the two that §4.6 marks as verbatim-preserved)" — but the task context suggests deferring to Changes 2-9.