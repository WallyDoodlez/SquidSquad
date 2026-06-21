# QA-RESULTS-12907 — VERDICT: PASS → pending-ship

- **Verified**: 2026-06-19 18:05 (cy371, POLLING session)
- **Issue**: #12907 (type:issue/high, role:skill) — `installer-files.txt` missing all 9 `l4_*.py` scripts → fresh installs can't run L4 customization/file-watch (ImportError on `l4_file_watcher`).
- **PR**: #12910, branch `squidsquad/task/12907` (MERGEABLE/CLEAN, "Closes #12907").
- **Result**: **PASS — core gap fixed, regression-locked, manifest integrity intact.** Append-only.

## ACs (from issue Fix direction)
1. Add 9 `l4_*.py` to `installer-files.txt` (alphabetical, scripts block) + bump header Total.
2. Add/extend a manifest-completeness regression test.

## Evidence (independent)
- **AC1 — PASS.** All 9 `l4_*.py` present in `references/installer-files.txt` (verified each: audit_gate, compose_dryrun, conflict_preempt, file_watcher, mini_cq, op_processor, parser, removal, write_commit). Header `# Total: 215 files` **matches** actual entry count (215 non-comment/non-blank lines — independently counted). **Installer integrity**: all 215 manifest entries resolve to real files on disk (zero dangling).
- **AC2 — PASS (scoped).** `tests/test_installer_wiring.py` adds `test_l4_subsystem_scripts_listed` (globs `l4_*.py` on disk, asserts each ∈ manifest — locks the exact bug + future l4 additions) + `test_header_total_matches_entry_count` (canary for add-without-recount edits). 24/24 pass.

## Scope note — broad completeness deferred to #12909 (NOT a #12907 gap)
My independent completeness sweep found **17 other `references/scripts/*.py` still absent** from the manifest, including **the critical `event_poll.py`** (every agent spawns it for event mode — a fresh install can't run event mode without it). This is OUT of #12907's scope (title = the 9 l4 scripts) and is correctly split to **#12909** (type:issue/high, OPEN — "broad completeness audit + curated allowlist test"). The full "every *.py listed" test legitimately belongs there because it requires per-script runtime-vs-dev triage (some dev-only scripts should NOT ship) — implementing it in #12907 would either fail on the 17 or need an allowlist that doesn't exist yet. The skill filed #12909 and disclosed it.

**→ Flag to PM (non-blocking):** #12909 carries the `event_poll.py` manifest gap, which is arguably install-blocking for event mode. Recommend prioritizing #12909 in the next intake. Does NOT block #12907.

## Disposition
- **VERDICT: PASS → pending-ship (DM).** Zero gaps within #12907's scope.
- Merge **deferred to DM** — PR carries "Closes #12907" (QA-merge would auto-close + skip DM).
- Counter NOT bumped (DM owns). No CQ gate (manifest data + test file, no LLM-instruction change).
