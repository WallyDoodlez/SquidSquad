# QA-RESULTS-10675 — PRD-D / Story D4: Catalog drift check (two-way orphan scan + abort)

**Verified**: 2026-06-02 05:45
**Branch**: `skill/d4-catalog-drift-10675` @ `b21fac73`
**PR**: #10744
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/catalog_drift.py` (+282 new) — `scan_drift(catalog_path, repo_root)` + `DriftReport` dataclass + manifest-reference collector. Lazy-imported by compose; v1 deploy paths see zero load cost.
- `references/scripts/compose.py` (+68) — `drift-check` subcommand with `--catalog` / `--repo-root` args + structured exit codes (0=clean, 1=drift, 2=setup-error).
- `tests/test_catalog_drift_d4.py` (+556 new) — 18 tests.
- `tests/run_tests.py` (+1) — STATIC_TEST_MODULES registration.
- `.squidsquad/skill/planning/ds-d4-review.md` (DS review log) — non-runtime artifact.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | New compose-time check, runnable independently as CLI subcommand + integrated into compose pipeline | `compose.py drift-check [--catalog <path>] [--repo-root <path>]` subcommand. Live invocation: `python references/scripts/compose.py drift-check` returns **exit 2** with structured catalog-parse error message on the known #10687 duplicate — proves CLI integration + exit-code contract. Pipeline integration via subcommand surface. | PASS |
| 2 | Two scan directions: catalog row → file exists; source file → catalog row exists | `scan_drift()` runs both directions; tests `test_missing_source_file_reported` + `test_orphan_file_reported` + `test_both_directions_listed`. Symmetric exclusions: `manifest.md`/`README.md`/`index.md` at sub-skills root (F4: root-only, not basename-recursive) + `project/` + `capabilities/` subdirs mirror the catalog parser's allowlist. | PASS |
| 3 | Drift output: structured report listing ALL orphans (not just first); abort with non-zero exit + report on stderr | `DriftReport.format()` renders multi-section report sorted alphabetically; `test_drift_returns_nonzero_with_stderr_report` confirms exit 1 + stderr surfacing on drift. `has_drift` property is union of both directions. | PASS |
| 4 | Dead-code candidate (catalog row, no manifest call-site) → warn but exit 0 | `report.has_dead_code` distinct from `has_drift`; CLI handler exits 0 with stderr warning when only dead-code present. `test_dead_code_only_returns_zero_with_warning` + `test_unreferenced_row_warns_but_does_not_abort`. Dead-code scan includes variant manifests via `additional_includes:` (F1) + slash-bearing exact-match rule (F5). | PASS |
| 5 | Independent of D2/D3 — D4 can land before D2/D3 | Module imports: `catalog_parser` only (D1 dep, already shipped). No `v2_link_stage` or `compose_link_stage` imports. Reads source tree only, never composes anything, never reads v2 output. | PASS |
| 6 | Tests cover: clean run / orphan catalog row / orphan source file / both / dead-code | All 5 scenarios present + 13 additional defense-in-depth tests (manifest variant shapes, slash-bearing names, YAML-error warning, nested manifest.md, project/ + capabilities/ subdir exclusion). | PASS |

## DS Review Feedback Internalized

Per `feedback_ds_review_per_change`, skill ran DS review and the test names map directly to DS feedback IDs (F1-F5):

- **F1** (variant manifests via `additional_includes:`) → `test_variant_additional_includes_satisfies_reference`
- **F2** (YAML error → warning-not-fail) → `test_malformed_manifest_warns_to_stderr` with `capsys` assertion
- **F4** (nested `manifest.md` ≠ root special-case) → `test_nested_manifest_md_treated_as_source_file`
- **F5** (slash-bearing catalog names = exact match, not basename-collapse) → `test_slash_bearing_catalog_name_requires_exact_match`

## v1 Coexistence

§9a v1 byte-stability gate: **5/5 passed** on `b21fac73`. D4 is purely additive — new module + new compose subcommand + new tests. No existing compose code path modified.

Per PRD AC: "D4 runs against the source tree (not output) — same sources both v1 and v2 read. Initial state of this repo's catalog vs source tree may surface real drift that needs cleanup; that cleanup is OUT OF SCOPE for D4 (the check just reports)." → confirmed: D4 exits 2 on the live tree due to pre-existing #10687 (or filed equivalent #10743). This is the intended behavior — drift-check fails loudly so the cleanup story has clear scope.

## Test Execution

`pytest tests/test_catalog_drift_d4.py tests/test_v1_byte_stability_9a.py tests/test_catalog_parser_d1.py -q` on `b21fac73` → **49 passed + 1 xfailed** (18 D4 + 5 §9a + 26 D1 + 1 xfail-strict #10687).

Live CLI: `python references/scripts/compose.py drift-check` → exit 2 with catalog parse-error message (correct behavior per AC1 + AC's setup-error exit code).

## Defense-in-Depth

- **Exit-code triad** (0/1/2) — clean separation between "clean", "drift detected", "setup error". CLI handler routes catalog-parse errors and unexpected exceptions BOTH to exit 2 with distinguishing stderr prefixes ("catalog parse failed" vs "drift-check setup failed").
- **Lazy import inside compose.py** — `import catalog_drift as _cd` only when drift-check subcommand is invoked, keeping v1 deploy paths free of D4 module load cost. Per source comment + AC5 independence.
- **Manifest reference union across all 3 schemas** (`includes.yml` + `includes-events.yml` + `includes-v2.yml`) — covers v1 split-manifest, event-mode, and post-D5 unified v2 file, so dead-code scan stays valid through the v1→v2 transition without amendment.
- **Slash-bearing matching asymmetry locked in** by `test_slash_bearing_catalog_name_requires_exact_match` — guards against future refactor that would basename-collapse `deep/X` matches and produce false negatives in dead-code surfacing.

## Outcome

All 6 ACs covered with explicit tests + 4 DS-review-driven defense tests. D4 is well-scoped, properly lazy-loaded, and structurally independent of D2/D3 per AC5. Live CLI honors the exit-code contract. **Transitioning #10675: pending-test → pending-ship.**
