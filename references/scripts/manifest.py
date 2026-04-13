#!/usr/bin/env python3
"""SquidSquad manifest registry — load, validate, resolve role/capability/preset manifests.

Single source of truth for the manifest schema. The wizard, compose.py, and
statusline all read through this module rather than parsing YAML inline.

Commands:
    python scripts/manifest.py validate           # lint the shipped registry
    python scripts/manifest.py list <kind>        # list all manifest ids of a kind
    python scripts/manifest.py load <kind> <id>   # print one manifest as JSON
    python scripts/manifest.py resolve <preset>   # print the installed role set
    python scripts/manifest.py --help

`<kind>` is one of: roles, capabilities (alias: tools), presets.

Enforced invariants (Q-new14/15/16 + side-effect mitigations from CONTEXT):
  * schema_version in {1, 2}
  * manifest id matches directory name
  * role.iteration_mode in {normal, hitl}
  * capability.provider in {mcp, builtin, http}; mcp requires mcp_name
  * role.requires_sub_skills.any_of/all_of ids exist in the capability registry
  * role.routes_to ids exist in the role registry
  * capability.applicable_roles ids exist in the role registry
  * preset.role_install_order ids exist and are NOT always_installed
  * capability sub_skill + setup.md files exist on disk
  * manifest free-text fields (tagline, description) are domain-only
    (no references to internal files, statuses, or scripts)

Cycle detection is intentionally NOT enforced on the routes_to graph. The
side-effect mitigation in CONTEXT §5 (item 6) was written on the premise
that "no v1 manifest creates cycles", but v1 locks bidirectional routing
(PM -> Designer -> PM) because each hand-off is a state-changing transition
on a specific work item, not a re-entry. routes_to is a per-item hand-off
preference list, not a flow DAG — the walker terminates because each
transition moves the work forward in its own lifecycle. A validator-level
cycle check would flag legitimate topology. If a future bug makes the
walker non-terminating, that's a walker bug, not a manifest bug.

PyYAML is required. It is a standard Python package; install with
`pip install pyyaml` if missing.
"""

import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    print(
        "ERROR: PyYAML is required for manifest operations.\n"
        "Install it with:  pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_REFERENCES = REPO_ROOT / "references"

SUPPORTED_SCHEMA_VERSIONS = {1, 2}
VALID_ITERATION_MODES = {"normal", "hitl"}
VALID_PROVIDERS = {"mcp", "builtin", "http"}
VALID_TOOL_CATEGORIES = {
    "design", "delivery", "tracker", "observability", "comms", "other",
}

# Phrases that indicate SquidSquad-internal language in a manifest. A
# manifest's free-text fields must describe the role or tool in domain
# terms only (Q-new14). These substrings trigger a domain-only violation.
# Matching is case-insensitive and applied to `tagline`, `description`,
# and `display_name`.
DOMAIN_ONLY_BLOCKLIST = [
    ("config.md", "internal config file"),
    (".squidsquad", "internal runtime directory"),
    ("claude.md", "internal agent template"),
    ("soul.md", "internal agent soul file"),
    ("sub-skill", "internal composition unit"),
    ("references/scripts", "internal script path"),
    ("references/sub-skills", "internal sub-skill path"),
    ("tracker.py", "internal script"),
    ("compose.py", "internal script"),
    ("role_install_order", "internal schema field"),
    ("schema_version", "internal schema field"),
]


# ---------------------------------------------------------------------------
# Issue record
# ---------------------------------------------------------------------------


class Issue:
    """A validation finding."""

    __slots__ = ("path", "field", "message", "severity")

    def __init__(self, path, field, message, severity="error"):
        self.path = str(path)
        self.field = field
        self.message = message
        self.severity = severity

    def __str__(self):
        loc = self.path
        if self.field:
            loc = f"{loc}:{self.field}"
        return f"{self.severity.upper()}: {loc} — {self.message}"

    def __repr__(self):
        return f"Issue({self.severity} {self.path}:{self.field} {self.message!r})"


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _load_yaml(path):
    """Load a YAML file. Returns (data, issue_or_None)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        return None, Issue(path, "", f"cannot read file: {e}")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return None, Issue(path, "", f"YAML parse error: {e}")
    if data is None:
        return None, Issue(path, "", "empty manifest")
    if not isinstance(data, dict):
        return None, Issue(
            path, "",
            f"top-level must be a mapping, got {type(data).__name__}",
        )
    return data, None


def _check_required(issues, path, data, required):
    for field in required:
        if field not in data:
            issues.append(Issue(path, field, "missing required field"))
    return [f for f in required if f in data]


def _check_domain_only(issues, path, data, fields):
    """Reject internal references in domain-only free-text fields."""
    for field in fields:
        value = data.get(field)
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        for phrase, label in DOMAIN_ONLY_BLOCKLIST:
            if phrase in lowered:
                issues.append(Issue(
                    path, field,
                    f"domain-only violation (Q-new14): contains {phrase!r} "
                    f"({label}). Manifests must describe the role/tool in "
                    f"domain terms only.",
                ))
                break  # one violation per field is enough


# ---------------------------------------------------------------------------
# Per-kind validators
# ---------------------------------------------------------------------------


def validate_role_manifest(path, data):
    """Return a list of Issues for a single role manifest."""
    issues = []
    required = [
        "schema_version", "id", "display_name", "tagline",
        "show_in_roster", "always_installed", "iteration_mode",
        "routes_to", "setup_requirements",
        # Q-new22: every role declares where its identity + template live
        "soul_template", "claude_template",
    ]
    _check_required(issues, path, data, required)
    if issues:
        return issues

    if data["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(Issue(
            path, "schema_version",
            f"unknown schema_version {data['schema_version']!r}; "
            f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
        ))

    dirname = Path(path).parent.name
    if data["id"] != dirname:
        issues.append(Issue(
            path, "id",
            f"id {data['id']!r} does not match directory name {dirname!r}",
        ))

    if data["iteration_mode"] not in VALID_ITERATION_MODES:
        issues.append(Issue(
            path, "iteration_mode",
            f"invalid iteration_mode {data['iteration_mode']!r}; "
            f"must be one of {sorted(VALID_ITERATION_MODES)}",
        ))

    for field in ("show_in_roster", "always_installed"):
        if not isinstance(data[field], bool):
            issues.append(Issue(
                path, field,
                f"must be a boolean, got {type(data[field]).__name__}",
            ))

    if not isinstance(data["routes_to"], list):
        issues.append(Issue(path, "routes_to", "must be a list"))

    if not isinstance(data["setup_requirements"], list):
        issues.append(Issue(path, "setup_requirements", "must be a list"))
    else:
        for i, req in enumerate(data["setup_requirements"]):
            if not isinstance(req, dict):
                issues.append(Issue(
                    path, f"setup_requirements[{i}]", "must be a mapping",
                ))
                continue
            for f in ("id", "needs", "used_for"):
                if f not in req:
                    issues.append(Issue(
                        path, f"setup_requirements[{i}].{f}", "missing",
                    ))

    # requires_sub_skills / requires_tools shape (values checked at cross-reference time)
    # v2 uses requires_sub_skills; v1 uses requires_tools. Accept both for backward compat.
    rt = data.get("requires_sub_skills") or data.get("requires_tools")
    rt_field = "requires_sub_skills" if "requires_sub_skills" in data else "requires_tools"
    if rt is not None and not isinstance(rt, dict):
        issues.append(Issue(
            path, rt_field, "must be a mapping (possibly empty)",
        ))

    # Q-new22: soul_template + claude_template files must exist on disk,
    # relative to the manifest's own directory.
    role_dir = Path(path).parent
    for field in ("soul_template", "claude_template"):
        value = data.get(field)
        if not isinstance(value, str) or not value:
            issues.append(Issue(
                path, field, "must be a non-empty string path",
            ))
            continue
        target = role_dir / value
        if not target.exists():
            issues.append(Issue(
                path, field,
                f"file not found: {value} (expected at {target.relative_to(role_dir.parent.parent)})",
            ))

    _check_domain_only(issues, path, data, [
        "display_name", "tagline", "description",
    ])

    return issues


def validate_tool_manifest(path, data):
    issues = []
    required = [
        "schema_version", "id", "display_name", "category",
        "description", "provider", "applicable_roles", "sub_skill",
    ]
    _check_required(issues, path, data, required)
    if issues:
        return issues

    if data["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(Issue(
            path, "schema_version",
            f"unknown schema_version {data['schema_version']!r}",
        ))

    dirname = Path(path).parent.name
    if data["id"] != dirname:
        issues.append(Issue(
            path, "id",
            f"id {data['id']!r} does not match directory {dirname!r}",
        ))

    if data["category"] not in VALID_TOOL_CATEGORIES:
        issues.append(Issue(
            path, "category",
            f"invalid category {data['category']!r}; "
            f"must be one of {sorted(VALID_TOOL_CATEGORIES)}",
        ))

    if data["provider"] not in VALID_PROVIDERS:
        issues.append(Issue(
            path, "provider",
            f"invalid provider {data['provider']!r}; "
            f"must be one of {sorted(VALID_PROVIDERS)}",
        ))

    if data["provider"] == "mcp" and not data.get("mcp_name"):
        issues.append(Issue(
            path, "mcp_name", "required when provider is 'mcp'",
        ))

    if not isinstance(data["applicable_roles"], list):
        issues.append(Issue(path, "applicable_roles", "must be a list"))

    tool_dir = Path(path).parent
    sub_skill_path = tool_dir / data["sub_skill"]
    if not sub_skill_path.exists():
        issues.append(Issue(
            path, "sub_skill",
            f"sub-skill file not found: {sub_skill_path.name}",
        ))

    setup_path = tool_dir / "setup.md"
    if not setup_path.exists():
        issues.append(Issue(
            path, "", "missing setup.md in tool directory",
        ))

    _check_domain_only(issues, path, data, ["display_name", "description"])
    return issues


def validate_preset_manifest(path, data):
    issues = []
    required = [
        "schema_version", "id", "display_name",
        "description", "role_install_order",
    ]
    _check_required(issues, path, data, required)
    if issues:
        return issues

    if data["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(Issue(
            path, "schema_version",
            f"unknown schema_version {data['schema_version']!r}",
        ))

    dirname = Path(path).parent.name
    if data["id"] != dirname:
        issues.append(Issue(
            path, "id",
            f"id {data['id']!r} does not match directory {dirname!r}",
        ))

    if not isinstance(data["role_install_order"], list):
        issues.append(Issue(
            path, "role_install_order", "must be a list",
        ))

    _check_domain_only(issues, path, data, ["display_name", "description"])
    return issues


# ---------------------------------------------------------------------------
# Cycle detection — intentionally NOT implemented. See the module docstring
# for the reasoning. routes_to is a per-item hand-off preference, not a flow
# DAG, so graph-level cycles are legitimate topology (e.g. PM <-> Designer).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Registry loader + cross-reference checker
# ---------------------------------------------------------------------------


def _load_kind(base_dir, kind_dir, validator):
    """Load every manifest under base_dir/kind_dir/*/manifest.yaml.

    Returns (loaded_dict, issues). `loaded_dict` only contains manifests
    that validated cleanly at the per-file level. Anything with errors is
    excluded so cross-reference checks don't cascade.
    """
    issues = []
    loaded = {}
    dir_path = Path(base_dir) / kind_dir
    if not dir_path.exists():
        return loaded, issues
    for d in sorted(dir_path.iterdir()):
        if not d.is_dir():
            continue
        manifest = d / "manifest.yaml"
        if not manifest.exists():
            issues.append(Issue(
                str(d.relative_to(base_dir.parent)) if hasattr(base_dir, "parent") else str(d),
                "", "missing manifest.yaml",
            ))
            continue
        data, err = _load_yaml(manifest)
        if err:
            issues.append(err)
            continue
        file_issues = validator(manifest, data)
        issues.extend(file_issues)
        if not any(i.severity == "error" for i in file_issues):
            loaded[d.name] = data
    return loaded, issues


def validate_registry(base_dir=None):
    """Validate the entire manifest registry.

    Args:
        base_dir: path to the `references/` directory. Defaults to the
            shipped one. Tests override to use a tmp fixture.

    Returns:
        (issues, roles, tools, presets)
    """
    if base_dir is None:
        base_dir = DEFAULT_REFERENCES
    base_dir = Path(base_dir)

    issues = []

    roles, role_issues = _load_kind(base_dir, "roles", validate_role_manifest)
    issues.extend(role_issues)

    # v2: capabilities live under sub-skills/capabilities/; fall back to tools/ for v1 compat
    cap_dir = "sub-skills/capabilities" if (base_dir / "sub-skills" / "capabilities").exists() else "tools"
    tools, tool_issues = _load_kind(base_dir, cap_dir, validate_tool_manifest)
    issues.extend(tool_issues)

    presets, preset_issues = _load_kind(base_dir, "presets", validate_preset_manifest)
    issues.extend(preset_issues)

    # ----- Cross-reference checks -----

    # Role requires_sub_skills (or legacy requires_tools) must point at known capabilities
    for name, data in roles.items():
        rt = data.get("requires_sub_skills") or data.get("requires_tools") or {}
        rt_field = "requires_sub_skills" if "requires_sub_skills" in data else "requires_tools"
        if not isinstance(rt, dict):
            continue
        for kind in ("any_of", "all_of"):
            for tool_id in rt.get(kind) or []:
                if tool_id not in tools:
                    issues.append(Issue(
                        f"references/roles/{name}/manifest.yaml",
                        f"{rt_field}.{kind}",
                        f"unknown capability id {tool_id!r}; "
                        f"known capabilities: {sorted(tools.keys())}",
                    ))

    # Role routes_to must point at known roles
    for name, data in roles.items():
        for target in data.get("routes_to") or []:
            if target not in roles:
                issues.append(Issue(
                    f"references/roles/{name}/manifest.yaml",
                    "routes_to",
                    f"unknown role id {target!r}; "
                    f"known roles: {sorted(roles.keys())}",
                ))

    # (routes_to cycle detection intentionally omitted — see module docstring)

    # Capability applicable_roles must point at known roles
    for name, data in tools.items():
        for role_id in data.get("applicable_roles") or []:
            if role_id not in roles:
                issues.append(Issue(
                    f"references/sub-skills/capabilities/{name}/manifest.yaml",
                    "applicable_roles",
                    f"unknown role id {role_id!r}",
                ))

    # Preset role_install_order: existing roles + NOT always_installed
    for name, data in presets.items():
        for role_id in data.get("role_install_order") or []:
            if role_id not in roles:
                issues.append(Issue(
                    f"references/presets/{name}/manifest.yaml",
                    "role_install_order",
                    f"unknown role id {role_id!r}",
                ))
            elif roles[role_id].get("always_installed"):
                issues.append(Issue(
                    f"references/presets/{name}/manifest.yaml",
                    "role_install_order",
                    f"role {role_id!r} is always_installed and must not "
                    f"appear in role_install_order (Q-new16)",
                ))

    return issues, roles, tools, presets


# ---------------------------------------------------------------------------
# Pipeline resolution
# ---------------------------------------------------------------------------


def resolve_pipeline(preset_id, roles, presets):
    """Return the set of role ids installed by `preset_id`.

    Combines always_installed roles (infrastructure) with the preset's
    role_install_order (specialists). Raises KeyError on unknown preset.
    """
    if preset_id not in presets:
        raise KeyError(f"unknown preset {preset_id!r}")
    installed = {name for name, d in roles.items() if d.get("always_installed")}
    for r in presets[preset_id].get("role_install_order") or []:
        installed.add(r)
    return installed


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


_KIND_DIRS = {
    "roles": "roles",
    "capabilities": "sub-skills/capabilities",
    "tools": "sub-skills/capabilities",  # backward compat alias
    "presets": "presets",
}


def cmd_validate(_args):
    issues, roles, tools, presets = validate_registry()
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    for i in issues:
        stream = sys.stderr if i.severity == "error" else sys.stdout
        print(str(i), file=stream)
    if errors:
        print(
            f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1
    print(
        f"OK -- {len(roles)} role(s), {len(tools)} capability(ies), "
        f"{len(presets)} preset(s)"
    )
    return 0


def cmd_list(args):
    if not args:
        print("Usage: manifest.py list <roles|capabilities|presets>", file=sys.stderr)
        return 1
    kind = args[0]
    if kind not in _KIND_DIRS:
        print(
            f"Unknown kind {kind!r}; expected one of "
            f"{sorted(_KIND_DIRS)}", file=sys.stderr,
        )
        return 1
    dir_path = DEFAULT_REFERENCES / _KIND_DIRS[kind]
    if not dir_path.exists():
        return 0
    for d in sorted(dir_path.iterdir()):
        if d.is_dir() and (d / "manifest.yaml").exists():
            print(d.name)
    return 0


def cmd_load(args):
    if len(args) < 2:
        print(
            "Usage: manifest.py load <roles|capabilities|presets> <id>",
            file=sys.stderr,
        )
        return 1
    kind, id_ = args[0], args[1]
    if kind not in _KIND_DIRS:
        print(f"Unknown kind {kind!r}", file=sys.stderr)
        return 1
    manifest = DEFAULT_REFERENCES / _KIND_DIRS[kind] / id_ / "manifest.yaml"
    if not manifest.exists():
        print(f"Not found: {manifest}", file=sys.stderr)
        return 1
    data, err = _load_yaml(manifest)
    if err:
        print(str(err), file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, default=str))
    return 0


def cmd_resolve(args):
    if not args:
        print("Usage: manifest.py resolve <preset-id>", file=sys.stderr)
        return 1
    issues, roles, tools, presets = validate_registry()
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        for e in errors:
            print(str(e), file=sys.stderr)
        print(
            "Registry has errors -- fix them before resolving.",
            file=sys.stderr,
        )
        return 1
    try:
        resolved = resolve_pipeline(args[0], roles, presets)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    for r in sorted(resolved):
        print(r)
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "validate": cmd_validate,
        "list": cmd_list,
        "load": cmd_load,
        "resolve": cmd_resolve,
    }
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 1
    return dispatch[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
