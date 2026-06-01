"""Tests for references/scripts/l4_compose_dryrun.py (#10654, PRD-C C5)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_compose_dryrun  # noqa: E402
from link_stage_validator import LinkStageValidationError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLEAN_L4 = (
    "## Instructions\n\n"
    "### append\n\n"
    "→ run sub-skill: weekly-smoke\n\n"
    "Once a week, run the security smoke tests as part of the cycle.\n"
)


def _registry(*alias_to_role_class):
    """Build a registry dict shaped like ``parse_aliases_registry`` output."""
    return {alias: (role_class, None) for alias, role_class in alias_to_role_class}


def _stub_check(approve_aliases=(), reject_aliases=()):
    """Build a check_alias_staged_l4 stub that approves / rejects per alias.

    ``approve_aliases`` and ``reject_aliases`` are iterables of alias names.
    Approval is a no-op; rejection raises ``LinkStageValidationError``
    with a configurable rule label.
    """
    approve = set(approve_aliases)
    reject = {alias: rule_or_message for alias, rule_or_message in reject_aliases}

    def check(alias, staged_path, *, target_root=None, registry=None):
        if alias in approve:
            return
        if alias in reject:
            rule, message = reject[alias]
            raise LinkStageValidationError(rule, message)
        # Default: approve when neither list mentions the alias.
        return

    return check


# ---------------------------------------------------------------------------
# AC5(a): clean L4 → DryrunResult(passed=True)
# ---------------------------------------------------------------------------

def test_clean_l4_returns_passed_true(tmp_path):
    check = _stub_check(approve_aliases=("pm-1", "pm-2"))
    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm"), ("pm-2", "pm"), ("worker-1", "worker")),
        check_alias_staged_l4_fn=check,
    )
    assert result.passed is True
    assert result.failures == []


def test_clean_l4_runs_check_for_every_alias_of_role_class(tmp_path):
    calls = []

    def check(alias, staged_path, *, target_root=None, registry=None):
        calls.append(alias)

    l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm"), ("pm-2", "pm"), ("worker-1", "worker")),
        check_alias_staged_l4_fn=check,
    )
    # Both pm-1 and pm-2 dispatched; worker-1 NOT included (different role-class)
    assert set(calls) == {"pm-1", "pm-2"}


def test_clean_l4_writes_staged_content_to_tempfile_under_repo_root(tmp_path):
    """AC4 + sandbox lesson: staged path must live under .squidsquad/tmp/l4-dryrun/."""
    captured = {}

    def check(alias, staged_path, *, target_root=None, registry=None):
        captured["path"] = Path(staged_path)
        captured["text"] = Path(staged_path).read_text(encoding="utf-8")

    l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm")),
        check_alias_staged_l4_fn=check,
    )
    assert captured["text"] == _CLEAN_L4
    # Path lives inside REPO_ROOT/.squidsquad/tmp/l4-dryrun/.
    p = captured["path"].resolve()
    assert "l4-dryrun" in p.parts
    repo_root = Path(__file__).resolve().parent.parent
    assert str(p).startswith(str(repo_root))


# ---------------------------------------------------------------------------
# AC5(b): orphan step-ID target → abort
# AC5(c): per-slot constraint violation → abort
# AC5(d): malformed H3 op → abort
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rule_label,message", [
    ("R5", "L4 op references non-existent step-id `ghost`"),
    ("R1", "L4 file contains `## Vault` H2"),
    ("R6", "whole-slot replace mixed with other ops"),
])
def test_validation_failure_returns_passed_false(rule_label, message):
    """AC2: non-zero exit captures stderr; AC5: covers R1/R5/R6 paths."""
    check = _stub_check(reject_aliases=[("pm-1", (rule_label, message))])
    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm")),
        check_alias_staged_l4_fn=check,
    )
    assert result.passed is False
    assert len(result.failures) == 1
    f = result.failures[0]
    assert f.alias == "pm-1"
    assert f.rule == rule_label
    assert message in f.detail


def test_setup_error_classified_as_setup_rule_label(tmp_path):
    """FileNotFoundError / KeyError from A4.5 surface as `<setup>`."""
    def check(alias, staged_path, *, target_root=None, registry=None):
        raise KeyError("alias 'pm-1' not found in registry")

    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm")),
        check_alias_staged_l4_fn=check,
    )
    assert result.passed is False
    assert result.failures[0].rule == "<setup>"


def test_unexpected_exception_classified_as_other(tmp_path):
    """Any non-validation, non-setup exception is `<other>` so callers can branch on it."""
    def check(alias, staged_path, *, target_root=None, registry=None):
        raise RuntimeError("compose pipeline broke in an unexpected way")

    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm")),
        check_alias_staged_l4_fn=check,
    )
    assert result.failures[0].rule == "<other>"
    assert "RuntimeError" in result.failures[0].detail


# ---------------------------------------------------------------------------
# AC5(e): one alias passes but another fails → abort with the failing alias named
# ---------------------------------------------------------------------------

def test_one_alias_fails_another_passes_returns_failed(tmp_path):
    """The whole dry-run aborts when ANY alias fails (AC3)."""
    check = _stub_check(
        approve_aliases=("pm-1",),
        reject_aliases=[("pm-2", ("R5", "orphan step in pm-2's variant"))],
    )
    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm"), ("pm-2", "pm")),
        check_alias_staged_l4_fn=check,
    )
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].alias == "pm-2"


def test_multiple_alias_failures_all_recorded(tmp_path):
    """When 2+ aliases fail, the result enumerates each."""
    check = _stub_check(
        reject_aliases=[
            ("pm-1", ("R5", "orphan in pm-1")),
            ("pm-2", ("R7", "duplicate replace in pm-2")),
        ],
    )
    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("pm-1", "pm"), ("pm-2", "pm")),
        check_alias_staged_l4_fn=check,
    )
    assert result.passed is False
    failures_by_alias = {f.alias: f.rule for f in result.failures}
    assert failures_by_alias == {"pm-1": "R5", "pm-2": "R7"}


# ---------------------------------------------------------------------------
# Edge: no aliases of the role-class exist in the install
# ---------------------------------------------------------------------------

def test_role_class_with_no_aliases_returns_setup_failure():
    """If the registry has no aliases for the requested role-class, there's
    nothing to dry-run against. Surface as a setup failure so the caller
    can guide the human to fix config.md."""
    result = l4_compose_dryrun.dryrun_l4(
        _CLEAN_L4,
        role_class="pm",
        registry=_registry(("worker-1", "worker")),
        check_alias_staged_l4_fn=_stub_check(),
    )
    assert result.passed is False
    assert len(result.failures) == 1
    assert result.failures[0].rule == "<setup>"
    assert "no aliases" in result.failures[0].detail


# ---------------------------------------------------------------------------
# format_failure_for_human helper
# ---------------------------------------------------------------------------

def test_format_failure_for_human_passed_returns_empty_string():
    result = l4_compose_dryrun.DryrunResult(passed=True)
    assert l4_compose_dryrun.format_failure_for_human(result) == ""


def test_format_failure_for_human_single_alias_matches_ac2_phrasing():
    result = l4_compose_dryrun.DryrunResult(
        passed=False,
        failures=[l4_compose_dryrun.DryrunFailure(
            alias="pm-1", rule="R5", detail="orphan step-id `ghost`",
        )],
    )
    out = l4_compose_dryrun.format_failure_for_human(result)
    assert "Dry-run failed" in out  # AC2 phrasing
    assert "pm-1" in out
    assert "R5" in out
    assert "ghost" in out


def test_format_failure_for_human_multi_alias_enumerates_each():
    result = l4_compose_dryrun.DryrunResult(
        passed=False,
        failures=[
            l4_compose_dryrun.DryrunFailure(alias="pm-1", rule="R5", detail="orphan"),
            l4_compose_dryrun.DryrunFailure(alias="pm-2", rule="R7", detail="dup"),
        ],
    )
    out = l4_compose_dryrun.format_failure_for_human(result)
    assert "2 alias(es)" in out
    assert "pm-1" in out and "R5" in out
    assert "pm-2" in out and "R7" in out


# ---------------------------------------------------------------------------
# DryrunResult / DryrunFailure dataclass surface
# ---------------------------------------------------------------------------

def test_dryrun_result_default_failures_is_independent_list():
    """default_factory=list means each DryrunResult has its own list, not a shared one."""
    a = l4_compose_dryrun.DryrunResult(passed=True)
    b = l4_compose_dryrun.DryrunResult(passed=True)
    a.failures.append("oops")
    assert b.failures == []


def test_dryrun_failure_has_all_three_fields():
    f = l4_compose_dryrun.DryrunFailure(alias="pm-1", rule="R5", detail="orphan")
    assert f.alias == "pm-1"
    assert f.rule == "R5"
    assert f.detail == "orphan"
