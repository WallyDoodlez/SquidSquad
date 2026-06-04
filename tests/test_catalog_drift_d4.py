"""Tests for references/scripts/catalog_drift.py (#10675, PRD-D D4).

AC6 mandates tests for:
  (a) clean run (no drift) -> exit 0 / has_drift=False
  (b) orphan catalog row -> abort + report
  (c) orphan source file -> abort + report
  (d) both kinds -> both reported (not just first)
  (e) dead-code candidate -> warn but exit 0

Plus structural tests for the report format and manifest-reference
collection (catalog rows whose names appear in any role's
``includes.yml`` are NOT flagged as dead-code).
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import catalog_drift as cd  # noqa: E402


def _make_fixture(tmp_path, *, catalog_body, sub_skill_files, manifests=None):
    """Build a self-contained repo-root fixture for drift testing.

    Lays out:
        tmp_path/docs/sub-skill-catalog.md
        tmp_path/references/sub-skills/<files...>
        tmp_path/references/roles/<role-path>/<manifest>

    ``manifests`` keys are ``(role_path, filename)`` where ``role_path``
    can contain slashes for variant manifests like ``worker/skill`` —
    the helper creates the nested directory.
    """
    repo = tmp_path
    (repo / "docs").mkdir()
    catalog = repo / "docs" / "sub-skill-catalog.md"
    catalog.write_text(textwrap.dedent(catalog_body).lstrip("\n"),
                       encoding="utf-8")

    sub_skills = repo / "references" / "sub-skills"
    sub_skills.mkdir(parents=True)
    for rel in sub_skill_files:
        full = sub_skills / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f"# {rel}\n", encoding="utf-8")

    roles_dir = repo / "references" / "roles"
    roles_dir.mkdir(parents=True)
    if manifests:
        for (role, fname), payload in manifests.items():
            role_dir = roles_dir / role
            role_dir.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, str):
                # Raw YAML body — used for malformed-manifest tests.
                (role_dir / fname).write_text(payload, encoding="utf-8")
                continue
            if isinstance(payload, dict):
                # Mapped form — e.g. {"includes": [...],
                # "additional_includes": [...], "base_role": "worker"}.
                body_parts = []
                for k, v in payload.items():
                    if isinstance(v, list):
                        body_parts.append(
                            f"{k}:\n" + "".join(f"  - {i}\n" for i in v)
                        )
                    else:
                        body_parts.append(f"{k}: {v}\n")
                (role_dir / fname).write_text(
                    "".join(body_parts), encoding="utf-8")
                continue
            # Plain list form — shorthand for {"includes": [...]}.
            body = "includes:\n" + "".join(f"  - {i}\n" for i in payload)
            (role_dir / fname).write_text(body, encoding="utf-8")

    return repo, catalog


# Catalog body templates — share the H2/header structure tests need.

_CATALOG_TWO_COMMON_ROWS = """
## `common/` — Cross-cutting

### Boot

| Sub-skill | One-liner | Used by |
|---|---|---|
| `boot-bootstrap` | Mode detection | all |
| `cycle-runner` | 3-phase cycle | all |
"""


class TestCleanRun:
    """AC6(a) — no drift in either direction, exit 0."""

    def test_all_rows_resolve_and_all_files_have_rows(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.has_drift is False
        assert report.has_dead_code is False
        assert report.orphan_catalog_rows == []
        assert report.orphan_source_files == []
        assert report.dead_code_candidates == []
        assert report.format() == ""


class TestOrphanCatalogRow:
    """AC6(b) — catalog row points at a missing file."""

    def test_missing_source_file_reported(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=["common/boot-bootstrap.md"],  # cycle-runner missing
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.has_drift is True
        assert report.orphan_catalog_rows == [
            ("cycle-runner", "references/sub-skills/common/cycle-runner.md"),
        ]
        # Other directions clean.
        assert report.orphan_source_files == []
        assert report.dead_code_candidates == []
        # Report names the orphan.
        out = report.format()
        assert "Orphan catalog rows" in out
        assert "`cycle-runner`" in out


class TestOrphanSourceFile:
    """AC6(c) — source file with no catalog row."""

    def test_orphan_file_reported(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
                "common/uncatalogued-helper.md",  # not in catalog
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.has_drift is True
        assert report.orphan_catalog_rows == []
        assert report.orphan_source_files == [
            "references/sub-skills/common/uncatalogued-helper.md",
        ]
        out = report.format()
        assert "Orphan source files" in out
        assert "uncatalogued-helper" in out


class TestBothDirections:
    """AC6(d) — report ALL orphans, not just the first."""

    def test_both_directions_listed(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                # cycle-runner is missing on disk (orphan catalog row)
                "common/orphan-file.md",  # not in catalog (orphan source file)
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.has_drift is True
        # Both rendered in the report.
        out = report.format()
        assert "Orphan catalog rows" in out
        assert "Orphan source files" in out
        assert "cycle-runner" in out
        assert "orphan-file" in out


class TestDeadCodeCandidate:
    """AC6(e) — catalog row not referenced in any manifest -> WARN, exit 0."""

    def test_unreferenced_row_warns_but_does_not_abort(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                # Only references boot-bootstrap. cycle-runner is dead-code.
                ("pm", "includes.yml"): ["common/boot-bootstrap"],
            },
        )
        report = cd.scan_drift(catalog, repo)
        # NOT drift — exit code stays 0.
        assert report.has_drift is False
        assert report.has_dead_code is True
        assert report.dead_code_candidates == ["cycle-runner"]
        out = report.format()
        assert "Dead-code candidates" in out
        assert "cycle-runner" in out


# TestManifestVariants retired in E6 cutover (#10685) Phase 3e: the
# v1 polling/event split (``includes-events.yml``) and the v2
# coexistence file (``includes-v2.yml``) both retired under Phase 1, so
# scanning multiple manifest filenames is no longer a behavior worth
# pinning. The unified ``includes.yml`` path is exercised by every
# other test class in this file.


class TestExclusions:
    """Files outside the catalog's domain must NOT be flagged as orphans."""

    def test_manifest_md_at_subskills_root_is_not_an_orphan(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        # Drop a manifest.md sibling — should NOT be an orphan source file.
        (repo / "references" / "sub-skills" / "manifest.md").write_text("# m\n")
        report = cd.scan_drift(catalog, repo)
        assert report.orphan_source_files == []

    def test_project_subdir_excluded_from_source_scan(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
                "project/skill-template.md",  # L4 seed - excluded
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.orphan_source_files == []

    def test_capabilities_subdir_excluded_from_source_scan(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
                "capabilities/some-cap/sub-skill.md",
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.orphan_source_files == []


class TestSlashBearingName:
    """Slash-bearing catalog names (e.g. `roles/dm/events/pr-merge-wait`)
    must resolve to the literal source-path and match the manifest entry."""

    def test_slash_bearing_name_resolves(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body="""
            ## `roles/<role>/` — per-role

            ### DM (`roles/dm/`)

            | Sub-skill | One-liner | Used by |
            |---|---|---|
            | `roles/dm/events/pr-merge-wait` | wait for PR merge | dm |
            """,
            sub_skill_files=[
                "roles/dm/events/pr-merge-wait.md",
            ],
            manifests={
                ("dm", "includes.yml"): ["roles/dm/events/pr-merge-wait"],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.has_drift is False
        assert report.dead_code_candidates == []


class TestVariantManifests:
    """DS review F1 — variant manifests at roles/<base>/<variant>/
    must be walked recursively, and additional_includes must be read."""

    def test_variant_additional_includes_satisfies_reference(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                # Base worker role uses only boot-bootstrap.
                ("worker", "includes.yml"): ["common/boot-bootstrap"],
                # Variant at worker/skill extends with cycle-runner via
                # additional_includes -- this is the schema compose.py
                # _load_manifest reads.
                ("worker/skill", "includes.yml"): {
                    "base_role": "worker",
                    "additional_includes": ["common/cycle-runner"],
                },
            },
        )
        report = cd.scan_drift(catalog, repo)
        # cycle-runner is referenced via the variant -- NOT dead-code.
        assert report.dead_code_candidates == []


class TestMalformedManifest:
    """DS review F2 — an unparseable manifest yields a stderr warning
    but does not raise; other manifests still resolve correctly."""

    def test_malformed_manifest_warns_to_stderr(self, tmp_path, capsys):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
                ("broken-role", "includes.yml"): "::: not valid yaml :::",
            },
        )
        report = cd.scan_drift(catalog, repo)
        # The good manifest covers everything -- no dead-code.
        assert report.dead_code_candidates == []
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "broken-role" in captured.err


class TestNestedManifestMdIsNotExcluded:
    """DS review F4 — manifest.md is only excluded at the sub-skills
    root, not nested under it. A nested file named manifest.md should
    surface as an orphan source file (matching parser semantics)."""

    def test_nested_manifest_md_treated_as_source_file(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
                "common/manifest.md",  # NESTED, should NOT be excluded
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        report = cd.scan_drift(catalog, repo)
        assert report.orphan_source_files == [
            "references/sub-skills/common/manifest.md",
        ]


class TestDeadCodeMatchTightening:
    """DS review F5 — exact match wins; basename-only match applies
    only to plain (no-slash) catalog names. Slash-bearing catalog
    names must match exactly to avoid false negatives."""

    def test_slash_bearing_catalog_name_requires_exact_match(self, tmp_path):
        repo, catalog = _make_fixture(
            tmp_path,
            catalog_body="""
            ## `roles/<role>/` — per-role

            ### DM (`roles/dm/`)

            | Sub-skill | One-liner | Used by |
            |---|---|---|
            | `roles/dm/events/pr-merge-wait` | wait for PR merge | dm |
            """,
            sub_skill_files=[
                "roles/dm/events/pr-merge-wait.md",
            ],
            manifests={
                # Manifest includes the basename only -- this should
                # NOT count as a reference because the catalog name is
                # slash-bearing and requires exact-path match.
                ("dm", "includes.yml"): ["pr-merge-wait"],
            },
        )
        report = cd.scan_drift(catalog, repo)
        # Dead-code: the catalog row exists, files exists, but no
        # exact-path reference.
        assert report.dead_code_candidates == [
            "roles/dm/events/pr-merge-wait",
        ]


class TestCLI:
    """The compose.py drift-check subcommand exits 0 on clean, 1 on drift."""

    def _run_drift_cli(self, repo, catalog_rel="docs/sub-skill-catalog.md"):
        cli = SCRIPTS / "compose.py"
        return subprocess.run(
            [sys.executable, str(cli), "drift-check",
             "--catalog", str(repo / catalog_rel),
             "--repo-root", str(repo)],
            capture_output=True, text=True,
        )

    def test_clean_returns_zero(self, tmp_path):
        repo, _ = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        result = self._run_drift_cli(repo)
        assert result.returncode == 0, result.stderr

    def test_drift_returns_nonzero_with_stderr_report(self, tmp_path):
        repo, _ = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=["common/boot-bootstrap.md"],  # missing cycle-runner
            manifests={
                ("pm", "includes.yml"): [
                    "common/boot-bootstrap",
                    "common/cycle-runner",
                ],
            },
        )
        result = self._run_drift_cli(repo)
        assert result.returncode != 0
        assert "Orphan catalog rows" in result.stderr
        assert "cycle-runner" in result.stderr

    def test_dead_code_only_returns_zero_with_warning(self, tmp_path):
        repo, _ = _make_fixture(
            tmp_path,
            catalog_body=_CATALOG_TWO_COMMON_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
            manifests={
                ("pm", "includes.yml"): ["common/boot-bootstrap"],
            },
        )
        result = self._run_drift_cli(repo)
        assert result.returncode == 0, result.stderr
        # The warning goes somewhere visible (stderr).
        assert "Dead-code" in result.stderr or "Dead-code" in result.stdout
