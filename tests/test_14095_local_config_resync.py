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
    def test_self_is_sibling_relative_and_siblings_relative(self, tmp_path):
        """Self is written '../<dir>', never '.': health_check's #13742
        exemption treats raw '.' on a non-pm role as stale."""
        roots = make_fleet(tmp_path)
        text = boot_remote.render_local_config_for(roots["qa"], roots)
        assert "- **qa**: ../Proj-qa\n" in text
        assert ": .\n" not in text
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
            assert list((r / ".squidsquad").glob(".local-config*.tmp")) == []

    def test_unwritable_clone_does_not_block_the_rest(self, tmp_path, capsys):
        roots = make_fleet(tmp_path)
        real_replace = os.replace
        bad = roots["skill"] / ".squidsquad" / ".local-config"

        def flaky(src, dst):
            if Path(dst) == bad:
                raise PermissionError("locked by a reader")
            return real_replace(src, dst)

        with patch.object(boot_remote.os, "replace", side_effect=flaky):
            rewritten = boot_remote.sync_local_config_to_clones(roots)
        assert bad not in rewritten
        assert "could not re-sync" in capsys.readouterr().err
        assert list((roots["skill"] / ".squidsquad").glob("*.tmp")) == []
        for role in ("pm", "qa", "dm"):
            assert entries(roots[role]) == resolved(roots)

    def test_dropped_roles_are_warned(self, tmp_path, capsys):
        roots = make_fleet(tmp_path)
        write_cfg(roots["dm"], {"pm": "../Proj", "ghost": "../Proj-ghost"})
        boot_remote.sync_local_config_to_clones(roots)
        assert "ghost" in capsys.readouterr().err
        assert "ghost" not in entries(roots["dm"])

    def test_concurrent_writers_tmp_file_untouched(self, tmp_path):
        """Review fix: a fixed tmp name let two concurrent syncs (harness boot
        + add_role) consume each other's tmp file. Another writer's in-flight
        tmp must be neither reused nor removed."""
        roots = make_fleet(tmp_path)
        other = roots["qa"] / ".squidsquad" / ".local-config.tmp"
        other.write_text("in-flight", encoding="utf-8")
        boot_remote.sync_local_config_to_clones(roots)
        assert other.read_text(encoding="utf-8") == "in-flight"
        assert entries(roots["qa"]) == resolved(roots)

    def test_non_utf8_file_is_rewritten_not_fatal(self, tmp_path):
        """Review fix: a cp1252-saved file raised UnicodeDecodeError and
        aborted the whole fleet sync; now it is treated as unreadable and
        rewritten, and later clones still get synced."""
        roots = make_fleet(tmp_path)
        (roots["skill"] / ".squidsquad" / ".local-config").write_bytes(
            b"- **pm**: caf\xe9\x9d\n")
        rewritten = boot_remote.sync_local_config_to_clones(roots)
        assert roots["skill"] / ".squidsquad" / ".local-config" in rewritten
        for r in roots.values():
            assert entries(r) == resolved(roots)


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

    def test_list_clones_resolves_relative_against_repo_root(
            self, tmp_path, monkeypatch, capsys):
        """Review fix: the synced primary file holds relative entries, so
        --list must resolve them against REPO_ROOT, not the cwd."""
        roots = make_fleet(tmp_path)
        cfg = roots["pm"] / ".squidsquad" / ".local-config"
        cfg.write_text(boot_remote.render_local_config_for(roots["pm"], roots),
                       encoding="utf-8")
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        with patch.object(add_role, "REPO_ROOT", roots["pm"]),              patch.object(add_role, "LOCAL_CONFIG", cfg):
            add_role.list_clones()
        out = capsys.readouterr().out
        assert "MISSING" not in out
        assert out.count("[OK]") == 4


class TestHealthCheckIntegration:
    def test_synced_clone_reads_all_agents_without_collision(self, tmp_path):
        """health_check.py run from a synced sibling clone sees no collision,
        and the clone's own entry is not raw '.', so the #13742 exemption
        ground-truths it even if another role's entry later breaks onto the
        same path."""
        import health_check
        roots = make_fleet(tmp_path)
        boot_remote.sync_local_config_to_clones(roots)
        cfg = roots["qa"] / ".squidsquad" / ".local-config"
        with patch.object(health_check, "REPO_ROOT", roots["qa"]), \
             patch.object(health_check, "LOCAL_CONFIG", cfg):
            parsed = health_check._parse_local_config()
            raw = dict(health_check._LAST_PARSED_RAW)
        assert parsed == resolved(roots)
        assert len(set(parsed.values())) == 4, "no two roles collide"
        assert raw["qa"] != "."
