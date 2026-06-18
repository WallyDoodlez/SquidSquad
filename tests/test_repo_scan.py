"""Tests for references/scripts/repo_scan.py — repo tech stack detection."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import repo_scan


class TestLanguageDetection:
    def test_detects_python(self, tmp_path):
        (tmp_path / "app.py").write_text("print('hello')")
        result = repo_scan.scan(tmp_path)
        assert "python" in result["languages"]

    def test_detects_typescript(self, tmp_path):
        (tmp_path / "index.ts").write_text("const x = 1;")
        result = repo_scan.scan(tmp_path)
        assert "typescript" in result["languages"]

    def test_detects_multiple_languages(self, tmp_path):
        (tmp_path / "app.py").write_text("")
        (tmp_path / "index.js").write_text("")
        (tmp_path / "main.go").write_text("")
        result = repo_scan.scan(tmp_path)
        assert len(result["languages"]) >= 3

    def test_empty_repo(self, tmp_path):
        result = repo_scan.scan(tmp_path)
        assert result["languages"] == []

    def test_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("")
        result = repo_scan.scan(tmp_path)
        assert "javascript" not in result["languages"]


class TestPackageManagerDetection:
    def test_detects_npm(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        result = repo_scan.scan(tmp_path)
        assert "npm" in result["package_managers"]

    def test_detects_pip(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==2.0")
        result = repo_scan.scan(tmp_path)
        assert "pip" in result["package_managers"]

    def test_detects_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')
        result = repo_scan.scan(tmp_path)
        assert "cargo" in result["package_managers"]


class TestFrameworkDetection:
    def test_detects_nextjs_config(self, tmp_path):
        (tmp_path / "next.config.js").write_text("module.exports = {}")
        result = repo_scan.scan(tmp_path)
        assert "nextjs" in result["frameworks"]

    def test_detects_react_from_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"react": "^18.0.0"}}'
        )
        result = repo_scan.scan(tmp_path)
        assert "react" in result["frameworks"]

    def test_detects_tailwind(self, tmp_path):
        (tmp_path / "tailwind.config.js").write_text("module.exports = {}")
        result = repo_scan.scan(tmp_path)
        assert "tailwind" in result["frameworks"]


    def test_detects_fastapi_from_requirements(self, tmp_path):
        """#4124 regression: FastAPI detected via requirements.txt, not file presence."""
        (tmp_path / "requirements.txt").write_text("fastapi>=0.100\nuvicorn\n")
        result = repo_scan.scan(tmp_path)
        assert "fastapi" in result["frameworks"]

    def test_detects_fastapi_from_pyproject(self, tmp_path):
        """#4124: FastAPI detected via pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi", "uvicorn"]\n'
        )
        result = repo_scan.scan(tmp_path)
        assert "fastapi" in result["frameworks"]


class TestCICDDetection:
    def test_detects_github_actions(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        result = repo_scan.scan(tmp_path)
        assert "github-actions" in result["ci_cd"]

    def test_detects_gitlab_ci(self, tmp_path):
        (tmp_path / ".gitlab-ci.yml").write_text("stages: [build]")
        result = repo_scan.scan(tmp_path)
        assert "gitlab-ci" in result["ci_cd"]


class TestTestFrameworkDetection:
    def test_detects_pytest(self, tmp_path):
        (tmp_path / "conftest.py").write_text("")
        result = repo_scan.scan(tmp_path)
        assert "pytest" in result["test_frameworks"]

    def test_detects_jest_from_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"devDependencies": {"jest": "^29.0.0"}}'
        )
        result = repo_scan.scan(tmp_path)
        assert "jest" in result["test_frameworks"]

    def test_detects_playwright(self, tmp_path):
        (tmp_path / "playwright.config.ts").write_text("")
        result = repo_scan.scan(tmp_path)
        assert "playwright" in result["test_frameworks"]


class TestDeployDetection:
    def test_detects_docker(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM node:18")
        result = repo_scan.scan(tmp_path)
        assert "docker" in result["deploy_targets"]

    def test_detects_vercel(self, tmp_path):
        (tmp_path / "vercel.json").write_text("{}")
        result = repo_scan.scan(tmp_path)
        assert "vercel" in result["deploy_targets"]


class TestMonorepoDetection:
    def test_detects_turborepo(self, tmp_path):
        (tmp_path / "turbo.json").write_text("{}")
        result = repo_scan.scan(tmp_path)
        assert "turborepo" in result["monorepo"]

    def test_detects_npm_workspaces(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"workspaces": ["packages/*"]}'
        )
        result = repo_scan.scan(tmp_path)
        assert "npm-workspaces" in result["monorepo"]


class TestResponsibilityMapping:
    def test_maps_pytest_to_qa(self, tmp_path):
        (tmp_path / "conftest.py").write_text("")
        result = repo_scan.scan(tmp_path)
        assert "qa" in result["responsibilities"]
        assert any("pytest" in r for r in result["responsibilities"]["qa"])

    def test_maps_docker_to_dm(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM node:18")
        result = repo_scan.scan(tmp_path)
        assert "dm" in result["responsibilities"]
        assert any("Docker" in r for r in result["responsibilities"]["dm"])

    def test_maps_openapi_to_skill(self, tmp_path):
        (tmp_path / "openapi.yaml").write_text("openapi: 3.0.0")
        result = repo_scan.scan(tmp_path)
        assert "skill" in result["responsibilities"]
        assert any("OpenAPI" in r for r in result["responsibilities"]["skill"])

    def test_empty_repo_no_responsibilities(self, tmp_path):
        result = repo_scan.scan(tmp_path)
        assert result["responsibilities"] == {}


class TestCLI:
    def test_outputs_json(self, tmp_path, capsys):
        (tmp_path / "app.py").write_text("")
        sys.argv = ["repo_scan.py", "--path", str(tmp_path)]
        code = repo_scan.main()
        assert code == 0
        output = json.loads(capsys.readouterr().out)
        assert "languages" in output

    def test_save_flag(self, tmp_path, capsys):
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        (tmp_path / "app.py").write_text("")
        sys.argv = ["repo_scan.py", "--path", str(tmp_path), "--save"]
        code = repo_scan.main()
        assert code == 0
        assert (squid / ".repo-scan.json").exists()

    def test_invalid_path(self, capsys):
        sys.argv = ["repo_scan.py", "--path", "/nonexistent/path"]
        code = repo_scan.main()
        assert code == 2


class TestScanCurrentRepo:
    def test_detects_python_in_squidsquad(self):
        """Scanning the actual SquidSquad repo should detect Python."""
        result = repo_scan.scan()
        assert "python" in result["languages"]


class TestTestStrategyDetection:
    """Unit-testing-strategy detection (task #12450) — framework + run command + location."""

    # --- run command / framework, ordered by ecosystem ---

    def test_pytest_via_ini(self, tmp_path):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "pytest"
        assert ts["run_command"] == "pytest"
        assert ts["detected"] is True

    def test_pytest_via_conftest(self, tmp_path):
        (tmp_path / "conftest.py").write_text("")
        assert repo_scan.detect_test_strategy(tmp_path)["framework"] == "pytest"

    def test_pytest_via_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
        assert repo_scan.detect_test_strategy(tmp_path)["run_command"] == "pytest"

    def test_pytest_via_setup_cfg(self, tmp_path):
        (tmp_path / "setup.cfg").write_text("[tool:pytest]\n")
        assert repo_scan.detect_test_strategy(tmp_path)["framework"] == "pytest"

    def test_pytest_via_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest==8.0\n")
        assert repo_scan.detect_test_strategy(tmp_path)["framework"] == "pytest"

    def test_node_explicit_test_script(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest --coverage"}})
        )
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["run_command"] == "npm test"
        assert ts["framework"] == "jest"  # inferred from the script body

    def test_node_test_script_unknown_tool(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "node ./run-tests.js"}})
        )
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["run_command"] == "npm test"
        assert ts["framework"] == "npm"  # falls back to npm when tool unrecognised

    def test_node_dep_without_script(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"devDependencies": {"vitest": "^1.0"}})
        )
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "vitest"
        assert ts["run_command"] == "npx vitest"

    def test_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/x\n")
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "go test"
        assert ts["run_command"] == "go test ./..."

    def test_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname='x'\n")
        assert repo_scan.detect_test_strategy(tmp_path)["run_command"] == "cargo test"

    def test_maven(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "junit"
        assert ts["run_command"] == "mvn test"

    def test_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
        assert repo_scan.detect_test_strategy(tmp_path)["run_command"] == "./gradlew test"

    def test_ruby_rspec(self, tmp_path):
        (tmp_path / "Gemfile").write_text("gem 'rspec'\n")
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "rspec"
        assert ts["run_command"] == "bundle exec rspec"

    def test_makefile_test_target(self, tmp_path):
        (tmp_path / "Makefile").write_text("test:\n\techo running\n")
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "make"
        assert ts["run_command"] == "make test"

    def test_makefile_assignment_not_target(self, tmp_path):
        # `test :=` is a variable assignment, not a target — must not match.
        (tmp_path / "Makefile").write_text("test := foo\n")
        assert repo_scan.detect_test_strategy(tmp_path)["run_command"] is None

    def test_bare_unittest_fallback(self, tmp_path):
        (tmp_path / "test_app.py").write_text("import unittest\n")
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts["framework"] == "unittest"
        assert ts["run_command"] == "python -m unittest discover"

    def test_explicit_script_beats_pytest(self, tmp_path):
        # Polyglot: an explicit package.json test script wins over a pytest signal.
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest"}})
        )
        assert repo_scan.detect_test_strategy(tmp_path)["run_command"] == "npm test"

    # --- location ---

    def test_location_conventional_dir(self, tmp_path):
        (tmp_path / "tests").mkdir()
        assert repo_scan.detect_test_strategy(tmp_path)["location"] == "tests/"

    def test_location_one_level_deep(self, tmp_path):
        (tmp_path / "src" / "tests").mkdir(parents=True)
        assert repo_scan.detect_test_strategy(tmp_path)["location"] == "src/tests/"

    def test_location_colocated_pattern(self, tmp_path):
        (tmp_path / "main_test.go").write_text("package x\n")
        assert "co-located" in repo_scan.detect_test_strategy(tmp_path)["location"]

    def test_location_skips_ignored_dirs(self, tmp_path):
        nm = tmp_path / "node_modules" / "tests"
        nm.mkdir(parents=True)
        assert repo_scan.detect_test_strategy(tmp_path)["location"] is None

    # --- coverage ---

    def test_coverage_coveragerc(self, tmp_path):
        (tmp_path / ".coveragerc").write_text("[run]\n")
        assert repo_scan.detect_test_strategy(tmp_path)["coverage"] == "coverage.py"

    def test_coverage_pytest_cov_dep(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pytest-cov\n")
        assert repo_scan.detect_test_strategy(tmp_path)["coverage"] == "coverage.py"

    # --- empty / negative ---

    def test_empty_repo_not_detected(self, tmp_path):
        ts = repo_scan.detect_test_strategy(tmp_path)
        assert ts == {
            "framework": None,
            "run_command": None,
            "location": None,
            "coverage": None,
            "detected": False,
        }

    def test_scan_includes_test_strategy(self, tmp_path):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        (tmp_path / "tests").mkdir()
        result = repo_scan.scan(tmp_path)
        assert result["test_strategy"]["framework"] == "pytest"
        assert result["test_strategy"]["location"] == "tests/"
