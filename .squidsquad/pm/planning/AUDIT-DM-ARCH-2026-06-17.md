# audit-dm-arch Research — DM-ARCH DRAFT Consistency Audit

**Date**: 2026-06-17  
**Docs audited**: `docs/DM-ARCH.md` (DRAFT) against `docs/COMPOSE-ARCHITECTURE.md`, `docs/VAULT-ARCH.md`, `references/roles/dm/instructions.md`, `references/roles/dm/responsibility.md`, `references/sub-skills/roles/verifier/verification.md`

**2 ERROR / 0 WARNING / 3 LOW**

---

## ERRORS

### E1 — Stale step-number cross-reference in §5 Design Corrections (§5, line 102)

**Actual text** (line 102):
> Versioning is an optional L4 facet of step 6 (Document), not a universal step.

**Issue**: The spine was reordered (revision log line 143 explicitly states "Renumbered all cross-references"). In the final order, "Generate the delivery report" is **step 5**, not step 6. Step 6 is now "Contribute institutional knowledge." Additionally, "(Document)" is the old step name — the step is now called "Generate the delivery report" (or "Report" in shorthand).

**Fix**: Change to `"… optional L4 facet of step 5 (Generate the delivery report) …"`.

---

### E2 — Stale step-number in §6 Open Questions (line 124)

**Actual text** (line 124):
> 3. **Step 7 knowledge scope** — narrow (only delivery/release patterns) vs broad …

**Issue**: In the final reordered spine, knowledge is **step 6**, publish is step 7. "Step 7 knowledge scope" is stale — knowledge contribution is step 6. The question itself is about the knowledge step's scope, which is step 6.

**Fix**: Change to `**Step 6 knowledge scope**`.

---

## LOW

### L1 — "Two stores" table is incomplete on step 5's vault read (line 64)

**Actual text** (Two stores table, lines 64-66):
> | System of record | … | step 5 **reads** it → generates the report |
> | Vault | … | step 6 **writes** it (as do all roles) |

**Issue**: Step 5's description (line 36) also says it "traverse[s] the vault knowledge graph to attribute *what knowledge informed the delivery*" — so step 5 **reads** from the vault as well, not just from the system of record. The table is correct about primary substrates (system-of-record = fact-source for the report; vault = write target for knowledge) but omits step 5's vault traversal read.

**Fix**: Add a parenthetical to the Vault row or a footnote noting step 5 also traverses the vault for provenance during report generation. E.g., "step 6 **writes** it (as do all roles; step 5 also **reads** it for provenance)".

---

### L2 — Guardrail finding slightly overstates VAULT-ARCH's actual guardrail (§3, lines 82-89)

**DM-ARCH text** (line 82):
> the current "the *whole* vault contract is L1-exclusive" guardrail is over-broad

**VAULT-ARCH actual text** (§1 line 24):
> **Vault slot authorship is L1-exclusive** … The composed `## Vault` section in every agent's CLAUDE.md is authored entirely by L1 fragments … — L2 / L3 / L4 cannot contribute `slot: vault` content.

VAULT-ARCH's guardrail is about the **vault slot** (the `## Vault` H2 section in composed CLAUDE.md) being L1-exclusive, plus the vault **contract spec** (PARAG, entity types, wikilink grammar, confidence levels) being framework-owned. VAULT-ARCH does **not** say "the whole vault contract" in the sweeping sense DM-ARCH implies — it does not claim that content-governance instructions in OTHER slots (instructions, responsibility) are L1-exclusive.

DM-ARCH's **conclusion** is sound (only the machine skeleton is genuinely load-bearing/L1-fixed) and its **resolution** is coherent (content-governance instructions live in the role's own instructions/responsibility slots, not the vault slot). The issue is only that DM-ARCH's framing slightly exaggerates what VAULT-ARCH actually locks down, creating a mild straw-man. This does not block the document — the finding is explicitly deferred to VAULT-ARCH (#10838), not decided unilaterally.

**Fix**: Tighten the framing to match VAULT-ARCH's actual text. Instead of "the *whole* vault contract is L1-exclusive," say something like: "the current guardrail that the vault **slot** and the contract **spec** (PARAG model, entity types, wikilink grammar, confidence levels) are L1-exclusive may be broader than necessary — only the machine skeleton is genuinely load-bearing; content governance and form instructions in other slots compose from layers normally."

---

### L3 — L1 source location imprecise in §2 layer table (line 19)

**DM-ARCH text** (line 19):
> | **L1** universal agent | `references/roles/` (base) | base agent behavior (all roles) | — |

**COMPOSE-ARCHITECTURE actual** (§2 L1 row, line 92):
> `references/sub-skills/common/` (sub-skills L1 references) **and** the L1 portion of role source files

DM-ARCH's "`references/roles/` (base)" is imprecise — L1 content for the DM role also comes from `references/sub-skills/common/` (vault-protocol, l4-curation, etc.), not just role-specific base files. The "(base)" qualifier hints at this but the path is incomplete.

**Fix**: Expand to match COMPOSE-ARCHITECTURE's precision, e.g., `references/sub-skills/common/ + references/roles/dm/ (L1 portions)` or simply note "see COMPOSE-ARCHITECTURE §2."

---

## CHECK 3 Adjudication — Guardrail Claim

**DM-ARCH claims**: The vault's machine skeleton (wikilinks, frontmatter schema, PARAG placement) is genuinely L1-fixed/load-bearing, but the note body/prose, content form, and content-admissibility policy should be layer-customizable. The current "whole vault contract is L1-exclusive" guardrail is over-broad. Resolution: role-flavor lives in the role's OWN layers (instructions/responsibility slots), not the vault slot — so no relaxation of the vault-slot contract.

**Adjudication**: **FAIR, with a minor overstatement.** VAULT-ARCH's actual guardrail locks the **vault slot** (the `## Vault` section in CLAUDE.md) to L1-exclusive authorship and declares the **vault contract spec** (PARAG, entity types, wikilinks, confidence levels) framework-owned. It does NOT claim that content-governance instructions in other slots are L1-exclusive. DM-ARCH's resolution — that governance/form instructions belong in instructions/responsibility slots, not the vault slot — is **fully consistent** with VAULT-ARCH and COMPOSE-ARCHITECTURE's slot model. The vault slot remains L1-exclusive; content-governance instructions compose normally in the instructions slot. No hand-wave, no contradiction.

**DM-ARCH does NOT unilaterally change the guardrail.** It explicitly defers scope-clarification to VAULT-ARCH (#10838) at lines 82-83 and 89-90: "Scope-clarification belongs to **VAULT-ARCH (#10838)**, not here" and "flagged there." The DM-ARCH only documents the finding; it does not decide it.

---

## Premise Verification (CHECK 4)

Both premises confirmed:

- **"Bump every 10 features" baked into L2 DM role**: `references/roles/dm/instructions.md` lines 79-83 define `step:cycle/version-bump` — "Monitor `Shipped Since Last Bump` counter. When threshold is reached, run version bump commit and create release." `references/roles/dm/responsibility.md` line 12: "Owns version-bump coordination: monitors `Shipped Since Last Bump`, runs the bump commit when the threshold is reached." **CONFIRMED** — the bump-counter policy is in L2 DM, not L4.

- **Verifier increments the bump counter (release concern leaking into verification)**: `references/sub-skills/roles/verifier/verification.md` line 121: "Increment `Shipped Since Last Bump`: `python references/scripts/config.py set shipped-since-bump [N+1]`" — in Step 4 item 6, after transitioning to pending-ship. **CONFIRMED** — the verifier increments a release counter, which is properly a DM concern. The premise is accurate.

---

## Cross-Doc Accuracy Summary (CHECKS 2–3)

| Claim (DM-ARCH) | Verified against | Result |
|---|---|---|
| Override mechanism = existing compose machinery (slot+ordinal, op grammar, L2–L3 inline→L4 file ops, higher-wins) | COMPOSE-ARCH §3.2, §3.3, §4.6 | ✅ Accurate |
| L3 path = `references/roles/dm/<domain>/` | COMPOSE-ARCH §2 L3 row | ✅ Accurate |
| L4 path = `.squidsquad/project/dm.md` | COMPOSE-ARCH §3.3.1 | ✅ Accurate |
| Vault = PARAG + Galaxy Zettelkasten | VAULT-ARCH §3, §3.2 | ✅ Accurate |
| `[[wikilinks]]` as edges | VAULT-ARCH §4.5 | ✅ Accurate |
| `links:` frontmatter auto-maintained | VAULT-ARCH §3.2, §4.5 | ✅ Accurate |
| `resources/` = summarize-and-reference externals | VAULT-ARCH §3.1 | ✅ Accurate |
| Vault contract/slot L1-exclusive | VAULT-ARCH §1; COMPOSE-ARCH §3.3, §5.6 | ✅ Accurate |

---

## VERDICT: CONVERGED

The document is internally consistent on all architectural points (spine order, classification, layering, vault treatment) and cross-doc accurate against COMPOSE-ARCHITECTURE and VAULT-ARCH. The 2 ERRORS are stale-number artifacts from the spine reorder — simple line edits. The 3 LOW findings are minor imprecisions. The guardrail claim is a fair reading with a mild overstatement that the doc itself defers to VAULT-ARCH rather than deciding. No blocking issues.