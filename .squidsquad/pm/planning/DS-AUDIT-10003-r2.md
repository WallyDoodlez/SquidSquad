Now I have all the data. Let me produce the final audit.

---

# 10003-ds-audit-r2 Research — VAULT-ARCH.md Internal Consistency Audit Round 2

## Summary

Round 2 systematically verified all 9 Round 1 findings (3 blockers, 6 minors) against the current text of `docs/VAULT-ARCH.md`. All 9 are **resolved**: dead section refs removed, `.gitattributes` locations harmonized, supersession pointer fully qualified, `recency` defined, "sonnet subagents" replaced with "lightweight-tier model subagents," planning-doc shorthand introduced, vestigial §4.5 refs now valid, bucket definitions directional (not circular), hub-list drift resolved.

However, the fixes introduced **one new blocker**: the §6.3 rewrite introduced three unqualified `§9.4` references (lines 317, 326, 329) that refer to the *planning doc's* §9.4 (telemetry storage/harness-local store), but now collide with this doc's own §9.4 ("Verification — receipt enforcement," line 448). A reader navigating to this doc's §9.4 will find unrelated content. Plus **5 minors**: a wrong external section ref, a stale status line, vestigial `-equivalent` qualifiers, a dangling decision-number cross-ref, and one additional ambiguous `§9.4` in §4.3.

**Verdict: 1 BLOCKER.**

## Vault Context
- **BRIEFING.md priorities**: DS re-audit needed on #10837/#10839 before PM pickup; #10838 (VAULT-ARCH) is one of 4 umbrella PRDs from DS TRD audits; the current BRIEFING notes the "v2 telemetry storage LOCKED" decision with canonical ref to this doc's §6.3.
- **Related decisions**: [[decision-vault-subagent-model-sonnet]] — references a v1-era §7 and §11.5 that no longer exist in v2 VAULT-ARCH.md; the note itself is stale but not within scope of this audit.
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." — consistent with this TRD's doc-first process.
- **Related learnings**: none directly applicable to an internal consistency audit.

## Impact Analysis
- **Files touched**: `docs/VAULT-ARCH.md` only (this audit is read-only; only flagging issues, not fixing them).
- **Behavior changes**: N/A — consistency audit, no code changes.
- **Dependencies**: `VAULT-COMPARISON-DMPWEB.md` (planning doc) — several cross-references point into it; `COMPOSE-ARCHITECTURE.md` — one cross-ref points to the wrong section.

## Side Effects
- **Risk 1**: The ambiguous `§9.4` references could mislead an implementer reviewing §6.3 into consulting the wrong section (§9.4 Verification) and missing the planning doc's telemetry-storage rationale — Severity: **H** — Mitigation: qualify all three as `VAULT-COMPARISON-DMPWEB.md §9.4`.

## Edge Cases
- **Context-dependent §9.4**: Line 224's `the §9.4 rule` is parenthetically anchored by a preceding `VAULT-COMPARISON-DMPWEB.md §9.4 P1` and is less ambiguous than lines 317/326/329, but still benefits from explicit qualification for a reader who jumps in mid-paragraph.

## Integration Risks
- **Planning-doc drift**: §6.3 (line 316) explicitly says the canonical wording lives in VAULT-ARCH.md, superseding the planning doc's §10.5 "where they differ." If the planning doc's §9.4 (§10.5 redesign section) is ever updated independently, the unqualified `§9.4` pointers in VAULT-ARCH.md would become even more confusing.

## Upgrade & Migration
- **New config values**: none
- **New files**: none
- **Template changes**: none
- **Upgrade steps**: N/A — no upgrade impact
- **Graceful degradation**: N/A

## Open Questions
- **Q1**: Should the `-equivalent` qualifiers be stripped entirely, or is there a deliberate reason to keep them (e.g., to distinguish v2 §7.3's *role* from what v1's §7.3 *was*)? — **Why**: Over-cleaning could lose intentional nuance; under-cleaning leaves vestigial noise that contradicts the "all sections v2" claim.

## Recommendation

**Feasible with caveats** — 1 blocker (ambiguous §9.4 refs), 5 minors. All are mechanical fixes: qualify references, fix a section number, drop a stale status line, clean up `-equivalent` qualifiers, fix a dangling decision-number pointer. No design rethinking needed. Estimated ~7 line edits.

## Vault Candidates
- **Type**: pattern — "Cross-reference discipline for TRDs: when a section is renumbered, grep all `§N.M` references in the doc; unqualified references to external docs' sections that collide with the doc's own numbering are a recurring trap." — **Why**: This is the second audit in a row where section renumbering during rewrite created ambiguous `§9.4` references (Round 1 had dead refs; Round 2 has collision refs). A checklist item in the DS-audit playbook would prevent recurrence.
- **Type**: learning — "Status-line staleness: when a resolution is recorded mid-doc but the header/status line still says 'pending,' the doc contradicts itself. The `still pending` on line 285 vs `Resolved direction` on line 383 is the canonical example." — **Why**: This pattern (status line not updated when the resolution lands elsewhere in the same doc) is common enough in long TRDs to warrant a specific audit check.

---

## Detailed Findings

### ROUND 1 VERIFICATION — ALL 9 RESOLVED ✅

| # | Round 1 Finding | Severity | Status | Evidence |
|---|---|---|---|---|
| 1 | Dead refs `§9.5.1`/`§9.3.2`/`§9.5-M1` | blocker | ✅ RESOLVED | Zero grep matches for any pattern |
| 2 | `.gitattributes` location contradiction §6.3 vs §8.5 | blocker | ✅ RESOLVED | §6.3 L323: full path `.squidsquad/vault/.telemetry/.gitattributes`; §8.5 L425: relative `.telemetry/.gitattributes` (context: installer seeds from vault root). Same file, no contradiction. |
| 3 | §6.3 supersession pointer at wrong §10.5 | blocker | ✅ RESOLVED | L316: `VAULT-COMPARISON-DMPWEB.md §10.5` — fully qualified to planning doc; planning doc §10.5 exists (line 395 of that file). |
| 4 | Undefined `recency` | minor | ✅ RESOLVED | L307: `recency = a 0–1 freshness score computed from days since the note's updated: frontmatter date, newer → higher` |
| 5 | "sonnet subagents" | minor | ✅ RESOLVED | L538: `lightweight-tier model subagents per topical cluster (per the house lower-models-for-subagents rule)` |
| 6 | Planning-doc shorthand un-introduced | minor | ✅ RESOLVED | L5: `(the "planning doc" hereafter)` |
| 7 | Vestigial `§4.5`-equivalent | minor | ✅ RESOLVED | All 3 `§4.5` refs (L159, L409, L532) now point validly to §4.5 "Wikilinks" |
| 8 | Circular bucket defs §4.4/§6.4 | minor | ✅ RESOLVED | §4.4 L241-245 defines buckets; §6.4 L335: `buckets every note into §4.4's three classes (definitions canonical there)` — directional |
| 9 | Hub-list drift §3.2/§10.3 | minor | ✅ RESOLVED | §10.3 L541: `exemplars per §3.2` — no separate list to drift |

### NEW FINDINGS — ROUND 2

#### BLOCKER

**B1 — Ambiguous `§9.4` references collide with this doc's own §9.4** (lines 317, 326, 329, and secondarily 224)

The doc's §9.4 (line 448) is **"Verification — receipt enforcement"** — the verifier checking that receipt sections exist in task artifacts. But §6.3 uses unqualified `§9.4` to refer to the *planning doc's* §9.4 (about telemetry storage, harness-local store, "notes stay pure content"):

- **Line 317**: `**Why §9.4's harness-local store had to change**` — this doc's §9.4 says nothing about a harness-local store.
- **Line 326**: `This preserves the intent behind §9.4's original "never in a PR" directive` — this doc's §9.4 is about receipt verification, not PR hygiene.
- **Line 329**: `**What survives from §9.4 unchanged**` — this doc's §9.4 doesn't contain anything about "notes stay pure content."
- **Line 224**: `the load-bearing half of the §9.4 rule` — same collision, though parenthetically anchored by a preceding `VAULT-COMPARISON-DMPWEB.md §9.4 P1`.

**Fix**: Qualify all four as `VAULT-COMPARISON-DMPWEB.md §9.4` (or, for lines 317/326/329, restructure to refer to `§10.5` of the planning doc since that's where the supersession design lives).

#### MINORS

**M1 — Wrong external section ref: §5.5 should be §5.6** (line 33)

> `How vault slot content gets into composed CLAUDE.md (see COMPOSE-ARCHITECTURE.md §5.5)`

COMPOSE-ARCHITECTURE.md §5.5 (line 967) is "Project Context" — about L4 project facts, not the vault slot. The vault slot is covered in §5.6 (line 997). **Fix**: `§5.5` → `§5.6`.

**M2 — Stale "still pending" contradicts "Resolved direction"** (line 285 vs 383)

> Line 285: `two feasibility checks still pending — see §7/§8`
> Line 383: `Resolved direction (planning doc §10.3, verified §10.7)`
> Revision log L600: `the two §10.3 packaging verifications resolved by live probe`

The §6 header text wasn't updated when §7.5 recorded the resolution. **Fix**: Change "still pending" to "now resolved (see §7.5)" or remove the parenthetical.

**M3 — Vestigial `-equivalent` qualifiers** (lines 216, 247, 341)

Three references use `§7.3-equivalent` or `§7-equivalent`:

- L216: `set by vault-optimize (§7.3-equivalent)`
- L247: `vault_optimize.py's pruning decisions (§7.3-equivalent)`
- L341: `vault_optimize.py's pruning/archival proposals (§7-equivalent)`

§7.3 "vault-optimize — maintenance" and §7 "The sub-skills" both exist now (lines 349, 370). Other references already use unqualified `§7.3` (line 409: `Analyze/apply split per §7.3`). The `-equivalent` suffix is vestigial from when sections were being ported in. **Fix**: Drop `-equivalent` for consistency with the "all sections v2" status claim.

**M4 — Dangling `(§9.6 open decision #5)`** (line 327)

> `6. **Durability** (§9.6 open decision #5) largely **dissolves**`

§9.6 is "Quiet cycles — maintenance" and doesn't contain open decisions. Open decisions are in §11, where #5 is "Viewer priority" (line 567) — not durability. The reference is to the planning doc's original decision numbering where #5 was telemetry durability. **Fix**: Change to `(planning doc §9.6 #5)` or remove since the resolution is stated inline ("largely dissolves").

**M5 — Ambiguous `§9.4 rule` in §4.3** (line 224)

> `"notes stay pure content" was always the load-bearing half of the §9.4 rule`

Though contextually near `VAULT-COMPARISON-DMPWEB.md §9.4 P1`, the unqualified `§9.4 rule` is still ambiguous against this doc's §9.4. **Fix**: `the §9.4 rule` → `that §9.4 rule` (anaphoric) or fully qualify.

### VERDICT

**1 BLOCKER.** The ambiguous §9.4 references (B1) are a real navigation hazard — a reader following `§9.4` from §6.3 will land on verification receipts, not telemetry storage. All other findings are minor mechanical fixes. The doc is otherwise internally consistent.

**CONVERGED with 1 blocker.**