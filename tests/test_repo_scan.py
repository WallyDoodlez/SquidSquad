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
