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

# Re-run detection — actions the installer agent can take
RERUN_ACTIONS = ("abort", "regenerate", "full-rebuild")


# ---------------------------------------------------------------------------
# Step 0 — gh prerequisite check
# ---------------------------------------------------------------------------


def _run(cmd, **kwargs):
    """Thin subprocess.run wrapper — list form only, captures output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
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
    # A per-role directory is any subdir containing a CLAUDE.md
    has_roles = any(
        (target / c / "CLAUDE.md").exists()
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
        "validate-rerun-action": cmd_validate_rerun_action,
    }
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2
    return dispatch[cmd](rest)


if __name__ == "__main__":
    sys.exit(main())
