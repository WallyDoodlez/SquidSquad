"""#12905 — pre-commit galaxy-frontmatter guard.

Galaxy notes committed without YAML frontmatter red the shared
tests/test_vault.py::TestGalaxyNotes gate for the whole fleet. This guard is the
write-time backstop: FAIL-CLOSED on a confirmed violation (block the commit),
FAIL-OPEN on any guard-internal error (never wedge the fleet on a guard bug).
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops  # noqa: E402


def _cp(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class TestGalaxyFrontmatterValidator(unittest.TestCase):
    """_galaxy_frontmatter_violation mirrors the test_vault contract exactly."""

    def test_valid_note_passes(self):
        content = "---\nname: x\ntype: pattern\n---\n\nBody.\n"
        self.assertIsNone(git_ops._galaxy_frontmatter_violation(content))

    def test_missing_frontmatter(self):
        content = "# heading instead of frontmatter\n\nBody.\n"
        self.assertIn("missing", git_ops._galaxy_frontmatter_violation(content))

    def test_unclosed_frontmatter(self):
        content = "---\nname: x\ntype: pattern\n"  # no closing ---
        self.assertIn("malformed", git_ops._galaxy_frontmatter_violation(content))

    def test_empty_frontmatter(self):
        content = "---\n---\nBody.\n"
        self.assertIn("empty", git_ops._galaxy_frontmatter_violation(content))

    def test_missing_type_key(self):
        content = "---\nname: x\ndescription: y\n---\nBody.\n"
        self.assertIn("type", git_ops._galaxy_frontmatter_violation(content))

    def test_matches_test_vault_contract(self):
        """A note this validator ACCEPTS must also pass the test_vault assertions
        (no false rejection of a gate-valid note)."""
        content = "---\nname: x\ntype: decision\n---\nBody.\n"
        # Replicate test_galaxy_notes_have_frontmatter's checks:
        self.assertTrue(content.startswith("---"))
        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3)
        fm_keys = {ln.split(":", 1)[0].strip()
                   for ln in parts[1].strip().splitlines() if ":" in ln}
        self.assertTrue(fm_keys)
        self.assertIn("type", fm_keys)
        self.assertIsNone(git_ops._galaxy_frontmatter_violation(content))


class TestGuardGalaxyFrontmatter(unittest.TestCase):
    """guard_galaxy_frontmatter scans staged galaxy notes via the index."""

    def _run_guard(self, staged_paths, blobs):
        """staged_paths: list of paths from --diff-filter=ACM.
        blobs: dict path -> staged content (git show :path)."""
        def fake_run_list(cmd, check=True):
            if cmd[:4] == ["git", "diff", "--cached", "--name-only"]:
                return _cp(0, "\n".join(staged_paths) + ("\n" if staged_paths else ""))
            if cmd[:2] == ["git", "show"]:
                ref = cmd[2]                      # ":<path>"
                path = ref[1:]
                if path in blobs:
                    return _cp(0, blobs[path])
                return _cp(1, "", "no such path")
            return _cp(0, "")
        with patch.object(git_ops, "_run_list", side_effect=fake_run_list), \
             patch.object(git_ops, "print"):
            return git_ops.guard_galaxy_frontmatter()

    def test_bad_galaxy_note_is_a_violation(self):
        v = self._run_guard(
            [".squidsquad/vault/galaxy/pattern-foo.md"],
            {".squidsquad/vault/galaxy/pattern-foo.md": "# no frontmatter\n"},
        )
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0][0], ".squidsquad/vault/galaxy/pattern-foo.md")

    def test_good_galaxy_note_passes(self):
        v = self._run_guard(
            [".squidsquad/vault/galaxy/pattern-foo.md"],
            {".squidsquad/vault/galaxy/pattern-foo.md":
             "---\nname: foo\ntype: pattern\n---\nBody.\n"},
        )
        self.assertEqual(v, [])

    def test_non_galaxy_files_ignored(self):
        v = self._run_guard(
            ["references/scripts/git_ops.py",
             ".squidsquad/vault/areas/human-profile.md",  # not galaxy
             ".squidsquad/skill/working-state.md"],
            {},
        )
        self.assertEqual(v, [])

    def test_gitkeep_and_template_skipped(self):
        v = self._run_guard(
            [".squidsquad/vault/galaxy/.gitkeep",
             ".squidsquad/vault/galaxy/galaxy-template.md"],
            {".squidsquad/vault/galaxy/.gitkeep": "",
             ".squidsquad/vault/galaxy/galaxy-template.md": "# template\n"},
        )
        self.assertEqual(v, [])

    def test_windows_path_separators_handled(self):
        v = self._run_guard(
            [".squidsquad\\vault\\galaxy\\pattern-foo.md"],
            {".squidsquad\\vault\\galaxy\\pattern-foo.md": "# no fm\n"},
        )
        self.assertEqual(len(v), 1)

    def test_only_bad_note_among_many_flagged(self):
        v = self._run_guard(
            [".squidsquad/vault/galaxy/pattern-good.md",
             ".squidsquad/vault/galaxy/learning-bad.md"],
            {".squidsquad/vault/galaxy/pattern-good.md":
             "---\ntype: pattern\n---\nok\n",
             ".squidsquad/vault/galaxy/learning-bad.md": "no fm\n"},
        )
        self.assertEqual([p for p, _ in v], [".squidsquad/vault/galaxy/learning-bad.md"])


class TestCliExitCodes(unittest.TestCase):
    """CLI: exit 1 on a confirmed violation (fail-closed), exit 0 otherwise
    INCLUDING on any guard-internal error (fail-open)."""

    def _main_exit(self):
        with patch.object(sys, "argv", ["git_ops.py", "guard-galaxy-frontmatter"]):
            try:
                git_ops.main()
            except SystemExit as e:
                return e.code if e.code is not None else 0
        return 0

    def test_violation_exits_1(self):
        with patch.object(git_ops, "guard_galaxy_frontmatter",
                          return_value=[("p", "missing")]), \
             patch.object(git_ops, "_ensure_hooks_installed"):
            self.assertEqual(self._main_exit(), 1)

    def test_clean_exits_0(self):
        with patch.object(git_ops, "guard_galaxy_frontmatter", return_value=[]), \
             patch.object(git_ops, "_ensure_hooks_installed"):
            self.assertEqual(self._main_exit(), 0)

    def test_guard_error_fails_open_exits_0(self):
        def boom():
            raise RuntimeError("guard bug")
        with patch.object(git_ops, "guard_galaxy_frontmatter", side_effect=boom), \
             patch.object(git_ops, "_ensure_hooks_installed"), \
             patch.object(git_ops, "print"):
            self.assertEqual(self._main_exit(), 0)


class TestHookWiring(unittest.TestCase):
    """The pre-commit shim must invoke the galaxy guard fail-closed (|| exit 1)."""

    def test_pre_commit_invokes_galaxy_guard(self):
        hook = (Path(__file__).resolve().parent.parent
                / "references" / "git-hooks" / "pre-commit")
        text = hook.read_text(encoding="utf-8")
        self.assertIn("guard-galaxy-frontmatter", text)
        self.assertIn("|| exit 1", text)  # fail-closed propagation

    def test_cli_excluded_from_self_heal(self):
        """The guard subcommand must be in the self-heal exclusion tuple so it
        doesn't trigger _ensure_hooks_installed mid-commit."""
        src = (SCRIPTS / "git_ops.py").read_text(encoding="utf-8")
        idx = src.find("if cmd not in (")
        self.assertNotEqual(idx, -1)
        excl_line = src[idx:src.find("\n", idx)]
        self.assertIn("guard-galaxy-frontmatter", excl_line)
        self.assertIn("guard-staged-state", excl_line)


if __name__ == "__main__":
    unittest.main()
