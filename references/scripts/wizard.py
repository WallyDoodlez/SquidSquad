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
        encoding="utf-8",
        errors="replace",
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
                    "id": "designer",
                    "alias": "designer",
                    "role": "designer",
                    "iteration_mode": "hitl",
                    "setup": {"install_optional": "yes"},
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
                "designer.tool": None,          # deferred -> "(unset ...)"
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

    # 2. Per-agent directories
    for agent in spec["agents"]:
        agent_id = agent["id"]
        role_identity = agent["role"]

        # Verify the role identity template exists before composing — a
        # friendlier error than whatever deploy_role would produce if the
        # entry file is missing.
        role_dir = REPO_ROOT / "references" / "roles" / role_identity
        if not (role_dir / "CLAUDE.md").exists():
            raise ValueError(
                f"agent {agent_id!r} references unknown role identity "
                f"{role_identity!r}: no CLAUDE.md at {role_dir}"
            )

        agent_dir = squid / agent_id
        was_new = not agent_dir.exists()
        agent_dir.mkdir(parents=True, exist_ok=True)
        if was_new:
            summary["created_dirs"].append(str(agent_dir))

        # CLAUDE.md — composed from role identity template + sub-skills.
        # deploy_role already handles the compose/substitute/write pipeline;
        # it takes the agent id (not the role identity) because [ROLE]
        # placeholder substitution uses the agent name.
        claude_path = deploy_role(agent_id, target_root=target_root)

        # SOUL.md — deploy_role wrote it if missing; honour existing files
        soul_path = agent_dir / "SOUL.md"

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

    return summary


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
    }
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2
    return dispatch[cmd](rest)


if __name__ == "__main__":
    sys.exit(main())
