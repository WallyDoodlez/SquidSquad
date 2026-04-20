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
    "fastapi": "fastapi",
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
