# QA-RESULTS-11087 — rm 38 orphan sub-skill source files (REJECTED)

**Verified at**: 2026-06-05 cycle 927
**PR**: #11088 (squidsquad/skill/11087-rm-orphan-source-files @ HEAD)
**Verdict**: REJECTED — routed back to `in-progress`. The deletion is real and the markers/inlined bodies are preserved correctly, but two cleanup surfaces that travel with the deletion were missed and produce concrete pytest regressions.

## What PASSED

- **AC1**: `compose.py drift-check` no longer emits an "Orphan source files" section — orphan_source_files 38 → 0 ✓.
- **AC2**: `compose.py deploy-all` succeeds with sizes byte-identical to main (dm 1006 / pm 1066 / qa 1008 / skill 1268).
- **AC3**: zero `{{include:}}` directives in `references/roles/`.
- **AC4**: 21 `<!-- #10360-cleanup: ... -->` markers preserved (pm:5 / worker:6 / dm:5 / verifier:5) — inlined content is intact.
- **AC5**: catalog retirement notes flipped to post-deletion language naming both #11087 and #10360 (two locations confirmed).

## What FAILED — the route-back reasons

1. **`tests/test_installer_wiring.py::TestInstallerFileManifest::test_every_listed_file_exists_on_disk` FAILS** — `references/installer-files.txt` still lists **37 of the deleted files**, e.g.:
   - `references/sub-skills/common/discussion-protocol.md`
   - `references/sub-skills/common/file-conventions.md`
   - `references/sub-skills/common/prohibitions.md`
   - `references/sub-skills/common/status-line.md`
   - all 20 `roles/{pm,dm,verifier,worker}/<domain>/domain-context.md` paths
   - the 4 per-role `responsibility.md` files
   - the 4 per-role `prohibitions.md` / `status-line.md` / `file-conventions.md`
2. **`tests/test_manifest.py::TestManifestIntegrity::test_include_targets_exist` FAILS** — all four `references/roles/{dm,pm,verifier,worker}/includes.yml` still list `common/discussion-protocol` (resolves to `references/sub-skills/common/discussion-protocol.md`, which the PR deleted).
3. Cascading: `test_manifest.py::TestIncludesYml::{test_includes_yml_paths_exist,test_includes_yml_covers_template}` and `test_install_wiring`'s sibling also fail off the same two root causes.

Net wider sweep: **4 failed, 374 passed** across `tests/test_catalog*.py tests/test_compose*.py tests/test_manifest.py tests/test_installer_wiring.py tests/test_a3_golden_link_stage.py tests/test_event_mode_fragments.py`. Skill's narrower "265/265 catalog-area regression suites PASS" claim didn't include `test_installer_wiring` / `test_manifest`, which is why this slipped.

## Required additional changes before re-ship

- Prune `references/installer-files.txt` of the 37 deleted-file entries (same shape as #11042's installer-files.txt prune).
- Remove the `common/discussion-protocol` entry from each of `references/roles/{dm,pm,verifier,worker}/includes.yml`. The file is `git rm`'d here; the manifest must drop the reference for the same reason the source file was retired.
- Re-run `tests/test_installer_wiring.py + tests/test_manifest.py` to confirm both go green; re-run the wider sweep to confirm no other downstream breakage.

## Recommendation

Re-transition `pending-test → in-progress` and prune the two metadata surfaces alongside the source-file deletion. This is exactly the pattern that caused #11042 in the first place (deletions without matching `installer-files.txt` updates) — the structural lesson there applies directly.
