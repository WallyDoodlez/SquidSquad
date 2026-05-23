"""#6274 sub-phase 6274.1 regression tests — dual-aware terminology shim.

Tests the AC1.1–AC1.7 contract from CONTEXT-6274.md:

  AC1.1 — `compose.py._list_known_role_identities()` returns the dual set
          {worker, verifier, pm, dm, dev, qa}.
  AC1.2 — `compose.py._resolve_variant("worker-skill")` and
          `_resolve_variant("dev-skill")` both return valid resolutions.
  (AC1.3–AC1.7 land in subsequent commits of the same sub-phase.)

This file lands in the 6274.1 PR and is the canonical assertion site for
the dual-aware contract. The full file gets deleted in 6274.3 once the
cutover is complete (per D10) and replaced by
`test_terminology_cutover_6274.py` which asserts the inverse.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


# ---------------------------------------------------------------------------
# AC1.1 — _list_known_role_identities returns the dual set
# ---------------------------------------------------------------------------


def test_ac1_1_dual_aware_identities_present():
    """The dual-aware identity set must include both old (dev, qa) and
    new (worker, verifier) names regardless of disk state."""
    ids = compose._list_known_role_identities()
    assert "worker" in ids, "worker missing from dual-aware identity set"
    assert "verifier" in ids, "verifier missing from dual-aware identity set"
    assert "dev" in ids, "dev missing from dual-aware identity set (backward compat)"
    assert "qa" in ids, "qa missing from dual-aware identity set (backward compat)"


def test_ac1_1_categorical_roles_still_present():
    """pm and dm are categorical and must always be in the identity set."""
    ids = compose._list_known_role_identities()
    assert "pm" in ids
    assert "dm" in ids


def test_ac1_1_dual_set_contains_at_least_six():
    """The dual-aware window guarantees these six identities at minimum.
    Real disks may surface more (e.g. designer if installed); this test
    only asserts the contract floor."""
    ids = compose._list_known_role_identities()
    expected = {"worker", "verifier", "dev", "qa", "pm", "dm"}
    assert expected.issubset(ids), (
        f"dual-aware identity set missing required members: "
        f"{expected - ids}"
    )


def test_ac1_1_dual_aware_constant_is_frozenset():
    """The dual-aware constant must be a frozenset so callers can't
    accidentally mutate it (the function returns a fresh union each
    call, but the constant itself should be immutable)."""
    assert isinstance(compose._DUAL_AWARE_IDENTITIES_6274, frozenset)
    assert compose._DUAL_AWARE_IDENTITIES_6274 == frozenset(
        {"worker", "verifier", "dev", "qa"}
    )
