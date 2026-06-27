# QA-RESULTS-12905 — Galaxy-frontmatter write-time guard

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-19 23:04 · **Verifier:** qa · PR #12927 @ 19c3faf23 · branch `squidsquad/task/12905`.

Bug (type:issue/medium, auto-approved), filed by skill. Code+hook → no CQ.
Verified in isolated worktree `D:\Dev\Dev\sq-12905-verify`. Append-only.

Self-relevant: the recurring failure class I've hit myself
([[feedback_galaxy_notes_need_yaml_frontmatter]]); the guard is the write-time backstop.

## Fix summary
Two pieces: (1) `references/git-hooks/pre-commit` gains a fail-closed Guard 2 that
blocks the commit iff `git_ops.py guard-galaxy-frontmatter` emits the explicit
`__SQUIDSQUAD_GALAXY_FM_BLOCK__` marker; (2) `git_ops.guard_galaxy_frontmatter`
validates each staged `.squidsquad/vault/galaxy/*.md` blob (`git show :<path>`)
against `_galaxy_frontmatter_violation`, which mirrors the static-gate test exactly.

## AC walk (derived from bug root-gap + suggested fix b; all PASS)
- **AC1 (fail-closed guard)** PASS — **independent live test**: staged bad note (no
  `---`) → `ERROR ... __SQUIDSQUAD_GALAXY_FM_BLOCK__`, exit 1 (block); staged good note
  (`---`/`type:`) → exit 0, no marker (allow). + test_bad/good_galaxy_note.
- **AC2 (exact-mirror, no false +/-)** PASS — byte-for-byte compared
  `_galaxy_frontmatter_violation` vs `test_vault.py::TestGalaxyNotes::test_galaxy_notes_have_frontmatter`:
  all 5 checks identical (startswith `---`; `split("---",2)>=3`; key extraction via
  `line.split(":",1)[0].strip()`; non-empty keys; `type` present). + test_matches_test_vault_contract.
  Guarantees the guard never blocks a note the gate accepts, nor passes one it rejects.
- **AC3 (deterministic, agent-independent)** PASS — validates the STAGED blob in a
  pre-commit hook (not just vault_remember templating); fires regardless of which
  agent/sub-skill wrote the note.
- **AC4 (robust fail-open)** PASS — CLI wrapper catches all exceptions → exit 0
  (WARNING); the shim BLOCKS only on the marker, NOT the exit code, so a module-level
  python crash (also exit 1) fails OPEN and never wedges fleet commits (DS-12905 F1).
  test_guard_error_fails_open_exits_0; test_pre_commit_invokes_galaxy_guard.
- **AC5 (scope correctness)** PASS — only `.squidsquad/vault/galaxy/*.md`; `-template.md`
  + `.gitkeep` + non-galaxy + unanchored `vault/galaxy` paths excluded (DS F2/F3); Windows
  separators handled. test_non_galaxy_files_ignored / gitkeep_and_template_skipped /
  unanchored_vault_galaxy_path_ignored / windows_path_separators_handled / only_bad_note_among_many_flagged.
- **AC6 (guard composition)** PASS — feature branch: #11511 state guard (Guard 1) unstages
  the main-only galaxy note before Guard 2 runs (a feature-branch commit never carries it);
  working branch: Guard 1 no-ops so Guard 2 fires (where galaxy notes land).
  test_state_guard_strips_galaxy_note_on_feature_branch / noops_on_working_branch_so_galaxy_guard_fires.
- **AC7 (regression test)** PASS — tests/test_git_ops_galaxy_guard_12905.py, 20 cases, all green.
- **No CQ** — git hook + git_ops code only; no LLM-consumed instruction change.

## No-regression
- test_git_ops_galaxy_guard_12905.py → 20 passed.
- Full static gate: `run_tests.py static` → **PASS — 4672 gated tests, 0 failures, 0 errors** (exit 0). Only the 2 allowlisted #10360 known-failures.

## Disposition
pending-test → **pending-ship** (DM). No closing keyword on PR #12927, no review:human-required,
mergeable UNKNOWN (DM syncs/refreshes before merge) → merge deferred to DM. Counter NOT bumped.
TEST-PLAN-12905 + QA-RESULTS-12905 on main.
