# TEST-PLAN-13101 — installer-files.txt omits L1 base slot files (identity.md + vault.md)

- **Issue**: #13101 (type:issue, severity:medium, role:skill) — `references/installer-files.txt` omits L1 slot-sources `identity.md` (slot: identity) + `vault.md` (slot: vault) → degraded/empty `## Identity` / `## Vault` composed sections on fresh installs. Same class as #12861.
- **PR**: #13125, branch `squidsquad/task/13101` @ `16dbbacb8`. Files: `installer-files.txt` (+3/-1), `tests/test_13101_installer_files_l1_slot_completeness.py` (+74/-0). No closing keyword.
- **Derived**: 2026-06-21 00:55. Deterministic (manifest + test) → **NO CQ**.
- **Method**: isolated worktree; manifest diff; completeness + count tests; independent negative-verify; full static gate.

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | `identity.md` + `vault.md` added to installer-files.txt. | Diff + manifest membership check (both present). |
| AC2 | `# Total:` bumped to 252 and matches the actual entry count. | Count integrity: header 252 == 252 actual non-comment entries. |
| AC3 | Completeness test: every `references/roles/*.md` with `slot:` frontmatter must be in the manifest (L1-slot analogue of #12861). | `test_13101_installer_files_l1_slot_completeness.py`. |
| AC4 | Test catches an omission (not a tautology). | Negative-verify: dropping `identity.md` fails both `test_all_l1_slot_sources_in_manifest` AND `test_total_count_matches_listed_paths`. |
| AC5 | No regression. | `run_tests.py static`. |
