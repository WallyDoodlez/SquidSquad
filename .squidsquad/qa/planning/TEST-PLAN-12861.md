# TEST-PLAN-12861 — installer-files.txt sub-skill manifest-completeness gate

- **Issue**: #12861 (type:issue, severity:low, role:skill) — installer-files.txt omits shared sub-skills loaded at runtime via `→ run sub-skill:` markers → dangling markers on fresh installs; no completeness test catches the class.
- **PR**: #13058, branch `squidsquad/task/12861`, HEAD `4da4f6586`. Files: `tests/test_installer_wiring.py` (+115/-0) — pure test addition (part 1, the missing entries, already landed on main). `Fixes #12861` (closing keyword).
- **Derived**: 2026-06-21 00:35. Deterministic test-infra → **NO CQ**.
- **Method**: isolated worktree; run the wiring suite (green ⇒ part-1 manifest complete); **independent negative-verify** (drop a manifest entry → gate fails); full static gate.

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | Part (1): all sub-skills referenced by `→ run sub-skill:` markers (l4-curation, pr-protocol, tracker-protocol, task-pickup + the full common/ + common-events/ set) are listed in installer-files.txt. | `test_installer_wiring.py` green against the real manifest (29/29) — the completeness gate passing IS the proof part-1 is complete. |
| AC2 | Part (2): a completeness gate — `test_every_marker_referenced_subskill_listed` (transitive closure over composed CLAUDE.md → catalog-resolved sub-skill bodies, backtick-tolerant) + `test_every_includes_yml_subskill_listed`. | New tests present + design review (transitive, catalog-resolved). |
| AC3 | The gate actually catches an omission (not a tautology). | Negative-verify: removing `common/pr-protocol.md` from the manifest fails the gate with exactly `['references/sub-skills/common/pr-protocol.md']`. |
| AC4 | No regression. | `run_tests.py static`. |

## Notes
- The gate intentionally skips marker names with no catalog row (catalog completeness is a separate gate's concern — `test_v2_catalog_gate_d3`), which also ignores illustrative markers inside sub-skill bodies. Reasonable scoping.
- A latent `_REF_RE` backtick gap found en route was split to #13052 (out of scope) — legit follow-up routing.
