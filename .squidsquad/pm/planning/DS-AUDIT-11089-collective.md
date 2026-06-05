I now have sufficient evidence for a comprehensive review. Here are my findings:

---

### Finding 1

- **File**: `docs/COMPOSE-ARCHITECTURE.md`
- **Line**: 418
- **Severity**: BLOCK
- **Issue**: §4 overview table says `CLAUDE.linked.md` is for "fallback when the assemble pass fails," but §4.6 lines 712 and 741 say it is "NOT a runtime fallback." These are directly contradictory statements about the same artifact within the same document.
- **Evidence**:
  - Line 418: "The **linked** output is preserved as a sibling artifact (...) for audit, debugging, and **fallback when the assemble pass fails**."
  - Line 712: "`CLAUDE.linked.md` — the **linked** output. **Audit / debug only — NOT a runtime fallback.**"
  - Line 741: "`CLAUDE.linked.md` is an audit/debug artifact, NOT a runtime fallback"
- **Suggested fix**: Change line 418 from "audit, debugging, and fallback when the assemble pass fails" to "audit and debugging only." This aligns the §4 overview table with the Change 8 semantics (per-slot fallback to verbatim inside the assembled output, never falling back to the linked file at runtime).

---

### Finding 2

- **File**: `.squidsquad/pm/planning/V2-AGENT-ASSEMBLE-DESIGN.md`
- **Line**: 76
- **Severity**: FLAG
- **Issue**: §1.4 Agent-tool invocation code example still uses `"subagent_type": "general-purpose"` with a comment `# or a new "assemble" type if we register one`. Meanwhile, the TRD §4.6 (line 595) shows `"subagent_type": "assemble"` as the settled value, and the planning artifact's own §9 Q1 LOCKED decision (line 412) says `LOCKED — register new subagent_type: "assemble"` and explicitly directs "Replaces line 76's 'general-purpose' placeholder with 'assemble' once the agent definition lands." The code section was never updated after the LOCKED decision.
- **Evidence**: TRD §4.6 line 595 vs. planning artifact §1.4 line 76 vs. planning artifact §9 Q1 line 412–413.
- **Suggested fix**: Update planning artifact §1.4 line 76 to `"subagent_type": "assemble"` and remove the comment. Also update §7.2 line 380 (`subagent_type: "general-purpose"` for Tier B audit) — the Tier B audit subagent should either use the custom `"assemble"` type with an audit-specific prompt or a distinct `"assemble-audit"` type; `"general-purpose"` is inconsistent with the TRD's rationale that "using the general-purpose subagent type … would leave the contract enforced only by prompt discipline" (TRD line 601).

---

### Finding 3

- **File**: `.squidsquad/pm/planning/V2-AGENT-ASSEMBLE-DESIGN.md`
- **Line**: Multiple — 124, 134, 394, 404, 426
- **Severity**: FLAG
- **Issue**: The planning artifact retains "opt-in" language in 5 locations despite the TL;DR (line 12) acknowledging "The opt-in/opt-out framing from this doc's first draft is superseded — the TRD-locked decision is unconditional assemble." The review criterion states "no opt-in language anywhere except as deprecated migration hint" — these are not migration hints, they're vestigial framing in the rollout plan, worked examples, and audit-cost estimate.
- **Evidence**:
  - Line 124: "No budget concern for the first **opt-in**."
  - Line 134: "Worked example — PM identity slot (first **opt-in** candidate)"
  - Line 394: "where N = **opted-in** slots. For the recommended first-**opt-in** (identity only), that's 2 spawns per deploy"
  - Line 404: "**opt** subsequent slots **in** (responsibility, then soul) once identity proves stable."
  - Line 426: "picks the first **opt-in** slot, signs off on Phase 2.2 ship."
- **Suggested fix**: Replace "opt-in" / "opted-in" / "opt … in" with "non-forced-verbatim" or "assembled" throughout. The phased rollout in §8 should be rewritten to describe progressive implementation of per-slot Agent spawns under the unconditional model, not progressive opt-in.

---

### Finding 4

- **File**: `docs/COMPOSE-ARCHITECTURE.md` line 707 vs. `.squidsquad/pm/planning/V2-AGENT-ASSEMBLE-DESIGN.md` lines 234–239
- **Severity**: FLAG
- **Issue**: The two documents specify different config formats for per-slot model overrides. TRD §4.6 line 707 uses `soul: { model: opus }` (object-valued with `model` sub-key). Planning artifact §3.1 lines 234–239 uses `soul-model: opus` (flat key with `-model` suffix). An implementer reading both documents would not know which format to parse.
- **Evidence**:
  - TRD line 707: "an install whose `soul` slot consistently produces low-quality reconciliations may set `soul: { model: opus }`"
  - Planning artifact lines 236–238: `- **identity-model**: sonnet`, `- **soul-model**: opus`, `- **instructions-model**: sonnet`
- **Suggested fix**: The planning artifact format (`<slot>-model: <tier>`) is simpler and unambiguous. Update TRD line 707 to match: change `soul: { model: opus }` to `soul-model: opus` and `identity: { model: haiku }` to `identity-model: haiku`. Consistent with the "update TRD first, then propagate to planning artifact" rule stated at TRD line 747.

---

### Finding 5

- **File**: `docs/COMPOSE-ARCHITECTURE.md`
- **Line**: 663–680 (conflict report format template)
- **Severity**: FLAG
- **Issue**: TRD §4.6 prose at line 639 says "Every conflict that survives the AC6 check appears in `CLAUDE.conflicts.md` (format below) **with the citation preserved verbatim** from the subagent's output." However, the conflict report format template at lines 663–680 does not include a `- **Justification citation**:` field. The planning artifact §5 (lines 312–334) DOES include this field. An implementer following only the TRD format template would omit the `justification_citation` from `CLAUDE.conflicts.md`, violating the operator-audit intent described in the prose.
- **Evidence**: TRD line 639 ("with the citation preserved verbatim") vs. TRD lines 670–677 (no `Justification citation` field in the template) vs. planning artifact line 327 (`- **Justification citation**: <justification_citation>`).
- **Suggested fix**: Add `- **Justification citation**: <justification_citation>` as a field in the TRD conflict report format template, between `Resolution` and the closing fence. Also consider adding `Total unresolvable fragments: <M>` to the header and an `## UNRESOLVABLE-U001` section template to match the planning artifact's §5 format (the TRD already defines unresolvable fragments in the failure mode table).

---

### Finding 6

- **File**: `docs/COMPOSE-ARCHITECTURE.md`
- **Line**: 491
- **Severity**: FLAG
- **Issue**: The §4.4 end-to-end pipeline mermaid diagram shows `LLM -->|LLM error| AbortAsm([Abort with diagnostic no output written])` — treating all LLM errors as whole-compose aborts. But §4.6 (Change 8) introduces a distinction: per-slot subagent failures (timeout, refusal, JSON parse, AC6 violation, preservation-token drop) fall back to verbatim for that slot only and compose succeeds. The pipeline diagram has not been updated to reflect this soft-degrade path.
- **Evidence**: §4.4 line 491 `LLM error → AbortAsm` vs. §4.6 failure mode table lines 721–726 showing per-slot fallback (compose succeeds) for timeout, refusal, JSON parse failure, AC6 violation, and preservation-token drop.
- **Suggested fix**: Update the §4.4 mermaid diagram to show two paths from the LLM node: per-slot failures (fall back to verbatim, continue to remaining slots) and structural contract violations (abort). The simplest fix: add a decision node after the Agent spawn that routes "per-slot failure" → "emit verbatim for this slot, continue" vs. "structural violation" → abort.

---

### Summary

| # | Severity | Location | Issue |
|---|---|---|---|
| 1 | **BLOCK** | COMPOSE-ARCHITECTURE.md:418 | §4 overview says linked file is "fallback when assemble fails"; §4.6 says "NOT a runtime fallback" — direct internal contradiction |
| 2 | FLAG | V2-AGENT-ASSEMBLE-DESIGN.md:76,380 | `subagent_type` still `"general-purpose"`; LOCKED decision (line 412) says `"assemble"`; code examples not updated |
| 3 | FLAG | V2-AGENT-ASSEMBLE-DESIGN.md:124,134,394,404,426 | 5 vestigial "opt-in" references contradict unconditional-assemble decision |
| 4 | FLAG | TRD:707 vs. planning:234–239 | Config format mismatch: `soul: { model: opus }` vs. `soul-model: opus` |
| 5 | FLAG | COMPOSE-ARCHITECTURE.md:663–680 | Conflict report format template missing `justification_citation` field that prose requires |
| 6 | FLAG | COMPOSE-ARCHITECTURE.md:491 | §4.4 mermaid diagram shows all LLM errors as abort; §4.6 has per-slot fallback for most |

**Cross-Change alignment checks passed:**
- **Changes 1 & 5** (unconditional + forced-verbatim-in-code): Aligned. TRD §3.0 line 137 and §4.6 line 603 both state unconditional assemble with `_FORCED_VERBATIM_SLOTS` enforced in code, not config.
- **Changes 2 & 3** (orchestrator-content rule + sub-skill criterion): Aligned. TRD §4.6 lines 572–586 define both consistently; `boot-bootstrap` is the sole must-be-inline exception.
- **Changes 4 & 5 & 7** (assemble subagent type + per-slot model override): Conceptually aligned but Finding 2 (subagent_type placeholder) and Finding 4 (config format mismatch) are implementation-level inconsistencies.
- **Changes 6 & 8** (AC6 retry + per-slot fallback): Aligned. TRD §4.6 line 637 (one retry) matches planning artifact §9 Q3 (one retry). Per-slot fallback ≠ compose abort is consistent across TRD §4.6 lines 717–741.
- **Change 9**: Does not contradict prior Changes. The audit-artifact descriptions (TRD §4.6 lines 709–713) are consistent with the rest of §4.6.
- **Per-slot fallback + atomic emit**: Consistent. TRD §4.6 line 739 explicitly states that partial assemble with fallback slots still emits the triple atomically.
- **Preservation guarantees / Cache / First-run determinism / Length-floor / Code-block parity**: All retain original semantics in §4.6 lines 620–631, 692–705, 745. Only the Substrate paragraph (lines 590–605) is new.
- **No opt-in language in TRD**: Confirmed. The TRD uses "unconditional" throughout; opt-in language appears only in the planning artifact (Finding 3).