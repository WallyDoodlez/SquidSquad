Now I have all the evidence needed. Let me compile the final research output.

---

# 10003-ds-audit-xp3-architecture Research — Cross-Pair Consistency: VAULT-ARCH.md vs ARCHITECTURE.md

## Summary

Audited `docs/VAULT-ARCH.md` (v1 current-state snapshot on `main`) against `docs/ARCHITECTURE.md` (system overview, L6 Memory layer) for cross-reference accuracy, shared invariants, and §12.2 reconciliation completeness. **The v2 TRD referenced in the task description does not exist on `main`** — it lives on branch `squidsquad/task/10003` (PR #13708, per BRIEFING.md L27). The audit was therefore performed against the v1 VAULT-ARCH.md that IS on `main` (descriptive snapshot, 2026-05-24), which has its own §12 cross-references and §12.2 reconciliation list.

Primary finding: the v1 VAULT-ARCH.md and ARCHITECTURE.md are **substantively consistent** in their shared description of the vault — same PARAG structure, same entity types, same key files, same design properties. No shared-invariant disagreements exist. However, VAULT-ARCH §12.1 (marked "verified") contains five cross-reference inaccuracies about ARCHITECTURE.md's content: a wrong layer count ("7-layer" vs. the actual "six"), misattributed section content, a stale reconciliation entry, a wrong table name, and minor line-number drift. None are blockers — all are documentation-level artifacts of VAULT-ARCH.md having been written before ARCHITECTURE.md was updated with its deep-dive pointer.

## Vault Context

- **BRIEFING.md priorities**: The v2 TRD is tracked on #10003 / PR #13708 (branch `squidsquad/task/10003`). The v2 telemetry storage design (§6.3) is LOCKED per operator 2026-07-18. DS re-audit needed on #10838 (VAULT-ARCH) — post-cutover, operator-paced. The v1 VAULT-ARCH.md on `main` is a "descriptive snapshot, 2026-05-24" with no proposals.
- **Related decisions**: [[decision-vault-subagent-model-sonnet]] — heavy vault sub-skills use `sonnet` tier; not directly relevant to this cross-doc audit.
- **Related patterns**: None directly applicable — this is a documentation audit, not an implementation pattern.
- **Human preferences**: "Terse, direct communication" / "Values working code over documentation" / "Cyclic/mechanical work must be programmatic" — the audit is documentation-scoped so code-verification is secondary; the doc-first process (learning below) governs cross-ref audits.
- **Related learnings**: [[learning-audit-scope-and-source-of-truth]] — "code is the tiebreaker, not the cross-doc delta" and "verify flagged premises doc-wide." [[learning-doc-first-for-architecture-changes]] — TRD must be human-reviewed before implementation tasks are filed; this audit is part of that pre-implementation gate.

## Impact Analysis

- **Files touched**: `docs/VAULT-ARCH.md` §12.1 and §12.2 (the cross-reference table and reconciliation list); `docs/ARCHITECTURE.md` is the reference target being described (no changes to ARCHITECTURE.md are proposed by this audit — only corrections to VAULT-ARCH.md's description of it).
- **Behavior changes**: None — documentation-only findings.
- **Dependencies**: None — this is a self-contained doc-vs-doc audit.

## Side Effects

- **Risk 1**: A reader following VAULT-ARCH §12.1 to ARCHITECTURE.md may expect a "7-layer stack" and find "six layers" — confusion about system fundamentals. Severity: **L** — Mitigation: Fix the cross-reference; actual system behavior is unaffected.
- **Risk 2**: The v2 TRD (branch `squidsquad/task/10003`) may inherit these cross-reference errors if the v1 §12.1 content is carried forward without re-verification. Severity: **M** — Mitigation: Flag all five findings for v2's §12.1 re-verification pass.

## Edge Cases

- **v1 vs v2 doc identity**: The task assumes `docs/VAULT-ARCH.md` is the v2 TRD, but the file on `main` is v1. This is not a finding under the task's rules (it's a premise mismatch, not a doc-vs-doc inconsistency), but it means the v2 TRD's §12.2 reconciliation list could not be audited. Whoever performs the v2 cutover should re-run this audit against the v2 file.
- **ARCHITECTURE.md was updated after VAULT-ARCH.md**: VAULT-ARCH.md v1 was written 2026-05-24; ARCHITECTURE.md's L152 deep-dive pointer to VAULT-ARCH.md was added later. This explains the stale §12.2 reconciliation item — it was correct when written but is now resolved.

## Integration Risks

- **No code-level integration risk**: This is a documentation audit. The systems described by both docs agree on substance.
- **The v2 TRD branch risk**: If the v2 TRD was built on the v1 §12.1 cross-reference table without re-verifying against current ARCHITECTURE.md, the five findings below will have propagated. The v2 TRD's §12.2 reconciliation list appears more extensive than v1's — whoever reconciles during M4 cutover (§10.5 in the v2 TRD) should verify ARCHITECTURE.md references fresh.

## Upgrade & Migration

- **New config values**: none
- **New files**: none
- **Template changes**: none
- **Upgrade steps**: N/A — no upgrade impact
- **Graceful degradation**: N/A

## Open Questions

- **Q1**: Does the v2 TRD on branch `squidsquad/task/10003` carry forward the v1 §12.1 "7-layer stack" error and the other four cross-reference inaccuracies? — **Why**: If yes, the v2 TRD's own "verified" cross-references are incorrect before it even lands, defeating the purpose of §12.2's reconciliation guidance.

## Recommendation

**Feasible with caveats.** The five findings are all documentation-level inaccuracies in VAULT-ARCH.md's §12.1 "verified" cross-reference table. None are blockers — the two docs agree on all substantive vault architecture claims (PARAG structure, entity types, key files, design properties). The fix is straightforward: correct the five items in §12.1 and mark the resolved item in §12.2. The caveat: whoever produces the v2 TRD must re-verify §12.1 against the then-current ARCHITECTURE.md before marking the section "verified."

## Vault Candidates

- **Type**: learning — "Cross-pair doc audits must verify the audited file actually exists in the expected version on the branch being audited" — **Why**: This audit's premise (VAULT-ARCH.md = v2 TRD) didn't match `main` reality. The v2 TRD lives on a feature branch; auditing `main` found v1. Future cross-pair audits should confirm file identity (version/status header) before proceeding.
- **Type**: learning — "VAULT-ARCH §12.1 layer-count error ("7-layer") persisted through a section marked 'verified'" — **Why**: A "verified" marker creates reader trust; when it's wrong, it erodes trust in the whole cross-reference table. §12.1 should either be re-verified on every revision or carry a "verify at reconciliation time" caveat.
- **Type**: learning — "Reconciliation lists go stale when the target doc is updated independently" — **Why**: VAULT-ARCH §12.2's ARCHITECTURE entry saying "doesn't reference this doc" was correct when written but is now stale because ARCHITECTURE.md gained the deep-dive pointer. Reconciliation lists that live in revision-tracked docs need a freshness date or a re-verify trigger.

---

**Verdict: CONVERGED (no blockers)** — 0 blockers, 3 minor, 2 nit. All findings are documentation cross-reference inaccuracies; no shared invariants disagree, no ARCHITECTURE.md sections are cited that don't exist, and no substantive vault design claims diverge between the two docs.