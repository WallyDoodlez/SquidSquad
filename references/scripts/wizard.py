#!/usr/bin/env python3
"""SquidSquad install wizard — mechanical helpers for the installer agent.

The wizard is a prose runbook that a Claude session (the "installer agent",
Q-new21) follows interactively. This script owns the *mechanical* pieces:
prerequisite checks, re-run detection, repo metadata probing, etc. Anything
that should be testable without talking to an LLM lives here. The intent
classifier, the setup_requirements walker, and the natural conversation
live in the prose runbook and use Claude's judgement.

Commands:
    python scripts/wizard.py check-gh              # Step 0
    python scripts/wizard.py check-existing        # Step 0b
    python scripts/wizard.py repo-info [--git-dir] # Step 1
    python scripts/wizard.py project-name-default  # Step 1
    python scripts/wizard.py build-config-md FILE  # Step 7 — print new
                                                   # config.md from a JSON
                                                   # install spec on disk
    python scripts/wizard.py scaffold FILE [DIR]   # Step 7 — write the
                                                   # full .squidsquad/ tree
                                                   # from a JSON install spec
    python scripts/wizard.py ensure-labels         # Step 7 — seed every
                                                   # required GH label if
                                                   # absent (idempotent)
    python scripts/wizard.py list-issues-by-label  # list issue numbers
                                                   # with a given label
    python scripts/wizard.py migrate-label         # rewrite one label to
                                                   # another on every
                                                   # issue that carries it
    python scripts/wizard.py migrate-labels-staged # staged migration with
                                                   # preflight + dry-run +
                                                   # execute + postflight +
                                                   # optional cleanup
    python scripts/wizard.py --help

Every command prints JSON on stdout and non-JSON errors on stderr. The
installer agent parses the JSON and drives the user conversation.

Exit codes:
    0 — success, JSON on stdout
    1 — operational failure (still prints JSON with `ok: false` + reason)
    2 — usage error (no JSON, plain text on stderr)
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
PRESETS_DIR = REPO_ROOT / "references" / "presets"

# Re-run detection — actions the installer agent can take
RERUN_ACTIONS = ("abort", "regenerate", "full-rebuild")

# Legacy project type → L3 variant mapping. Retained for backward compat
# with project types not yet backed by a preset manifest (e.g. ios, android).
# New code should use load_preset_manifest() + domain_variants instead (#6581).
PROJECT_TYPE_PRESETS = {
    "ios": "ios",
    "android": "android",
    "multi-platform": "fullstack",  # shared codebase concerns
    "web": "web",
    "pwa": "web",                   # PWA is a web specialization
    "backend": "web",               # backend shares web security/API concerns
    "fullstack": "fullstack",
    "skill": "skill",
    "custom": None,                 # no L3 preset
}


def load_preset_manifest(preset_id):
    """Load a preset manifest YAML and return as dict.

    Returns None if the preset directory or manifest.yaml doesn't exist,
    or if yaml parsing fails.
    """
    manifest_path = PRESETS_DIR / preset_id / "manifest.yaml"
    if not manifest_path.exists():
        return None
    try:
        import yaml
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_domain_variants(preset_id):
    """Resolve per-role domain variants from a preset manifest.

    Returns a dict mapping role → variant (e.g. {"dev": "skill", "pm": "skill"}).
    Returns empty dict if the preset has no domain_variants or doesn't exist.
    """
    manifest = load_preset_manifest(preset_id)
    if manifest is None:
        return {}
    return manifest.get("domain_variants", {}) or {}

# Human-readable labels for project type selection
PROJECT_TYPE_LABELS = {
    "ios": "iOS (Swift/UIKit/SwiftUI)",
    "android": "Android (Kotlin/Java)",
    "multi-platform": "Multi-platform (React Native/Flutter/KMP)",
    "web": "Web (React/Vue/Angular/etc.)",
    "pwa": "Progressive Web App (service workers, offline-first)",
    "backend": "Backend (API/database/server-side)",
    "fullstack": "Full-stack (frontend + backend)",
    "skill": "Skill (Claude Code skills, probabilistic/deterministic)",
    "custom": "Custom (base agents only, no domain preset)",
}


# ---------------------------------------------------------------------------
# Step 0 — gh prerequisite check
# ---------------------------------------------------------------------------


def _run(cmd, *, timeout=30, **kwargs):
    """Thin subprocess.run wrapper — list form only, captures output.

    A default ``timeout`` of 30 seconds guards the wizard against hangs in
    ``gh`` and ``git`` (slow OAuth, captive-portal proxy, firewall drop without
    RST, GitHub Enterprise rate-limit delay). On timeout, returns a
    ``CompletedProcess`` with ``returncode=124`` so existing callers that
    inspect ``.returncode`` / ``.stdout`` / ``.stderr`` keep working without
    branching on exception types.

    Pass ``timeout=None`` (or a larger value) for call sites that legitimately
    take longer than 30 seconds.
    """
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
            **kwargs,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=124,
            stdout="",
            stderr=f"timeout after {timeout}s: {' '.join(str(c) for c in cmd[:2])}\n",
        )


def check_gh():
    """Check that the gh CLI is installed AND authenticated.

    Returns a dict with:
        ok: bool
        stage: "installed" | "authenticated" | "ready"
        message: str — one-line summary
        fix: list[str] — commands/steps the user should run to fix it
    """
    if shutil.which("gh") is None:
        return {
            "ok": False,
            "stage": "installed",
            "message": "gh CLI is not installed or not on PATH",
            "fix": [
                "Install GitHub CLI: https://cli.github.com/",
                "On macOS:   brew install gh",
                "On Windows: winget install --id GitHub.cli",
                "On Linux:   see https://github.com/cli/cli/blob/trunk/docs/install_linux.md",
                "After installing, run: gh auth login",
            ],
        }

    # gh is on PATH. Check auth.
    auth = _run(["gh", "auth", "status"])
    if auth.returncode != 0:
        return {
            "ok": False,
            "stage": "authenticated",
            "message": "gh is installed but not authenticated",
            "fix": [
                "Run: gh auth login",
                "Choose GitHub.com, HTTPS, and authenticate with a browser or token",
                "Make sure the 'repo' scope is granted",
                "Verify with: gh auth status",
            ],
        }

    return {
        "ok": True,
        "stage": "ready",
        "message": "gh is installed and authenticated",
        "fix": [],
    }


def preflight(base_dir=None):
    """Run all pre-flight checks before setup begins.

    Checks (in order):
    1. gh CLI installed and authenticated
    2. Current directory is a git repository
    3. Git remote exists

    Returns a dict with:
        ok: bool — all checks passed
        checks: list[dict] — individual check results
        message: str — summary
    """
    if base_dir is None:
        base_dir = REPO_ROOT
    base_dir = Path(base_dir)

    checks = []

    # 1. gh auth
    gh_result = check_gh()
    checks.append({"name": "gh_auth", "ok": gh_result["ok"],
                    "message": gh_result["message"]})
    if not gh_result["ok"]:
        return {"ok": False, "checks": checks,
                "message": f"Pre-flight failed: {gh_result['message']}"}

    # 2. git repo
    git_dir = base_dir / ".git"
    if not git_dir.exists():
        checks.append({"name": "git_repo", "ok": False,
                        "message": "not a git repository"})
        return {"ok": False, "checks": checks,
                "message": "Pre-flight failed: not a git repository."}
    checks.append({"name": "git_repo", "ok": True, "message": "git repo found"})

    # 3. git remote
    remote = _run(["git", "-C", str(base_dir), "remote", "-v"])
    if remote.returncode != 0 or not remote.stdout.strip():
        checks.append({"name": "git_remote", "ok": False,
                        "message": "no git remote detected"})
        return {"ok": False, "checks": checks,
                "message": "Pre-flight failed: no git remote detected."}
    checks.append({"name": "git_remote", "ok": True,
                    "message": "git remote found"})

    return {"ok": True, "checks": checks, "message": "Pre-flight passed."}


# ---------------------------------------------------------------------------
# Step 0b — re-run detection
# ---------------------------------------------------------------------------


def detect_existing_install(base_dir=None):
    """Check for an existing SquidSquad install at `base_dir/.squidsquad/`.

    Returns a dict with:
        exists: bool
        path: str — the absolute path checked
        contents: list[str] — top-level entries if it exists (roles, config, etc.)
        has_config: bool — whether config.md is present (indicates completed setup)
        has_roles: bool — whether at least one per-role directory exists
        actions: list[str] — the 3 legal re-run actions (same as RERUN_ACTIONS)
        default_action: str — "abort" — the safe default on the 3-way prompt

    This helper intentionally does NOT prompt the user — it reports state
    and lets the prose runbook drive the interactive 3-way prompt.
    """
    if base_dir is None:
        base_dir = REPO_ROOT
    base_dir = Path(base_dir)
    target = base_dir / ".squidsquad"

    if not target.exists() or not target.is_dir():
        return {
            "exists": False,
            "path": str(target),
            "contents": [],
            "has_config": False,
            "has_roles": False,
            "actions": list(RERUN_ACTIONS),
            "default_action": "abort",
        }

    # Catalogue what's inside so the agent can summarise for the user
    contents = sorted(p.name for p in target.iterdir() if not p.name.startswith("."))
    has_config = (target / "config.md").exists()
    # A per-role directory is any subdir containing a CLAUDE.md (deployed output)
    has_roles = any(
        (target / c / "CLAUDE.md").exists() or (target / c / "instructions.md").exists()
        for c in contents
        if (target / c).is_dir()
    )

    return {
        "exists": True,
        "path": str(target),
        "contents": contents,
        "has_config": has_config,
        "has_roles": has_roles,
        "actions": list(RERUN_ACTIONS),
        "default_action": "abort",
    }


def validate_rerun_action(action):
    """Return a normalised re-run action or None if invalid.

    Accepts variations: "1"/"2"/"3", full names, short-forms, and empty
    string (which maps to the default "abort" per Q8).
    """
    if action is None or action == "":
        return "abort"
    raw = str(action).strip().lower()
    # Numeric prompt answers (1=abort, 2=regenerate, 3=full-rebuild)
    numeric = {"1": "abort", "2": "regenerate", "3": "full-rebuild"}
    if raw in numeric:
        return numeric[raw]
    # Short-forms
    short = {
        "a": "abort",
        "r": "regenerate",
        "f": "full-rebuild",
        "rebuild": "full-rebuild",
        "fullrebuild": "full-rebuild",
        "full_rebuild": "full-rebuild",
    }
    if raw in short:
        return short[raw]
    if raw in RERUN_ACTIONS:
        return raw
    return None


# ---------------------------------------------------------------------------
# Step 1 — project details (auto-fill from gh repo view + git)
# ---------------------------------------------------------------------------


# Project names must be simple, cross-platform-safe identifiers.
_PROJECT_NAME_ALLOWED = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def is_valid_project_name(name):
    """Project name must be non-empty and reasonably path-safe."""
    if not isinstance(name, str):
        return False
    name = name.strip()
    if not name:
        return False
    if len(name) > 100:
        return False
    return bool(_PROJECT_NAME_ALLOWED.match(name))


def validate_interval(value, default=10):
    """Parse and validate the Ralph Loop interval (Step 5, TC-49..TC-52).

    Accepts any string-ish value the user might type. Returns a dict:

        {"ok": bool, "minutes": int | None, "reason": str | None}

    Rules:
      - Empty string or None -> ok with minutes=default
      - Whole integer >= 1 -> ok
      - Zero, negative, float-ish, or non-numeric -> not ok, with a
        user-facing reason the runbook can surface as a re-prompt
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return {
            "ok": True,
            "minutes": int(default),
            "reason": f"empty input — defaulting to {default} minutes",
        }

    raw = str(value).strip()
    # Reject float-looking input explicitly so "10.5" doesn't silently truncate
    if "." in raw or "," in raw:
        return {
            "ok": False,
            "minutes": None,
            "reason": f"{raw!r} must be a whole number of minutes",
        }
    try:
        minutes = int(raw)
    except ValueError:
        return {
            "ok": False,
            "minutes": None,
            "reason": f"{raw!r} is not a number — enter an integer minute count",
        }
    if minutes < 1:
        return {
            "ok": False,
            "minutes": None,
            "reason": f"interval must be at least 1 minute (got {minutes})",
        }
    return {"ok": True, "minutes": minutes, "reason": None}


def project_name_default(base_dir=None):
    """Best guess at the project name for the current install target.

    Order of preference:
        1. `gh repo view --json name` -> .name (authoritative if available)
        2. Current working-directory basename
    """
    if base_dir is None:
        base_dir = Path.cwd()
    base_dir = Path(base_dir)

    gh = _run(["gh", "repo", "view", "--json", "name"], cwd=str(base_dir))
    if gh.returncode == 0 and gh.stdout.strip():
        try:
            data = json.loads(gh.stdout)
            name = data.get("name", "").strip()
            if is_valid_project_name(name):
                return name
        except json.JSONDecodeError:
            pass

    return base_dir.resolve().name


def get_repo_info(base_dir=None):
    """Probe `gh repo view` for project + repo metadata.

    Returns a dict with:
        ok: bool — True if we got usable data
        source: "gh" | "git" | "none"
        project_name: str | None
        repo_slug: str | None   — e.g. "WallyDoodlez/SquidSquad"
        owner: str | None
        name: str | None
        description: str | None
        remote_url: str | None

    If gh is unreachable (wrong directory, no remote, no auth), falls back
    to `git remote get-url origin` and parses a best-effort slug. If that
    also fails, returns ok=False with source="none".
    """
    if base_dir is None:
        base_dir = Path.cwd()
    base_dir = Path(base_dir)

    gh = _run(
        ["gh", "repo", "view", "--json", "name,nameWithOwner,owner,description,url"],
        cwd=str(base_dir),
    )
    if gh.returncode == 0 and gh.stdout.strip():
        try:
            data = json.loads(gh.stdout)
            owner_obj = data.get("owner") or {}
            owner = owner_obj.get("login") if isinstance(owner_obj, dict) else None
            return {
                "ok": True,
                "source": "gh",
                "project_name": data.get("name"),
                "repo_slug": data.get("nameWithOwner"),
                "owner": owner,
                "name": data.get("name"),
                "description": data.get("description"),
                "remote_url": data.get("url"),
            }
        except json.JSONDecodeError:
            pass

    # Fallback: parse `git remote get-url origin`
    git = _run(["git", "remote", "get-url", "origin"], cwd=str(base_dir))
    if git.returncode == 0 and git.stdout.strip():
        url = git.stdout.strip()
        slug = _parse_github_slug(url)
        if slug:
            owner, name = slug.split("/", 1)
            return {
                "ok": True,
                "source": "git",
                "project_name": name,
                "repo_slug": slug,
                "owner": owner,
                "name": name,
                "description": None,
                "remote_url": url,
            }

    return {
        "ok": False,
        "source": "none",
        "project_name": None,
        "repo_slug": None,
        "owner": None,
        "name": None,
        "description": None,
        "remote_url": None,
    }


def _parse_github_slug(url):
    """Extract `owner/repo` from a git remote URL. Returns None on no match.

    Handles:
        https://github.com/alice/foo.git
        git@github.com:alice/foo.git
        ssh://git@github.com/alice/foo
    """
    if not url:
        return None
    # SSH form
    m = re.match(r"git@github\.com:([A-Za-z0-9._-]+/[A-Za-z0-9._-]+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    # HTTPS form
    m = re.match(
        r"https?://github\.com/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+?)(?:\.git)?/?$",
        url,
    )
    if m:
        return m.group(1)
    # ssh://git@github.com/... form
    m = re.match(
        r"ssh://git@github\.com/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+?)(?:\.git)?/?$",
        url,
    )
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Step 7 — config.md writer (Q-new17 schema)
# ---------------------------------------------------------------------------

# Q-new17 locks the new config.md schema under these top-level sections
# in this exact order. The writer always emits them in this order, even
# when a section is empty, so that downstream readers can rely on the
# layout.
_SECTION_ORDER = [
    "## Project",
    "## Preset",
    "## Agents",
    "## Tools",
    "## Loop",
    "## Flags",
]


# Fields that are part of the Agent line's inline alias, not the nested
# block. Ordered — the writer emits nested fields in this order.
_AGENT_NESTED_FIELD_ORDER = [
    "role",
    "variant",
    "iteration_mode",
    "stack",
    "test_command",
]


def apply_project_type(spec, project_type):
    """Apply a project type preset to an install spec.

    Reads the preset manifest's domain_variants field to assign per-role
    L3 variants. Falls back to legacy PROJECT_TYPE_PRESETS for project
    types not backed by a manifest. "custom" = no variant (L1+L2 only).

    Args:
        spec: the install spec dict (mutated in place).
        project_type: key from PROJECT_TYPE_PRESETS or a preset ID.

    Returns:
        Dict of {role: variant} applied (or None for custom/no variants).
    """
    spec["project_type"] = project_type

    if project_type == "custom":
        return None

    # Try manifest-driven resolution first (#6581)
    preset_id = spec.get("preset", "")
    domain_variants = resolve_domain_variants(preset_id) if preset_id else {}

    if domain_variants:
        # Manifest is the single authority for domain-to-agent mappings
        for agent in spec.get("agents", []):
            role = agent.get("role", "")
            variant = domain_variants.get(role)
            if variant:
                agent["variant"] = variant
        return domain_variants

    # Legacy fallback: uniform variant from PROJECT_TYPE_PRESETS
    variant = PROJECT_TYPE_PRESETS.get(project_type)
    if variant is None:
        return None

    for agent in spec.get("agents", []):
        role = agent.get("role", "")
        if role in ("dev", "pm", "qa", "dm"):
            agent["variant"] = variant
    return {role: variant for role in ("dev", "pm", "qa", "dm")}


def build_config_md(spec):
    """Render a new-schema config.md as a string from an install spec dict.

    The spec is the wizard's in-memory state at Step 7 review time. Shape:

        {
            "squidsquad_version": "0.15.0",
            "project": {
                "name": "my-app",
                "repo": "github.com/alice/my-app",
            },
            "preset": "software-dev",
            "agents": [
                {
                    "id": "pm",
                    "alias": "peggy",
                    "role": "pm",
                },
                {
                    "id": "be",
                    "alias": "be",
                    "role": "dev",
                    "variant": "be",
                    "stack": "FastAPI + Python 3.11 + pytest",
                    "test_command": "pytest tests/be",
                },
            ],
            "tools": {
                "dm.tool": "local_delivery",
            },
            "loop": {
                "interval_minutes": 10,
                "context_threshold": 70,
            },
            "flags": {
                "pr_flow": False,
                "improvement_scan": True,
                "vault_remember": True,
                "diagnostics": True,
            },
        }

    Returns the config.md text. Does NOT write to disk — callers persist
    the output themselves. Deterministic: same spec -> same bytes.

    Raises ValueError if required top-level fields are missing.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")

    for required in ("project", "preset", "agents", "tools", "loop", "flags"):
        if required not in spec:
            raise ValueError(f"spec missing required section: {required!r}")

    lines = []

    # --- Header ---
    version = spec.get("squidsquad_version", "0.0.0")
    lines.append("# SquidSquad Config")
    lines.append("")
    lines.append(f"- **SquidSquad Version**: {version}")
    lines.append("- **Tracker**: github-issues")
    lines.append("- **Architecture Version**: 2")  # v2 = #328 schema
    lines.append("")

    # --- ## Project ---
    lines.append("## Project")
    lines.append("")
    project = spec["project"] or {}
    project_name = project.get("name", "")
    project_repo = project.get("repo", "")
    lines.append(f"- **Name**: {project_name}")
    lines.append(f"- **Repo**: {project_repo}")
    if project.get("description"):
        lines.append(f"- **Description**: {project['description']}")
    if project.get("domain_context"):
        lines.append(f"- **Domain Context**: {project['domain_context']}")
    if project.get("conventions"):
        lines.append(f"- **Conventions**: {project['conventions']}")
    lines.append("")

    # --- ## Preset ---
    lines.append("## Preset")
    lines.append("")
    lines.append(f"- **Id**: {spec['preset']}")
    lines.append("")

    # --- ## Agents ---
    lines.append("## Agents")
    lines.append("")
    for agent in spec["agents"]:
        lines.extend(_render_agent(agent))
    lines.append("")

    # --- ## Tools ---
    lines.append("## Tools")
    lines.append("")
    for key, value in spec["tools"].items():
        if value is None or value == "":
            lines.append(
                f"- **{key}**: (unset — PM will configure on first use)"
            )
        else:
            lines.append(f"- **{key}**: {value}")
    if not spec["tools"]:
        lines.append("- (none)")
    lines.append("")

    # --- ## Loop ---
    lines.append("## Loop")
    lines.append("")
    loop = spec["loop"] or {}
    lines.append(f"- **Interval Minutes**: {loop.get('interval_minutes', 10)}")
    lines.append(
        f"- **Context Threshold**: {loop.get('context_threshold', 70)}"
    )
    lines.append("")

    # --- ## Flags ---
    lines.append("## Flags")
    lines.append("")
    flags = spec["flags"] or {}
    # Emit in deterministic order regardless of dict insertion
    for key in sorted(flags):
        lines.append(f"- **{_flag_label(key)}**: {_render_bool(flags[key])}")
    if not flags:
        lines.append("- (none)")
    lines.append("")

    # --- ## Git Branches ---
    lines.append("## Git Branches")
    lines.append("")
    branches = spec.get("git_branches") or {}
    lines.append(f"- **Working Branch**: {branches.get('working', 'main')}")
    lines.append(f"- **State Branch**: {branches.get('state', 'squid-squad')}")
    lines.append("")

    # --- ## Forge Backend ---
    lines.append("## Forge Backend")
    lines.append("")
    forge = spec.get("forge_backend") or {}
    lines.append(f"- **Provider**: {forge.get('provider', 'github')}")
    lines.append(f"- **Endpoint**: {forge.get('endpoint', 'https://api.github.com')}")
    if forge.get("owner"):
        lines.append(f"- **Owner**: {forge['owner']}")
    if forge.get("repo"):
        lines.append(f"- **Repo**: {forge['repo']}")
    lines.append("")

    # --- ## Model Routing ---
    lines.append("## Model Routing")
    lines.append("")
    routing = spec.get("model_routing") or {}
    lines.append(f"- **Default Model**: {routing.get('model', 'claude')}")
    lines.append(f"- **Research Model**: {routing.get('research_model', 'claude')}")
    lines.append("- **Discussion Prep Model**: claude")
    lines.append("- **Test Plan Model**: claude")
    lines.append("- **QA Execution Model**: claude")
    lines.append("- **Comprehension Model**: claude")
    lines.append("- **Improvement Scan Model**: claude")
    lines.append("- **Code Review Model**: claude")
    lines.append("- **Fallback Model**: claude")
    lines.append("- **API Timeout Seconds**: 120")
    lines.append("")

    # Ensure exactly one trailing newline
    text = "\n".join(lines).rstrip("\n") + "\n"
    return text


def _render_agent(agent):
    """Emit the lines for a single agent entry (Q-new17)."""
    if not isinstance(agent, dict):
        raise ValueError(f"agent must be a mapping, got {type(agent).__name__}")
    if "id" not in agent:
        raise ValueError(f"agent missing required 'id': {agent!r}")
    if "role" not in agent:
        raise ValueError(
            f"agent {agent['id']!r} missing required 'role' field"
        )

    lines = []
    alias = agent.get("alias", agent["id"])
    lines.append(f"- **{agent['id']}**: {alias}")

    for field in _AGENT_NESTED_FIELD_ORDER:
        if field not in agent:
            continue
        value = agent[field]
        if value is None or value == "":
            continue
        lines.append(f"  - {field}: {_quote_if_needed(value)}")

    # `setup:` block — only emitted if non-empty
    setup = agent.get("setup") or {}
    if setup:
        lines.append("  - setup:")
        for key in sorted(setup):
            lines.append(f"    - {key}: {_quote_if_needed(setup[key])}")

    return lines


def _quote_if_needed(value):
    """Wrap string values with whitespace or punctuation in double quotes.

    Matches Q-new17 examples (`stack: "FastAPI + Python 3.11 + pytest"`).
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    if not isinstance(value, str):
        return str(value)
    # Quote if the value contains a space, quote, colon, or comma
    if any(ch in value for ch in (" ", '"', ":", ",", "#")):
        return f'"{value}"'
    return value


def _render_bool(value):
    """Render a boolean flag the way existing config.md uses — yes/no."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _flag_label(key):
    """Turn a snake_case flag key into a Title Case display label."""
    return " ".join(part.capitalize() for part in key.replace("-", "_").split("_"))


# ---------------------------------------------------------------------------
# Step 7 — .squidsquad/ scaffolder
# ---------------------------------------------------------------------------

# Default working-state.md content written at install time. Agents update
# this themselves during their Ralph Loop — the scaffolder just seeds it.
_DEFAULT_WORKING_STATE = """\
# Working State

- **Task**: none
- **Status**: none
- **Quiet Cycle Counter**: 0
"""


def _detect_remote_url(repo_dir):
    """Detect the git remote URL for cloning.

    Returns the origin URL string, or None if not available.
    """
    result = _run(["git", "remote", "get-url", "origin"], cwd=str(repo_dir))
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


INSTALL_SPEC_FILENAME = ".install-spec.json"


def save_install_spec(spec, target_root):
    """Save install spec to .squidsquad/.install-spec.json.

    The spec is the wizard's in-memory state — saved for reproducibility,
    upgrade re-use, and --yes mode. Committed to git so other team members
    can see what was configured.

    Returns the path written.
    """
    target_root = Path(target_root)
    squid_dir = target_root / ".squidsquad"
    squid_dir.mkdir(parents=True, exist_ok=True)
    spec_path = squid_dir / INSTALL_SPEC_FILENAME
    spec_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return str(spec_path)


def load_install_spec(target_root):
    """Load install spec from .squidsquad/.install-spec.json.

    Returns the spec dict, or None if the file does not exist.
    Raises ValueError if the file exists but is invalid JSON.
    """
    target_root = Path(target_root)
    spec_path = target_root / ".squidsquad" / INSTALL_SPEC_FILENAME
    if not spec_path.exists():
        return None
    raw = spec_path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON in {spec_path}: {e}") from e


def _write_l4_project_files(spec, project_dir, summary):
    """Write structured L4 project files from scan data in the spec (#6581).

    This is the mechanical half of the hybrid L4 writer. Writes stack details,
    test commands, and detected config as structured markdown. The WIZARD.md
    runbook adds qualitative content (conventions, patterns) afterward.

    Respects overwrite guards: existing files are preserved and recorded in
    summary["preserved"].
    """
    # Extract scan data from agents (test_command, stack are per-agent)
    scan_data = {}
    for agent in spec.get("agents", []):
        if agent.get("test_command"):
            scan_data["test_command"] = agent["test_command"]
        if agent.get("stack"):
            scan_data["stack"] = agent["stack"]

    project_info = spec.get("project", {})

    # shared-stack-details.md — detected tech stack and test commands
    stack_file = project_dir / "shared-stack-details.md"
    if stack_file.exists():
        summary.setdefault("preserved", []).append(str(stack_file))
    else:
        stack = scan_data.get("stack", "Not detected")
        test_cmd = scan_data.get("test_command", "Not detected")
        name = project_info.get("name", "Unknown")
        stack_file.write_text(
            f"## Project Stack Details — {name}\n\n"
            f"These details apply to all agents on this project.\n\n"
            f"### Stack\n\n- **Detected stack**: {stack}\n\n"
            f"### Test Command\n\n- **Test command**: `{test_cmd}`\n\n"
            f"### Conventions\n\n"
            f"_To be populated by the installer agent or human with "
            f"project-specific conventions, patterns, and preferences._\n",
            encoding="utf-8",
        )


def _copy_l4_seed_stubs(project_dir, summary):
    """Copy worker-*/verifier-* L4 seed stubs from references/sub-skills/project/.

    Only copies files that do not yet exist in project_dir (overwrite guard).
    Records newly-copied paths in summary["l4_stubs_copied"] and preserved
    paths in summary["preserved"].

    Per D6/D7 (sub-phase 6274.2): new installs get worker-responsibility.md,
    worker-instructions.md, worker-soul-directives.md, verifier-responsibility.md,
    verifier-instructions.md, verifier-soul-directives.md from seed templates.
    """
    seed_dir = REPO_ROOT / "references" / "sub-skills" / "project"
    if not seed_dir.is_dir():
        return  # Seed directory absent — silent skip

    copied = []
    for src in sorted(seed_dir.iterdir()):
        if not src.is_file():
            continue
        name = src.name
        # Only copy worker-* and verifier-* stubs; leave other seeds alone
        if not (name.startswith("worker-") or name.startswith("verifier-")):
            continue
        dest = project_dir / name
        if dest.exists():
            summary.setdefault("preserved", []).append(str(dest))
        else:
            shutil.copy2(src, dest)
            copied.append(str(dest))

    if copied:
        summary["l4_stubs_copied"] = copied


def scaffold_install(spec, target_root, overwrite_existing=False):
    """Write a full `.squidsquad/` tree from an install spec.

    This is the mechanical realisation of Step 7: everything the wizard
    actually puts on disk at the moment the user hits [P]roceed. It is
    deterministic, side-effects-only, and safe to re-run: existing SOUL.md
    and working-state.md files are never clobbered (they may contain the
    agent's customisations or in-progress state).

    Args:
        spec: the same install-spec dict `build_config_md` accepts.
        target_root: base directory that will contain `.squidsquad/`.
        overwrite_existing: if True, refuse-on-exist is skipped and
            CLAUDE.md templates are overwritten on every run. Working
            state and SOUL.md remain protected regardless — those are
            never overwritten even with the flag.

    Returns a dict summarising what was written:
        {
            "target": str,
            "squidsquad_dir": str,
            "config_md": str,
            "agents": [{id, role, claude_md, soul_md, working_state}, ...],
            "preserved": [...paths that already existed and were not overwritten],
            "created_dirs": [...paths of newly-created per-role directories],
        }

    Raises:
        ValueError — if `spec` is missing required fields (see
            build_config_md) or if an agent references a role identity
            that does not exist under `references/roles/`.
        FileExistsError — if `.squidsquad/` exists and `overwrite_existing`
            is False. The caller (the prose runbook) is responsible for
            the re-run detection + 3-way prompt, so this should only fire
            as a safety net.
    """
    # Delegate validation of spec shape to build_config_md so we have
    # a single source of truth for required sections.
    config_md_text = build_config_md(spec)

    target_root = Path(target_root).resolve()
    squid = target_root / ".squidsquad"

    if squid.exists() and not overwrite_existing:
        raise FileExistsError(
            f"{squid} already exists — pass overwrite_existing=True "
            f"or delete the directory first"
        )

    # Import compose.py lazily so tests that don't need the scaffolder
    # don't import it either.
    try:
        from compose import deploy_role  # same dir as wizard.py
    except ImportError:
        import sys as _sys
        _sys.path.insert(0, str(SCRIPT_DIR))
        from compose import deploy_role  # type: ignore

    squid.mkdir(parents=True, exist_ok=True)

    summary = {
        "target": str(target_root),
        "squidsquad_dir": str(squid),
        "config_md": None,
        "agents": [],
        "preserved": [],
        "created_dirs": [],
    }

    # 1. config.md
    config_path = squid / "config.md"
    if config_path.exists() and not overwrite_existing:
        summary["preserved"].append(str(config_path))
    else:
        config_path.write_text(config_md_text, encoding="utf-8")
    summary["config_md"] = str(config_path)

    # 1b. L4 project directory — create .squidsquad/project/ for project-local
    # L4 content. compose.py reads from here, not from references/sub-skills/project/.
    project_dir = squid / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # 1c. L4 structured files — write mechanically-detected project data (#6581).
    # These are the "structured" half of the hybrid L4 writer. The WIZARD.md
    # runbook adds qualitative notes (conventions, patterns) after scaffold.
    _write_l4_project_files(spec, project_dir, summary)

    # 1d. L4 seed stubs — copy worker-*/verifier-* stubs from
    # references/sub-skills/project/ to .squidsquad/project/ for new installs.
    # This absorbs #9925 deferred work per D6/D7. Existing files are preserved
    # (overwrite guard) so re-runs don't clobber operator customisations.
    _copy_l4_seed_stubs(project_dir, summary)

    # 2. Per-agent directories
    for agent in spec["agents"]:
        agent_id = agent["id"]
        role_identity = agent["role"]

        # Verify the role identity template exists before composing — a
        # friendlier error than whatever deploy_role would produce if the
        # entry file is missing.
        role_dir = REPO_ROOT / "references" / "roles" / role_identity
        if not (role_dir / "instructions.md").exists():
            raise ValueError(
                f"agent {agent_id!r} references unknown role identity "
                f"{role_identity!r}: no instructions.md at {role_dir}"
            )

        agent_dir = squid / agent_id
        was_new = not agent_dir.exists()
        agent_dir.mkdir(parents=True, exist_ok=True)
        if was_new:
            summary["created_dirs"].append(str(agent_dir))

        # CLAUDE.md — composed from role identity template + sub-skills.
        # deploy_role handles the compose/substitute/write pipeline.
        # When a variant is set, compose from the variant role (e.g. "dev-ios")
        # but output to the agent_id directory (e.g. "skill").
        variant = agent.get("variant")
        if variant:
            compose_name = f"{role_identity}-{variant}"
        else:
            compose_name = agent_id
        try:
            claude_path = deploy_role(compose_name, target_root=target_root,
                                      output_name=agent_id)
        except (SystemExit, Exception) as e:
            print(f"  WARNING: Failed to deploy {agent_id}: {e}", file=sys.stderr)
            summary["agents"].append({
                "id": agent_id, "role": role_identity,
                "claude_md": "FAILED", "soul_md": "FAILED",
                "working_state": "FAILED",
            })
            continue

        # SOUL.md — deploy_role wrote it if missing; honour existing files.
        # Seed with ### Project Context section from adaptive answers (#462).
        soul_path = agent_dir / "SOUL.md"
        domain_ctx = (spec.get("project") or {}).get("domain_context", "")
        if soul_path.exists() and domain_ctx:
            soul_text = soul_path.read_text(encoding="utf-8")
            # Replace placeholder text if section exists with stub content
            placeholder = "_Populated during setup. Describes what this project does, its tech stack, conventions, and key tools._"
            if placeholder in soul_text:
                soul_text = soul_text.replace(placeholder, domain_ctx)
                soul_path.write_text(soul_text, encoding="utf-8")
            elif "### Project Context" not in soul_text:
                # Section missing entirely — append it
                soul_text += f"\n### Project Context\n\n{domain_ctx}\n"
                soul_path.write_text(soul_text, encoding="utf-8")

        # Project-Specific Responsibilities — seed from repo scan if available
        scan_file = target_root / ".squidsquad" / ".repo-scan.json"
        if soul_path.exists() and scan_file.exists():
            try:
                scan_data = json.loads(scan_file.read_text(encoding="utf-8"))
                responsibilities = scan_data.get("responsibilities", {})
                role_resps = responsibilities.get(role_identity, [])
                if role_resps:
                    soul_text = soul_path.read_text(encoding="utf-8")
                    resp_placeholder = "_Populated during setup based on repo scan and human input. Preserved on upgrade._"
                    if resp_placeholder in soul_text:
                        resp_lines = "\n".join(f"- {r}" for r in role_resps)
                        soul_text = soul_text.replace(resp_placeholder, resp_lines)
                        soul_path.write_text(soul_text, encoding="utf-8")
            except (json.JSONDecodeError, OSError):
                pass

        # working-state.md — never overwrite
        ws_path = agent_dir / "working-state.md"
        if ws_path.exists():
            summary["preserved"].append(str(ws_path))
        else:
            ws_path.write_text(_DEFAULT_WORKING_STATE, encoding="utf-8")

        # Working directories that agents use to organise their own files
        for sub in ("iterations", "planning"):
            (agent_dir / sub).mkdir(parents=True, exist_ok=True)

        summary["agents"].append({
            "id": agent_id,
            "role": role_identity,
            "claude_md": str(claude_path),
            "soul_md": str(soul_path),
            "working_state": str(ws_path),
        })

    # 3. Create sibling clones for non-PM agents
    clone_paths = {}  # {agent_id: relative_path_string}
    non_pm_agents = [a for a in spec["agents"] if a["role"] != "pm"]
    if non_pm_agents:
        project_name = (spec.get("project") or {}).get("name") or target_root.name
        remote_url = _detect_remote_url(target_root)
        if remote_url:
            for agent in non_pm_agents:
                agent_id = agent["id"]
                clone_dir_name = f"{project_name}-{agent_id}"
                clone_dir = target_root.parent / clone_dir_name
                rel_path = f"../{clone_dir_name}"
                clone_paths[agent_id] = rel_path

                if clone_dir.exists() and (clone_dir / ".git").exists():
                    # Idempotent: clone already exists, skip
                    summary.setdefault("existing_clones", []).append(str(clone_dir))
                else:
                    try:
                        result = _run(
                            ["git", "clone", remote_url, str(clone_dir)],
                            timeout=None,
                        )
                        if result.returncode != 0:
                            print(
                                f"  WARNING: Failed to clone for {agent_id}: "
                                f"{result.stderr.strip()}",
                                file=sys.stderr,
                            )
                            continue
                        summary.setdefault("clones_created", []).append(str(clone_dir))
                    except Exception as e:
                        print(f"  WARNING: Clone failed for {agent_id}: {e}", file=sys.stderr)
                        continue

    # PM always maps to current directory
    for agent in spec["agents"]:
        if agent["role"] == "pm":
            clone_paths[agent["id"]] = "."

    # 4. Generate .local-config for health check and auto-boot
    try:
        from compose import generate_local_config
    except ImportError:
        pass
    else:
        all_roles = [a["id"] for a in spec["agents"]]
        generate_local_config(all_roles, target_root=target_root,
                              clone_paths=clone_paths)

    # 5. Copy skill commands to .claude/commands/ (#5888)
    ref_commands = target_root / "references" / "commands"
    claude_commands = target_root / ".claude" / "commands"
    if ref_commands.exists():
        claude_commands.mkdir(parents=True, exist_ok=True)
        for cmd_file in ref_commands.glob("*.md"):
            dest = claude_commands / cmd_file.name
            if not dest.exists():  # don't overwrite user customizations
                shutil.copy2(cmd_file, dest)

    # 6. Save install spec for reproducibility and upgrade re-use (#13)
    spec_path = save_install_spec(spec, target_root)
    summary["install_spec"] = spec_path

    return summary


# ---------------------------------------------------------------------------
# D4 upgrade step — dev→worker / qa→verifier migration (#6274.2)
# ---------------------------------------------------------------------------


def upgrade_install(base_dir=None):
    """Upgrade an existing .squidsquad/ install from dev/qa to worker/verifier.

    Runs BEFORE any other install/upgrade logic per D4.

    Returns a dict:
        {
            "ok": bool,
            "action": "no-op" | "migrated" | "error",
            "summary": str,   — human-readable one-line summary
            "migrated": list  — what was renamed/rewritten
        }

    Exit codes (for CLI callers):
        0 — success or no-op
        2 — partial migration detected (manual intervention required)
    """
    if base_dir is None:
        base_dir = REPO_ROOT
    base_dir = Path(base_dir).resolve()
    squid = base_dir / ".squidsquad"
    config_path = squid / "config.md"

    # --- Read current state ---
    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    # The legacy field name appears in two formats:
    #   v1 (arch v1 legacy): "- **Dev Agents**: skill"  (no bare "Dev Agents:")
    #   v2 (new schema):     "- Dev Agents: skill"      (rare/hypothetical)
    # Search for the field name string "Dev Agents" (case-sensitive) to catch
    # both. "Workers" covers both "**Workers**: ..." and "Workers: ..." forms.
    config_has_workers = "Workers" in config_text
    config_has_dev_agents = "Dev Agents" in config_text
    dir_worker_exists = (squid / "worker").is_dir()
    dir_dev_exists = (squid / "dev").is_dir()
    dir_verifier_exists = (squid / "verifier").is_dir()
    dir_qa_exists = (squid / "qa").is_dir()

    # --- Idempotency / partial-migration checks (D4 canonical rule) ---
    partial_mismatches = []
    if config_has_workers and config_has_dev_agents:
        partial_mismatches.append(
            "config.md has both 'Workers' and 'Dev Agents' fields"
        )
    if config_has_workers and dir_dev_exists and not dir_worker_exists:
        partial_mismatches.append(
            "config.md has 'Workers' but .squidsquad/dev/ still exists "
            "and .squidsquad/worker/ is missing"
        )
    if dir_worker_exists and config_has_dev_agents and not config_has_workers:
        partial_mismatches.append(
            ".squidsquad/worker/ exists but config.md still has 'Dev Agents' "
            "(no 'Workers' field)"
        )
    if dir_worker_exists and dir_dev_exists:
        partial_mismatches.append(
            "both .squidsquad/worker/ and .squidsquad/dev/ exist"
        )
    if dir_verifier_exists and dir_qa_exists:
        partial_mismatches.append(
            "both .squidsquad/verifier/ and .squidsquad/qa/ exist"
        )

    if partial_mismatches:
        mismatch_str = "; ".join(partial_mismatches)
        msg = (
            f"partial migration detected: {mismatch_str}; "
            f"manual intervention required"
        )
        print(msg, file=sys.stderr)
        return {
            "ok": False,
            "action": "error",
            "exit_code": 2,
            "summary": msg,
            "migrated": [],
        }

    # --- No-op check ---
    # Nothing installed at all (no dev/qa/worker/verifier dirs, no config fields)
    nothing_installed = (
        not dir_dev_exists and not dir_worker_exists
        and not dir_qa_exists and not dir_verifier_exists
        and not config_has_dev_agents and not config_has_workers
    )
    # Already fully migrated: both pairs complete
    worker_pair_complete = (
        config_has_workers and not config_has_dev_agents
        and dir_worker_exists and not dir_dev_exists
    )
    verifier_pair_complete = dir_verifier_exists and not dir_qa_exists
    already_done = worker_pair_complete and verifier_pair_complete

    if nothing_installed or already_done:
        return {
            "ok": True,
            "action": "no-op",
            "summary": "upgrade: nothing to migrate (already up to date)",
            "migrated": [],
        }

    migrated = []

    # --- 1. Rewrite config.md: Dev Agents → Workers ---
    # Handles both legacy v1 format ("**Dev Agents**: ...") and
    # hypothetical bare format ("Dev Agents: ...").
    if config_has_dev_agents and config_path.exists():
        # Replace bold form first (most common), then bare form
        new_text = config_text.replace("**Dev Agents**:", "**Workers**:")
        new_text = new_text.replace("Dev Agents:", "Workers:")
        tmp = config_path.with_suffix(".tmp")
        tmp.write_text(new_text, encoding="utf-8")
        tmp.replace(config_path)
        migrated.append("config.md: 'Dev Agents' -> 'Workers'")

    # --- 2. Rename .squidsquad/dev/ → .squidsquad/worker/ ---
    if dir_dev_exists and not dir_worker_exists:
        (squid / "dev").rename(squid / "worker")
        migrated.append(".squidsquad/dev/ -> .squidsquad/worker/")

    # --- 3. Rename .squidsquad/qa/ → .squidsquad/verifier/ ---
    if dir_qa_exists and not dir_verifier_exists:
        (squid / "qa").rename(squid / "verifier")
        migrated.append(".squidsquad/qa/ -> .squidsquad/verifier/")

    # --- 4. Update .harness-state.json agent keys ---
    state_path = squid / ".harness-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            agents = state.get("agents", {})
            changed = False
            # qa → verifier
            if "qa" in agents:
                agents["verifier"] = agents.pop("qa")
                changed = True
                migrated.append(".harness-state.json: agents.qa -> agents.verifier")
            # dev → worker (rare — variant keys like 'skill' are unchanged)
            if "dev" in agents:
                agents["worker"] = agents.pop("dev")
                changed = True
                migrated.append(".harness-state.json: agents.dev -> agents.worker")
            if changed:
                state["agents"] = agents
                tmp_state = state_path.with_suffix(".json.tmp")
                tmp_state.write_text(
                    json.dumps(state, indent=2) + "\n", encoding="utf-8"
                )
                tmp_state.replace(state_path)
        except (json.JSONDecodeError, OSError):
            pass  # Non-fatal: state file absent or malformed; skip key rename

    summary_str = (
        "upgrade: migrated — " + ", ".join(migrated)
        if migrated
        else "upgrade: no changes needed"
    )
    print(summary_str)
    return {
        "ok": True,
        "action": "migrated" if migrated else "no-op",
        "summary": summary_str,
        "migrated": migrated,
    }


def cmd_upgrade(args):
    """Run the dev→worker / qa→verifier upgrade step.

    Usage: wizard.py upgrade [target_dir]
    """
    target = args[0] if args else "."
    result = upgrade_install(target)
    exit_code = result.get("exit_code", 0 if result["ok"] else 1)
    _print_json(result)
    return exit_code


# ---------------------------------------------------------------------------
# Step 7 — GitHub label helpers (ensure + migrate)
# ---------------------------------------------------------------------------


def _tracker():
    """Import tracker.py lazily and return it.

    Tracker is the single source of truth for the label taxonomy. Importing
    lazily avoids a hard dependency when tests exercise unrelated helpers.
    """
    try:
        import tracker  # same dir as wizard.py
        return tracker
    except ImportError:
        sys.path.insert(0, str(SCRIPT_DIR))
        import tracker  # type: ignore
        return tracker


# Reasonable defaults per label category. Chosen to match GitHub's standard
# palette — labels that already exist on the repo keep their stored colour
# because `gh label create --force` only updates description/colour when
# the values explicitly differ.
_CATEGORY_DESCRIPTIONS = {
    "type": "Work type classification",
    "status": "Workflow state",
    "priority": "Priority level",
    "severity": "Issue severity",
    "role": "Owning role",
    "design": "Design workflow state",
    "special": "Special tag",
}

_CATEGORY_COLORS = {
    "type:issue": "d73a4a",
    "type:task": "0075ca",
    "priority:high": "b60205",
    "priority:medium": "fbca04",
    "priority:low": "c2e0c6",
    "severity:high": "d93f0b",
    "severity:medium": "e4e669",
    "severity:low": "fef2c0",
    "status:open": "ededed",
    "status:pending": "ededed",
    "status:pending-human-approval": "fef2c0",
    "status:pending-human-review": "d4c5f9",
    "status:pending-human-setup": "c5def5",
    "status:planning": "bfe5bf",
    "status:planned": "bfe5bf",
    "status:approved": "0075ca",
    "status:in-progress": "fbca04",
    "status:pending-test": "fef2c0",
    "status:pending-ship": "c2e0c6",
    "status:shipped": "1d76db",
    "design:needed": "fef2c0",
    "design:in-progress": "fbca04",
    "design:complete": "c2e0c6",
    "squidsquad": "1d1d1d",
    "improvement-scan": "1d1d1d",
    "squidsquad-test": "1d1d1d",
}

# Default colour for any label that is not in _CATEGORY_COLORS. gh picks a
# random colour if we omit --color, which is fine for cross-team or
# per-role labels (role:skill etc.) whose colour is cosmetic.
_DEFAULT_LABEL_COLOR = "1d76db"


def _label_description(name):
    """Return a reasonable description for `name` based on its category prefix."""
    descriptions = {
        "type:issue": "Issue report",
        "type:task": "Task request",
        "priority:high": "High priority",
        "priority:medium": "Medium priority",
        "priority:low": "Low priority",
        "severity:high": "High severity",
        "severity:medium": "Medium severity",
        "severity:low": "Low severity",
        "status:open": "Filed, awaiting triage",
        "status:pending": "Awaiting approval (legacy — see pending-human-approval)",
        "status:pending-human-approval": "Awaiting initial human approval (intake gate)",
        "status:pending-human-review": "In-progress iteration awaiting HITL review",
        "status:pending-human-setup": "Worker paused — needs human to complete tool/environment setup",
        "status:planning": "PM running intake",
        "status:planned": "Planning complete, awaiting approval for execution",
        "status:approved": "Approved for development",
        "status:in-progress": "Being worked on",
        "status:pending-test": "Implementation complete, awaiting QA",
        "status:pending-ship": "QA verified, awaiting DM delivery",
        "status:shipped": "Delivered, closed",
        "design:needed": "Designer must produce specs before dev",
        "design:in-progress": "Designer working on specs",
        "design:complete": "Design approved, dev can proceed",
        "squidsquad": "Managed by SquidSquad",
        "improvement-scan": "Filed by improvement scanning",
        "squidsquad-test": "Created by integration test harness",
    }
    if name in descriptions:
        return descriptions[name]
    # Category prefix -> generic description
    for prefix, desc in _CATEGORY_DESCRIPTIONS.items():
        if name.startswith(prefix + ":"):
            return desc
    return _CATEGORY_DESCRIPTIONS.get("special", "SquidSquad label")


def build_label_inventory():
    """Return the full list of labels SquidSquad expects on a repo.

    Returns a list of dicts with keys:
        name: str — full label name
        description: str — human-readable description
        color: str — 6-char hex without leading '#'

    The canonical source is `tracker.py` — this function adapts that to
    the shape wizard.ensure_labels wants. Importing at call time rather
    than at module load keeps tracker.py lazy.
    """
    t = _tracker()
    names = set()
    names.update(t.TYPE_LABELS.values())
    names.update(t.PRIORITY_LABELS.values())
    names.update(t.STATUS_LABELS.values())
    names.update(t.SEVERITY_LABELS.values())
    names.update(t.DESIGN_LABELS.values())
    names.update(t.SPECIAL_LABELS)

    inventory = []
    for name in sorted(names):
        inventory.append({
            "name": name,
            "description": _label_description(name),
            "color": _CATEGORY_COLORS.get(name, _DEFAULT_LABEL_COLOR),
        })
    return inventory


def list_gh_labels():
    """Return the set of label names currently on the repo via `gh label list`.

    Empty set on any error — caller decides whether to treat that as an
    API failure or an uninitialised repo.
    """
    result = _run([
        "gh", "label", "list", "--limit", "200", "--json", "name",
    ])
    if result.returncode != 0 or not result.stdout.strip():
        return set()
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return set()
    return {item["name"] for item in data if isinstance(item, dict) and "name" in item}


def ensure_labels(dry_run=False):
    """Seed every required label. Idempotent — only creates what is missing.

    Args:
        dry_run: if True, reports what WOULD be created without calling gh.

    Returns a summary dict:
        {
            "total": int,
            "existing": [...label names that were already on the repo],
            "created": [...label names that were newly created],
            "failed": [{name, error}, ...],
            "dry_run": bool,
        }

    The wizard calls this in Step 7 after writing files, as the last
    repo-side step. Safe to re-run at any time.
    """
    inventory = build_label_inventory()
    existing = list_gh_labels()

    summary = {
        "total": len(inventory),
        "existing": [],
        "created": [],
        "failed": [],
        "dry_run": bool(dry_run),
    }

    for spec in inventory:
        name = spec["name"]
        if name in existing:
            summary["existing"].append(name)
            continue
        if dry_run:
            summary["created"].append(name)
            continue
        result = _run([
            "gh", "label", "create", name,
            "--description", spec["description"],
            "--color", spec["color"],
        ])
        if result.returncode == 0:
            summary["created"].append(name)
        else:
            # gh label create returns non-zero if the label already exists,
            # which can happen if the list_gh_labels cache is stale. Treat
            # "already exists" as success.
            err = (result.stderr or "").strip()
            if "already exists" in err.lower():
                summary["existing"].append(name)
            else:
                summary["failed"].append({
                    "name": name,
                    "error": err or f"gh exit {result.returncode}",
                })

    return summary


def list_issues_with_label(label, state="all"):
    """Return the list of issue numbers that currently carry `label`.

    Args:
        label: the full label name to search for (e.g. "status:pending")
        state: "open" | "closed" | "all" — passed to `gh issue list --state`

    Returns a list of ints (issue numbers). Empty list on error.
    """
    result = _run([
        "gh", "issue", "list",
        "--label", label,
        "--state", state,
        "--limit", "500",
        "--json", "number",
    ])
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [
        int(item["number"])
        for item in data
        if isinstance(item, dict) and "number" in item
    ]


def migrate_label(old, new, dry_run=False, state="all"):
    """Rewrite every issue carrying `old` to carry `new` instead.

    This is the core of Phase I (the `pending` -> `pending-human-approval`
    rename). The new label must already exist on the repo (call
    `ensure_labels` first if in doubt). The old label is NOT deleted —
    that is a separate, intentional step.

    Args:
        old: the label to remove from each issue
        new: the label to add to each issue
        dry_run: if True, returns what WOULD be migrated without touching gh
        state: "open" | "closed" | "all"

    Returns a summary dict:
        {
            "old_label": str,
            "new_label": str,
            "dry_run": bool,
            "candidates": [...issue numbers scanned],
            "migrated": [...issue numbers successfully relabelled],
            "skipped": [...issue numbers that already had `new` for some reason],
            "failed": [{number, error}, ...],
        }
    """
    summary = {
        "old_label": old,
        "new_label": new,
        "dry_run": bool(dry_run),
        "candidates": [],
        "migrated": [],
        "skipped": [],
        "failed": [],
    }

    candidates = list_issues_with_label(old, state=state)
    summary["candidates"] = list(candidates)

    if not candidates:
        return summary

    for number in candidates:
        if dry_run:
            summary["migrated"].append(number)
            continue
        result = _run([
            "gh", "issue", "edit", str(number),
            "--remove-label", old,
            "--add-label", new,
        ])
        if result.returncode == 0:
            summary["migrated"].append(number)
        else:
            err = (result.stderr or "").strip()
            # gh reports "label already on the issue" on an add-label no-op
            # — treat as already migrated, not an error.
            if "already" in err.lower() and "label" in err.lower():
                summary["skipped"].append(number)
            else:
                summary["failed"].append({
                    "number": number,
                    "error": err or f"gh exit {result.returncode}",
                })

    return summary


def _delete_gh_label(name):
    """Delete a GitHub label by name via `gh label delete`.

    Returns (ok: bool, error: str|None). Treats "not found" as success
    so deletes are idempotent.
    """
    result = _run([
        "gh", "label", "delete", name, "--yes",
    ])
    if result.returncode == 0:
        return True, None
    err = (result.stderr or "").strip()
    if "not found" in err.lower():
        return True, None
    return False, err or f"gh exit {result.returncode}"


# Stage names in the exact order they run. Tests and callers can use
# this list to assert the pipeline shape without tying themselves to
# implementation details.
LABEL_MIGRATION_STAGES = [
    "preflight",
    "dry_run",
    "execute",
    "postflight",
    "cleanup",
]


def stage_label_migration(old, new, execute=False, delete_old=False, state="all"):
    """Run a label migration in stages with preflight and postflight guards.

    This is the production runner for renaming a legacy label across
    every issue in a repo (e.g. Phase I: `status:pending` ->
    `status:pending-human-approval`). Safe to call with any combination
    of flags — stages that are not enabled simply report their findings
    without touching gh.

    Stages (all run unconditionally, in order):

        1. `preflight`   — Verify both labels exist on the repo. If
                           either is missing, abort before touching
                           anything.
        2. `dry_run`     — Count candidates (issues with the old label)
                           without calling `gh issue edit`.
        3. `execute`     — Only runs when `execute=True`. Calls
                           `migrate_label(old, new)` for real.
        4. `postflight`  — Re-list issues with the old label. Clean state
                           is zero candidates. Runs unconditionally so
                           callers see how close they are even in dry-run.
        5. `cleanup`     — Only runs when `delete_old=True` AND postflight
                           is clean AND execute ran. Deletes the old
                           label from the repo via `gh label delete`.

    Args:
        old:         legacy label name (e.g. "status:pending")
        new:         target label name (e.g. "status:pending-human-approval")
        execute:     if True, actually rewrite labels on gh issues
        delete_old:  if True, delete the old label from the repo after
                     postflight verifies zero candidates remain
        state:       "open" | "closed" | "all" — passed through to the
                     candidate queries

    Returns a nested summary dict with per-stage results and a top-level
    `ok` flag that is True only when every run stage succeeded without
    errors. Callers should check `ok` before claiming the migration
    landed.
    """
    summary = {
        "old_label": old,
        "new_label": new,
        "execute": bool(execute),
        "delete_old": bool(delete_old),
        "state": state,
        "stages": {name: None for name in LABEL_MIGRATION_STAGES},
        "ok": False,
    }

    # --- Stage 1: preflight -------------------------------------------------
    repo_labels = list_gh_labels()
    preflight = {
        "old_exists": old in repo_labels,
        "new_exists": new in repo_labels,
        "ok": True,
        "errors": [],
    }
    if not preflight["old_exists"]:
        preflight["ok"] = False
        preflight["errors"].append(
            f"legacy label {old!r} does not exist on the repo "
            f"(nothing to migrate)"
        )
    if not preflight["new_exists"]:
        preflight["ok"] = False
        preflight["errors"].append(
            f"target label {new!r} does not exist on the repo — "
            f"call `ensure-labels` first, or create it manually"
        )
    summary["stages"]["preflight"] = preflight

    if not preflight["ok"]:
        return summary

    # --- Stage 2: dry-run ---------------------------------------------------
    candidates = list_issues_with_label(old, state=state)
    summary["stages"]["dry_run"] = {
        "candidate_count": len(candidates),
        "candidates": list(candidates),
        "ok": True,
    }

    # Nothing to migrate -> short-circuit postflight is also clean
    if not candidates:
        summary["stages"]["execute"] = {
            "ok": True,
            "skipped": True,
            "reason": "no candidates",
        }
        summary["stages"]["postflight"] = {
            "remaining_count": 0,
            "ok": True,
        }
        summary["stages"]["cleanup"] = _maybe_cleanup(old, delete_old, True, True)
        summary["ok"] = True
        return summary

    # --- Stage 3: execute ---------------------------------------------------
    if execute:
        migration = migrate_label(old, new, dry_run=False, state=state)
        summary["stages"]["execute"] = {
            "ok": not migration["failed"],
            "migrated": migration["migrated"],
            "skipped": migration["skipped"],
            "failed": migration["failed"],
        }
        if migration["failed"]:
            # Still run postflight so the caller sees how much progress
            # was made; cleanup will refuse to run.
            pass
    else:
        summary["stages"]["execute"] = {
            "ok": True,
            "skipped": True,
            "reason": "execute flag not set (dry-run mode)",
        }

    # --- Stage 4: postflight ------------------------------------------------
    remaining = list_issues_with_label(old, state=state)
    postflight_ok = len(remaining) == 0
    summary["stages"]["postflight"] = {
        "remaining_count": len(remaining),
        "remaining": list(remaining),
        "ok": postflight_ok,
    }

    # --- Stage 5: cleanup ---------------------------------------------------
    execute_ok = summary["stages"]["execute"]["ok"]
    summary["stages"]["cleanup"] = _maybe_cleanup(
        old, delete_old, postflight_ok, execute_ok and execute,
    )

    # Top-level `ok` is True only when every stage that RAN succeeded.
    summary["ok"] = (
        preflight["ok"]
        and summary["stages"]["execute"]["ok"]
        and summary["stages"]["postflight"]["ok"]
        and summary["stages"]["cleanup"]["ok"]
    )
    return summary


def _maybe_cleanup(old, delete_old, postflight_ok, execute_ran_ok):
    """Delete the old label if all cleanup preconditions hold."""
    if not delete_old:
        return {
            "ok": True,
            "skipped": True,
            "reason": "delete_old flag not set",
        }
    if not execute_ran_ok:
        return {
            "ok": True,
            "skipped": True,
            "reason": "execute stage did not run successfully — "
                      "refusing to delete label",
        }
    if not postflight_ok:
        return {
            "ok": True,
            "skipped": True,
            "reason": "postflight found remaining candidates — "
                      "refusing to delete label",
        }
    ok, err = _delete_gh_label(old)
    return {
        "ok": ok,
        "deleted": ok,
        "error": err,
    }


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


def _print_json(data, ok=True):
    """Print a JSON object with an `ok` envelope field prepended."""
    out = dict(data)
    if "ok" not in out:
        out["ok"] = ok
    print(json.dumps(out, indent=2, default=str))


def cmd_check_gh(_args):
    result = check_gh()
    _print_json(result)
    return 0 if result["ok"] else 1


def cmd_preflight(_args):
    result = preflight()
    _print_json(result)
    return 0 if result["ok"] else 1


def cmd_check_existing(_args):
    result = detect_existing_install()
    _print_json(result)
    return 0


def cmd_repo_info(_args):
    result = get_repo_info()
    _print_json(result, ok=result["ok"])
    return 0 if result["ok"] else 1


def cmd_project_name_default(_args):
    name = project_name_default()
    _print_json({
        "project_name": name,
        "valid": is_valid_project_name(name),
    })
    return 0


def cmd_validate_name(args):
    if not args:
        print(
            "Usage: wizard.py validate-name <project-name>",
            file=sys.stderr,
        )
        return 2
    name = args[0]
    valid = is_valid_project_name(name)
    _print_json({"project_name": name, "valid": valid})
    return 0 if valid else 1


def cmd_validate_interval(args):
    """Usage: wizard.py validate-interval <value> [--default N]"""
    if not args:
        print(
            "Usage: wizard.py validate-interval <value> [--default N]",
            file=sys.stderr,
        )
        return 2
    value = args[0]
    default = 10
    if "--default" in args:
        idx = args.index("--default")
        if idx + 1 < len(args):
            try:
                default = int(args[idx + 1])
            except ValueError:
                print(f"ERROR: --default must be an integer", file=sys.stderr)
                return 2
    result = validate_interval(value, default=default)
    _print_json(result, ok=result["ok"])
    return 0 if result["ok"] else 1


def cmd_build_config_md(args):
    """Read a JSON install spec from disk (or `-`) and print config.md text.

    Usage: wizard.py build-config-md <spec.json>
           wizard.py build-config-md -         # read from stdin
    """
    if not args:
        print(
            "Usage: wizard.py build-config-md <spec.json|->",
            file=sys.stderr,
        )
        return 2
    src = args[0]
    try:
        if src == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(src).read_text(encoding="utf-8")
        spec = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read spec: {e}", file=sys.stderr)
        return 1
    try:
        text = build_config_md(spec)
    except ValueError as e:
        print(f"ERROR: invalid spec: {e}", file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


def cmd_scaffold(args):
    """Read a JSON install spec and write the full `.squidsquad/` tree.

    Usage: wizard.py scaffold <spec.json> [target_dir]
    """
    if not args:
        print(
            "Usage: wizard.py scaffold <spec.json|-> [target_dir]",
            file=sys.stderr,
        )
        return 2
    src = args[0]
    target_dir = args[1] if len(args) > 1 else "."
    try:
        if src == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(src).read_text(encoding="utf-8")
        spec = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read spec: {e}", file=sys.stderr)
        return 1
    try:
        summary = scaffold_install(spec, target_dir)
    except (ValueError, FileExistsError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    _print_json(summary)
    return 0


def cmd_ensure_labels(args):
    """Usage: wizard.py ensure-labels [--dry-run]"""
    dry = "--dry-run" in args
    summary = ensure_labels(dry_run=dry)
    _print_json(summary, ok=not summary["failed"])
    return 0 if not summary["failed"] else 1


def cmd_list_issues_by_label(args):
    """Usage: wizard.py list-issues-by-label <label> [--state open|closed|all]"""
    if not args:
        print(
            "Usage: wizard.py list-issues-by-label <label> [--state all]",
            file=sys.stderr,
        )
        return 2
    label = args[0]
    state = "all"
    if "--state" in args:
        idx = args.index("--state")
        if idx + 1 < len(args):
            state = args[idx + 1]
    numbers = list_issues_with_label(label, state=state)
    _print_json({"label": label, "state": state, "issues": numbers})
    return 0


def cmd_migrate_label(args):
    """Usage: wizard.py migrate-label <old> <new> [--dry-run] [--state all]"""
    if len(args) < 2:
        print(
            "Usage: wizard.py migrate-label <old> <new> [--dry-run] [--state all|open|closed]",
            file=sys.stderr,
        )
        return 2
    old, new = args[0], args[1]
    dry = "--dry-run" in args
    state = "all"
    if "--state" in args:
        idx = args.index("--state")
        if idx + 1 < len(args):
            state = args[idx + 1]
    summary = migrate_label(old, new, dry_run=dry, state=state)
    _print_json(summary, ok=not summary["failed"])
    return 0 if not summary["failed"] else 1


def cmd_migrate_labels_staged(args):
    """Usage: wizard.py migrate-labels-staged <old> <new> [--execute] [--delete-old] [--state all|open|closed]

    Runs the staged label migration runner. Without --execute it only
    reports what WOULD happen (preflight + dry-run + postflight). With
    --execute it actually rewrites labels on gh issues. --delete-old
    removes the legacy label after a clean postflight.
    """
    if len(args) < 2:
        print(
            "Usage: wizard.py migrate-labels-staged <old> <new> "
            "[--execute] [--delete-old] [--state all|open|closed]",
            file=sys.stderr,
        )
        return 2
    old, new = args[0], args[1]
    execute = "--execute" in args
    delete_old = "--delete-old" in args
    state = "all"
    if "--state" in args:
        idx = args.index("--state")
        if idx + 1 < len(args):
            state = args[idx + 1]
    summary = stage_label_migration(
        old, new, execute=execute, delete_old=delete_old, state=state,
    )
    _print_json(summary, ok=summary["ok"])
    return 0 if summary["ok"] else 1


def cmd_validate_rerun_action(args):
    if not args:
        print(
            "Usage: wizard.py validate-rerun-action <input>",
            file=sys.stderr,
        )
        return 2
    raw = args[0]
    action = validate_rerun_action(raw)
    _print_json({
        "input": raw,
        "action": action,
        "valid": action is not None,
    }, ok=action is not None)
    return 0 if action is not None else 1


def pr_flow_prompt():
    """Return the PR Flow question text and options for the setup agent."""
    return {
        "question": (
            "Do you want Pull Request review flow enabled?\n\n"
            "**PR Flow OFF** (default): Agents commit directly to the working branch. "
            "Code lands immediately. Faster iteration, less overhead per change.\n\n"
            "**PR Flow ON**: Agents create feature branches and open Pull Requests. "
            "Code only lands after you review and merge each PR. "
            "Gives you a review gate on every change."
        ),
        "options": ["Off (default — direct commits)", "On (PRs for every change)"],
        "default": False,
    }


def post_setup_summary(spec):
    """Generate the 'What's Next' summary after setup completes.

    Returns a formatted string with boot instructions, interaction guide,
    and status monitoring info based on the configured agents.
    """
    agents = spec.get("agents", [])
    project_name = spec.get("project", {}).get("name", "your project")

    lines = []
    lines.append("## What's Next")
    lines.append("")
    lines.append(f"SquidSquad is installed for **{project_name}**. Here's how to get started:")
    lines.append("")

    # Boot instructions
    lines.append("### 1. Boot your agents")
    lines.append("")
    lines.append("Each agent runs in its own terminal. Open a terminal for each and run:")
    lines.append("")

    for agent in agents:
        agent_id = agent.get("id", "")
        role = agent.get("role", "")
        if role == "pm":
            lines.append(f"```bash")
            lines.append(f"# Terminal 1 — PM (coordinator)")
            lines.append(f"claude --resume")
            lines.append(f"```")
        elif role == "dev":
            variant = agent.get("variant", agent_id)
            lines.append(f"```bash")
            lines.append(f"# Terminal — {variant} (dev agent)")
            lines.append(f"claude --resume")
            lines.append(f"```")
        elif role == "qa":
            lines.append(f"```bash")
            lines.append(f"# Terminal — QA (verification)")
            lines.append(f"claude --resume")
            lines.append(f"```")
        elif role == "dm":
            lines.append(f"```bash")
            lines.append(f"# Terminal — DM (delivery)")
            lines.append(f"claude --resume")
            lines.append(f"```")
    lines.append("")

    # What happens first
    lines.append("### 2. What happens on the first cycle")
    lines.append("")
    lines.append("- PM starts a check-in and waits for your first task or bug report")
    lines.append("- Dev agents poll for work — nothing to do yet until PM assigns something")
    lines.append("- QA runs any configured E2E tests and verifies completed work")
    lines.append("")

    # How to interact
    lines.append("### 3. How to interact")
    lines.append("")
    lines.append("Type in the **PM terminal** to:")
    lines.append("- Report a bug: describe the issue, PM will investigate and file it")
    lines.append("- Request a feature: describe what you want, PM will run the planning process")
    lines.append("- Change priorities: tell PM to bump or lower priority on any item")
    lines.append("- Approve tasks: PM presents planned tasks for your approval before dev starts")
    lines.append("")

    # Where to see status
    lines.append("### 4. Where to see status")
    lines.append("")
    lines.append("- **Terminal status bar**: each agent shows a live status line at the bottom")
    lines.append("- **GitHub Issues**: all bugs, tasks, and progress tracked as labeled Issues")
    lines.append("- **Iteration logs**: `.squidsquad/<role>/iterations/` for cycle-by-cycle history")
    lines.append("")

    return "\n".join(lines)


def format_scan_summary(scan_data):
    """Format repo scan data into a grouped human-readable summary.

    Takes the output of repo_scan.scan() and returns a string
    suitable for presenting to the user during setup.
    """
    if not scan_data:
        return "No project detected (empty repo or no recognizable files)."

    sections = []

    langs = scan_data.get("languages", [])
    if langs:
        sections.append(f"**Languages**: {', '.join(langs)}")

    frameworks = scan_data.get("frameworks", [])
    if frameworks:
        sections.append(f"**Frameworks**: {', '.join(frameworks)}")

    pkg = scan_data.get("package_managers", [])
    if pkg:
        sections.append(f"**Package Managers**: {', '.join(pkg)}")

    tests = scan_data.get("test_frameworks", [])
    if tests:
        sections.append(f"**Test Tools**: {', '.join(tests)}")

    ci = scan_data.get("ci_cd", [])
    if ci:
        sections.append(f"**CI/CD**: {', '.join(ci)}")

    deploy = scan_data.get("deploy_targets", [])
    if deploy:
        sections.append(f"**Deploy**: {', '.join(deploy)}")

    docs = scan_data.get("documentation", [])
    if docs:
        sections.append(f"**Docs**: {', '.join(docs)}")

    mono = scan_data.get("monorepo", [])
    if mono:
        sections.append(f"**Monorepo**: {', '.join(mono)}")

    if not sections:
        return "No project features detected."

    return "\n".join(sections)


def generate_default_spec(scan_data=None, repo_info=None):
    """Generate a default install spec from auto-detected data.

    Used by --yes mode and as pre-filled defaults for interactive mode.
    Returns a spec dict with smart defaults based on scan results.
    """
    scan = scan_data or {}
    info = repo_info or {}

    # Project info
    project_name = info.get("name", "")
    project_repo = info.get("repo", "")

    # Detect test command from scan
    test_frameworks = scan.get("test_frameworks", [])
    test_command = ""
    if "pytest" in test_frameworks:
        test_command = "pytest"
    elif "jest" in test_frameworks:
        test_command = "npx jest"
    elif "vitest" in test_frameworks:
        test_command = "npx vitest"
    elif "mocha" in test_frameworks:
        test_command = "npx mocha"

    # Detect stack from scan
    langs = scan.get("languages", [])
    frameworks = scan.get("frameworks", [])
    stack_parts = []
    if frameworks:
        stack_parts.extend(frameworks[:3])
    if langs:
        stack_parts.extend(l for l in langs[:3] if l not in stack_parts)
    stack = " + ".join(stack_parts) if stack_parts else "general"

    # Resolve domain variants from the default preset manifest (#6581)
    default_preset = "software-dev"
    domain_variants = resolve_domain_variants(default_preset)

    # Default agents — variants from manifest, not hardcoded.
    # Use canonical new identity 'worker' (renamed from 'dev' in #6274.2);
    # `or domain_variants.get("dev")` keeps pre-rename manifests resolving
    # during the 6274.1 dual-aware window (deleted in 6274.3).
    worker_variant = domain_variants.get("worker") or domain_variants.get("dev")
    pm_variant = domain_variants.get("pm")
    agents = [
        {"id": "pm", "alias": "pm", "role": "pm",
         **({"variant": pm_variant} if pm_variant else {})},
        {
            "id": "skill",
            "alias": "skill",
            "role": "worker",
            **({"variant": worker_variant} if worker_variant else {}),
            "stack": stack,
            "test_command": test_command,
        },
    ]

    # Read version dynamically from config.md or fallback
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import config as _cfg
        current_version = _cfg.get_field("version") or "0.36.0"
    except (ImportError, SystemExit, Exception):
        current_version = "0.36.0"

    return {
        "squidsquad_version": current_version,
        "project": {
            "name": project_name,
            "repo": project_repo,
        },
        "preset": default_preset,
        "agents": agents,
        "tools": {},
        "loop": {
            "interval_minutes": 30,
            "context_threshold": 70,
        },
        "flags": {
            "pr_flow": False,
            "improvement_scan": True,
            "vault_remember": True,
            "diagnostics": True,
        },
        "git_branches": {
            "working": "main",
            "state": "squid-squad",
        },
        "forge_backend": {
            "provider": "github",
            "endpoint": "https://api.github.com",
        },
        "model_routing": {
            "model": "claude",
        },
    }


def cmd_scan_summary(args):
    """Run repo scan and print formatted summary.

    Usage: wizard.py scan-summary [target_dir]
    """
    target = args[0] if args else "."
    scan_path = Path(target) / ".squidsquad" / ".repo-scan.json"
    if scan_path.exists():
        scan_data = json.loads(scan_path.read_text(encoding="utf-8"))
    else:
        # Run scan on the fly
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from repo_scan import scan
            scan_data = scan(target)
        except ImportError:
            print("ERROR: repo_scan.py not available", file=sys.stderr)
            return 1
    print(format_scan_summary(scan_data))
    return 0


def cmd_generate_defaults(args):
    """Generate a default install spec from auto-detected data.

    Usage: wizard.py generate-defaults [target_dir]
    """
    target = args[0] if args else "."
    target_path = Path(target)

    # Load scan data
    scan_data = {}
    scan_path = target_path / ".squidsquad" / ".repo-scan.json"
    if scan_path.exists():
        try:
            scan_data = json.loads(scan_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Load repo info
    repo_info = {}
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "wizard.py"), "repo-info"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=target,
        )
        if result.returncode == 0:
            repo_info = json.loads(result.stdout)
    except (json.JSONDecodeError, OSError):
        pass

    spec = generate_default_spec(scan_data, repo_info)
    _print_json(spec)
    return 0


def cmd_setup_yes(args):
    """Non-interactive setup: generate defaults, scaffold, ensure labels.

    Usage: wizard.py setup-yes [target_dir]

    Equivalent to `npx squidsquad --yes` — accepts all defaults,
    skips interactive questions. Good for CI/testing and dogfooding.
    """
    target = args[0] if args else "."
    target_path = Path(target)

    print("[SquidSquad] Non-interactive setup (--yes mode)")

    # 1. Load scan data if available
    scan_data = {}
    scan_path = target_path / ".squidsquad" / ".repo-scan.json"
    if scan_path.exists():
        try:
            scan_data = json.loads(scan_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    else:
        # Run scan
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from repo_scan import scan
            scan_data = scan(str(target_path))
        except ImportError:
            pass

    # 2. Load repo info
    repo_info = {}
    result = _run(["gh", "repo", "view", "--json", "name,url"])
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            repo_info["name"] = data.get("name", "")
            repo_info["repo"] = data.get("url", "").replace("https://", "")
        except (json.JSONDecodeError, ValueError):
            pass
    if not repo_info.get("name"):
        repo_info["name"] = target_path.resolve().name

    # 3. Show scan summary
    summary = format_scan_summary(scan_data)
    if summary:
        print(f"\nDetected:\n{summary}\n")

    # 4. Generate default spec
    spec = generate_default_spec(scan_data, repo_info)
    print(f"Project: {spec['project']['name']}")
    print(f"Agents: {', '.join(a['id'] for a in spec['agents'])}")
    print(f"Stack: {spec['agents'][-1].get('stack', 'general')}")

    # 5. Scaffold
    print("\nScaffolding...")
    try:
        result = scaffold_install(spec, target_path, overwrite_existing=True)
        print(f"  Created {len(result.get('agents', []))} agent(s)")
    except (ValueError, FileExistsError) as e:
        print(f"ERROR: scaffold failed: {e}", file=sys.stderr)
        return 1

    # 6. Ensure labels
    print("Creating GitHub labels...")
    try:
        label_result = ensure_labels(dry_run=False)
        created = label_result.get("created", 0)
        if created:
            print(f"  Created {created} label(s)")
        else:
            print("  All labels exist")
    except Exception as e:
        print(f"WARNING: label creation failed: {e}", file=sys.stderr)

    # 7. Post-setup summary
    print()
    print(post_setup_summary(spec))

    return 0


def cmd_pr_flow_prompt(_args):
    """Print the PR Flow question and options as JSON."""
    _print_json(pr_flow_prompt())
    return 0


def cmd_post_setup_summary(args):
    """Read a JSON install spec and print the post-setup summary.

    Usage: wizard.py post-setup-summary <spec.json|->
    """
    if not args:
        print("Usage: wizard.py post-setup-summary <spec.json|->", file=sys.stderr)
        return 2
    src = args[0]
    try:
        if src == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(src).read_text(encoding="utf-8")
        spec = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read spec: {e}", file=sys.stderr)
        return 1
    print(post_setup_summary(spec))
    return 0


def cmd_load_spec(args):
    """Load and print the install spec from .squidsquad/.install-spec.json.

    Usage: wizard.py load-spec [target_dir]
    """
    target = args[0] if args else "."
    spec = load_install_spec(target)
    if spec is None:
        print("No .install-spec.json found (pre-#13 install or first run)",
              file=sys.stderr)
        return 1
    _print_json(spec)
    return 0


def cmd_save_spec(args):
    """Save a JSON install spec to .squidsquad/.install-spec.json.

    Usage: wizard.py save-spec <spec.json|-> [target_dir]
    """
    if not args:
        print("Usage: wizard.py save-spec <spec.json|-> [target_dir]",
              file=sys.stderr)
        return 2
    src = args[0]
    target = args[1] if len(args) > 1 else "."
    try:
        if src == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(src).read_text(encoding="utf-8")
        spec = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read spec: {e}", file=sys.stderr)
        return 1
    path = save_install_spec(spec, target)
    print(f"Saved: {path}")
    return 0


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0
    cmd = args[0]
    rest = args[1:]
    dispatch = {
        "check-gh": cmd_check_gh,
        "check-existing": cmd_check_existing,
        "repo-info": cmd_repo_info,
        "project-name-default": cmd_project_name_default,
        "validate-name": cmd_validate_name,
        "validate-interval": cmd_validate_interval,
        "validate-rerun-action": cmd_validate_rerun_action,
        "build-config-md": cmd_build_config_md,
        "scaffold": cmd_scaffold,
        "ensure-labels": cmd_ensure_labels,
        "list-issues-by-label": cmd_list_issues_by_label,
        "migrate-label": cmd_migrate_label,
        "migrate-labels-staged": cmd_migrate_labels_staged,
        "pr-flow-prompt": cmd_pr_flow_prompt,
        "post-setup-summary": cmd_post_setup_summary,
        "load-spec": cmd_load_spec,
        "save-spec": cmd_save_spec,
        "scan-summary": cmd_scan_summary,
        "generate-defaults": cmd_generate_defaults,
        "setup-yes": cmd_setup_yes,
        "preflight": cmd_preflight,
        "upgrade": cmd_upgrade,
    }
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2
    return dispatch[cmd](rest)


if __name__ == "__main__":
    sys.exit(main())
