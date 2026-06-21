# TEST-PLAN-12905 — Galaxy notes land without YAML frontmatter (no write-time guard)

Bug (type:issue/medium, auto-approved), filed by skill. PR #12927, branch
`squidsquad/task/12905`. No explicit AC list → ACs derived from the bug report's
root-gap + suggested fix (b: fail-closed pre-commit hook). Code+hook only → **no CQ**.
Verified in isolated worktree `D:\Dev\Dev\sq-12905-verify`.

Self-relevant: this is the recurring failure class I've hit myself
([[feedback_galaxy_notes_need_yaml_frontmatter]]); the guard would protect against it.

## Derived ACs
- **AC1 (fail-closed write-time guard):** a pre-commit guard BLOCKS committing a
  staged `vault/galaxy/*.md` note lacking a valid YAML frontmatter block.
- **AC2 (exact-mirror, no false +/-):** the guard's contract exactly mirrors
  `tests/test_vault.py::TestGalaxyNotes::test_galaxy_notes_have_frontmatter` —
  accepts exactly what the gate accepts, rejects exactly what it rejects.
- **AC3 (deterministic, agent-independent):** the guard validates the STAGED blob
  (`git show :<path>`) in a pre-commit hook — independent of which agent/sub-skill
  wrote the note (suggested fix b, deterministic backstop).
- **AC4 (robust fail-open):** guard-internal error/crash → exit 0 (never wedges the
  fleet's commits). The shim BLOCKS only on the explicit `__SQUIDSQUAD_GALAXY_FM_BLOCK__`
  marker, NOT the exit code (a module-level python crash also exits 1) — DS-12905 F1.
- **AC5 (scope correctness):** only `.squidsquad/vault/galaxy/*.md`; `-template.md`,
  `.gitkeep`, non-galaxy files, and unanchored `vault/galaxy` paths excluded (DS F2/F3);
  Windows path separators handled.
- **AC6 (guard composition):** on a feature branch the #11511 state guard (Guard 1)
  unstages the main-only galaxy note before Guard 2 runs; on the working branch Guard 1
  no-ops so Guard 2 fires (where galaxy notes land).
- **AC7 (regression test):** would have caught the original defect.

## Test cases / evidence
- **TC1 (AC2)** — byte-for-byte compare `_galaxy_frontmatter_violation` vs test_vault
  TestGalaxyNotes: 5 checks identical (startswith ---, split>=3, key-extract, non-empty, type). CONFIRMED exact mirror. + test_matches_test_vault_contract.
- **TC2 (AC1/AC4 live)** — INDEPENDENT live: stage bad note → guard prints ERROR + `__SQUIDSQUAD_GALAXY_FM_BLOCK__` + exit 1; stage good note → exit 0, no marker. PASS.
- **TC3 (AC4 fail-open)** — test_guard_error_fails_open_exits_0; shim keys block on marker not exit code (test_pre_commit_invokes_galaxy_guard).
- **TC4 (AC5)** — test_non_galaxy_files_ignored, test_gitkeep_and_template_skipped, test_unanchored_vault_galaxy_path_ignored, test_windows_path_separators_handled, test_only_bad_note_among_many_flagged.
- **TC5 (AC6)** — test_state_guard_strips_galaxy_note_on_feature_branch, test_state_guard_noops_on_working_branch_so_galaxy_guard_fires.
- **TC6 (AC7)** — tests/test_git_ops_galaxy_guard_12905.py (20 cases) → 20 passed.
- **TC7 (no-reg)** — full run_tests.py static (pending — see QA-RESULTS).
