Now I have all the data needed. Let me compile the final research document.

---

# 10003-ds-audit-xp1-agent-runtime Research — Cross-Pair Consistency Audit: VAULT-ARCH v2 vs AGENT-RUNTIME

## Summary

Audited `docs/VAULT-ARCH.md` (v2 TRD, prescriptive TARGET design) against `docs/AGENT-RUNTIME.md` (CURRENT-state runtime doc) for the four discrepancy classes specified in the task brief. Both docs are live on `main`; VAULT-ARCH v2 is the prescriptive future-state TRD, AGENT-RUNTIME describes today's runtime. The audit surfaced **2 BLOCKER findings**: (1) VAULT-ARCH §12.1's cross-reference line numbers (L195, L507, L1044) are stale from a 2026-05-24 snapshot — AGENT-RUNTIME has undergone 19+ revisions since, and the current vault references live at completely different locations; (2) AGENT-RUNTIME §7.6 (L729) contains `"Tracked as VAULT-ARCH §11.5 + #10180"` — a dead cross-reference since v2 §11 is restructured as a flat table with no subsections — and this stale reference is absent from VAULT-ARCH §12.2's reconciliation list. Additionally, §12.1's depth characterization of AGENT-RUNTIME's vault coverage as "One row + two citations" significantly understates the current document, which devotes an entire dedicated subsection (§7.6) to vault touchpoints plus multiple inline references across four sections. No shared-invariant disagreements were found; all deliberate target-vs-current differences are properly scoped in §12.2.

**Recommendation**: Fix the §12.1 line numbers (re-verify against current AGENT-RUNTIME HEAD), add the stale-§11.5 cross-reference to the §12.2 reconciliation list, and refresh the §12.1 depth column for AGENT-RUNTIME to reflect its current substantial vault coverage. These are documentation-maintenance fixes with zero code impact.

## Vault Context

- **BRIEFING.md priorities**: "4 umbrella PRDs from DS TRD audits (#10836 INSTALLER-ARCH / #10837 HARNESS-ARCH / #10838 VAULT-ARCH / #10839 cross-TRD role→alias rename) — operator-paced post-cutover, #10837/#10839 need DS re-audit before pickup." This audit IS the #10838 VAULT-ARCH DS audit. Also: "Audit refresh strategy: HARD GATE for #10836/#10838; DS re-audit needed for #10837/#10839 before PM pickup."
- **Related decisions**: [[decision-vault-subagent-model-sonnet]] — the subagent execution lane for vault-remember/vault-synthesis uses `sonnet` tier; relevant because AGENT-RUNTIME §7.6 references this for its "Implementation gap" section.
- **Related patterns**: [[learning-audit-scope-and-source-of-truth]] — "A premise rarely lives in one section. When an audit flags a claim, grep that claim across the whole document before scoping the fix." Applied here: the stale L195/L507/L1044 line numbers affect only §12.1 but the "VAULT-ARCH §11.5" reference in AGENT-RUNTIME is a cross-doc issue. Also: [[learning-wire-format-specs-triplicated-across-trds]] — confirms cross-TRD drift is a recurring pattern; this audit is an instance of that class (VAULT-ARCH and AGENT-RUNTIME cross-references).
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." — directly relevant: the stale cross-references are documentation debt that will propagate at cutover if not fixed.
- **Related learnings**: [[pattern-stale-ac-vs-canonical-arch]] — "When a task's acceptance criteria contradict the canonical architecture doc, surface the specific fork." Not directly applicable here (no AC mismatch) but the principle of surfacing contradictions is the same.

## Impact Analysis

- **Files touched**: `docs/VAULT-ARCH.md` (re-verify §12.1 table row for AGENT-RUNTIME, add stale-§11.5 to §12.2 reconciliation), `docs/AGENT-RUNTIME.md` (the §11.5 cross-reference at L729 will need updating at cutover — already covered by the general "cycle-integration touchpoints change materially" clause in §12.2, but the specific §11.5 pointer needs to be part of the reconciliation sweep).
- **Behavior changes**: None — documentation-only audit.
- **Dependencies**: None — this audit finding feeds into the DS audit gate for #10838 (VAULT-ARCH).

## Side Effects

- **Risk 1**: If the §12.1 stale line numbers are not fixed before the VAULT-ARCH v2 merge, readers using the cross-reference table to navigate will land on unrelated content (L195 = DMTree mermaid label, L507 = EAD forge API budget header, L1044 = routing heading). — **Severity: M** — **Mitigation**: Re-verify §12.1 against current AGENT-RUNTIME HEAD and update the line numbers and depth column. This is a 5-minute mechanical check, not a design decision.

## Edge Cases

- **§12.1 claims verified 2026-05-24 but v2 rewrite happened 2026-07-18**: The rev log explicitly says "§12.1 verified cross-refs with line numbers" was done in the v1 draft and the v2 rewrite updated §12.2 but did NOT refresh §12.1. The L587 sentence "The §12.1 map of where the vault appears elsewhere still holds" is a blanket claim that was not re-verified. The fix is to either remove that sentence or explicitly re-verify and update the §12.1 data.
- **AGENT-RUNTIME §7.6 L731 "see VAULT-ARCH.md — §7 for sub-skills, §9 for cycle integration, §11 for known gaps"**: In v2, §11 is "Open decisions & gaps" (a table of 7 items). The semantic match is close enough that this cross-reference survives without breaking, unlike the specific "§11.5" pointer at L729 which is unequivocally dead.

## Integration Risks

- **§12.2 reconciliation completeness**: The current §12.2 AGENT-RUNTIME entry describes what changes (new touchpoints: context injection, consultation + receipts, receipt enforcement) but doesn't list the specific AGENT-RUNTIME sections that hold the current vault behavior needing replacement. Particularly §7.1 (cycle diagram with v1 vault touchpoints) and §7.6 (four-touchpoint table + implementation gap) are the sections that will need the heaviest reconciliation at M4 cutover. Naming them in §12.2 would make the reconciliation more mechanically verifiable.

## Upgrade & Migration

- **New config values**: None
- **New files**: None
- **Template changes**: None
- **Upgrade steps**: N/A — documentation findings, no code upgrade impact
- **Graceful degradation**: N/A

## Open Questions

- **Q1**: Should the VAULT-ARCH §12.1 cross-reference verification be re-run as part of the DS audit gate for #10838, or deferred to a separate doc-maintenance task? — **Why**: If it's deferred, the merged VAULT-ARCH v2 will ship with known-stale cross-references, violating the "documents live on forge, not chat" preference. If it's fixed inline, it adds scope to the audit but keeps the doc honest.

## Recommendation

**Feasible with caveats.** The three substantive findings are all documentation-maintenance issues with no code impact. They can be addressed directly in the VAULT-ARCH v2 draft before merge:

1. Re-verify AGENT-RUNTIME vault reference locations against current HEAD and update §12.1: L283 (decision note in §5.1), L621 (state persistence table row), L631-731 (vault touchpoints in §7.1/§7.6), L1387 (source material). Update depth from "One row + two citations" to "State-persistence row + dedicated vault touchpoints subsection (§7.6) + multiple cross-references."
2. Add to §12.2 AGENT-RUNTIME entry: "AGENT-RUNTIME §7.6's cross-reference to 'VAULT-ARCH §11.5' (implementation gap tracking) must be updated — v2 §11 is restructured as a flat table with no subsections."
3. Optionally, qualify or remove the L587 "still holds" sentence if §12.1 isn't re-verified.

The two remaining MINOR/NIT items (explicit §7.1/§7.6 naming in §12.2, §11.5 dead reference explicit callout) can be folded into the same edit pass.

## Vault Candidates

- **Type**: learning — "VAULT-ARCH v2 §12.1 cross-reference line numbers survived the v2 rewrite without re-verification" — **Why**: Instance of the [[learning-audit-scope-and-source-of-truth]] pattern: the v2 rewrite touched every section EXCEPT §12.1's line numbers, creating a 2-month verification gap. Future TRD rewrites should include a "re-verify all cross-reference line numbers" step in the rewrite checklist, or replace hard line numbers with section references (e.g., "AGENT-RUNTIME §5.1" instead of "L195").
- **Type**: learning — "AGENT-RUNTIME §7.6 cross-references a VAULT-ARCH subsection number (§11.5) that was restructured out of existence" — **Why**: Concrete instance of the general problem: when a target doc is restructured, inbound cross-references from sibling docs break silently. The §12.2 reconciliation list is the right place to catch these, but it only helps if the reconciler knows to check for them. A "grep all sibling TRDs for `VAULT-ARCH §` before finalizing a restructuring" rule would prevent this class of breakage.

---

**Verdict: 2 BLOCKERS**

| # | Criterion | Severity | Summary |
|---|---|---|---|
| F1 | (d) | **BLOCKER** | VAULT-ARCH §12.1 cites AGENT-RUNTIME at L195, L507, L1044 — all stale from 2026-05-24 snapshot. Current vault refs are at L283, L621, L631-731, L1387. Depth "One row + two citations" is wrong (AGENT-RUNTIME has a dedicated §7.6 vault touchpoints subsection). |
| F2 | (b) | **BLOCKER** | AGENT-RUNTIME §7.6 L729: "Tracked as VAULT-ARCH §11.5 + #10180" — v2 §11 has no subsections (flat table, items #1-7). §12.2 reconciliation list doesn't flag this dead cross-reference. |
| F3 | (b) | MINOR | §12.2 AGENT-RUNTIME entry describes what changes but doesn't name the specific AGENT-RUNTIME sections needing heaviest reconciliation (§7.1 cycle diagram, §7.6 vault touchpoints table). |
| F4 | (d) | NIT | §12.1 L587: "The §12.1 map of where the vault appears elsewhere still holds" is false for AGENT-RUNTIME — the data is unverified since 2026-05-24. |