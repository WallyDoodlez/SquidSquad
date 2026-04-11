"""Unit tests for the install wizard helpers (#328 Phase G part 1).

The wizard's mechanical pieces — gh prerequisite check, re-run detection,
repo metadata probing, project-name validation, re-run action parsing —
are tested here with subprocess and filesystem calls fully stubbed. No
test talks to the real `gh` CLI or the real `.squidsquad/` directory.

The prose runbook and the LLM-driven pieces (intent classification,
setup_requirements walker, natural conversation) are NOT tested here —
they live in the runbook Claude follows and are exercised via the
integration-level wizard tests in TEST-PLAN.md once Phase G lands.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — make a fake subprocess.run and a fake `which`
# ---------------------------------------------------------------------------


def _fake_proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _install_fake_run(monkeypatch, mapping):
    """Stub wizard._run so it returns canned responses by command prefix.

    mapping: {(cmd_tuple_prefix,): fake_proc}. The longest matching prefix
    wins so callers can override specific subcommands.
    """
    def _fake(cmd, **kwargs):
        best = None
        for prefix, proc in mapping.items():
            if tuple(cmd[: len(prefix)]) == prefix:
                if best is None or len(prefix) > len(best[0]):
                    best = (prefix, proc)
        if best is not None:
            return best[1]
        return _fake_proc(returncode=127, stderr=f"unstubbed: {cmd}")

    monkeypatch.setattr(wizard, "_run", _fake)


# ===========================================================================
# Step 0 — check_gh
# ===========================================================================


class TestCheckGh:
    def test_gh_not_installed(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", lambda name: None)
        result = wizard.check_gh()
        assert result["ok"] is False
        assert result["stage"] == "installed"
        assert "not installed" in result["message"]
        assert any("gh auth login" in line for line in result["fix"])

    def test_gh_installed_but_unauthenticated(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", lambda name: "/usr/bin/gh")
        _install_fake_run(monkeypatch, {
            ("gh", "auth", "status"): _fake_proc(
                returncode=1,
                stderr="You are not logged in to any hosts.",
            ),
        })
        result = wizard.check_gh()
        assert result["ok"] is False
        assert result["stage"] == "authenticated"
        assert any("gh auth login" in line for line in result["fix"])
        assert any("repo" in line for line in result["fix"])

    def test_gh_ready(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", lambda name: "/usr/bin/gh")
        _install_fake_run(monkeypatch, {
            ("gh", "auth", "status"): _fake_proc(returncode=0, stderr="ok"),
        })
        result = wizard.check_gh()
        assert result["ok"] is True
        assert result["stage"] == "ready"
        assert result["fix"] == []


# ===========================================================================
# Step 0b — detect_existing_install + validate_rerun_action
# ===========================================================================


class TestDetectExistingInstall:
    def test_no_existing_install(self, tmp_path):
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is False
        assert result["contents"] == []
        assert result["has_config"] is False
        assert result["has_roles"] is False
        assert result["default_action"] == "abort"
        assert set(result["actions"]) == {"abort", "regenerate", "full-rebuild"}

    def test_empty_squidsquad_dir(self, tmp_path):
        (tmp_path / ".squidsquad").mkdir()
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is True
        assert result["contents"] == []
        assert result["has_config"] is False
        assert result["has_roles"] is False

    def test_partial_install_with_config_only(self, tmp_path):
        sq = tmp_path / ".squidsquad"
        sq.mkdir()
        (sq / "config.md").write_text("# config\n")
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is True
        assert "config.md" in result["contents"]
        assert result["has_config"] is True
        assert result["has_roles"] is False

    def test_full_install_with_roles(self, tmp_path):
        sq = tmp_path / ".squidsquad"
        sq.mkdir()
        (sq / "config.md").write_text("# config\n")
        (sq / "pm").mkdir()
        (sq / "pm" / "CLAUDE.md").write_text("# pm\n")
        (sq / "skill").mkdir()
        (sq / "skill" / "CLAUDE.md").write_text("# skill\n")
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is True
        assert result["has_config"] is True
        assert result["has_roles"] is True
        assert "pm" in result["contents"]
        assert "skill" in result["contents"]

    def test_hidden_entries_excluded(self, tmp_path):
        """`.gitkeep`, `.local-config`, etc. are not listed in contents."""
        sq = tmp_path / ".squidsquad"
        sq.mkdir()
        (sq / ".local-config").write_text("hidden\n")
        (sq / ".gitkeep").write_text("")
        (sq / "config.md").write_text("# config\n")
        result = wizard.detect_existing_install(tmp_path)
        assert ".local-config" not in result["contents"]
        assert ".gitkeep" not in result["contents"]
        assert "config.md" in result["contents"]


class TestValidateRerunAction:
    @pytest.mark.parametrize("raw,expected", [
        ("abort", "abort"),
        ("regenerate", "regenerate"),
        ("full-rebuild", "full-rebuild"),
        ("1", "abort"),
        ("2", "regenerate"),
        ("3", "full-rebuild"),
        ("a", "abort"),
        ("r", "regenerate"),
        ("f", "full-rebuild"),
        ("rebuild", "full-rebuild"),
        ("fullrebuild", "full-rebuild"),
        ("full_rebuild", "full-rebuild"),
        ("ABORT", "abort"),
        (" 2 ", "regenerate"),
        ("", "abort"),  # Empty -> default
        (None, "abort"),  # None -> default
    ])
    def test_valid_inputs(self, raw, expected):
        assert wizard.validate_rerun_action(raw) == expected

    @pytest.mark.parametrize("raw", [
        "maybe", "yes", "no", "42", "delete",
    ])
    def test_invalid_inputs(self, raw):
        assert wizard.validate_rerun_action(raw) is None


# ===========================================================================
# Step 1 — project name validation
# ===========================================================================


class TestProjectNameValidation:
    @pytest.mark.parametrize("name", [
        "my-app",
        "MyApp",
        "my_app",
        "app.v2",
        "squidsquad",
        "a",
        "Project123",
    ])
    def test_valid_names(self, name):
        assert wizard.is_valid_project_name(name)

    @pytest.mark.parametrize("name", [
        "",
        "   ",
        "my app",  # space
        "my/app",  # slash
        "my\\app",  # backslash
        ".hidden",  # leading dot
        "-leading-dash",  # leading dash
        "my@app",  # @
        "very" * 50,  # > 100 chars
    ])
    def test_invalid_names(self, name):
        assert not wizard.is_valid_project_name(name)

    def test_non_string_rejected(self):
        assert not wizard.is_valid_project_name(None)
        assert not wizard.is_valid_project_name(42)
        assert not wizard.is_valid_project_name([])


# ===========================================================================
# Step 1 — git remote slug parsing
# ===========================================================================


class TestParseGithubSlug:
    @pytest.mark.parametrize("url,expected", [
        ("https://github.com/alice/foo.git", "alice/foo"),
        ("https://github.com/alice/foo", "alice/foo"),
        ("https://github.com/alice/foo/", "alice/foo"),
        ("git@github.com:alice/foo.git", "alice/foo"),
        ("git@github.com:alice/foo", "alice/foo"),
        ("ssh://git@github.com/alice/foo.git", "alice/foo"),
        ("https://github.com/Org-Name/Repo.Name", "Org-Name/Repo.Name"),
        ("https://github.com/wally/squid_squad", "wally/squid_squad"),
    ])
    def test_parses_common_forms(self, url, expected):
        assert wizard._parse_github_slug(url) == expected

    @pytest.mark.parametrize("url", [
        "",
        None,
        "https://gitlab.com/alice/foo.git",  # not github
        "not-a-url",
        "https://github.com/",  # no owner/repo
    ])
    def test_non_github_or_malformed(self, url):
        assert wizard._parse_github_slug(url) is None


# ===========================================================================
# Step 1 — repo-info resolution (gh primary, git fallback, neither)
# ===========================================================================


class TestGetRepoInfo:
    def test_gh_succeeds(self, monkeypatch, tmp_path):
        gh_json = (
            '{"name": "my-app", "nameWithOwner": "alice/my-app", '
            '"owner": {"login": "alice"}, '
            '"description": "Cool thing", '
            '"url": "https://github.com/alice/my-app"}'
        )
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=0, stdout=gh_json),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "gh"
        assert result["project_name"] == "my-app"
        assert result["repo_slug"] == "alice/my-app"
        assert result["owner"] == "alice"
        assert result["description"] == "Cool thing"
        assert result["remote_url"] == "https://github.com/alice/my-app"

    def test_gh_fails_git_remote_succeeds(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=1, stderr="not a gh repo",
            ),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="https://github.com/bob/other.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "git"
        assert result["repo_slug"] == "bob/other"
        assert result["owner"] == "bob"
        assert result["project_name"] == "other"
        assert result["description"] is None

    def test_ssh_remote_parsed(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="git@github.com:wally/squid-squad.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "git"
        assert result["repo_slug"] == "wally/squid-squad"

    def test_both_fail(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
            ("git", "remote", "get-url", "origin"): _fake_proc(returncode=1),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is False
        assert result["source"] == "none"
        assert result["project_name"] is None
        assert result["repo_slug"] is None

    def test_malformed_gh_json_falls_through(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=0, stdout="not json {",
            ),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="https://github.com/c/d.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "git"
        assert result["repo_slug"] == "c/d"

    def test_non_github_remote_returns_not_ok(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="https://gitlab.com/a/b.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is False
        assert result["source"] == "none"


# ===========================================================================
# project_name_default — prefers gh, falls back to cwd basename
# ===========================================================================


class TestProjectNameDefault:
    def test_gh_returns_valid_name(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=0, stdout='{"name": "my-app"}',
            ),
        })
        assert wizard.project_name_default(tmp_path) == "my-app"

    def test_gh_returns_invalid_name_falls_back_to_dirname(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=0, stdout='{"name": "my app with spaces"}',
            ),
        })
        # Falls back to the tmp directory's name
        assert wizard.project_name_default(tmp_path) == tmp_path.resolve().name

    def test_gh_fails_returns_dirname(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
        })
        assert wizard.project_name_default(tmp_path) == tmp_path.resolve().name
