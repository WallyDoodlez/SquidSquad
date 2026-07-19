Now I have everything I need. Here's the audit:

---

# 10003-ds-audit-xp2-compose Research — Cross-Pair Consistency Audit: VAULT-ARCH (v2 TRD) vs COMPOSE-ARCHITECTURE (CURRENT)

## Summary

I audited `docs/VAULT-ARCH.md` (v2 prescriptive TARGET design) against `docs/COMPOSE-ARCHITECTURE.md` (CURRENT-state compose doc) for the four discrepancy classes specified in the task rules. The shared core invariant — the vault slot's L1-exclusivity — is correctly and consistently described in **both** docs (VAULT-ARCH §1/§2, COMPOSE §3.3/§5.6/§11.2-G4), and VAULT-ARCH §12.1 accurately characterizes COMPOSE's current treatment of the vault slot as one of six composed-output slots with L1-only authoring. Two low-severity findings emerged: a wrong section citation in VAULT-ARCH §1, and an incomplete reconciliation list in §12.2 that misses `confidence levels` references strewn across COMPOSE. Neither is a blocker — the docs are functionally converged on the L1-exclusivity guardrail that was the primary audit concern. Primary risk: the `confidence levels` references in COMPOSE are a v1 vocabulary vestige that will silently contradict VAULT-ARCH v2's entity model (§4.3) if not caught at cutover time.

## Vault Context

- **BRIEFING.md priorities**: The `>>> 2026-07-18 increment` lists four umbrella PRDs from DS TRD audits including `#10838 VAULT-ARCH` and `#10839 cross-TRD role→alias rename` — both are operator-paced post-cutover. The `#10837/#10839 need DS re-audit before pickup` constraint in "Constraints & Blockers" is directly relevant: this audit IS that DS re-audit (for the COMPOSE pair specifically). The HARD GATE for `#10838` is noted in "Recent Decisions" (audit refresh strategy).
- **Related decisions**: [[VAULT-ARCH v2 LOCKED telemetry storage]] — confirms §6.3 as operator-approved; no impact on this COMPOSE-pair audit since telemetry is a vault-internal concern, not a compose concern.
- **Related patterns**: None directly applicable — this is a doc-to-doc consistency audit, not an implementation pattern.
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." — reinforces the doc-first, audit-before-merge workflow this task is executing.
- **Related learnings**: None applicable.

## Impact Analysis

- **Files touched**: This audit is read-only — no files are modified. The two files examined are `docs/VAULT-ARCH.md` and `docs/COMPOSE-ARCHITECTURE.md`.
- **Behavior changes**: None — this is a consistency audit, not a code change.
- **Dependencies**: Findings here feed into VAULT-ARCH's final revision before merge; downstream, the COMPOSE reconciliation work item in §12.2 may need one additional sentence covering `confidence levels` cleanup.

## Side Effects

- **Risk 1**: The `confidence levels` references in COMPOSE §3.3, §5.6, and §11.2-G4 survive the §12.2 reconciliation pass uncaught — Severity: L — Mitigation: Add a note to §12.2's COMPOSE entry to also scrub `confidence levels` references when adding the vault-schema.json carve-out.
- **Risk 2**: The wrong §5.5 citation in VAULT-ARCH §1 could mislead a reader navigating to the wrong COMPOSE section — Severity: L — Mitigation: Fix the citation to §5.6 before merge.

## Edge Cases

- **VAULT-ARCH §1's "see COMPOSE §5.5"**: The reader lands on "Project Context" (L4-exclusive slot) instead of "Vault" (L1-exclusive slot). The section headings are different enough that the error is self-evident, but the chapter-and-verse citation is still wrong.
- **`confidence levels` as a contested term**: COMPOSE uses it in 5 locations; VAULT-ARCH v2 explicitly drops it (§4.3). At cutover time, a grep for `confidence` across COMPOSE would catch these, but §12.2 should list the locations to ensure none are missed — especially §11.2 G4 which is a gap-closure marker that references VAULT-ARCH's (now-changed) §4.4.

## Integration Risks

- **Risk**: AGENT-RUNTIME.md and INSTALLER-ARCH.md both also reference VAULT-ARCH's entity model (§7.6, §4.4 respectively). The `confidence levels` cleanup may cascade beyond COMPOSE. This audit's scope is COMPOSE-only, but the finding pattern (v1 vocabulary vestiges in cross-referencing docs) likely generalizes. Severity: L. Mitigation: Flag in the audit verdict so the AGENT-RUNTIME and INSTALLER reconciliation passes (also in §12.2) can grep for the same class of stale reference.

## Upgrade & Migration

- **New config values**: none
- **New files**: none
- **Template changes**: none
- **Upgrade steps**: N/A — no upgrade impact
- **Graceful degradation**: N/A

## Open Questions

- **Q1**: Should §12.2's COMPOSE entry enumerate every location needing text-level reconciliation (confidence levels, PARAG→type-registry vocabulary, contract description), or is the current "add the §3.1 carve-out" summary sufficient as a reconciliation directive? — **Why**: Overly granular §12.2 entries become maintenance burdens themselves; overly coarse ones miss cleanup targets. The current entry is coarse.

## Recommendation

**Feasible with caveats** — the two findings are low-severity and the core invariant (L1-exclusivity) is undamaged. The docs can merge as-is if the citation fix and §12.2 expansion are applied in a fast-follow revision. The `confidence levels` grep across COMPOSE is mechanical enough that a cutover-task checklist item covers it, but the safer path is a one-sentence addition to §12.2 now.

## Vault Candidates

- **Type**: learning — "Cross-TRD confidence-levels vocabulary vestige" — VAULT-ARCH v2 drops `confidence` from the entity model, but COMPOSE (and likely AGENT-RUNTIME, INSTALLER-ARCH) still reference it. When a TRD redefines a term, grep all cross-referencing docs for stale uses of the old term. **Why**: Prevents the same class of finding in future TRD audits (e.g., if `PARAG` is ever renamed).
- **Type**: pattern — "§12.2 reconciliation entries should enumerate concrete text changes, not just conceptual additions" — The current entry "add the §3.1 carve-out" is conceptual; a checklist-style entry listing specific stale terms to remove would be more auditable. **Why**: The §12.2 is the cutover operator's checklist; conceptual entries rely on the operator remembering to grep for secondary changes.

---

## Findings

### F1 — Wrong COMPOSE section citation (type d, nit)

- **VAULT-ARCH §1 line 33**: `"How vault slot content gets into composed CLAUDE.md (see [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) §5.5)"`
- **COMPOSE-ARCHITECTURE.md**: `§5.5` is "Project Context" (line 967); the vault section is **§5.6 "Vault"** (line 997). §5.5 discusses L4-exclusive project-context slot — irrelevant to vault slot content.
- **Severity**: **nit** — the reader can self-correct; §5.5 and §5.6 are adjacent in the TOC and the heading is clearly labeled. But the citation is objectively wrong.

### F2 — §12.2 COMPOSE entry misses `confidence levels` cleanup locations (type b, minor)

- **VAULT-ARCH §12.2 line 591**: Only mentions `"COMPOSE-ARCHITECTURE.md §5.6 / §3.3: the L1-exclusive vault slot survives; add the §3.1 carve-out — vault-schema.json is the sanctioned per-install taxonomy customization point, distinct from slot authoring."`
- **VAULT-ARCH §4.3** explicitly drops `confidence` from the entity model: `"Dropped from v1: confidence (was write-only — nothing ever consumed it for ranking or filtering; operator decision 2026-07-18)."`
- **COMPOSE locations still referencing `confidence levels`** (none flagged in §12.2):
  - §3.3 line 378 (vault row scope note): `"...PARAG model, entity types, wikilink grammar, confidence levels"`
  - §5.6 line 1005 (terminology table, vault contract row): `"...PARAG taxonomy, entity types, wikilink grammar, confidence levels"`
  - §5.6 line 1010 (slot description bullet): `"Wikilink format reminder, entity model, confidence levels."`
  - §5.6 line 1012 (L1-exclusivity rationale): `"...PARAG model, entity types, wikilink grammar, confidence levels — see VAULT-ARCH.md"`
  - §11.2 G4 line 1622 (gap-closure marker): `"VAULT-ARCH.md covers entity types (§4), wikilink grammar (§4.5), confidence levels (§4.4)"`
- **Severity**: **minor** — mechanical cleanup; a grep at cutover time catches these. But §12.2 is the operator's reconciliation checklist and it should enumerate stale terms, not rely on the operator to infer them from a conceptual directive.

---

## Verdict: **CONVERGED (0 blockers)**

The core shared invariant — the vault slot's L1-exclusivity — is stated identically in both docs with no contradiction. The two findings are a wrong citation (nit) and an incomplete §12.2 reconciliation checklist (minor). Neither blocks the TRD merge.