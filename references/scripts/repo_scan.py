#!/usr/bin/env python3
"""SquidSquad repo scanner — detect project tech stack mechanically.

Scans the repository for languages, frameworks, test tools, CI/CD,
deployment targets, and package managers. Outputs structured JSON.
No LLM needed — pure file detection.

Usage:
    python scripts/repo_scan.py                    # Scan current repo
    python scripts/repo_scan.py --path /some/repo  # Scan specific path
    python scripts/repo_scan.py --save             # Save to .squidsquad/.repo-scan.json
    python scripts/repo_scan.py --help

Exit codes:
    0 — success
    2 — usage error
"""

import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# Directories to skip during scanning
SKIP_DIRS = {
    ".git", "node_modules", "vendor", ".squidsquad", "__pycache__",
    "dist", "build", "out", ".next", ".nuxt", ".venv", "venv",
    "env", ".tox", "target", "coverage", ".cache",
}

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Language detection by file extension
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
}

# Package manager detection
PACKAGE_FILES = {
    "package.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "pyproject.toml": "pip",
    "setup.py": "pip",
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "Cargo.toml": "cargo",
    "go.mod": "go",
    "Gemfile": "bundler",
    "composer.json": "composer",
    "pom.xml": "maven",
    "build.gradle": "gradle",
}

# Framework detection (file presence or package.json dependency)
FRAMEWORK_FILES = {
    "next.config.js": "nextjs",
    "next.config.ts": "nextjs",
    "next.config.mjs": "nextjs",
    "nuxt.config.ts": "nuxt",
    "nuxt.config.js": "nuxt",
    "svelte.config.js": "svelte",
    "angular.json": "angular",
    "vite.config.ts": "vite",
    "vite.config.js": "vite",
    "webpack.config.js": "webpack",
    "tailwind.config.js": "tailwind",
    "tailwind.config.ts": "tailwind",
    "tsconfig.json": "typescript",
    "manage.py": "django",
    "app.py": "flask",
}

# CI/CD detection
CI_FILES = {
    ".github/workflows": "github-actions",
    "Jenkinsfile": "jenkins",
    ".gitlab-ci.yml": "gitlab-ci",
    ".circleci": "circleci",
    ".travis.yml": "travis",
    "azure-pipelines.yml": "azure-pipelines",
}

# Test framework detection
TEST_FILES = {
    "jest.config.js": "jest",
    "jest.config.ts": "jest",
    "vitest.config.ts": "vitest",
    "vitest.config.js": "vitest",
    "playwright.config.ts": "playwright",
    "playwright.config.js": "playwright",
    "cypress.config.js": "cypress",
    "cypress.config.ts": "cypress",
    "pytest.ini": "pytest",
    "setup.cfg": "pytest",  # may contain pytest config
    "conftest.py": "pytest",
    "Cargo.toml": "cargo-test",  # rust has built-in tests
}

# Conventional unit-test directory names (checked at repo root and one level in).
TEST_LOCATION_DIRS = ("tests", "test", "spec", "__tests__")

# Test file-name conventions: (prefix, suffix, human label). Empty prefix means
# "suffix only". Used to spot co-located tests when no conventional dir exists.
TEST_FILE_PATTERNS = (
    ("test_", ".py", "test_*.py"),
    ("", "_test.py", "*_test.py"),
    ("", ".test.ts", "*.test.ts"),
    ("", ".test.tsx", "*.test.tsx"),
    ("", ".test.js", "*.test.js"),
    ("", ".spec.ts", "*.spec.ts"),
    ("", ".spec.js", "*.spec.js"),
    ("", "_test.go", "*_test.go"),
    ("", "Test.java", "*Test.java"),
    ("", "_spec.rb", "*_spec.rb"),
)

# Coverage tooling markers (file presence).
COVERAGE_FILES = {
    ".coveragerc": "coverage.py",
    "codecov.yml": "codecov",
    ".codecov.yml": "codecov",
    ".nycrc": "nyc",
    ".nycrc.json": "nyc",
}

# Deploy target detection
DEPLOY_FILES = {
    "Dockerfile": "docker",
    "docker-compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
    "vercel.json": "vercel",
    "netlify.toml": "netlify",
    "fly.toml": "fly",
    "railway.json": "railway",
    "app.yaml": "gcp-app-engine",
    "serverless.yml": "serverless",
    "sam.template.yaml": "aws-sam",
    "Procfile": "heroku",
}

# Documentation detection
DOC_FILES = {
    ".storybook": "storybook",
    "docs/": "docs",
    "openapi.yaml": "openapi",
    "openapi.json": "openapi",
    "swagger.yaml": "openapi",
    "swagger.json": "openapi",
    "mkdocs.yml": "mkdocs",
    "docusaurus.config.js": "docusaurus",
}

# Monorepo detection
MONOREPO_FILES = {
    "lerna.json": "lerna",
    "pnpm-workspace.yaml": "pnpm-workspaces",
    "turbo.json": "turborepo",
    "nx.json": "nx",
}

# Role responsibility mapping
ROLE_RESPONSIBILITIES = {
    "npm": {"dm": "Own npm publish on version bumps"},
    "pip": {"dm": "Own PyPI publish on version bumps"},
    "cargo": {"dm": "Own crates.io publish on version bumps"},
    "docker": {"dm": "Own Docker image build and push"},
    "docker-compose": {"dm": "Maintain docker-compose for local dev"},
    "github-actions": {"dm": "Own CI/CD workflow maintenance"},
    "gitlab-ci": {"dm": "Own CI/CD pipeline maintenance"},
    "jest": {"qa": "Run Jest as primary test suite"},
    "vitest": {"qa": "Run Vitest as primary test suite"},
    "pytest": {"qa": "Run pytest as primary test suite"},
    "playwright": {"qa": "Run Playwright for E2E tests"},
    "cypress": {"qa": "Run Cypress for E2E tests"},
    "openapi": {"skill": "Maintain OpenAPI spec accuracy"},
    "storybook": {"designer": "Maintain Storybook stories"},
    "vercel": {"dm": "Own Vercel deployment"},
    "netlify": {"dm": "Own Netlify deployment"},
    "fly": {"dm": "Own Fly.io deployment"},
    "nextjs": {"skill": "Follow Next.js conventions and app router patterns"},
    "django": {"skill": "Follow Django conventions and ORM patterns"},
    "tailwind": {"skill": "Use Tailwind utility classes for styling"},
    "typescript": {"skill": "Maintain strict TypeScript types"},
}


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def _count_extensions(root):
    """Count file extensions in the repo. Returns {ext: count}."""
    counts = {}
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            ext = Path(f).suffix.lower()
            if ext:
                counts[ext] = counts.get(ext, 0) + 1
    return counts


def _check_file_exists(root, name):
    """Check if a file or directory exists at root level."""
    path = Path(root) / name
    return path.exists()


def _check_package_json_deps(root, *dep_names):
    """Check if package.json contains specific dependencies."""
    pkg = Path(root) / "package.json"
    if not pkg.exists():
        return []
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        all_deps = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))
        return [d for d in dep_names if d in all_deps]
    except (json.JSONDecodeError, OSError):
        return []


def _check_python_deps(root, *dep_names):
    """Check if requirements.txt or pyproject.toml contains specific Python packages."""
    found = []
    # Check requirements.txt
    req = Path(root) / "requirements.txt"
    if req.exists():
        try:
            text = req.read_text(encoding="utf-8").lower()
            for dep in dep_names:
                if dep.lower() in text:
                    found.append(dep)
        except OSError:
            pass
    # Check pyproject.toml [project.dependencies] or [tool.poetry.dependencies]
    pyp = Path(root) / "pyproject.toml"
    if pyp.exists():
        try:
            text = pyp.read_text(encoding="utf-8").lower()
            for dep in dep_names:
                if dep.lower() in text and dep not in found:
                    found.append(dep)
        except OSError:
            pass
    return found


def _file_contains(root, name, needle):
    """True if file ``name`` exists at root and contains ``needle`` (case-insensitive)."""
    path = Path(root) / name
    if not path.exists():
        return False
    try:
        return needle.lower() in path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False


def _read_package_json_script(root, name):
    """Return the package.json ``scripts.<name>`` command string, or None."""
    pkg = Path(root) / "package.json"
    if not pkg.exists():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        val = data.get("scripts", {}).get(name)
        return val if isinstance(val, str) and val.strip() else None
    except (json.JSONDecodeError, OSError):
        return None


def _makefile_has_test_target(root):
    """True if a Makefile defines a ``test:`` target."""
    for name in ("Makefile", "makefile", "GNUmakefile"):
        mk = Path(root) / name
        if not mk.exists():
            continue
        try:
            text = mk.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # A target line begins at column 0 with `test` then `:` (not `:=` assignment).
        if re.search(r"(?m)^test\s*:(?!=)", text):
            return True
    return False


def _framework_from_command(command):
    """Best-effort: name the test framework referenced by a run command string."""
    cmd = (command or "").lower()
    for tool in ("jest", "vitest", "playwright", "cypress", "mocha", "ava",
                 "jasmine", "pytest"):
        if tool in cmd:
            return tool
    return None


def _has_python_test_files(root):
    """Bounded walk: True if any ``test_*.py`` / ``*_test.py`` file exists."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py") and (f.startswith("test_") or f.endswith("_test.py")):
                return True
    return False


def _detect_test_location(root):
    """Detect the repo's test-location convention. Returns a label string or None."""
    root = Path(root)
    if not root.is_dir():
        return None
    # Conventional test directory at repo root.
    for dirname in TEST_LOCATION_DIRS:
        if (root / dirname).is_dir():
            return dirname + "/"
    # One level deep (e.g. src/tests, app/__tests__).
    for child in sorted(root.iterdir()):
        if child.is_dir() and child.name not in SKIP_DIRS:
            for dirname in TEST_LOCATION_DIRS:
                if (child / dirname).is_dir():
                    return f"{child.name}/{dirname}/"
    # Co-located file-name conventions (bounded walk).
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            for prefix, suffix, label in TEST_FILE_PATTERNS:
                if (not prefix or f.startswith(prefix)) and f.endswith(suffix):
                    return f"{label} (co-located)"
    return None


def _detect_coverage(root):
    """Detect coverage tooling. Returns a tool name or None."""
    for fname, tool in COVERAGE_FILES.items():
        if _check_file_exists(root, fname):
            return tool
    if _check_python_deps(root, "pytest-cov", "coverage"):
        return "coverage.py"
    if _check_package_json_deps(root, "nyc", "c8"):
        return "nyc"
    return None


def _detect_test_run(root):
    """Detect the primary test framework + run command. Returns (framework, command) or (None, None).

    Ordered by signal strength: an explicit ``package.json`` test script or a
    pytest config beats a language default, which beats a Makefile wrapper,
    which beats the bare-unittest fallback. First match wins.
    """
    root = Path(root)

    # 1. Node — explicit author intent via package.json scripts.test.
    script = _read_package_json_script(root, "test")
    if script:
        return (_framework_from_command(script) or "npm", "npm test")

    # 2. Python — pytest signalled by config/dep/marker.
    if (_check_file_exists(root, "pytest.ini")
            or _check_file_exists(root, "conftest.py")
            or bool(_check_python_deps(root, "pytest"))
            or _file_contains(root, "setup.cfg", "[tool:pytest]")
            or _file_contains(root, "pyproject.toml", "[tool.pytest")):
        return ("pytest", "pytest")

    # 3. Go — built-in testing when a module is present.
    if _check_file_exists(root, "go.mod"):
        return ("go test", "go test ./...")

    # 4. Rust — built-in testing.
    if _check_file_exists(root, "Cargo.toml"):
        return ("cargo test", "cargo test")

    # 5. Java/JVM.
    if _check_file_exists(root, "pom.xml"):
        return ("junit", "mvn test")
    if _check_file_exists(root, "build.gradle") or _check_file_exists(root, "build.gradle.kts"):
        return ("gradle", "./gradlew test")

    # 6. Ruby.
    if _check_file_exists(root, "Gemfile"):
        if _file_contains(root, "Gemfile", "rspec"):
            return ("rspec", "bundle exec rspec")
        return ("minitest", "rake test")

    # 7. Node test-runner dep without an explicit script.
    node_tool = (_check_package_json_deps(root, "jest", "vitest", "mocha", "ava")
                 or [None])[0]
    if node_tool:
        return (node_tool, f"npx {node_tool}")

    # 8. Makefile test target (generic wrapper).
    if _makefile_has_test_target(root):
        return ("make", "make test")

    # 9. Bare Python unittest (test files present, no pytest).
    if _has_python_test_files(root):
        return ("unittest", "python -m unittest discover")

    return (None, None)


def detect_test_strategy(root=None):
    """Detect the repo's unit-testing strategy.

    Returns a dict ``{framework, run_command, location, coverage, detected}``.
    ``detected`` is True when at least one of framework / run_command / location
    was found — the installer uses it to decide whether to seed the L4 Project
    Context or fall back to asking the human (task #12450).
    """
    if root is None:
        root = REPO_ROOT
    framework, run_command = _detect_test_run(root)
    location = _detect_test_location(root)
    coverage = _detect_coverage(root)
    return {
        "framework": framework,
        "run_command": run_command,
        "location": location,
        "coverage": coverage,
        "detected": bool(framework or run_command or location),
    }


def scan(root=None):
    """Scan a repository and return structured detection results.

    Returns dict with: languages, package_managers, frameworks, ci_cd,
    test_frameworks, deploy_targets, documentation, monorepo,
    responsibilities (per-role mapping).
    """
    if root is None:
        root = REPO_ROOT
    root = Path(root)

    result = {
        "languages": [],
        "package_managers": [],
        "frameworks": [],
        "ci_cd": [],
        "test_frameworks": [],
        "test_strategy": {},
        "deploy_targets": [],
        "documentation": [],
        "monorepo": [],
        "responsibilities": {},
    }

    # Language detection
    ext_counts = _count_extensions(root)
    detected_langs = set()
    for ext, lang in LANGUAGE_EXTENSIONS.items():
        if ext_counts.get(ext, 0) > 0:
            detected_langs.add(lang)
    result["languages"] = sorted(detected_langs)

    # Package manager detection
    for filename, manager in PACKAGE_FILES.items():
        if _check_file_exists(root, filename):
            if manager not in result["package_managers"]:
                result["package_managers"].append(manager)

    # Framework detection
    detected_frameworks = set()
    for filename, framework in FRAMEWORK_FILES.items():
        if _check_file_exists(root, filename):
            detected_frameworks.add(framework)
    # Also check package.json for common frameworks
    pkg_deps = _check_package_json_deps(
        root, "react", "vue", "svelte", "next", "nuxt",
        "express", "fastify", "nestjs", "tailwindcss",
    )
    for dep in pkg_deps:
        fw_map = {"react": "react", "vue": "vue", "next": "nextjs",
                  "nuxt": "nuxt", "express": "express", "fastify": "fastify",
                  "nestjs": "nestjs", "tailwindcss": "tailwind"}
        if dep in fw_map:
            detected_frameworks.add(fw_map[dep])
    # Check Python deps for frameworks not detectable by file presence
    py_deps = _check_python_deps(root, "fastapi", "flask", "django")
    for dep in py_deps:
        detected_frameworks.add(dep)
    result["frameworks"] = sorted(detected_frameworks)

    # CI/CD detection
    for path_name, ci_system in CI_FILES.items():
        if _check_file_exists(root, path_name):
            result["ci_cd"].append(ci_system)

    # Test framework detection
    detected_tests = set()
    for filename, framework in TEST_FILES.items():
        if _check_file_exists(root, filename):
            detected_tests.add(framework)
    # Check package.json for test deps
    test_deps = _check_package_json_deps(
        root, "jest", "vitest", "playwright", "cypress", "mocha",
    )
    for dep in test_deps:
        detected_tests.add(dep)
    result["test_frameworks"] = sorted(detected_tests)

    # Unit-testing strategy detection (framework + run command + location).
    result["test_strategy"] = detect_test_strategy(root)

    # Deploy target detection
    for filename, target in DEPLOY_FILES.items():
        if _check_file_exists(root, filename):
            if target not in result["deploy_targets"]:
                result["deploy_targets"].append(target)

    # Documentation detection
    for path_name, doc_type in DOC_FILES.items():
        if _check_file_exists(root, path_name):
            if doc_type not in result["documentation"]:
                result["documentation"].append(doc_type)

    # Monorepo detection
    for filename, tool in MONOREPO_FILES.items():
        if _check_file_exists(root, filename):
            result["monorepo"].append(tool)
    # Also check package.json for workspaces
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "workspaces" in data:
                if "npm-workspaces" not in result["monorepo"]:
                    result["monorepo"].append("npm-workspaces")
        except (json.JSONDecodeError, OSError):
            pass

    # Build responsibilities mapping
    all_detected = set()
    all_detected.update(result["package_managers"])
    all_detected.update(result["frameworks"])
    all_detected.update(result["ci_cd"])
    all_detected.update(result["test_frameworks"])
    all_detected.update(result["deploy_targets"])
    all_detected.update(result["documentation"])

    responsibilities = {}  # role -> [responsibility]
    for detection in all_detected:
        if detection in ROLE_RESPONSIBILITIES:
            for role, resp in ROLE_RESPONSIBILITIES[detection].items():
                if role not in responsibilities:
                    responsibilities[role] = []
                if resp not in responsibilities[role]:
                    responsibilities[role].append(resp)

    result["responsibilities"] = responsibilities

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    root = REPO_ROOT
    save = "--save" in args

    for i, a in enumerate(args):
        if a == "--path" and i + 1 < len(args):
            root = Path(args[i + 1])
            if not root.exists():
                print(f"ERROR: Path does not exist: {root}", file=sys.stderr)
                return 2

    result = scan(root)
    output = json.dumps(result, indent=2)
    print(output)

    if save:
        save_path = Path(root) / ".squidsquad" / ".repo-scan.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(output + "\n", encoding="utf-8")
        print(f"Saved to {save_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
