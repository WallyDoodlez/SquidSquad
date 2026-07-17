"""Independent verifier tests for #13513 — greenfield install ships docs/sub-skill-catalog.md.

Bug: the catalog was missing from references/installer-files.txt, so a fresh install
did not stage <target>/docs/sub-skill-catalog.md; compose's catalog gate then hard-failed
and produced ZERO CLAUDE.md. Verifies the manifest ships the catalog and proves, via a
real staged greenfield compose, that the catalog is the necessary+sufficient condition
for the gate (positive: CLAUDE.md produced; negative: 'catalog file not found').
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "installer-files.txt").exists():
            return p
    raise RuntimeError("could not locate repo root")


REPO = _find_repo_root(Path(__file__).resolve())
MANIFEST = REPO / "references" / "installer-files.txt"


def _entries():
    return [l.strip() for l in MANIFEST.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def test_catalog_in_manifest():
    """AC1: docs/sub-skill-catalog.md is listed in the install manifest."""
    assert "docs/sub-skill-catalog.md" in _entries()


def test_manifest_header_count_matches():
    """AC2: the 'Total: N files' header matches the actual entry count."""
    header = [l for l in MANIFEST.read_text(encoding="utf-8").splitlines() if "Total:" in l]
    assert header, "no 'Total:' header"
    declared = int("".join(c for c in header[0] if c.isdigit()))
    assert declared == len(_entries()), f"header {declared} != {len(_entries())} entries"


def _stage(tmp):
    for rel in _entries():
        src = REPO / rel
        if src.exists():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / rel)
    (tmp / ".squidsquad").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / ".squidsquad" / "config.md", tmp / ".squidsquad" / "config.md")


def _compose_qa(tmp):
    return subprocess.run(
        [sys.executable, str(tmp / "references/scripts/compose.py"), "deploy", "qa"],
        cwd=str(tmp), capture_output=True, text=True)


def test_greenfield_positive_catalog_present_composes(tmp_path):
    """AC3 positive: manifest-staged greenfield (catalog present) composes CLAUDE.md."""
    _stage(tmp_path)
    assert (tmp_path / "docs/sub-skill-catalog.md").exists(), "catalog not staged from manifest"
    r = _compose_qa(tmp_path)
    assert r.returncode == 0, f"compose failed: {(r.stderr or r.stdout)[-300:]}"
    assert (tmp_path / ".squidsquad/qa/CLAUDE.md").exists(), "no CLAUDE.md produced"
    assert "catalog file not found" not in (r.stdout + r.stderr).lower()


def test_greenfield_negative_missing_catalog_fails_gate(tmp_path):
    """AC3 negative: without the catalog, the gate hard-fails (proves necessity)."""
    _stage(tmp_path)
    (tmp_path / "docs/sub-skill-catalog.md").unlink()
    r = _compose_qa(tmp_path)
    assert r.returncode != 0
    assert "catalog file not found" in (r.stdout + r.stderr).lower()


def test_regression_test_present():
    """AC4: worker ships a regression asserting the catalog FILE is shipped."""
    wt = REPO / "tests" / "test_12821_installer_files_subskill_completeness.py"
    assert wt.exists()
    assert "sub-skill-catalog" in wt.read_text(encoding="utf-8").lower()
