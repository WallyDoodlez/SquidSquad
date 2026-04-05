"""Shared fixtures for SquidSquad static analysis tests."""

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
REFERENCES_DIR = REPO_ROOT / "references"
VAULT_DIR = SQUIDSQUAD_DIR / "vault"
SUB_SKILLS_DIR = REFERENCES_DIR / "sub-skills"


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
