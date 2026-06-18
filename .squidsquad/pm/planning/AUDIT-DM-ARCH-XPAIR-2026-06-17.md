---

# audit-dm-arch-xpair Research — Cross-Pair Prose-Drift Audit (Pass 2)

## Summary
Pass-2 reverse-direction audit of `docs/DM-ARCH.md` (draft, 2026-06-17) against the five paired documents from pass 1. DM-ARCH is internally clean: the post-pass-1 §6 resolved decisions + §3 step-6 enrichment introduced no new drift, and all internal cross-references are consistent. **However, DM-ARCH's generic reframe of the DM generates 4 ERROR-class contradictions in the OTHER docs (ARCHITECTURE.md, L2 DM instructions/responsibility, and verification.md)**, plus 1 DM-ARCH internal naming inconsistency (Q2 `skill-dev` vs existing L3 `skill` convention). Orphan linkage is real — no doc indexes or links DM-ARCH. The VAULT-ARCH guardrail clarification DM-ARCH flags for #10838 is confirmed not yet applied (genuinely needed).

**Recommendation**: File reverse-obligation tasks on the four impacted docs; fix the one DM-ARCH internal naming issue; add index entries. Then CONVERGED.

## Vault Context
- **BRIEFING.md priorities**: #10838 (VAULT-ARCH alignment) is in the post-cutover queue — this audit's guardrail finding directly feeds it. #12442 (DM event-mode auto-route) is active. #11400 (retire sub-skill-guide.md) may overlap with ARCHITECTURE.md doc-index changes.
- **Related decisions**: none specifically constraining this audit.
- **Related patterns**: [[learning-audit-scope-and-source-of-truth]] — the lesson that "a premise rarely lives in one section" and "code is the tiebreaker, not the cross-doc delta" guided this audit's approach: every contradiction was verified doc-wide before being filed.
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." Reverse obligations must be filed as tracker tasks, not applied silently.
- **Related learnings**: [[learning-audit-scope-and-source-of-truth]] — specifically, when two docs disagree, the delta tells you they disagree, not which is correct.

## Impact Analysis
- **Files touched**: 5 paired docs checked; 4 need changes; DM-ARCH needs 1 fix.
- **Behavior changes**: None (doc-only audit). No code changes needed.
- **Dependencies**: Reverse-obligation tasks depend on DM-ARCH being finalized (currently DRAFT/kickoff).

## Side Effects
- **Risk 1**: ARCHITECTURE.md's DM row is the most-visible summary to new readers. Leaving it stale while DM-ARCH exists creates confusion about which is canonical. — Severity: **H** — Mitigation: Update immediately when DM-ARCH is locked.
- **Risk 2**: The L2 DM `instructions.md` + `responsibility.md` currently run in production. DM-ARCH says they must be stripped to L4. Until the refactor tasks are filed and completed, the contradiction is acute — agents read the L2 DM today and execute the 10-feature-bump policy. — Severity: **H** — Mitigation: File as explicit "target" tasks gated on DM-ARCH polish pass.

## Edge Cases
- **L2 DM files are the CURRENT active agent instructions**: Changing `responsibility.md`/`instructions.md` changes what the live DM agent does. This is NOT a doc-only fix — it's a refactor that requires the full L3 extraction + L4 migration described in DM-ARCH §7.
- **ARCHITECTURE.md's 6-layer model predates COMPOSE-ARCHITECTURE's L1-L4**: ARCHITECTURE.md uses L1-L6 numbering for the runtime stack, not the compose layering. The DM row sits under "Agent Roles" in the Behavior (L3) section. Updating it for DM-ARCH's reframe must be careful not to introduce layer-number confusion.

## Integration Risks
- **COMPOSE-ARCHITECTURE L3 anchoring limitation**: DM-ARCH Q4 proposes H3 step anchors for L3/L4 targeting, but COMPOSE-ARCHITECTURE line 360 documents `#11227 AC-6` — L3→L2 anchoring is currently deferred (processor only anchors on H3, L2 sub-steps are H4). DM-ARCH's design (promote L2 DM steps to H3) would *fix* this limitation for the DM role, but the fix is novel — no other L2 role currently uses H3 for its sub-steps. Risk: compose tooling may need adjustment. Mitigation: Q2's "extract minimally" validates with minimal L3 content before scaling.
- **VAULT-ARCH #10838 scope**: DM-ARCH's guardrail finding (machine-skeleton vs content-policy) touches VAULT-ARCH §1 and COMPOSE-ARCHITECTURE §3.3/§5.6. Both docs assert L1-exclusive vault slot. DM-ARCH's refinement (only the skeleton is fixed; content policy composes) must be reconciled in VAULT-ARCH before DM-ARCH's step-6 content-policy design can be validated.

## Upgrade & Migration
- **New config values**: none
- **New files**: `references/roles/dm/skill-dev/` (or renamed from existing `skill/`) — TBD in DM-ARCH polish pass
- **Template changes**: L2 DM `instructions.md` + `responsibility.md` will be substantially rewritten (strip version-bump, reframe as generic spine)
- **Upgrade steps**: N/A — DM-ARCH is a draft; no upgrade impact until refactor tasks land
- **Graceful degradation**: N/A

## Open Questions
- **Q1**: Should the new L3 DM variant be named `skill-dev` (per DM-ARCH Q2) or reuse the existing `skill` directory? — **Why**: The existing `references/roles/dm/skill/` directory already exists as a DM domain variant. DM-ARCH proposes `skill-dev` as a new path. If they're the same thing, naming must be reconciled. If `skill-dev` is intentionally different, the distinction must be documented.
- **Q2**: Should COMPOSE-ARCHITECTURE's §12.1 cross-reference table add DM-ARCH? — **Why**: DM-ARCH is a consumer of the compose op grammar. Without a back-reference, a reader of COMPOSE-ARCHITECTURE won't discover DM-ARCH as an architectural consumer of the mechanism it documents.

## Recommendation
**Feasible with caveats.** DM-ARCH is internally clean (post-pass-1 edits verified). All reverse obligations are genuine and scoped. File them as tracker tasks. Fix the one DM-ARCH internal naming issue (Q2 `skill-dev` vs `skill`). Add index entries. After those tasks are filed: CONVERGED.

---

# Findings

## ERROR (5 findings)

### E1 — ARCHITECTURE.md DM characterization is STALE/CONTRADICTS DM-ARCH's generic reframe
- **Pair**: `docs/ARCHITECTURE.md` ↔ `docs/DM-ARCH.md`
- **Location**: `docs/ARCHITECTURE.md` line 215
- **Current text**: `| **DM** | Delivery packaging, docs, CHANGELOG, version bumps | User-first communicator, last-mile owner | Autonomous |`
- **What DM-ARCH says**: The DM is the **deliverer + historian + knowledge-harvester** (DM-ARCH §4, lines 92–97). Version-bumping is NOT universal — it's L4-only, project-specific policy layered onto step 5 (DM-ARCH §4 line 98, §5 line 102). "User-first communicator, last-mile owner" is a SquidSquad-specific characterization, not the generic DM.
- **Fix**: Rewrite the DM row in ARCHITECTURE.md's role table to: `| **DM** | Deliver verified work, generate delivery report, capture institutional knowledge | Deliverer + historian + knowledge-harvester | Autonomous |`. The "version bumps" and "CHANGELOG" entries should move to an L4 note (e.g., a parenthetical "project-configurable via L4: cadence, changelog format, version scheme").
- **Type**: REVERSE OBLIGATION on ARCHITECTURE.md (file as task)

### E2 — L2 DM `instructions.md` bakes `step:cycle/version-bump` as universal spine step
- **Pair**: `references/roles/dm/instructions.md` ↔ `docs/DM-ARCH.md`
- **Location**: `references/roles/dm/instructions.md` lines 5, 79–83
- **Current text**: Line 5 `step-ids: [step:cycle/issue-triage, step:cycle/delivery-packaging, step:cycle/version-bump, step:cycle/doc-improvement]`; lines 79–83 `#### step:cycle/version-bump` → `Monitor Shipped Since Last Bump counter. When threshold is reached, run version bump commit and create release.`
- **What DM-ARCH says**: Version is NOT an L2 spine step (DM-ARCH §5 line 102: "Version is not an L2 spine step. Many projects have no version."). The bump counter + threshold + semver policy are L4 project policy overlaid on step 5 (DM-ARCH §4 line 98). L2 DM must be version-agnostic.
- **Fix**: In the refactor (DM-ARCH §7): remove `step:cycle/version-bump` from the `step-ids` frontmatter; delete lines 79–83; move the bump-counter logic to L4 `.squidsquad/project/dm.md` as an op targeting a stable L2 spine step. The DM-ARCH spine has 8 steps; `version-bump` is not among them.
- **Type**: REVERSE OBLIGATION on `references/roles/dm/instructions.md` (file as task, gated on DM-ARCH polish pass)

### E3 — L2 DM `responsibility.md` describes a SquidSquad-specific shipper, not the generic DM
- **Pair**: `references/roles/dm/responsibility.md` ↔ `docs/DM-ARCH.md`
- **Location**: `references/roles/dm/responsibility.md` lines 9–14, 25
- **Current text**: Line 12: "Owns version-bump coordination: monitors Shipped Since Last Bump, runs the bump commit when the threshold is reached, and packages the release." Line 25: "honest version bumps let the operator trust the squad's output." Lines 9–14: The entire "What this role does" section describes the DM as a SquidSquad shipper (CHANGELOG, version bumps, merge feature branches).
- **What DM-ARCH says**: The DM's generic essence (DM-ARCH §4 lines 92–97) is three things — deliverer (steps 3–5), historian (step 5), end-to-end knowledge vantage (step 6). Version-bump ownership belongs to L4, not L2. The `responsibility` slot should describe the generic spine + defaults, not bake project policy.
- **Fix**: Rewrite `responsibility.md` to describe the generic DM: Detect ready work → Pre-flight → Package → Confirm landing → Generate delivery report → Contribute knowledge → Publish → Handle failure. Mention that cadence/version scheme/record format are L4-configurable. Remove all SquidSquad-specific policy (bump counter, CHANGELOG, merge-to-main, "version bumps let the operator trust").
- **Type**: REVERSE OBLIGATION on `references/roles/dm/responsibility.md` (file as task, gated on DM-ARCH polish pass)

### E4 — `verification.md` verifier increments the bump counter (release concern leaking into verification)
- **Pair**: `references/sub-skills/roles/verifier/verification.md` ↔ `docs/DM-ARCH.md`
- **Location**: `references/sub-skills/roles/verifier/verification.md` line 121
- **Current text**: `- Increment Shipped Since Last Bump: python references/scripts/config.py set shipped-since-bump [N+1]`
- **What DM-ARCH says**: DM-ARCH §5 line 103–104: "Release state belongs to the DM, not the verifier. Today SquidSquad's verifier increments the bump counter — a release concern leaking into verification. In the clean model, the verifier verifies and knows nothing about release policy; the DM owns all release state and reads its cadence from L4."
- **Fix**: Remove line 121 from `verification.md`. The DM (post-refactor) will own this increment as part of its L4-configured step-5 behavior. This is one of the refactor tasks enumerated in DM-ARCH §7 line 135.
- **Type**: REVERSE OBLIGATION on `references/sub-skills/roles/verifier/verification.md` (file as task, gated on DM refactor)

### E5 — DM-ARCH Q2 L3 path `skill-dev` inconsistent with existing L3 naming convention
- **Pair**: `docs/DM-ARCH.md` §6 Q2 ↔ `docs/COMPOSE-ARCHITECTURE.md` §2 + existing `references/roles/dm/skill/`
- **Location**: `docs/DM-ARCH.md` line 123: "extract into an L3 `references/roles/dm/skill-dev/` variant"
- **Current reality**: 
  - COMPOSE-ARCHITECTURE line 94 defines L3 as `references/roles/<role>/<domain>/` with examples `roles/worker/android/`, `roles/verifier/web/`
  - The repo already has DM L3 domain variants at `references/roles/dm/skill/`, `references/roles/dm/android/`, `references/roles/dm/ios/`, `references/roles/dm/web/`, `references/roles/dm/fullstack/`
  - The domain name `skill` (not `skill-dev`) is the existing convention for the "Claude Code skill development" L3 variant
- **Contradiction**: DM-ARCH proposes a new path `skill-dev` that doesn't match the existing `skill` domain directory. If `skill-dev` is intended as the same variant, the naming diverges from the existing convention. If `skill-dev` is intentionally different from `skill`, the distinction is undocumented.
- **Fix**: Either (a) rename `skill-dev` → `skill` in DM-ARCH to match the existing convention, or (b) document why `skill-dev` is a distinct new variant and what happens to the existing `skill/` directory. The COMPOSE-ARCHITECTURE L3 convention is `references/roles/<role>/<domain>/` — the domain name is a short descriptor (`android`, `web`, `fe`, `be`), not a compound. `skill-dev` is a compound; `skill` matches the pattern.
- **Type**: DM-ARCH INTERNAL FIX (naming inconsistency in Q2; resolve in polish pass)

## WARNING (5 findings)

### W1 — DM-ARCH absent from ARCHITECTURE.md and README.md doc indexes
- **Pair**: `docs/ARCHITECTURE.md` + `README.md` ↔ `docs/DM-ARCH.md`
- **Location**: `README.md` lines 145–154 (Documentation table); `docs/ARCHITECTURE.md` — no companion-docs section exists
- **Current state**: README.md lists 6 docs: ARCHITECTURE.md, AGENT-RUNTIME.md, sub-skill-guide.md, CONTRIBUTING.md, CHANGELOG.md, SKILL.md. DM-ARCH is not listed. ARCHITECTURE.md only cross-references VAULT-ARCH.md (line 152); no other ARCH docs are indexed.
- **Obligation**: DM-ARCH should be added to README.md's Documentation table (e.g., `| [DM Architecture](docs/DM-ARCH.md) | The layered delivery manager — generic L2 spine, L3 domain variants, L4 project policy |`). ARCHITECTURE.md should gain a "Companion architecture docs" section listing DM-ARCH alongside VAULT-ARCH, COMPOSE-ARCHITECTURE, etc. This is a forward-obligation from DM-ARCH existing.
- **Type**: REVERSE OBLIGATION on README.md + ARCHITECTURE.md

### W2 — DM-ARCH Q4 H3 naming convention doesn't match COMPOSE-ARCHITECTURE's `step:cycle/<id>` format
- **Pair**: `docs/DM-ARCH.md` §6 Q4 ↔ `docs/COMPOSE-ARCHITECTURE.md` §3.3
- **Location**: `docs/DM-ARCH.md` line 124: "one H3 per spine step in the instructions slot (e.g. ### Step 3 — Package)"
- **Current convention**: COMPOSE-ARCHITECTURE line 358: "Anchor must be an H3. An inline step-targeted directive only anchors if its target appears as a top-level `### step:cycle/<id>` heading in the base." The op grammar resolves `### insert-after step:cycle/<id>` against `### step:cycle/<id>` anchors. The existing L2 DM uses `#### step:cycle/delivery-packaging`, `#### step:cycle/version-bump` (H4, line 73, 79 of instructions.md).
- **Drift**: DM-ARCH's example `### Step 3 — Package` would NOT match the `step:cycle/<id>` pattern the op processor looks for. However, DM-ARCH uses "e.g." — this is illustrative, not prescriptive. The actual authoring must use `### step:cycle/package` or similar for the op grammar to target it.
- **Fix**: Clarify in the DM-ARCH polish pass that the H3 naming convention for step addressability must follow the `### step:cycle/<id>` pattern (e.g., `### step:cycle/package`, `### step:cycle/preflight`, etc.) to be compatible with the existing op grammar. The current "Step 3 — Package" example is misleading as a concrete naming example.
- **Type**: DM-ARCH INTERNAL FIX (clarify H3 naming in §6 Q4 or §7)

### W3 — ARCHITECTURE.md Feature Lifecycle diagram now incomplete (missing knowledge step)
- **Pair**: `docs/ARCHITECTURE.md` ↔ `docs/DM-ARCH.md`
- **Location**: `docs/ARCHITECTURE.md` lines 219–232
- **Current text**: The feature lifecycle flow chart ends with "DM delivers docs+changelog → Shipped → Done"
- **DM-ARCH reframe**: The DM now additionally captures institutional knowledge (step 6) and publishes (step 7) after the report. The lifecycle diagram doesn't reflect the knowledge-harvesting role.
- **Fix**: Add "DM captures knowledge → vault" as a post-delivery step in the lifecycle diagram, or add a note that the DM's delivery step now includes knowledge contribution per DM-ARCH.
- **Type**: REVERSE OBLIGATION on ARCHITECTURE.md (low priority, can be batched with E1)

### W4 — COMPOSE-ARCHITECTURE §12.1 cross-reference table should add DM-ARCH
- **Pair**: `docs/COMPOSE-ARCHITECTURE.md` ↔ `docs/DM-ARCH.md`
- **Location**: `docs/COMPOSE-ARCHITECTURE.md` §12.1 cross-reference table (if exists — verify; DM-ARCH references COMPOSE-ARCHITECTURE §3.2–§3.3 as the override mechanism)
- **Drift**: DM-ARCH is a significant consumer of COMPOSE-ARCHITECTURE's op grammar — it parameterizes the DM entirely through the existing L2→L4 compose mechanism. But COMPOSE-ARCHITECTURE doesn't list DM-ARCH as a consumer/doc. This is a discoverability gap.
- **Fix**: Add DM-ARCH to COMPOSE-ARCHITECTURE's cross-reference section as an architectural consumer of the op grammar.
- **Type**: REVERSE OBLIGATION on COMPOSE-ARCHITECTURE.md (low priority)

### W5 — ARCHITECTURE.md DM row uses "version bumps" and "last-mile owner" which are now SquidSquad-specific, not generic
- **Pair**: `docs/ARCHITECTURE.md` line 215 ↔ `docs/DM-ARCH.md` §4
- **Location**: Same as E1 but flagged separately because the Soul column ("User-first communicator, last-mile owner") is also stale.
- **Drift**: DM-ARCH reframes the DM as deliverer+historian+knowledge-harvester. "User-first communicator, last-mile owner" is a project-specific soul characterization that belongs in L3/L4 soul fragments, not in the architecture overview of what the DM *is*.
- **Fix**: Replace Soul column too: `| Deliverer + historian + knowledge-harvester |` or keep it brief: `| End-to-end delivery owner, squad knowledge synthesizer |`.
- **Type**: REVERSE OBLIGATION on ARCHITECTURE.md (combine with E1)

## LOW (3 findings)

### L1 — VAULT-ARCH guardrail clarification NOT yet applied (confirms #10838 genuinely needed)
- **Pair**: `docs/VAULT-ARCH.md` §1 ↔ `docs/DM-ARCH.md` §3 guardrail finding
- **Location**: `docs/VAULT-ARCH.md` line 24: "Vault slot authorship is L1-exclusive (guardrail dated 2026-05-29). … The contract documented here (PARAG model, entity types, wikilink grammar, confidence levels) is framework-owned and is not customizable per-role-class, per-domain, or per-install."
- **DM-ARCH finding** (lines 82–89): The guardrail is **mildly over-broad** — ONLY the machine-readable skeleton (`[[wikilink]]` syntax, frontmatter keys, PARAG placement) is genuinely L1-fixed. The note body/prose, content-form, and content-admissibility policy compose from layers like every other slot. DM-ARCH correctly defers this scope-clarification to VAULT-ARCH (#10838).
- **Verified**: VAULT-ARCH §1 still asserts the entire vault slot is L1-exclusive with no distinction between machine skeleton and content policy. The clarification DM-ARCH flags does NOT exist in VAULT-ARCH yet. DM-ARCH did NOT unilaterally change it — it flagged the finding and deferred. #10838 is genuinely needed.
- **Type**: CONFIRMATION ONLY — no DM-ARCH action needed; feeds #10838

### L2 — DM-ARCH §6 Q3 two-granularities resolution: no contradiction with §3 or §7
- **Pair**: `docs/DM-ARCH.md` §6 Q3 ↔ `docs/DM-ARCH.md` §3 step 6 + §7
- **Verified**: Q3 resolves "both — broad is the DM's signature contribution" with part-level detail (like every role) + broad task-level synthesis (by vantage). §3 step 6 (line 37) already describes "two granularities" with identical framing. §7 line 96 says "end-to-end vantage" — consistent. No drift. ✓
- **Type**: VERIFICATION ONLY — no action

### L3 — DM-ARCH revision log has stale step-number references from pre-reorder era
- **Pair**: `docs/DM-ARCH.md` revision log entries ↔ current §3 numbering
- **Location**: `docs/DM-ARCH.md` line 143: "step 6 also traverses the graph for provenance" — by current numbering, traversal is step 5 (Generate delivery report), not step 6. Line 142: "step 7 writes it" — now step 6 (Contribute institutional knowledge).
- **Drift**: The revision log entries from 2026-06-17 (before the Package/Publish reorder at line 148) reference the old numbering where step 6 = report and step 7 = knowledge. After the reorder, these are steps 5 and 6 respectively. This is purely cosmetic — revision logs record historical state, not current state.
- **Fix**: Optional: add a parenthetical note in the revision log saying "(numbering at time of entry; current steps 5 + 6 after the Package/Publish reorder)". Not required.
- **Type**: DM-ARCH INTERNAL — cosmetic only, no urgency

---

## Orphan Linkage — Required Insertions

| # | Target file | Insertion point | What to add |
|---|-------------|-----------------|-------------|
| LK1 | `README.md` | Documentation table (lines 145–154) | New row: `[DM Architecture](docs/DM-ARCH.md) \| The layered delivery manager — generic L2 spine, L3 domain variants, L4 project policy` |
| LK2 | `docs/ARCHITECTURE.md` | New section after §Key Design Decisions (line 280) or as a "Companion architecture docs" block after the layer diagram | Companion docs listing: `[DM-ARCH.md](DM-ARCH.md)` — layered delivery manager architecture |
| LK3 | `docs/COMPOSE-ARCHITECTURE.md` | Cross-reference table (or new §12 entry) | DM-ARCH as a consumer of the compose op grammar for L2–L4 DM customization |

---

## Post-Pass-1 Edits Verification

| Edit | Status | Notes |
|------|--------|-------|
| §6 Resolved Q1 (ship-on-ready default) | ✓ CLEAN | Consistent with §3 "Default (no L4 policy)" line 41 |
| §6 Resolved Q2 (extract L3 now, `skill-dev/`) | ⚠️ NAMING ISSUE | Path `skill-dev` diverges from existing `skill/` convention — see E5 |
| §6 Resolved Q3 (two-granularities knowledge) | ✓ CLEAN | Matches §3 step 6 and §7; no contradiction |
| §6 Resolved Q4 (H3 per step in instructions) | ⚠️ NAMING DRIFT | Example `### Step 3 — Package` doesn't use `step:cycle/` prefix convention — see W2 |
| §3 step 6 two-granularities enrichment | ✓ CLEAN | Consistent with §6 Q3; no internal contradiction |

---

## VERDICT: NOT CONVERGED

**Reason**: 4 ERROR-class reverse obligations exist on other docs (ARCHITECTURE.md E1, L2 DM instructions.md E2, L2 DM responsibility.md E3, verification.md E4) + 1 DM-ARCH internal naming issue (E5 `skill-dev` vs `skill`). Orphan linkage is unaddressed (LK1–LK3). DM-ARCH itself is internally clean post-pass-1 — the "NOT CONVERGED" is entirely about what the OTHER docs must change to align with DM-ARCH's target model.

**To reach CONVERGED**: (1) Fix E5 in DM-ARCH (reconcile `skill-dev` naming); (2) File E1–E4 as reverse-obligation tasks on the respective docs (do NOT change them here — DM-ARCH is the target draft); (3) File LK1–LK3 as index-linkage tasks; (4) Address W2 (H3 naming convention) in the DM-ARCH polish pass. After all tasks are filed: CONVERGED.

## Vault Candidates
- **Type**: learning — **Prose-drift audits need both forward and reverse passes; a forward-only pass under-reports systemic contradictions** — **Why**: Pass 1 (forward: "is DM-ARCH accurate about other docs?") caught 0 errors in the other docs. Pass 2 (reverse: "are other docs accurate about DM-ARCH's new model?") caught 4 ERRORs. This confirms the audit methodology should always be bidirectional, and the pass-1 scope note was correct to exclude reverse direction.
- **Type**: learning — **When a TRD reframes a role, the role's existing L2 instructions become instant contradictions** — **Why**: DM-ARCH's generic reframe makes the current L2 DM instructions/responsibility wrong by definition. The refactor tasks are not "improvements" — they are mandatory reconciliation. This pattern will recur for any future role reframe (PM, verifier, worker).
- **Type**: decision — **DM-ARCH L3 path naming: use existing convention (`skill`) not new compound (`skill-dev`)** — **Why**: COMPOSE-ARCHITECTURE's L3 convention uses short domain descriptors (`fe`, `be`, `android`, `ios`, `web`, `skill`). A new compound name (`skill-dev`) breaks the pattern and creates ambiguity with the existing `skill/` directory. This decision should be locked before the refactor tasks are filed.