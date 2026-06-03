# In-progress work manifest — DO NOT TREAT AS GAPS

This document lists the work that is **currently in flight** or **explicitly held**. The auditor must NOT flag these areas as gaps — they are known and being addressed.

## In flight (currently being implemented)

| Item | Status | Branch / PR | Scope |
|------|--------|-------------|-------|
| **E6 V2 CUTOVER (#10685)** | `status:in-progress` | `skill/e6-v2-cutover-10685` (multiple phases committed, no PR yet) | Atomic switch: drop `--v2` flag, make v2 default, delete v1 paths (`deploy_role`, `_load_manifest`, manifest-split, hint emit), rename v2 outputs to canonical paths. Phases 1-6 + 3a/3b/3b.2/3c/3c.5 committed; remaining sub-phases in flight. Per AC5 a single squash-PR at the end. |
| **PRD-D Sub-skills as Claude Skills (#10781)** | `status:planned` (Phase 2 locked rev 3) | not started | New PRD slice under COMPOSE-ARCH TRD §4.5.1. Hard-gated on E6 ship. Phase 2 decisions: 2-tier (inlined standing rules ~3 + Claude Skills ~55-60); per-clone install filter via catalog `Used by` column; deploy-time generator at separate installer step; ONE shared SKILL.md per Skill with agent inferring role from identity. Removes 3 catalog rows (`self-restart`, `context-pressure`, `cycle-runner`) — bodies still inline via includes.yml. Folds #10362. |

## Held (gated, not yet started — DO NOT flag as gaps)

| Item | Status | Gate |
|------|--------|------|
| **E7 V2 migration smoke (#10686)** | `status:approved` | Gated on E6 ship |
| **D6 Remove `event-driven:` config field (#10677)** | `status:approved` | Gated on E6 ship |
| **#10690 Wiki-link cross-reference rework + documentation-linkage sub-skill** | `status:approved` | Gated on E6 + E7 ship |

## Recently shipped (treat as DONE)

| Family | Stories | Notes |
|--------|---------|-------|
| **PRD-A (compose link stage)** | A1, A2, A2.6, A2a–A2f, A3, A4, A4.5, A5, A6 | All shipped. DS-audit umbrella #10751 also shipped (4 of 5 findings fixed; W3 was a §9a doc fix per #10756). |
| **PRD-B (compose assemble stage)** | B1, B2, B3, B4, B5, B6, B7, B8 + **B9 wiring (#10763)** | All shipped. DS-audit umbrella #10752 shipped (all 7 findings resolved — 5 as side effects of B9, plus W1 (B2 preservation verifier extension) + W4 (LLM context string) explicit). |
| **PRD-C (L4 customization)** | C1, C2, C3, C4, C5, C6, C7, C8, C9, C10 | All shipped. DS-audit umbrella #10753 shipped (1 ERROR + 3 WARNINGS all addressed). |
| **PRD-D (catalog + wake-mode)** | D1, D2, D3, D4, D5, D7, D8 + D6 held | D1–D5, D7, D8 shipped. D6 held until E6. |
| **PRD-E (freshness + cutover)** | E1, E2, E3, E4, E5 | Shipped. E6 in flight. E7 held. |
| Various bug fixes | many | E.g. #10743 catalog parser, #10817 catalog drift, etc. |

## What to audit FOR

For each TRD, identify:

1. **CONFIRMED**: TRD-promised features delivered by shipped work — cite shipped PRD/issue numbers as evidence.
2. **IN PROGRESS** (do NOT report as gap): TRD-promised features that the in-flight items above will deliver. Note which in-flight item covers each.
3. **HELD** (do NOT report as gap): TRD-promised features that the held items above will deliver. Note which held item covers each.
4. **REAL GAPS**: TRD-promised features that have NO corresponding shipped, in-progress, or held work. **These are the actual gaps.** Cite TRD section and what's missing.
5. **DRIFT**: TRD says X; shipped code does Y. Spec/impl mismatches that should be reconciled.
6. **STALE**: TRD makes claims that are now obsolete because the implementation diverged or scope changed (e.g. PRD-A §9a wording corrected at #10756).

## Output format

Per finding:
- **TRD section** cited (heading + line range if useful)
- **Verdict**: CONFIRMED / IN PROGRESS / HELD / GAP / DRIFT / STALE
- **Evidence**: file paths + issue numbers
- **Severity** (for GAP/DRIFT/STALE): high/medium/low
- **Suggested action**

Summary table at the end: per-section verdict count.
