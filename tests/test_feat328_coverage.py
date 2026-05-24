"""#328 Phase K — test-plan coverage gate.

This file backs the Phase K deliverable: a statically-verifiable gate
that asserts the shipped registry satisfies the invariants called out
in `FEAT-328-TEST-PLAN.md`. Integration TCs (TC-01..TC-09 etc.) that
need a live Claude session running the wizard runbook against a scratch
repo are deferred to manual QA — see FEAT-328-COVERAGE.md for the full
mapping.

These tests map to specific TCs in the plan so a failure points directly
at which expectation the shipped code stops satisfying.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402

pytest.importorskip("yaml")
import manifest  # noqa: E402


# ---------------------------------------------------------------------------
# TC-47 — PM / DM / QA have empty setup_requirements
# ---------------------------------------------------------------------------


class TestTC47EmptySetupRequirements:
    """PM/DM/QA manifests must ship with empty setup_requirements.

    Rationale: in v1 the wizard's Step 4 walker must skip straight past
    these roles — they have nothing to ask the user about. The empty
    list is the declarative way to express that.
    """

    @pytest.mark.parametrize("role", ["pm", "dm", "verifier"])
    def test_role_has_empty_setup_requirements(self, role):
        # Post-6274.2 D5: qa → verifier; manifest.validate_registry reads
        # `references/roles/<role>/manifest.yaml` from disk so the keys are
        # the canonical on-disk identities.
        _, roles, _, _ = manifest.validate_registry()
        assert role in roles, f"role manifest not loaded: {role}"
        assert roles[role]["setup_requirements"] == [], (
            f"{role}.setup_requirements must be empty in v1 — the wizard "
            f"walker should skip these roles entirely in Step 4"
        )

    def test_dev_has_variant_and_stack(self):
        _, roles, _, _ = manifest.validate_registry()
        # Post-6274.2: dev role renamed to worker.
        ids = [r["id"] for r in roles["worker"]["setup_requirements"]]
        assert ids == ["variant", "stack"]


# ---------------------------------------------------------------------------
# TC-49..TC-52 — Loop interval validation
# ---------------------------------------------------------------------------


class TestTC49To52IntervalValidation:
    """Step 5 interval input must be an integer >= 1."""

    def test_tc49_accepts_integer_10(self):
        r = wizard.validate_interval("10")
        assert r["ok"] is True
        assert r["minutes"] == 10

    def test_accepts_integer_1(self):
        assert wizard.validate_interval("1")["minutes"] == 1

    def test_accepts_integer_high(self):
        assert wizard.validate_interval("60")["minutes"] == 60

    def test_accepts_native_int(self):
        r = wizard.validate_interval(5)
        assert r["ok"] is True
        assert r["minutes"] == 5

    def test_tc50_rejects_zero(self):
        r = wizard.validate_interval("0")
        assert r["ok"] is False
        assert "at least 1" in r["reason"]

    def test_tc51_rejects_negative(self):
        r = wizard.validate_interval("-5")
        assert r["ok"] is False
        assert r["minutes"] is None

    def test_tc52_rejects_non_numeric(self):
        r = wizard.validate_interval("abc")
        assert r["ok"] is False
        assert "not a number" in r["reason"]

    def test_rejects_float(self):
        r = wizard.validate_interval("10.5")
        assert r["ok"] is False
        assert "whole number" in r["reason"]

    def test_rejects_comma_float(self):
        """European-locale numeric should be rejected, not silently parsed."""
        r = wizard.validate_interval("1,5")
        assert r["ok"] is False

    def test_empty_string_uses_default(self):
        r = wizard.validate_interval("")
        assert r["ok"] is True
        assert r["minutes"] == 10

    def test_none_uses_default(self):
        r = wizard.validate_interval(None)
        assert r["ok"] is True
        assert r["minutes"] == 10

    def test_whitespace_only_uses_default(self):
        r = wizard.validate_interval("   ")
        assert r["ok"] is True
        assert r["minutes"] == 10

    def test_custom_default_respected(self):
        r = wizard.validate_interval("", default=30)
        assert r["minutes"] == 30

    def test_whitespace_around_integer_ok(self):
        r = wizard.validate_interval("  15  ")
        assert r["ok"] is True
        assert r["minutes"] == 15


# ---------------------------------------------------------------------------
# TC-70..TC-77 — Pipeline resolution (shipped + synthetic scenarios)
# ---------------------------------------------------------------------------


class TestTC70To77PipelineResolution:
    def test_tc70_software_dev_all_roles(self):
        """software-dev preset → pm + dm + worker + verifier (#6274 dev→worker, qa→verifier)."""
        _, roles, _, presets = manifest.validate_registry()
        resolved = manifest.resolve_pipeline("software-dev", roles, presets)
        assert resolved == {"pm", "dm", "worker", "verifier"}

    def test_tc75_design_preset(self):
        """design preset → pm + dm + verifier (verifier is always_installed since #347; qa→verifier per #6274 D5)."""
        _, roles, _, presets = manifest.validate_registry()
        resolved = manifest.resolve_pipeline("design", roles, presets)
        assert resolved == {"pm", "dm", "verifier"}

    def test_every_shipped_role_is_reachable_from_some_preset(self):
        """Sanity — every non-infra role appears in at least one preset."""
        _, roles, _, presets = manifest.validate_registry()
        reached = set()
        for preset in presets:
            reached |= manifest.resolve_pipeline(preset, roles, presets)
        specialist_roles = {
            r for r, d in roles.items() if not d.get("always_installed")
        }
        unreachable = specialist_roles - reached
        assert not unreachable, (
            f"specialist roles not reachable from any preset: {unreachable}"
        )


# ---------------------------------------------------------------------------
# TC-63 — New labels are present in the repo (live check via tracker module)
# ---------------------------------------------------------------------------


class TestTC63NewLabelsInTracker:
    """The tracker module must know every #328 Phase E label by name."""

    @pytest.mark.parametrize("short_name", [
        "pending-human-approval",
        "pending-human-review",
        "pending-human-setup",
    ])
    def test_phase_e_labels_in_status_map(self, short_name):
        sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
        import tracker
        assert short_name in tracker.STATUS_LABELS
        assert tracker.STATUS_LABELS[short_name] == f"status:{short_name}"


# ---------------------------------------------------------------------------
# TC-66 — tracker.py legal transitions include the new edges
# ---------------------------------------------------------------------------


class TestTC66LegalTransitions:
    """Every new Q-new4 / Q-new11 edge must be legal in tracker.py."""

    @pytest.mark.parametrize("from_s,to_s", [
        ("status:pending-human-approval", "status:planning"),
        ("status:pending-human-approval", "status:approved"),
        ("status:in-progress", "status:pending-human-review"),
        ("status:pending-human-review", "status:in-progress"),
        ("status:pending-human-review", "status:pending-ship"),
        ("status:in-progress", "status:pending-human-setup"),
        ("status:pending-human-setup", "status:in-progress"),
    ])
    def test_new_edge_is_legal(self, from_s, to_s):
        sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
        import tracker
        assert to_s in tracker.LEGAL_TRANSITIONS.get(from_s, set()), (
            f"{from_s} -> {to_s} should be legal after Phase E"
        )


# ---------------------------------------------------------------------------
# TC-115 — compose.py produces valid CLAUDE.md for every shipped role
# ---------------------------------------------------------------------------


class TestTC115ComposeEveryRole:
    """Every shipped role manifest must resolve to a compose-able identity."""

    def test_compose_resolves_every_shipped_role(self):
        sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
        import compose
        _, roles, _, _ = manifest.validate_registry()
        for role_id in roles:
            entry = compose._get_entry_file_for_role(role_id)
            assert entry, f"compose could not resolve entry for {role_id}"


# ---------------------------------------------------------------------------
# ST-1..ST-3 — Smoke gate: every shipped manifest loads cleanly
# ---------------------------------------------------------------------------


class TestSmokeManifestValidation:
    """ST-1..ST-3 — validator must pass on the real shipped registry."""

    def test_st1_role_manifests_load_cleanly(self):
        issues, roles, _, _ = manifest.validate_registry()
        errors = [i for i in issues if i.severity == "error"]
        assert not errors, [str(e) for e in errors]
        # Core v1 roles present (post-#6274: dev→worker, qa→verifier)
        assert set(roles.keys()) >= {"pm", "dm", "worker", "verifier"}

    def test_st2_tool_manifests_load_cleanly(self):
        _, _, tools, _ = manifest.validate_registry()
        assert set(tools.keys()) >= {
            "figma", "google_stitch", "local_html", "local_delivery",
        }

    def test_st3_preset_manifests_load_cleanly(self):
        _, _, _, presets = manifest.validate_registry()
        assert set(presets.keys()) >= {"software-dev", "design"}


# ---------------------------------------------------------------------------
# TC-78 — Cycle detection (OBSOLETE — retained as a documentation anchor)
# ---------------------------------------------------------------------------


class TestTC78CycleDetectionObsolete:
    """TC-78 is obsolete and intentionally retired.

    The plan expected the validator to reject a synthetic `A -> B -> A`
    routes_to loop. In practice the v1 shipped topology intentionally
    includes a `PM -> Designer -> PM` loop (Q1 + Q7). At the
    graph-edge level a pathological synthetic loop is indistinguishable
    from the legitimate bidirectional hand-off — you can't catch one
    without rejecting the other. Phase D's manifest.py docstring
    documents the rationale.

    This test locks in the decision: cycle detection is NOT implemented,
    and the module docstring explaining why must stay intact.
    """

    def test_manifest_module_documents_cycle_detection_decision(self):
        module_text = (
            REPO_ROOT / "references" / "scripts" / "manifest.py"
        ).read_text(encoding="utf-8")
        assert "Cycle detection is intentionally NOT enforced" in module_text

    def test_shipped_registry_validates_cleanly(self):
        """The shipped registry must pass validation."""
        issues, _, _, _ = manifest.validate_registry()
        errors = [i for i in issues if i.severity == "error"]
        assert not errors, "shipped registry must validate cleanly"
