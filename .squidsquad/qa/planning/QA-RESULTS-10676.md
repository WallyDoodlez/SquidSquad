# QA-RESULTS-10676 — PRD-D / Story D5: Unify manifest (additive includes-v2.yml)

**Verified**: 2026-06-02 06:10
**Branch**: `skill/d5-manifest-v2-10676` @ `aeebf6aa`
**PR**: #10745
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/roles/pm/includes-v2.yml` (+41 new) — 29 entries
- `references/roles/dm/includes-v2.yml` (+35 new) — 19 entries
- `references/roles/verifier/includes-v2.yml` (+30 new) — 16 entries
- `references/roles/worker/includes-v2.yml` (+40 new) — 23 entries
- `references/scripts/compose.py` (+142) — `_load_manifest_v2(role_name)` + `_load_manifest_v2_from_file()` helper + `_V2_MANIFEST_FILENAME` constant
- `tests/test_manifest_v2_d5.py` (+268 new) — 36 tests
- `tests/run_tests.py` (+1)
- `.squidsquad/skill/planning/ds-d5-review.md` (DS review log) — non-runtime

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | New `includes-v2.yml` per role-class with content = union of `includes.yml` + `includes-events.yml`, no mode-conditional sections | Live set-arithmetic check: pm (29=29∪28), dm (19=19∪18), verifier (16=16∪15), worker (23=23∪21). **extra={} and missing={}** for all 4. Event includes are strict subsets of polling includes in this codebase, so union ≡ polling set — sensible and verifiable. | PASS |
| 2 | `_load_manifest_v2(role_class)` with NO `wake_mode` argument | Live introspect: `_load_manifest_v2(role_name: str) -> list \| None`. `'wake_mode' in sig.parameters` = **False**. Source comment: "No `wake_mode` argument: the architectural rule is that v2 compose is wake-mode-blind." Per TRD §6.5. | PASS |
| 3 | v1 `_load_manifest(role_class, wake_mode)` preserved unchanged | Live introspect: `_load_manifest(role_name: str, wake_mode: str = 'polling') -> list \| None` — signature intact. v1's `wake_mode == "event-driven"` → `includes-events.yml` dispatch at line 227 untouched. | PASS |
| 4 | D5 does NOT delete or modify any existing `includes.yml` or `includes-events.yml` file | `git diff --name-only origin/main..HEAD -- references/roles` shows ONLY 4 NEW files: `{pm,dm,verifier,worker}/includes-v2.yml`. Zero existing manifests touched. Strictly additive per §9a. | PASS |
| 5 | Compose dispatch: `--v2` → v2 path; otherwise v1 | Existing PRD-A/A6 dispatch (lines 2025-2030 of compose.py) intact: `v2_mode = "--v2" in args` flag-flips into `deploy_alias_v2(alias)`. D5 wires `_load_manifest_v2` into the v2 path; v1 path keeps reading via `_load_manifest`. Default (no flag) = v1. | PASS |
| 6a | v1 compose byte-identical to pre-D5 | §9a v1 byte-stability gate: **5/5 passed** on `aeebf6aa`. v1 manifests + code path unchanged. | PASS |
| 6b | v2 compose with v2 manifest produces expected v2 output | 36 D5 tests cover variant/base resolution, additional_includes, missing-file diagnostic, legacy-alias fallback, schema parity with v1 patterns. | PASS |
| 6c | No `includes-events.yml` referenced in v2 code path | grep on compose.py: lines 335 / 352 / 431 mention `includes-events.yml` ONLY in comments asserting "do NOT reference [it] directly." `_load_manifest_v2` body never reads the file. | PASS |

## DS Review Feedback Internalized

Per `feedback_ds_review_per_change`, skill ran DS review. Test names map to DS feedback IDs (F1/F2/F4/F5):

- **F1 + F4** (legacy alias fallback parity) — fallback applies symmetrically to base role AND variant base; source comment explicitly notes "kept OUTSIDE the if/else so it fires for both paths"
- **F2** (two-sided union check) — assertions on both directions (v1∪v2 ⊆ v2 AND v2 ⊆ v1∪v2)
- **F3** (variant test skip-guard)
- **F5** (byte-equivalence enforced by §9a gate) — sealed in by `tests/test_v1_byte_stability_9a.py`

## Defense-in-Depth

- **Variant manifests stay mode-agnostic by construction** — variant `includes.yml` (e.g. `roles/worker/skill/includes.yml`) was already single-file; D5's `_load_manifest_v2` reads them in place. No `includes-v2.yml` needed at variant level; comment at line 348 makes this explicit.
- **Schema-mirrored error surface** — missing sub-skill produces an `ERROR: includes-v2.yml ... references missing sub-skill` diagnostic identical in shape to v1's error. Operators get one mental model across both manifests.
- **Recursive `base_role` resolution** routes through `_load_manifest_v2` itself, GUARANTEEING that no path in the recursive walk drops back to v1's manifest. Source comment: "guarantees the base manifest comes from the v2 file, never includes.yml or includes-events.yml."
- **Lazy yaml import already in place** — D5 piggy-backs on the existing `if yaml is None` guard pattern.

## v1 Coexistence

§9a v1 byte-stability gate: **5/5 passed** on `aeebf6aa`. This is the canonical v1 untouchability witness — passing the gate means the produced v1 `CLAUDE.md` byte-strings match the locked baseline. Per AC4 (D5 most delicate v1-coexistence story): zero v1 file mutations confirmed by diff.

## Test Execution

`pytest tests/test_manifest_v2_d5.py tests/test_v1_byte_stability_9a.py -q` on `aeebf6aa` → **41 passed** (36 D5 + 5 §9a). Skill reported 36 D5 tests; matches.

## Outcome

All 6 ACs (incl. 3 AC6 sub-bullets) covered. D5 — "most delicate D-story for v1 coexistence" per the issue body — lands purely additively: 4 new manifest files, 1 new loader, recursive base-role resolution that can never escape to v1 manifests. §9a gate green. **Transitioning #10676: pending-test → pending-ship.**
