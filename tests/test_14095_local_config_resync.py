"""#14095 — .local-config drifts stale with no re-sync mechanism.

Each clone carries its own gitignored ``.local-config`` whose relative entries
resolve against THAT clone's root. Nothing re-synced sibling copies after
clones were renamed or relocated, and ``add_role._sync_local_config`` copied
the primary's map verbatim, so the primary's ``- **pm**: .`` resolved to every
other clone's own checkout. The verifier saw this live in the qa clone: pm/dm
collided with qa's own path and skill pointed at a deleted directory, which
``health_check.py`` reported as false ``unknown`` readings.

Fix: ``boot_remote.render_local_config_for`` / ``sync_local_config_to_clones``
re-render the authoritative map relative to each target clone. The harness
runs the sync at every boot from its own copy (the one it spawns agents
from), and ``add_role`` uses the same renderer.
"""

import inspect
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import add_role  # noqa: E402
import boot_remote  # noqa: E402
import harness  # noqa: E402


def make_fleet(tmp_path: Path):
    """Four sibling clones laid out like this install: primary + 3 others."""
    roots = {
        "pm": tmp_path / "Proj",
        "skill": tmp_path / "Proj-2",
        "qa": tmp_path / "Proj-qa",
        "dm": tmp_path / "Proj-3",
    }
    for r in roots.values():
        (r / ".squidsquad").mkdir(parents=True)
    return roots


def write_cfg(root: Path, entries: dict):
    lines = ["# stale", ""] + [f"- **{k}**: {v}" for k, v in entries.items()]
    (root / ".squidsquad" / ".local-config").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def entries(root: Path) -> dict:
    return boot_remote._resolved_entries(
        root / ".squidsquad" / ".local-config", root)


def resolved(roots: dict) -> dict:
    return {k: v.resolve() for k, v in roots.items()}


class TestRender:
    def test_self_is_dot_and_siblings_relative(self, tmp_path):
        roots = make_fleet(tmp_path)
        text = boot_remote.render_local_config_for(roots["qa"], roots)
        assert "- **qa**: .\n" in text
        assert "- **pm**: ../Proj\n" in text
        assert "- **skill**: ../Proj-2\n" in text
        assert "\\" not in text.split("\n", 5)[-1], "forward slashes only"

    def test_order_follows_the_map(self, tmp_path):
        roots = make_fleet(tmp_path)
        text = boot_remote.render_local_config_for(roots["pm"], roots)
        body = [l for l in text.splitlines() if l.startswith("- **")]
        assert [l.split("**")[1] for l in body] == ["pm", "skill", "qa", "dm"]

    def test_cross_drive_falls_back_to_absolute(self, tmp_path):
        roots = make_fleet(tmp_path)
        with patch.object(boot_remote.os.path, "relpath",
                          side_effect=ValueError("path is on mount 'C:'")):
            text = boot_remote.render_local_config_for(roots["qa"], roots)
        want = str(roots["pm"].resolve()).replace(os.sep, "/")
        assert f"- **pm**: {want}\n" in text

    def test_rendered_file_round_trips_through_the_parser(self, tmp_path):
        roots = make_fleet(tmp_path)
        for r in roots.values():
            (r / ".squidsquad" / ".local-config").write_text(
                boot_remote.render_local_config_for(r, roots), encoding="utf-8")
            assert entries(r) == resolved(roots)


class TestSync:
    def test_fixes_the_observed_qa_clone_drift(self, tmp_path):
        """The exact #14095 shape: pm/dm '.' collide with qa's own root and
        skill points at a directory that no longer exists."""
        roots = make_fleet(tmp_path)
        write_cfg(roots["qa"], {"skill": "../Proj-skill", "pm": ".",
                                "qa": "../Proj-qa", "dm": "."})
        rewritten = boot_remote.sync_local_config_to_clones(roots)
        assert roots["qa"] / ".squidsquad" / ".local-config" in rewritten
        got = entries(roots["qa"])
        assert got == resolved(roots)
        assert got["pm"] != roots["qa"].resolve(), "pm no longer collides with qa"
        assert got["skill"].exists(), "skill resolves to a real clone"

    def test_every_clone_resolves_the_same_map(self, tmp_path):
        roots = make_fleet(tmp_path)
        boot_remote.sync_local_config_to_clones(roots)
        for r in roots.values():
            assert entries(r) == resolved(roots)

    def test_correct_file_is_not_rewritten(self, tmp_path):
        """A healthy fleet sees no churn, even when the existing file writes
        an equivalent path differently (absolute vs relative)."""
        roots = make_fleet(tmp_path)
        boot_remote.sync_local_config_to_clones(roots)
        write_cfg(roots["dm"], {k: str(v.resolve()) for k, v in roots.items()})
        before = (roots["dm"] / ".squidsquad" / ".local-config").read_text()
        assert boot_remote.sync_local_config_to_clones(roots) == []
        after = (roots["dm"] / ".squidsquad" / ".local-config").read_text()
        assert before == after

    def test_skip_roots_left_alone(self, tmp_path):
        roots = make_fleet(tmp_path)
        write_cfg(roots["pm"], {"pm": "sentinel"})
        boot_remote.sync_local_config_to_clones(roots, skip_roots=(roots["pm"],))
        text = (roots["pm"] / ".squidsquad" / ".local-config").read_text()
        assert "sentinel" in text

    def test_missing_clone_is_not_created_but_still_listed(self, tmp_path):
        roots = make_fleet(tmp_path)
        gone = tmp_path / "Proj-web"
        roots["web"] = gone
        boot_remote.sync_local_config_to_clones(roots)
        assert not gone.exists(), "sync never creates clone directories"
        assert entries(roots["qa"])["web"] == gone.resolve()

    def test_no_tmp_file_left_behind(self, tmp_path):
        roots = make_fleet(tmp_path)
        boot_remote.sync_local_config_to_clones(roots)
        for r in roots.values():
            assert not (r / ".squidsquad" / ".local-config.tmp").exists()


class TestHarnessWiring:
    def test_isolated_harness_skips_resync(self, tmp_path):
        with patch.object(harness, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(harness.boot_remote, "_parse_local_config",
                          side_effect=AssertionError(
                              "isolated harness must not even READ .local-config")):
            assert harness._distribute_local_config_to_clones() is None

    def test_production_harness_resyncs_siblings_not_itself(self, tmp_path):
        roots = make_fleet(tmp_path)
        write_cfg(roots["pm"], {"pm": "sentinel"})
        write_cfg(roots["qa"], {"pm": ".", "dm": "."})
        with patch.object(harness, "REPO_ROOT", roots["pm"]), \
             patch.object(harness, "SQUIDSQUAD_DIR", roots["pm"] / ".squidsquad"), \
             patch.object(harness.boot_remote, "_parse_local_config",
                          return_value=resolved(roots)):
            rewritten = harness._distribute_local_config_to_clones()
        assert roots["qa"] / ".squidsquad" / ".local-config" in rewritten
        assert entries(roots["qa"]) == resolved(roots)
        assert "sentinel" in (roots["pm"] / ".squidsquad" / ".local-config").read_text(), \
            "the harness's own (source) copy is never rewritten"

    def test_resync_runs_in_harness_boot(self):
        """The module ships WIRED: the boot-time deferred init calls it."""
        src = inspect.getsource(harness.lifespan)
        init = src[src.index("def _deferred_init"):]
        assert "_distribute_local_config_to_clones()" in init


class TestAddRoleSync:
    def test_relative_map_is_rerendered_per_target(self, tmp_path):
        """add_role used to copy the primary's relative map verbatim, making
        '- **pm**: .' resolve to each target clone's own root."""
        roots = make_fleet(tmp_path)
        compose_style = {"pm": ".", "skill": "../Proj-2",
                         "qa": "../Proj-qa", "dm": "../Proj-3"}
        with patch.object(add_role, "REPO_ROOT", roots["pm"]):
            add_role._sync_local_config(compose_style)
        for r in roots.values():
            assert entries(r) == resolved(roots)

    def test_absolute_map_still_supported(self, tmp_path):
        roots = make_fleet(tmp_path)
        with patch.object(add_role, "REPO_ROOT", roots["pm"]):
            add_role._sync_local_config({k: str(v) for k, v in roots.items()})
        assert entries(roots["qa"]) == resolved(roots)
