"""Tests for model_router.py — multi-model subagent routing."""

import json
import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import model_router


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

class TestParseModelRouting:
    def test_parses_model_routing_section(self):
        config = textwrap.dedent("""\
        ## Model Routing

        - **Default Model**: claude
        - **Research Model**: gpt-5.2
        - **API Timeout Seconds**: 120
        """)
        result = model_router._parse_model_routing(config)
        assert result["default-model"] == "claude"
        assert result["research-model"] == "gpt-5.2"
        assert result["api-timeout-seconds"] == "120"

    def test_missing_section_returns_empty(self):
        config = "## Other Section\n- **Foo**: bar\n"
        result = model_router._parse_model_routing(config)
        assert result == {}

    def test_none_config_returns_empty(self):
        result = model_router._parse_model_routing(None)
        assert result == {}


class TestGetModelForTask:
    @patch("model_router._read_config")
    def test_claude_locked_comprehension(self, mock_config):
        mock_config.return_value = "## Model Routing\n- **Comprehension Model**: gpt-5.2\n"
        assert model_router.get_model_for_task("comprehension") == "claude"

    @patch("model_router._read_config")
    def test_claude_locked_qa_execution(self, mock_config):
        mock_config.return_value = "## Model Routing\n- **QA Execution Model**: gpt-5.2\n"
        assert model_router.get_model_for_task("qa-execution") == "claude"

    @patch("model_router._read_config")
    def test_research_reads_config(self, mock_config):
        mock_config.return_value = "## Model Routing\n- **Research Model**: gpt-5.2\n- **Default Model**: claude\n"
        assert model_router.get_model_for_task("research") == "gpt-5.2"

    @patch("model_router._read_config")
    def test_defaults_to_default_model(self, mock_config):
        mock_config.return_value = "## Model Routing\n- **Default Model**: claude\n"
        assert model_router.get_model_for_task("research") == "claude"

    @patch("model_router._read_config")
    def test_missing_config_defaults_claude(self, mock_config):
        mock_config.return_value = None
        assert model_router.get_model_for_task("research") == "claude"


class TestGetTimeout:
    @patch("model_router._read_config")
    def test_reads_timeout(self, mock_config):
        mock_config.return_value = "## Model Routing\n- **API Timeout Seconds**: 60\n"
        assert model_router.get_timeout() == 60

    @patch("model_router._read_config")
    def test_default_timeout(self, mock_config):
        mock_config.return_value = "## Other\n"
        assert model_router.get_timeout() == 120


# ---------------------------------------------------------------------------
# Security — 4 layers
# ---------------------------------------------------------------------------

class TestPathSandbox:
    def test_repo_path_allowed(self):
        path = str(model_router.REPO_ROOT / "README.md")
        assert model_router._is_path_in_sandbox(path) is True

    def test_parent_dir_blocked(self):
        path = str(model_router.REPO_ROOT.parent / "etc" / "passwd")
        assert model_router._is_path_in_sandbox(path) is False

    def test_relative_escape_blocked(self):
        # ../../etc/passwd resolved should be outside repo
        path = str(model_router.REPO_ROOT / ".." / ".." / "etc" / "passwd")
        assert model_router._is_path_in_sandbox(path) is False

    def test_prefix_collision_blocked(self):
        # /repo-other/file should NOT pass check for sandbox root /repo
        fake_sibling = str(model_router.REPO_ROOT) + "-other"
        path = fake_sibling + "/secret.txt"
        assert model_router._is_path_in_sandbox(path) is False

    def test_case_mismatch_still_resolves(self):
        # On Windows (case-insensitive FS), mixed-case paths should still
        # resolve correctly. On Linux this just tests a different-case path
        # which is genuinely different and should be blocked if not in repo.
        import os
        repo_str = str(model_router.REPO_ROOT / "README.md")
        swapped = repo_str.swapcase()
        # On case-insensitive FS (Windows): should be True (same file)
        # On case-sensitive FS (Linux): should be False (different path)
        result = model_router._is_path_in_sandbox(swapped)
        if os.name == "nt":
            assert result is True
        else:
            # On case-sensitive FS, swapped case is a different path
            # that likely doesn't exist, so resolve() keeps it as-is
            # and it won't be relative to REPO_ROOT
            assert result is False


class TestSensitiveFiles:
    def test_env_blocked(self):
        assert model_router._is_sensitive_file(".env") is True

    def test_env_local_blocked(self):
        assert model_router._is_sensitive_file(".env.local") is True

    def test_key_file_blocked(self):
        assert model_router._is_sensitive_file("server.key") is True

    def test_pem_file_blocked(self):
        assert model_router._is_sensitive_file("cert.pem") is True

    def test_git_config_blocked(self):
        path = str(model_router.REPO_ROOT / ".git" / "config")
        assert model_router._is_sensitive_file(path) is True

    def test_normal_file_allowed(self):
        assert model_router._is_sensitive_file("README.md") is False

    def test_python_file_allowed(self):
        assert model_router._is_sensitive_file("model_router.py") is False


class TestToolWhitelist:
    def test_read_whitelisted(self):
        assert "read" in model_router.TOOL_REGISTRY

    def test_grep_whitelisted(self):
        assert "grep" in model_router.TOOL_REGISTRY

    def test_glob_whitelisted(self):
        assert "glob" in model_router.TOOL_REGISTRY

    def test_bash_not_available(self):
        result = model_router._handle_tool_call("bash", {"command": "ls"})
        assert "not available" in result

    def test_write_not_available(self):
        result = model_router._handle_tool_call("write", {"path": "x", "content": "y"})
        assert "not available" in result


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

class TestToolRead:
    def test_reads_existing_file(self):
        path = str(model_router.REPO_ROOT / "README.md")
        result = model_router._tool_read({"file_path": path})
        assert "ERROR" not in result
        assert len(result) > 0

    def test_rejects_path_outside_sandbox(self):
        result = model_router._tool_read({"file_path": "/etc/passwd"})
        assert "ERROR" in result
        assert "boundary" in result

    def test_rejects_sensitive_file(self):
        # Create a temp .env to test
        env_path = str(model_router.REPO_ROOT / ".env")
        result = model_router._tool_read({"file_path": env_path})
        assert "ERROR" in result
        assert "sensitive" in result.lower() or "denied" in result.lower()

    def test_nonexistent_file(self):
        path = str(model_router.REPO_ROOT / "nonexistent_file_abc123.txt")
        result = model_router._tool_read({"file_path": path})
        assert "ERROR" in result
        assert "not found" in result.lower()


class TestToolGlob:
    def test_finds_python_files(self):
        result = model_router._tool_glob({"pattern": "**/*.py", "path": str(model_router.REPO_ROOT / "references" / "scripts")})
        assert "model_router.py" in result

    def test_rejects_path_outside_sandbox(self):
        result = model_router._tool_glob({"pattern": "*.py", "path": "/etc"})
        assert "ERROR" in result


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

class TestPromptAssembly:
    def test_loads_research_template(self):
        template = model_router._load_prompt_template("research")
        assert template is not None
        assert "research" in template.lower() or "analyze" in template.lower()

    def test_loads_discussion_prep_template(self):
        template = model_router._load_prompt_template("discussion-prep")
        assert template is not None

    def test_loads_test_plan_template(self):
        template = model_router._load_prompt_template("test-plan")
        assert template is not None

    def test_loads_improvement_scan_template(self):
        template = model_router._load_prompt_template("improvement-scan")
        assert template is not None

    def test_unknown_task_returns_none(self):
        template = model_router._load_prompt_template("unknown-task")
        assert template is None

    def test_assemble_substitutes_variables(self):
        prompt = model_router.assemble_prompt(
            "research", "FEAT-TEST-001", "", "Test context"
        )
        assert "FEAT-TEST-001" in prompt
        assert "Test context" in prompt


class TestReadInputFilesSecurity:
    """#8583: _read_input_files must apply security layers."""

    def test_skips_sensitive_file(self, tmp_path):
        """Sensitive files (.env) are excluded from external model input."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET_KEY=abc123")
        with patch.object(model_router, "REPO_ROOT", tmp_path):
            result = model_router._read_input_files(str(env_file))
        assert "SECRET_KEY" not in result
        assert "SKIPPED" in result
        assert "Sensitive file" in result

    def test_skips_path_outside_sandbox(self):
        """Files outside the repo are excluded."""
        outside_path = str(model_router.REPO_ROOT.parent / "etc" / "passwd")
        result = model_router._read_input_files(outside_path)
        assert "SKIPPED" in result
        assert "outside repository" in result

    def test_truncates_large_file(self, tmp_path):
        """Files exceeding MAX_FILE_READ_BYTES are truncated."""
        big_file = tmp_path / "big.py"
        big_file.write_text("x" * (model_router.MAX_FILE_READ_BYTES + 100))
        with patch.object(model_router, "REPO_ROOT", tmp_path):
            result = model_router._read_input_files(str(big_file))
        assert "TRUNCATED" in result
        assert len(result) < model_router.MAX_FILE_READ_BYTES + 500

    def test_reads_normal_file(self, tmp_path):
        """Normal files within sandbox are read correctly."""
        normal_file = tmp_path / "code.py"
        normal_file.write_text("def hello(): pass")
        with patch.object(model_router, "REPO_ROOT", tmp_path):
            result = model_router._read_input_files(str(normal_file))
        assert "def hello(): pass" in result

    def test_multiple_files_mixed(self, tmp_path):
        """Multiple files: sensitive ones skipped, normal ones read."""
        good_file = tmp_path / "ok.py"
        good_file.write_text("good content")
        bad_file = tmp_path / ".env"
        bad_file.write_text("SECRET=leak")
        input_str = f"{good_file},{bad_file}"
        with patch.object(model_router, "REPO_ROOT", tmp_path):
            result = model_router._read_input_files(input_str)
        assert "good content" in result
        assert "SECRET" not in result
        assert "SKIPPED" in result

    def test_key_file_skipped(self, tmp_path):
        """Key files (.key, .pem) are excluded."""
        key_file = tmp_path / "server.key"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----")
        with patch.object(model_router, "REPO_ROOT", tmp_path):
            result = model_router._read_input_files(str(key_file))
        assert "RSA PRIVATE KEY" not in result
        assert "SKIPPED" in result


# ---------------------------------------------------------------------------
# Route logic
# ---------------------------------------------------------------------------

class TestRoute:
    @patch("model_router._read_config")
    def test_claude_config_returns_1(self, mock_config):
        """All-claude config should exit 1 (use Agent tool)."""
        mock_config.return_value = "## Model Routing\n- **Default Model**: claude\n"
        code = model_router.route("research", "TEST", "", "/tmp/out.md", "test")
        assert code == 1

    @patch("model_router._read_config")
    def test_comprehension_always_returns_1(self, mock_config):
        """Comprehension is locked to claude regardless of config."""
        mock_config.return_value = "## Model Routing\n- **Comprehension Model**: gpt-5.2\n"
        code = model_router.route("comprehension", "TEST", "", "/tmp/out.md", "test")
        assert code == 1

    @patch("model_router._read_config")
    def test_qa_execution_always_returns_1(self, mock_config):
        """QA execution is locked to claude regardless of config."""
        mock_config.return_value = "## Model Routing\n- **QA Execution Model**: gpt-5.2\n"
        code = model_router.route("qa-execution", "TEST", "", "/tmp/out.md", "test")
        assert code == 1

    @patch("model_router._read_config")
    def test_missing_api_key_returns_2(self, mock_config, monkeypatch):
        """Missing API key (env + secrets) should exit 2."""
        mock_config.return_value = "## Model Routing\n- **Research Model**: gpt-5.2\n- **Default Model**: claude\n"
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Also block the secrets file fallback
        with patch("model_router.os.environ.get", return_value=None):
            with patch.dict("sys.modules", {"shared_fs": MagicMock(read_secret_or_env=MagicMock(return_value=None))}):
                code = model_router.route("research", "TEST", "", "/tmp/out.md", "test")
        assert code == 2


# ---------------------------------------------------------------------------
# CLI dispatch — bare 'route' subcommand (#3814)
# ---------------------------------------------------------------------------

class TestRouteSubcommandTaskType:
    """Regression test for #3814: bare 'route' should use --task-type, not hardcode 'research'."""

    @patch("model_router.route")
    def test_bare_route_defaults_to_research(self, mock_route):
        """Without --task-type, bare 'route' defaults to 'research'."""
        mock_route.return_value = 0
        with patch.object(sys, "argv", [
            "model_router.py", "route", "--task-id", "T1", "--output-file", "/tmp/out.md",
        ]):
            with pytest.raises(SystemExit) as exc:
                model_router.main()
            assert exc.value.code == 0
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == "research"

    @patch("model_router.route")
    def test_bare_route_accepts_task_type_override(self, mock_route):
        """--task-type overrides the default for bare 'route' subcommand."""
        mock_route.return_value = 0
        with patch.object(sys, "argv", [
            "model_router.py", "route", "--task-type", "test-plan",
            "--task-id", "T1", "--output-file", "/tmp/out.md",
        ]):
            with pytest.raises(SystemExit) as exc:
                model_router.main()
            assert exc.value.code == 0
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == "test-plan"

    @patch("model_router.route")
    def test_named_alias_uses_command_as_task_type(self, mock_route):
        """Named aliases (e.g. 'test-plan') use command name, not --task-type."""
        mock_route.return_value = 0
        with patch.object(sys, "argv", [
            "model_router.py", "test-plan", "--task-id", "T1", "--output-file", "/tmp/out.md",
        ]):
            with pytest.raises(SystemExit) as exc:
                model_router.main()
            assert exc.value.code == 0
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == "test-plan"


# ---------------------------------------------------------------------------
# Provider manifest
# ---------------------------------------------------------------------------

class TestProviderManifest:
    def test_openai_manifest_exists(self):
        manifest_path = model_router.PROVIDERS_DIR / "openai" / "manifest.yaml"
        assert manifest_path.exists()

    def test_openai_manifest_loads(self):
        name, manifest = model_router._load_provider_manifest("gpt-5.2")
        assert name == "openai"
        assert manifest is not None
        assert "auth" in manifest
        assert manifest["auth"]["env_var"] == "OPENAI_API_KEY"

    def test_unknown_model_returns_none(self):
        name, manifest = model_router._load_provider_manifest("unknown-model-xyz")
        assert name is None
        assert manifest is None


# ---------------------------------------------------------------------------
# OpenAI tool definitions
# ---------------------------------------------------------------------------

class TestOpenAIToolDefs:
    def test_three_tools_defined(self):
        assert len(model_router.OPENAI_TOOL_DEFS) == 3

    def test_all_function_type(self):
        for tool in model_router.OPENAI_TOOL_DEFS:
            assert tool["type"] == "function"

    def test_tool_names(self):
        names = {t["function"]["name"] for t in model_router.OPENAI_TOOL_DEFS}
        assert names == {"read", "grep", "glob"}

    def test_no_shell_tools(self):
        names = {t["function"]["name"] for t in model_router.OPENAI_TOOL_DEFS}
        assert "bash" not in names
        assert "shell" not in names
        assert "exec" not in names


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_help(self):
        """--help should not crash."""
        with pytest.raises(SystemExit) as exc:
            model_router.main.__wrapped__ if hasattr(model_router.main, '__wrapped__') else None
            sys.argv = ["model_router.py", "--help"]
            model_router.main()
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# list_providers
# ---------------------------------------------------------------------------

class TestListProviders:
    def test_discovers_openai_provider(self):
        """list_providers should find the openai provider from manifest."""
        providers = model_router.list_providers()
        names = [p["name"] for p in providers]
        assert "openai" in names

    def test_discovers_deepseek_provider(self):
        """list_providers should find the deepseek provider from manifest."""
        providers = model_router.list_providers()
        names = [p["name"] for p in providers]
        assert "deepseek" in names

    def test_deepseek_has_correct_fields(self):
        """DeepSeek provider should have correct auth and models."""
        providers = model_router.list_providers()
        ds = [p for p in providers if p["name"] == "deepseek"]
        assert len(ds) == 1
        assert ds[0]["auth_env_var"] == "DEEPSEEK_API_KEY"
        assert "deepseek-v4-pro" in ds[0]["models"]

    def test_provider_has_required_fields(self):
        """Each provider entry should have name, display_name, default_model, models, auth_env_var."""
        providers = model_router.list_providers()
        assert len(providers) > 0
        for p in providers:
            assert "name" in p
            assert "display_name" in p
            assert "default_model" in p
            assert "models" in p
            assert isinstance(p["models"], list)
            assert "auth_env_var" in p

    def test_empty_providers_dir(self, tmp_path):
        """list_providers returns empty list when no providers exist."""
        with patch.object(model_router, "PROVIDERS_DIR", tmp_path / "empty"):
            result = model_router.list_providers()
        assert result == []

    def test_cli_list_providers(self, capsys):
        """CLI list-providers subcommand outputs valid JSON."""
        with pytest.raises(SystemExit) as exc:
            sys.argv = ["model_router.py", "list-providers"]
            model_router.main()
        assert exc.value.code == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# setup-provider and validate
# ---------------------------------------------------------------------------

class TestFindProviderManifest:
    def test_finds_openai(self):
        path, manifest = model_router._find_provider_manifest("openai")
        assert path is not None
        assert manifest is not None
        assert manifest["name"] == "openai"

    def test_not_found_returns_none(self):
        path, manifest = model_router._find_provider_manifest("nonexistent")
        assert path is None
        assert manifest is None

    def test_case_insensitive(self):
        path, manifest = model_router._find_provider_manifest("OpenAI")
        assert manifest is not None


class TestSetupProvider:
    def test_unknown_provider_returns_2(self, capsys):
        code = model_router.setup_provider("nonexistent")
        assert code == 2
        err = capsys.readouterr().err
        assert "not found" in err

    @patch("os.startfile", create=True)
    def test_known_provider_returns_0(self, mock_startfile, capsys):
        code = model_router.setup_provider("openai")
        assert code == 0
        out = capsys.readouterr().out
        assert "OPENAI_API_KEY" in out
        assert "secrets" in out.lower()


class TestValidateProvider:
    def test_unknown_provider_returns_2(self, capsys):
        code = model_router.validate_provider("nonexistent")
        assert code == 2

    def test_no_api_key_returns_1(self, capsys):
        # Remove key from env AND mock shared_fs to raise ImportError
        env_copy = os.environ.copy()
        env_copy.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, env_copy, clear=True):
            # Mock the import of shared_fs inside validate_provider
            with patch.dict("sys.modules", {"shared_fs": None}):
                code = model_router.validate_provider("openai")
        assert code == 1
        err = capsys.readouterr().err
        assert "not set" in err


# ---------------------------------------------------------------------------
# No shell=True
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# #3422 regression: quota exceeded notification
# ---------------------------------------------------------------------------

class TestQuotaNotification:
    @patch("model_router._read_config", return_value="## Model Routing\n- **Research Model**: gpt-5.2\n")
    @patch("model_router._load_provider_manifest")
    @patch("model_router._ensure_deps")
    @patch("model_router._log_diagnostic")
    @patch("model_router._load_adapter")
    def test_429_prints_prominent_notification(
        self, mock_adapter, mock_diag, mock_deps, mock_manifest, mock_config, capsys
    ):
        """Quota exceeded error prints prominent human-visible notification."""
        mock_manifest.return_value = ("openai", {
            "name": "openai", "auth": {"env_var": "OPENAI_API_KEY"},
            "api_base": "", "deps": [],
        })
        fake_module = MagicMock()
        fake_module.call.side_effect = Exception("Error code: 429 - quota exceeded")
        mock_adapter.return_value = fake_module
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("model_router.assemble_prompt", return_value="test"):
                code = model_router.route("research", "test-1", "", "/tmp/out", "ctx")
        assert code == 1
        captured = capsys.readouterr()
        assert "QUOTA EXCEEDED" in captured.out
        assert "Add credits" in captured.out
        # Verify diagnostic logged as quota-exceeded
        mock_diag.assert_called_once()
        assert mock_diag.call_args[0][0]["action"] == "quota-exceeded"

    @patch("model_router._read_config", return_value="## Model Routing\n- **Research Model**: gpt-5.2\n")
    @patch("model_router._load_provider_manifest")
    @patch("model_router._ensure_deps")
    @patch("model_router._log_diagnostic")
    @patch("model_router._load_adapter")
    def test_non_quota_error_uses_stderr(
        self, mock_adapter, mock_diag, mock_deps, mock_manifest, mock_config, capsys
    ):
        """Non-quota API errors go to stderr, not the prominent notification."""
        mock_manifest.return_value = ("openai", {
            "name": "openai", "auth": {"env_var": "OPENAI_API_KEY"},
            "api_base": "", "deps": [],
        })
        fake_module = MagicMock()
        fake_module.call.side_effect = Exception("Connection refused")
        mock_adapter.return_value = fake_module
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("model_router.assemble_prompt", return_value="test"):
                code = model_router.route("research", "test-1", "", "/tmp/out", "ctx")
        assert code == 1
        captured = capsys.readouterr()
        assert "QUOTA EXCEEDED" not in captured.out
        assert "Connection refused" in captured.err
        mock_diag.assert_called_once()
        assert mock_diag.call_args[0][0]["action"] == "api-error"


    @patch("model_router._read_config", return_value="## Model Routing\n- **Research Model**: gpt-5.2\n")
    @patch("model_router._load_provider_manifest")
    @patch("model_router._ensure_deps")
    @patch("model_router._log_diagnostic")
    @patch("model_router._load_adapter")
    def test_timeout_error_returns_exit_code_3(
        self, mock_adapter, mock_diag, mock_deps, mock_manifest, mock_config, capsys
    ):
        """Timeout errors return exit code 3 (distinct from quota/generic errors)."""
        mock_manifest.return_value = ("openai", {
            "name": "openai", "auth": {"env_var": "OPENAI_API_KEY"},
            "api_base": "", "deps": [],
        })
        fake_module = MagicMock()
        fake_module.call.side_effect = Exception("Request timed out after 120s")
        mock_adapter.return_value = fake_module
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("model_router.assemble_prompt", return_value="test"):
                code = model_router.route("research", "test-1", "", "/tmp/out", "ctx")
        assert code == 3
        captured = capsys.readouterr()
        assert "timeout" in captured.err.lower()
        mock_diag.assert_called_once()
        assert mock_diag.call_args[0][0]["action"] == "timeout"

    @patch("model_router._read_config", return_value="## Model Routing\n- **Research Model**: gpt-5.2\n")
    @patch("model_router._load_provider_manifest")
    @patch("model_router._ensure_deps")
    @patch("model_router._log_diagnostic")
    @patch("model_router._load_adapter")
    def test_timeout_error_type_returns_exit_code_3(
        self, mock_adapter, mock_diag, mock_deps, mock_manifest, mock_config, capsys
    ):
        """TimeoutError exception type also returns exit code 3."""
        mock_manifest.return_value = ("openai", {
            "name": "openai", "auth": {"env_var": "OPENAI_API_KEY"},
            "api_base": "", "deps": [],
        })
        fake_module = MagicMock()
        fake_module.call.side_effect = TimeoutError("connection timed out")
        mock_adapter.return_value = fake_module
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("model_router.assemble_prompt", return_value="test"):
                code = model_router.route("research", "test-1", "", "/tmp/out", "ctx")
        assert code == 3
        mock_diag.assert_called_once()
        assert mock_diag.call_args[0][0]["action"] == "timeout"


class TestNoShellTrue:
    def test_no_shell_true_in_source(self):
        """model_router.py must not use shell=True (security layer 3)."""
        source = (model_router.SCRIPT_DIR / "model_router.py").read_text(encoding="utf-8")
        assert "shell=True" not in source


class TestEnsureYaml:
    """#5125: _ensure_yaml() deduplicates yaml import with error handling."""

    def test_returns_yaml_when_available(self):
        """Returns yaml module when already installed."""
        result = model_router._ensure_yaml()
        assert result is not None
        assert hasattr(result, "safe_load")

    def test_returns_none_on_pip_failure(self, monkeypatch):
        """Returns None (not crash) when both import and pip fail."""
        import builtins
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setattr(
            model_router.subprocess, "check_call",
            MagicMock(side_effect=model_router.subprocess.CalledProcessError(1, "pip")),
        )
        result = model_router._ensure_yaml()
        assert result is None

    def test_no_duplicate_blocks_in_source(self):
        """Verify triplicate pattern is eliminated (#5125)."""
        source = (model_router.SCRIPT_DIR / "model_router.py").read_text(encoding="utf-8")
        # Count raw "import yaml" lines (excluding the helper function itself)
        import_lines = [
            l.strip() for l in source.splitlines()
            if l.strip() == "import yaml"
        ]
        # Should only appear inside _ensure_yaml (2 times: try + after install)
        assert len(import_lines) <= 2, \
            f"Found {len(import_lines)} bare 'import yaml' lines — should be ≤2 (inside _ensure_yaml only)"
