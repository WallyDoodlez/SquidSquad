"""Shared fixtures for SquidSquad static analysis tests."""

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
REFERENCES_DIR = REPO_ROOT / "references"
VAULT_DIR = SQUIDSQUAD_DIR / "vault"
SUB_SKILLS_DIR = REFERENCES_DIR / "sub-skills"


@pytest.fixture(scope="session", autouse=True)
def _snapshot_restore_live_config_md():
    """#11044: session-scoped defense against tests that shell out to
    `references/scripts/config.py set ...` (or otherwise write to
    `.squidsquad/config.md` without isolating to tmp_path).

    Subprocess-side writes are not subject to in-process monkeypatches —
    `config.py`'s module-level `CONFIG_PATH` resolves from `__file__`
    at import time, not from the test process's patched `REPO_ROOT`.
    The leak surfaced via `_do_version_bump` shelling out to
    `config.py set version <X>` and silently bumping the live config
    during full-suite runs.

    Belt-and-braces: even after every individual leak is patched, this
    fixture snapshots the live config.md before the suite and restores
    it after. If a future test re-introduces the pattern, the next
    full-suite run still leaves the file at its pre-suite contents.
    """
    config_path = SQUIDSQUAD_DIR / "config.md"
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    try:
        yield
    finally:
        if original is None:
            if config_path.exists():
                config_path.unlink()
        else:
            current = config_path.read_text(encoding="utf-8") if config_path.exists() else None
            if current != original:
                config_path.write_text(original, encoding="utf-8")


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def squidsquad_dir():
    return SQUIDSQUAD_DIR


@pytest.fixture
def references_dir():
    return REFERENCES_DIR


@pytest.fixture
def vault_dir():
    return VAULT_DIR


@pytest.fixture
def sub_skills_dir():
    return SUB_SKILLS_DIR


@pytest.fixture
def config_text():
    return (SQUIDSQUAD_DIR / "config.md").read_text(encoding="utf-8")


@pytest.fixture
def skill_claude_md():
    return (SQUIDSQUAD_DIR / "skill" / "CLAUDE.md").read_text(encoding="utf-8")
