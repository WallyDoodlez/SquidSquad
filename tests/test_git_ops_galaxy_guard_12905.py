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
        # .gitkeep is excluded by the .md extension check; *-template.md by the
        # explicit template exclusion (DS-12905 F3).
        v = self._run_guard(
            [".squidsquad/vault/galaxy/.gitkeep",
             ".squidsquad/vault/galaxy/galaxy-template.md"],
            {".squidsquad/vault/galaxy/.gitkeep": "",
             ".squidsquad/vault/galaxy/galaxy-template.md": "# template\n"},
        )
        self.assertEqual(v, [])

    def test_unanchored_vault_galaxy_path_ignored(self):
        """DS-12905 Finding 2: a path that merely CONTAINS 'vault/galaxy' but is
        NOT under .squidsquad/vault/galaxy/ must not be treated as a galaxy note
        (the static gate only ever checks .squidsquad/vault/galaxy/)."""
        v = self._run_guard(
            ["docs/vault/galaxy/architecture.md",
             "some/other/vault/galaxy/note.md"],
            {"docs/vault/galaxy/architecture.md": "# no frontmatter\n",
             "some/other/vault/galaxy/note.md": "# no frontmatter\n"},
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


class TestGuardComposition(unittest.TestCase):
    """The two pre-commit guards compose by branch (the subtle interaction that
    makes the galaxy guard's effective scope the WORKING branch).

    Galaxy notes are main-only state: on a feature branch the #11511 state guard
    UNSTAGES a staged galaxy note (it doesn't belong in a PR), so a feature-branch
    commit never carries it and the galaxy guard has nothing left to check. The
    galaxy guard therefore only ever fires where galaxy notes actually land — on
    the working branch, where the state guard no-ops. A smoke run on a feature
    branch shows the hook 'allowing' a bad note precisely because the state guard
    already removed it — that is correct composition, not a guard miss.
    """

    def test_state_guard_strips_galaxy_note_on_feature_branch(self):
        """On a feature branch, Guard 1 unstages the galaxy note before Guard 2."""
        galaxy = ".squidsquad/vault/galaxy/learning-bad.md"
        reset_calls = []

        def fake_run(cmd, check=True):
            if cmd == "git branch --show-current":
                return _cp(0, "squidsquad/task/12905\n")  # NOT the working branch
            return _cp(0, "")

        def fake_run_list(cmd, check=True):
            if cmd[:4] == ["git", "diff", "--cached", "--name-only"]:
                return _cp(0, galaxy + "\n")
            if cmd[:3] == ["git", "diff", "--cached"] and "--quiet" in cmd:
                # #13724: matches-origin/main check -- returncode=1 (differs)
                # so the note proceeds to the genuine-leak unstage path below.
                return _cp(1, "")
            if cmd[:2] == ["git", "reset"]:
                reset_calls.append(cmd[-1])
                return _cp(0, "")
            return _cp(0, "")

        with patch.object(git_ops, "_get_working_branch", return_value="main"), \
             patch.object(git_ops, "_run", side_effect=fake_run), \
             patch.object(git_ops, "_run_list", side_effect=fake_run_list), \
             patch.object(git_ops, "print"):
            stripped = git_ops.guard_staged_state()
        self.assertEqual(stripped, [galaxy])
        self.assertIn(galaxy, reset_calls)  # actually unstaged

    def test_state_guard_noops_on_working_branch_so_galaxy_guard_fires(self):
        """On the working branch, Guard 1 no-ops, leaving the note for Guard 2."""
        galaxy = ".squidsquad/vault/galaxy/learning-bad.md"

        def fake_run(cmd, check=True):
            if cmd == "git branch --show-current":
                return _cp(0, "main\n")  # IS the working branch
            return _cp(0, "")

        def fake_run_list(cmd, check=True):
            if cmd[:4] == ["git", "diff", "--cached", "--name-only"]:
                return _cp(0, galaxy + "\n")
            if cmd[:2] == ["git", "show"]:
                return _cp(0, "# no frontmatter\n")
            return _cp(0, "")

        with patch.object(git_ops, "_get_working_branch", return_value="main"), \
             patch.object(git_ops, "_run", side_effect=fake_run), \
             patch.object(git_ops, "_run_list", side_effect=fake_run_list), \
             patch.object(git_ops, "print"):
            stripped = git_ops.guard_staged_state()       # Guard 1: no-op
            violations = git_ops.guard_galaxy_frontmatter()  # Guard 2: catches it
        self.assertEqual(stripped, [])
        self.assertEqual([p for p, _ in violations], [galaxy])


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

    def test_violation_exits_1_and_emits_marker(self):
        """Violation → exit 1 AND prints the block marker the shim keys on."""
        printed = []
        with patch.object(git_ops, "guard_galaxy_frontmatter",
                          return_value=[("p", "missing")]), \
             patch.object(git_ops, "_ensure_hooks_installed"), \
             patch("builtins.print",
                   side_effect=lambda *a, **k: printed.append(" ".join(str(x) for x in a))):
            self.assertEqual(self._main_exit(), 1)
        self.assertTrue(any("__SQUIDSQUAD_GALAXY_FM_BLOCK__" in line for line in printed),
                        "violation must emit the block marker for the pre-commit shim")

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
        # DS-12905 F1: the shim BLOCKS on the explicit marker, not the exit code
        # (a module-level python crash also exits 1 and must NOT wedge commits).
        self.assertIn("__SQUIDSQUAD_GALAXY_FM_BLOCK__", text)
        self.assertIn("exit 1", text)  # fail-closed on the marker match

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
