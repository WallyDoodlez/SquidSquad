# QA-RESULTS-10751 — PRD-A audit findings (1 ERROR + 4 WARNINGS)

**Verified**: 2026-06-02 10:10
**Branch**: `skill/issue-10751-prd-a-audit` @ `8db942e5`
**PR**: #10757
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Implementation files:
- `references/scripts/config.py` (+110) — `_parse_aliases_bullet_form()` helper + bullet-form fallback in `parse_aliases_registry()` + `_BULLET_LEGACY_ROLE_CLASS_SHIM` (qa→verifier, dev→worker) + `_BULLET_LEGACY_WORKER_L3_DOMAINS` (skill/ios/web/android/fullstack)
- `references/scripts/link_stage_validator.py` (+8) — R3 explicit layer guard
- `tests/test_config_aliases_registry_10385.py` (+120 new) — bullet-form + shim coverage + DS-review regression
- `tests/test_compose_a2f_10492.py` (+22) — W1 fixture column header fix + integration test
- `tests/test_link_stage_validator.py` (+12) — R3 layer guard regression
- `tests/test_compose_a6_v2.py` (+25) — D3 collateral fixture fix

## Audit Finding Resolution

| Finding | Disposition | Evidence |
|---|---|---|
| **ERROR** — Aliases registry parser rejects bullet form (blocks v2 deploys) | **FIXED** | `_parse_aliases_bullet_form` + bullet-form fallback in `parse_aliases_registry`. **Live verify**: `python -c "import config; print(config.parse_aliases_registry())"` on living install returns `{skill: (worker, skill), pm: (pm, None), dm: (dm, None), qa: (verifier, None)}` — exactly the expected shim semantics. v2 deploys now proceed past aliases parsing. SC1+SC2 are testable end-to-end again. |
| **W1** — A2f fixture column header `"Role class"` (space) vs strict `"role-class"` (hyphen) | **FIXED** | Test fixture now writes canonical `"role-class"`. Integration test added that actually exercises `parse_aliases_registry` against the staged config.md (was bypassed via pre-built dict before — silent latent regression source). |
| **W2** — `qa` role-class missing from `ALIASES_ROLE_CLASSES`; v2 parser doesn't participate in #6274 shim | **FIXED** | New `_BULLET_LEGACY_ROLE_CLASS_SHIM = {"qa": "verifier", "dev": "worker"}` mirrors `compose._BASE_ALIAS_6274` semantics. Applied symmetrically in both bullet-form and table-form normalization paths (per "qa/dev shim in table-form path too" in PT comment). |
| **W3** — A4 §9a coexistence claim wrong (no `--check --v2`) | **DEFERRED with tracking** | Filed as separate PM-scope question on **#10756**. Legitimate scope split — the disposition (implement vs defer + correct §9a wording) is a PM design call, not a skill-can-just-fix-it. Per `feedback_no_ship_with_gaps`: the gap is in a TRACKED issue, not "noted for follow-up". |
| **W4** — R3 validator missing explicit layer guard | **FIXED** | `link_stage_validator._check_r3_l1_l3_no_project_context_slot` now has `if src.slot == "project-context" and src.layer in ("L1", "L2", "L3"):` — symmetric with R2's existing guard. `test_link_stage_validator.py +12` adds regression coverage. |

## DS Review Catches

Skill ran DS code-review per `feedback_ds_review_per_change` and the review caught an additional bug:

- **Silent-drop on mixed-typo** — original `_parse_aliases_bullet_form` would silently drop a single bullet with an unrecognized value (e.g. `- **skill**: skil` typo) while accepting the other bullets. Fix: raise `AliasesRegistryError` naming the offending bullet AND the accepted value set so the operator can fix from the diagnostic alone. Regression test: `test_mixed_recognized_and_typo_raises_not_silently_drops`.

This is exactly the kind of bug a typo would smuggle past silently — DS review caught it before it could ship.

## Collateral Fixes

D3 (#10747) merge to main left `test_compose_a6_v2` failing because its fixture catalog was missing entries that D3's new catalog gate now requires. Skill fixed 4 collateral failures in `tests/test_compose_a6_v2.py` (+25). Surfaces appropriately: bug-fix scope properly widened to cover regressions introduced by adjacent merges.

## Per `feedback_bugs_need_research` + `feedback_ds_review_per_change`

PM's PT comment directed:
- Impact analysis before fix (`feedback_bugs_need_research`) — `.squidsquad/skill/planning/ds-10751-review.md` documents the analysis
- DS review each commit (`feedback_ds_review_per_change`) — DS found the silent-drop bug

Both protocols followed. Audit doc is in `.squidsquad/pm/planning/AUDIT-PRD-A-DS-REVIEW.md`.

## Live v2 Deploy Check

`python references/scripts/compose.py deploy pm --v2` on the branch:
- BEFORE fix: aborts with `"section is present but contains no table"` (the ERROR finding)
- AFTER fix: aliases parse cleanly; deploy proceeds to link-stage validation. Hits an R4 validation error on the live `.squidsquad/project/pm.md` (PRE-EXISTING L4 content concern, NOT in scope for #10751)

The chain is unblocked — the ERROR finding's specific failure mode no longer occurs.

## Test Execution

`pytest tests/test_config_aliases_registry_10385.py tests/test_compose_a2f_10492.py tests/test_link_stage_validator.py tests/test_v1_byte_stability_9a.py tests/test_compose_a6_v2.py -q` on `8db942e5` → **100 passed**.

Targeted coverage:
- Aliases registry (new tests for bullet-form + shim + typo-trap)
- A2f compose integration (W1 fixture + real-parser exercise)
- Link stage validator (W4 R3 layer guard)
- §9a v1 byte stability — **5/5 passed**, v1 untouched
- A6 v2 deploy (D3 collateral fixes)

Skill reported 95 tests in scope + 239 in wider sweep. My 100-pass cut covers all explicit AC bug-fixes + §9a regression.

## E6 Gate Status

Per issue body: "Hard gate on E6 (V2 CUTOVER #10685): the ERROR finding MUST be resolved before E6 can ship." → **gate cleared by this PR**.

## Outcome

ERROR fixed + 3 of 4 WARNINGS fixed + 1 WARNING properly deferred to tracked PM-scope question (#10756) + DS-caught silent-drop bug pre-shipped with regression. Scope discipline is good — collateral D3 regressions also addressed. **Transitioning #10751: pending-test → pending-ship.**
