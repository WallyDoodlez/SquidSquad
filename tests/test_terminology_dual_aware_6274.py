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


# ---------------------------------------------------------------------------
# AC1.2 — _resolve_variant accepts both old and new prefixes
# ---------------------------------------------------------------------------


def test_ac1_2_dev_skill_resolves_pre_rename():
    """Pre-6274.2 state: `references/roles/dev/skill/` exists. The
    canonical form resolves directly."""
    result = compose._resolve_variant("dev-skill")
    assert result == ("dev", "skill"), (
        f"dev-skill should resolve to ('dev', 'skill') pre-rename; got {result}"
    )


def test_ac1_2_worker_skill_resolves_pre_rename_via_alias():
    """Pre-6274.2 state: `worker-skill` is input-normalized to the
    on-disk `dev/skill/` directory via the dual-aware alias. F3
    contract: input independent of disk; return tracks disk."""
    result = compose._resolve_variant("worker-skill")
    assert result == ("dev", "skill"), (
        f"worker-skill should resolve to ('dev', 'skill') pre-rename "
        f"(return tracks disk per F3); got {result}"
    )


def test_ac1_2_qa_and_verifier_resolve_identically():
    """`qa-*` and `verifier-*` follow the same dual-aware rule as
    dev/worker. Even when the directory has no `instructions.md`
    (scaffolding-only per D5/F10), the fallback path resolves it via
    `_list_known_role_identities()`."""
    qa_result = compose._resolve_variant("qa-skill")
    verifier_result = compose._resolve_variant("verifier-skill")
    assert qa_result == verifier_result, (
        f"qa-skill and verifier-skill must resolve identically; "
        f"got qa={qa_result}, verifier={verifier_result}"
    )
    # Both should resolve to a qa-rooted tuple pre-rename
    assert qa_result is not None
    assert qa_result[0] == "qa"


def test_ac1_2_non_variant_inputs_return_none():
    """Inputs that aren't variant-shaped (no hyphen, or no matching
    directory) return None."""
    assert compose._resolve_variant("pm") is None
    assert compose._resolve_variant("skill") is None  # legacy dev variant w/o hyphen
    assert compose._resolve_variant("nonexistent-nope") is None


def test_ac1_2_alias_table_is_bidirectional():
    """The alias table must be bidirectional so that both the old→new
    direction (pre-rename) and the new→old direction (post-rename) are
    handled by a single lookup. Tested as a static structural assertion
    so callers can rely on the symmetry."""
    assert compose._BASE_ALIAS_6274["worker"] == "dev"
    assert compose._BASE_ALIAS_6274["verifier"] == "qa"
    assert compose._BASE_ALIAS_6274["dev"] == "worker"
    assert compose._BASE_ALIAS_6274["qa"] == "verifier"
    # pm and dm are categorical — they must NOT be in the alias table
    assert "pm" not in compose._BASE_ALIAS_6274
    assert "dm" not in compose._BASE_ALIAS_6274


# ---------------------------------------------------------------------------
# AC1.3 — config.py.get_field("workers") dual-aware
# ---------------------------------------------------------------------------


import config  # noqa: E402  (intentional late import — needs SCRIPTS on sys.path)


def test_ac1_3_workers_short_name_in_field_map():
    """`workers` must be in FIELD_MAP so the canonical post-rename key
    is the primary entry point. The deprecated `dev-agents` key stays
    until 6274.3 cutover."""
    assert "workers" in config.FIELD_MAP
    assert config.FIELD_MAP["workers"] == ("Agents", "Workers")
    # The deprecated key MUST still be present during the dual-aware
    # window so `get_field('dev-agents')` still works for any caller
    # that hasn't migrated yet.
    assert "dev-agents" in config.FIELD_MAP


def test_ac1_3_dual_aware_mapping_present():
    """The dual-aware fallback table must map workers -> dev-agents.
    Deleted in 6274.3 along with the legacy FIELD_MAP row."""
    assert "workers" in config._DUAL_AWARE_CONFIG_FIELDS_6274
    assert config._DUAL_AWARE_CONFIG_FIELDS_6274["workers"] == "dev-agents"


def test_ac1_3_workers_reads_legacy_field_with_warning(capsys):
    """When config.md still has `Dev Agents:` (and no `Workers:`),
    `get_field('workers')` must return the legacy value AND emit a
    deprecation warning to stderr."""
    val = config.get_field("workers")
    captured = capsys.readouterr()
    assert val is not None, "get_field('workers') should fall back to dev-agents"
    assert val == config.get_field("dev-agents"), (
        "workers fallback must equal dev-agents value"
    )
    # Deprecation warning was emitted on the first call above
    # (capsys captures across both calls). The second `get_field(
    # 'dev-agents')` call does NOT emit the warning, so only one
    # occurrence is expected.
    assert "deprecated field `Dev Agents:`" in captured.err, (
        f"expected deprecation warning in stderr; got: {captured.err!r}"
    )
