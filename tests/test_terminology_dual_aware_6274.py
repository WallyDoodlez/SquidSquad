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


# ---------------------------------------------------------------------------
# AC1.4 — tracker.py dual-tag + --role suffix shim (D11)
# ---------------------------------------------------------------------------


import tracker  # noqa: E402


def test_ac1_4_dual_label_for_dev_and_qa_inputs():
    """role=dev emits both role:dev and role:worker; same for qa/verifier."""
    assert tracker._build_dual_role_labels_6274("dev") == "role:dev,role:worker"
    assert tracker._build_dual_role_labels_6274("qa") == "role:qa,role:verifier"


def test_ac1_4_dual_label_for_new_inputs_too():
    """role=worker / role=verifier also dual-tag back to the old form so
    the migration works in both directions."""
    assert tracker._build_dual_role_labels_6274("worker") == "role:worker,role:dev"
    assert (
        tracker._build_dual_role_labels_6274("verifier") == "role:verifier,role:qa"
    )


def test_ac1_4_categorical_and_variants_not_dual_tagged():
    """pm, dm, skill, and other variant prefixes are NOT in the alias
    table per Out-of-Scope. They get the single `role:<x>` label."""
    assert tracker._build_dual_role_labels_6274("pm") == "role:pm"
    assert tracker._build_dual_role_labels_6274("dm") == "role:dm"
    assert tracker._build_dual_role_labels_6274("skill") == "role:skill"
    assert tracker._build_dual_role_labels_6274("ios") == "role:ios"


def test_ac1_4_label_pair_table_bidirectional():
    """Static structural assertion — table must be symmetric so the
    direction-agnostic dual-tagging holds."""
    pairs = tracker._DUAL_LABEL_PAIRS_6274
    assert pairs["dev"] == "worker"
    assert pairs["worker"] == "dev"
    assert pairs["qa"] == "verifier"
    assert pairs["verifier"] == "qa"
    # pm, dm, and variant prefixes must NOT be in the table
    for non_dual in ("pm", "dm", "skill", "ios", "android", "fullstack", "web"):
        assert non_dual not in pairs


def test_ac1_4_role_suffix_new_form_silent(capsys):
    """--role verifier-lead and --role worker-lead are the new D11 forms —
    accepted, normalized to canonical, and emit no warning."""
    canon = tracker._canonicalize_role("verifier-lead")
    assert canon == "qa"
    assert capsys.readouterr().err == ""

    canon = tracker._canonicalize_role("worker-lead")
    assert canon == "dev"
    assert capsys.readouterr().err == ""


def test_ac1_4_role_suffix_old_form_warns(capsys):
    """--role qa-lead and --role dev-lead are the deprecated forms —
    still accepted (passthrough to canonical) but emit a stderr
    deprecation warning per D11."""
    canon = tracker._canonicalize_role("qa-lead")
    assert canon == "qa"
    assert "deprecated" in capsys.readouterr().err

    canon = tracker._canonicalize_role("dev-lead")
    assert canon == "dev"
    assert "deprecated" in capsys.readouterr().err


def test_ac1_4_unaffected_roles_pass_through_silently(capsys):
    """Per Out-of-Scope: pm-lead, dm-lead, skill-lead are NOT renamed.
    They must pass through `_canonicalize_role` with no warning."""
    for role_with_suffix, expected_canon in [
        ("pm-lead", "pm"),
        ("dm-lead", "dm"),
        ("skill-lead", "skill"),
        ("ios-lead", "ios"),
        ("designer-lead", "designer"),
    ]:
        canon = tracker._canonicalize_role(role_with_suffix)
        assert canon == expected_canon, (
            f"{role_with_suffix} -> {canon}, expected {expected_canon}"
        )
        assert capsys.readouterr().err == "", (
            f"{role_with_suffix} must NOT warn (Out-of-Scope)"
        )
