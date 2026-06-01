"""§9a v1 byte-equivalence regression gate (#10394 prerequisite, PRD-A §9a).

Per PRD-A §9a coexistence rule, every change that touches L1-L3 source
files MUST leave v1 ``compose.py deploy <role>`` output byte-identical
to the prior committed golden. This gate is the prerequisite the A2.6
frontmatter migration (#10394) runs against batch-by-batch: when a
migration adds YAML frontmatter to inlined source files, v1's
``_resolve_includes`` would otherwise carry the frontmatter through to
its composed output, breaking the contract.

The gate works by snapshotting the current ``deploy_role`` output for
each role-class (pm, dm, verifier, worker) under
``tests/compose-fixtures/v1-byte-stability/<role>/CLAUDE.md.golden``
and asserting the live invocation matches byte-for-byte.

When the goldens drift, the failure unified-diff names exactly which
slot/section changed so the operator can decide:

- Was the source change intentional behavior shift? Regenerate the
  golden via the docstring instructions in ``_regenerate_golden``.
- Was the source change supposed to be v1-invisible (e.g. A2.6
  frontmatter migration)? Fix v1 to skip the new content (e.g. strip
  frontmatter at include time) and re-run the gate.

Out of scope per #10394's body:
- Migrating source files (this PR ships the gate only).
- CI hook / pre-merge wiring (PRD-E concern).
"""

import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
GOLDEN_ROOT = REPO_ROOT / "tests" / "compose-fixtures" / "v1-byte-stability"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


_ROLE_CLASSES = ["pm", "dm", "verifier", "worker"]


@pytest.fixture(autouse=True)
def _disable_agent_compose(monkeypatch):
    """Keep the deterministic compose path. ``agent_compose`` calls a live
    LLM when enabled in config; pin it OFF so the gate stays reproducible
    regardless of the operator's local agent-compose setting.
    """
    monkeypatch.setattr(compose, "_is_agent_compose_enabled", lambda: False)


# ---------------------------------------------------------------------------
# Gate: deploy_role output matches the committed golden, byte-for-byte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", _ROLE_CLASSES)
def test_v1_byte_identical_against_golden(role, tmp_path):
    """Invoke v1 ``deploy_role`` into a tmp tree, diff vs the committed golden."""
    golden_path = GOLDEN_ROOT / role / "CLAUDE.md.golden"
    assert golden_path.exists(), (
        f"Golden missing for role '{role}'. Regenerate via _regenerate_golden() "
        f"(see this file's docstring)."
    )
    expected = golden_path.read_text(encoding="utf-8")

    out_path = compose.deploy_role(role, target_root=tmp_path)
    actual = out_path.read_text(encoding="utf-8")

    if actual != expected:
        import difflib
        diff_lines = list(difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=str(golden_path.relative_to(REPO_ROOT)),
            tofile=f"deploy_role({role!r})",
            lineterm="",
            n=3,
        ))
        # Cap the diff to keep CI logs survivable on a large drift.
        cap = 200
        snippet = "\n".join(diff_lines[:cap])
        if len(diff_lines) > cap:
            snippet += (
                f"\n... [{len(diff_lines) - cap} more diff lines truncated; "
                f"re-run locally for full diff]"
            )
        pytest.fail(
            f"v1 §9a byte-equivalence drift on role '{role}'. "
            f"Either the references/ change was intentional (regenerate "
            f"golden) or v1's include path needs to ignore the new content "
            f"(e.g. strip frontmatter at include time for A2.6). "
            f"Length: expected={len(expected)} actual={len(actual)}.\n\n{snippet}"
        )


def test_golden_set_covers_all_role_classes():
    """The gate must cover every role-class in ``MANDATORY_ROLES``.

    A goldens-less role-class would silently bypass the v1 byte-stability
    check, defeating the §9a contract. Re-add the missing golden via
    ``_regenerate_golden(role)``.
    """
    golden_roles = {p.name for p in GOLDEN_ROOT.iterdir() if p.is_dir()}
    missing = compose.MANDATORY_ROLES - golden_roles
    assert not missing, (
        f"v1-byte-stability goldens missing for: {sorted(missing)}. "
        f"This breaks the §9a gate's coverage."
    )
    # The worker role-class is also part of the gate (it's the engineering
    # specialist; not mandatory but central to PRD-B).
    assert "worker" in golden_roles, (
        "worker role-class golden missing; the gate must cover it."
    )


# ---------------------------------------------------------------------------
# Maintenance helper — invoked by hand when intentionally regenerating
# ---------------------------------------------------------------------------

def _regenerate_golden(role):
    """Regenerate the v1 byte-stability golden for ``role``.

    Intended for hand use when an intentional v1 behavior change ships:

        from tests.test_v1_byte_stability_9a import _regenerate_golden
        _regenerate_golden("pm")

    Re-running this from a Python REPL writes a fresh golden over the
    committed snapshot. The PR that ships the regeneration MUST explain
    why the v1 output changed (the §9a contract is the operator's
    fundamental "v2 doesn't break v1" guarantee).
    """
    with tempfile.TemporaryDirectory() as td:
        out_path = compose.deploy_role(role, target_root=Path(td))
        content = out_path.read_text(encoding="utf-8")
    golden_path = GOLDEN_ROOT / role / "CLAUDE.md.golden"
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(content, encoding="utf-8")
    return golden_path
