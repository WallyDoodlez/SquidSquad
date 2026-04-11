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
                "context_threshold": 80,
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
        f"- **Context Threshold**: {loop.get('context_threshold', 80)}"
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
        "build-config-md": cmd_build_config_md,
        "scaffold": cmd_scaffold,
    }
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2
    return dispatch[cmd](rest)


if __name__ == "__main__":
    sys.exit(main())
