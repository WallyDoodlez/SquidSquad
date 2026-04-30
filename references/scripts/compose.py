#!/usr/bin/env python3
"""SquidSquad sub-skill composition engine.

Reads role entry files, resolves {{include: path}} directives by inlining
the referenced sub-skill content, and wraps each inclusion with
<!-- sub-skill: name --> section markers.

Usage:
    python scripts/compose.py dev-agent        # Compose dev agent template
    python scripts/compose.py pm-agent         # Compose PM/QA template
    python scripts/compose.py all              # Compose all roles to agent-instructions.md
    python scripts/compose.py --help
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SUB_SKILLS_DIR = REPO_ROOT / "references" / "sub-skills"
CAPABILITIES_DIR = REPO_ROOT / "references" / "sub-skills" / "capabilities"
ROLES_DIR = REPO_ROOT / "references" / "roles"
OUTPUT_FILE = REPO_ROOT / "references" / "agent-instructions.md"


def _strip_outer_markers(content: str, name: str) -> str:
    """Strip matching sub-skill open/close markers from the first/last lines.

    Source sub-skill files contain their own markers. Since compose.py wraps
    each include in markers, strip the source markers to avoid doubling (#2537).
    """
    lines = content.splitlines()
    open_marker = f"<!-- sub-skill: {name} -->"
    close_marker = f"<!-- /sub-skill: {name} -->"
    if lines and lines[0].strip() == open_marker:
        lines = lines[1:]
    if lines and lines[-1].strip() == close_marker:
        lines = lines[:-1]
    return "\n".join(lines)


def _resolve_capability(cap_id: str) -> list[str]:
    """Resolve a {{capability: id}} directive into content lines."""
    full_path = CAPABILITIES_DIR / cap_id / "sub-skill.md"
    if not full_path.exists():
        return [f"<!-- ERROR: Missing capability: {cap_id} -->"]
    content = full_path.read_text(encoding="utf-8").rstrip()
    content = _strip_outer_markers(content, f"capability-{cap_id}")
    return [
        f"<!-- sub-skill: capability-{cap_id} -->",
        content,
        f"<!-- /sub-skill: capability-{cap_id} -->",
    ]


def _resolve_runtime(runtime_path: str) -> list[str]:
    """Resolve a {{runtime: path}} directive into content lines."""
    sub_skill_name = Path(runtime_path).stem
    return [
        f"<!-- sub-skill: {sub_skill_name} -->",
        "## Soul",
        "",
        "Read `.squidsquad/[ROLE]/SOUL.md` at session start and follow its "
        "instructions as your professional identity. If SOUL.md is missing, "
        "proceed with default behavior — you are a pragmatic engineer focused "
        "on correctness and simplicity.",
        f"<!-- /sub-skill: {sub_skill_name} -->",
    ]


def _resolve_includes(entry_file: Path) -> str:
    """Resolve all {{include: path}} directives in an entry file."""
    text = entry_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    result = []

    for line in lines:
        # {{include: path}} — inline the content
        inc_match = re.match(r'\s*\{\{include:\s*(.+?)\}\}\s*$', line)
        # {{runtime: path}} — emit a "read at boot" instruction
        rt_match = re.match(r'\s*\{\{runtime:\s*(.+?)\}\}\s*$', line)
        # {{capability: id}} — inline a capability sub-skill
        cap_match = re.match(r'\s*\{\{capability:\s*(.+?)\}\}\s*$', line)

        if inc_match:
            include_path = inc_match.group(1).strip()
            full_path = SUB_SKILLS_DIR / f"{include_path}.md"
            if not full_path.exists():
                result.append(f"<!-- ERROR: Missing include: {include_path} -->")
                continue
            sub_skill_name = full_path.stem
            content = full_path.read_text(encoding="utf-8").rstrip()
            content = _strip_outer_markers(content, sub_skill_name)
            result.append(f"<!-- sub-skill: {sub_skill_name} -->")
            result.append(content)
            result.append(f"<!-- /sub-skill: {sub_skill_name} -->")

        elif cap_match:
            cap_id = cap_match.group(1).strip()
            result.extend(_resolve_capability(cap_id))

        elif rt_match:
            runtime_path = rt_match.group(1).strip()
            result.extend(_resolve_runtime(runtime_path))

        else:
            result.append(line)

    return "\n".join(result)


def _load_manifest(role_name: str) -> list | None:
    """Load includes.yml for a role, with variant inheritance.

    Returns a list of include paths (e.g. ['common/tracker-protocol', ...])
    or None if no manifest exists.

    Supports two schemas:
    - Base role (Layer 2): ``includes: [list]``
    - Variant (Layer 3): ``base_role: <base>`` + ``additional_includes: [list]``
      Recursively loads the base role's manifest and appends additional includes.

    Dev variants (skill, be, fe) without their own includes.yml inherit
    from references/roles/dev/includes.yml. Non-dev variants use
    _strip_variant_suffix() to find their base role.
    """
    if yaml is None:
        return None

    # Try nested variant path first (dev-skill -> dev/skill/includes.yml)
    resolved = _resolve_variant(role_name)
    if resolved:
        base, variant = resolved
        manifest_path = ROLES_DIR / base / variant / "includes.yml"
    else:
        manifest_path = ROLES_DIR / role_name / "includes.yml"
    if not manifest_path.exists():
        # Legacy dev variant inheritance: fall back to dev manifest
        identities = _list_known_role_identities()
        if role_name not in identities and "dev" in identities:
            manifest_path = ROLES_DIR / "dev" / "includes.yml"
        if not manifest_path.exists():
            return None

    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: Failed to parse {manifest_path}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        return None

    # Layer 3 variant schema: base_role + additional_includes
    if "base_role" in data:
        base_role = data["base_role"]
        base_includes = _load_manifest(base_role)
        if base_includes is None:
            print(
                f"ERROR: includes.yml for {role_name} declares base_role={base_role} "
                f"but {base_role} has no includes.yml",
                file=sys.stderr,
            )
            sys.exit(1)
        additional = data.get("additional_includes", [])
        if not isinstance(additional, list):
            additional = []
        # Validate additional includes
        for inc_path in additional:
            full_path = SUB_SKILLS_DIR / f"{inc_path}.md"
            if not full_path.exists():
                print(
                    f"ERROR: includes.yml for {role_name} references missing "
                    f"sub-skill: {inc_path} (expected at {full_path})",
                    file=sys.stderr,
                )
                sys.exit(1)
        return base_includes + additional

    # Base role schema: includes list
    if "includes" not in data:
        return None
    includes = data["includes"]
    if not isinstance(includes, list):
        return None

    # Validate all paths exist
    for inc_path in includes:
        full_path = SUB_SKILLS_DIR / f"{inc_path}.md"
        if not full_path.exists():
            print(
                f"ERROR: includes.yml for {role_name} references missing "
                f"sub-skill: {inc_path} (expected at {full_path})",
                file=sys.stderr,
            )
            sys.exit(1)

    return includes


def _resolve_includes_with_manifest(entry_file: Path, manifest: list) -> str:
    """Resolve includes using manifest order, preserving inline content.

    The manifest declares which sub-skills to include. The entry file's
    {{include:}} directives are replaced with manifest-resolved content.
    Inline (non-include) content is preserved in its original position.
    """
    text = entry_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    result = []

    # Build a set of manifest includes for quick lookup
    manifest_set = set(manifest)

    for line in lines:
        inc_match = re.match(r'\s*\{\{include:\s*(.+?)\}\}\s*$', line)
        rt_match = re.match(r'\s*\{\{runtime:\s*(.+?)\}\}\s*$', line)
        cap_match = re.match(r'\s*\{\{capability:\s*(.+?)\}\}\s*$', line)

        if inc_match:
            include_path = inc_match.group(1).strip()

            # Check if the manifest overrides this include
            # (e.g. vault-protocol -> vault-protocol-slim)
            resolved_path = include_path
            if include_path not in manifest_set:
                # Check for a variant in the manifest that shares the
                # same base name (e.g. vault-protocol-slim for vault-protocol)
                base = include_path.rsplit("/", 1)[-1] if "/" in include_path else include_path
                prefix = include_path.rsplit("/", 1)[0] + "/" if "/" in include_path else ""
                found = False
                for m in manifest:
                    m_base = m.rsplit("/", 1)[-1] if "/" in m else m
                    if m_base.startswith(base + "-") or base.startswith(m_base + "-"):
                        resolved_path = m
                        found = True
                        break
                if not found:
                    # Include is in the template but not in the manifest — skip it
                    # This enables manifest-driven removal in Phase B
                    continue

            full_path = SUB_SKILLS_DIR / f"{resolved_path}.md"
            if not full_path.exists():
                result.append(f"<!-- ERROR: Missing include: {resolved_path} -->")
                continue
            sub_skill_name = full_path.stem
            content = full_path.read_text(encoding="utf-8").rstrip()
            content = _strip_outer_markers(content, sub_skill_name)
            result.append(f"<!-- sub-skill: {sub_skill_name} -->")
            result.append(content)
            result.append(f"<!-- /sub-skill: {sub_skill_name} -->")

        elif cap_match:
            cap_id = cap_match.group(1).strip()
            result.extend(_resolve_capability(cap_id))

        elif rt_match:
            runtime_path = rt_match.group(1).strip()
            sub_skill_name = Path(runtime_path).stem
            result.append(f"<!-- sub-skill: {sub_skill_name} -->")
            result.append("## Soul")
            result.append("")
            result.append("Read `.squidsquad/[ROLE]/SOUL.md` at session start and follow its instructions as your professional identity. If SOUL.md is missing, proceed with default behavior — you are a pragmatic engineer focused on correctness and simplicity.")
            result.append(f"<!-- /sub-skill: {sub_skill_name} -->")

        else:
            result.append(line)

    return "\n".join(result)


def _assemble_claude(role_name: str) -> str:
    """Assemble a CLAUDE.md template from Layer 1 + Layer 2 + Layer 3 sources.

    Same concatenation pattern as _assemble_soul():
    - Layer 1: references/roles/base/CLAUDE.md (shared agent definition)
    - Layer 2: references/roles/<role>/CLAUDE.md (role definition)
    - Layer 3: references/roles/<variant>/CLAUDE.md (variant customization)

    The assembled template still contains {{include:}} directives which
    are resolved separately by _resolve_includes_with_manifest().
    """
    parts = []

    # Layer 1 — Base agent instructions (at roles/ root)
    base_claude = BASE_ROLE_DIR / "instructions.md"
    if base_claude.exists():
        parts.append(base_claude.read_text(encoding="utf-8").rstrip())
        parts.append("")

    # Layer 2 — Role instructions (the role's entry template)
    role_identity = _get_entry_file_for_role(role_name)
    role_claude = ROLES_DIR / role_identity / "instructions.md"
    if role_claude.exists():
        parts.append(role_claude.read_text(encoding="utf-8").rstrip())

    # Layer 3 — Variant instructions (nested: roles/<base>/<variant>/)
    resolved = _resolve_variant(role_name)
    if resolved:
        base, variant = resolved
        variant_claude = ROLES_DIR / base / variant / "instructions.md"
        if variant_claude.exists():
            parts.append("")
            parts.append(variant_claude.read_text(encoding="utf-8").rstrip())

    # Layer 4 — Project sub-skills (PM-owned, applied to all agents)
    # PM writes sub-skills to references/sub-skills/project/*.md
    # These are auto-included in every agent's CLAUDE.md if present.
    project_skills_dir = SUB_SKILLS_DIR / "project"
    if project_skills_dir.is_dir():
        for skill_file in sorted(project_skills_dir.glob("*.md")):
            content = skill_file.read_text(encoding="utf-8").rstrip()
            name = skill_file.stem
            content = _strip_outer_markers(content, name)
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append(f"<!-- sub-skill: project-{name} -->")
            parts.append(content)
            parts.append(f"<!-- /sub-skill: project-{name} -->")

    return "\n".join(parts)


def compose_role(role_name: str) -> str:
    """Compose a role's full CLAUDE.md from 3-layer assembly + include resolution.

    Step 1: Assemble the template from Layer 1 + Layer 2 + Layer 3 CLAUDE.md
            source files (same concatenation pattern as SOUL.md).
    Step 2: Resolve {{include:}}, {{runtime:}}, {{capability:}} directives
            using the role's includes.yml manifest.

    The result is a single flat CLAUDE.md with all sub-skills inlined.
    """
    # Step 1: Assemble template from 3 layers
    assembled = _assemble_claude(role_name)

    # Write to a temp file for include resolution (reuses existing logic)
    import tempfile
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text(assembled, encoding="utf-8")

    try:
        # Step 2: Resolve includes
        manifest = _load_manifest(role_name)
        if manifest is not None:
            composed = _resolve_includes_with_manifest(tmp, manifest)
        else:
            composed = _resolve_includes(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    return composed


def compose_all() -> str:
    """Compose the dev-agent template as the default agent-instructions.md."""
    # agent-instructions.md is the dev template (primary output)
    header = "<!-- GENERATED FILE — DO NOT EDIT. -->\n"
    header += "<!-- Source: references/roles/dev/instructions.md + sub-skills/ -->\n"
    header += "<!-- Regenerate with: python references/scripts/compose.py all -->\n\n"
    composed = compose_role("dev")
    return header + composed


def _read_config_value(field: str) -> str:
    """Read a config value using config.py.

    Degrades gracefully to "" when:
      - config.py is unavailable (import error)
      - the field does not exist (config.py calls sys.exit(1) -> SystemExit)
      - anything else goes wrong during parsing

    This matters for the wizard's scaffolder path: when installing a fresh
    agent variant like `be` into a scratch directory, the target config.md
    does not yet have `be-tests` / `be-framework` entries, and we must not
    hard-exit the whole process just because the field is missing. Empty
    string is the correct fallback — downstream callers substitute a
    friendly default.
    """
    try:
        from config import get_field
        return get_field(field)
    except SystemExit:
        return ""
    except BaseException:  # noqa: BLE001 — genuinely want a last-resort fallback
        return ""


def _list_known_role_identities():
    """Return the set of role identities shipped in `references/roles/`.

    A role identity is any directory under `references/roles/` that
    contains a `CLAUDE.md` entry-file template (the Q-new22 layout).
    We read the filesystem every time rather than caching so that
    tests which build a fresh role directory at runtime see the new
    role immediately — the hot path here is tiny (a single readdir).
    """
    if not ROLES_DIR.exists():
        return set()
    return {
        d.name for d in ROLES_DIR.iterdir()
        if d.is_dir() and (d / "instructions.md").exists()
    }


def _get_entry_file_for_role(role_name: str) -> str:
    """Map an agent instance to its role identity for composition.

    After Q-new22 each role has its own self-contained directory at
    `references/roles/<role>/`. For any role that exists in the registry
    the identity equals the role name. Anything else is resolved via:
    1. Suffix-strip: pm-skill -> pm (Layer 3 variant of any base role)
    2. Dev fallback: skill, be, fe -> dev (legacy dev variants)

    After #328 Phase H the identity list is read from the manifest
    registry, not hardcoded — adding a new role directory under
    `references/roles/` automatically makes it a first-class identity
    without any compose.py edit.
    """
    identities = _list_known_role_identities()
    if role_name in identities:
        return role_name
    # Layer 3 variant: resolve nested directory (dev-skill -> dev/skill/)
    resolved = _resolve_variant(role_name)
    if resolved:
        base, _ = resolved
        return base
    # Dev variants (skill, be, fe, bespoke names) compose from the
    # `dev` role template as long as one exists in the registry.
    if "dev" in identities:
        return "dev"
    # No registry, or no `dev` identity — fall back to the literal
    # role name so at least the error message points at the right file.
    return role_name


def _substitute_placeholders(content: str, role_name: str, entry_file: str) -> str:
    """Substitute role-specific placeholders in composed content.

    [ROLE] and [ROLE_UPPER] are substituted for ALL roles (needed by
    cycle-runner sub-skill which is shared across all agents).
    [ROLE_TEST_CMD], [OTHER_ROLES] are dev-only.
    """
    is_dev = entry_file == "dev"

    # Universal substitution — all roles need [ROLE] for cycle-runner paths
    content = content.replace("[ROLE]", role_name)
    content = content.replace("[ROLE_UPPER]", role_name.upper())

    if is_dev:

        # Test command
        test_cmd = _read_config_value(f"{role_name}-tests") or \
                   f'echo "{role_name.title()} repo -- no automated tests."'
        content = content.replace("[ROLE_TEST_CMD]", test_cmd)

        # Other roles
        all_agents = _read_config_value("dev-agents") or role_name
        other = [r.strip() for r in all_agents.split(",") if r.strip() != role_name]
        content = content.replace("[OTHER_ROLES]", ", ".join(other) if other else "(none)")

    # Shared placeholders (all roles)
    interval = _read_config_value("interval") or "30"
    content = content.replace("[INTERVAL]", interval)

    # PM/DM-specific
    if not is_dev:
        active_agents = _read_config_value("dev-agents") or ""
        content = content.replace("[ACTIVE_AGENTS]", active_agents)

        e2e_cmd = _read_config_value("e2e-tests") or "(none)"
        content = content.replace("[E2E_TEST_CMD]", e2e_cmd)

    return content


def deploy_role(role_name: str, target_root: Path = None) -> Path:
    """Full pipeline: compose entry file -> substitute placeholders -> write CLAUDE.md.

    Args:
        role_name: the agent instance id (e.g. "skill", "be", "fe", "pm").
            Resolves to a role identity via `_get_entry_file_for_role`.
        target_root: base directory that will contain `.squidsquad/<role_name>/`.
            Defaults to REPO_ROOT (the installed repo). Tests override to
            write into a scratch directory without touching the real install.

    Returns the absolute path of the composed CLAUDE.md.
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)

    entry_file = _get_entry_file_for_role(role_name)
    composed = compose_role(role_name)
    final = _substitute_placeholders(composed, role_name, entry_file)

    header = f"# SquidSquad -- {role_name} Lead\n\n"
    header += f"<!-- GENERATED by compose.py deploy {role_name}. DO NOT EDIT. -->\n"
    header += f"<!-- Regenerate: python references/scripts/compose.py deploy {role_name} -->\n\n"

    output_path = target_root / ".squidsquad" / role_name / "CLAUDE.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(header + final, encoding="utf-8")

    # Assemble SOUL.md from 3 layers if missing (#3465 layered architecture).
    # Never overwrite an existing local SOUL.md — use upgrade_soul() for that.
    soul_path = target_root / ".squidsquad" / role_name / "SOUL.md"
    if not soul_path.exists():
        _assemble_and_write_soul(role_name, target_root)

    return output_path


# Layer 1 source files live at the root of ROLES_DIR (no subdirectory)
BASE_ROLE_DIR = ROLES_DIR

# Layer boundary marker in assembled SOUL.md
SOUL_LAYER_BASE_START = "<!-- layer: base -->"
SOUL_LAYER_BASE_END = "<!-- /layer: base -->"


def _resolve_variant(role_name: str) -> tuple[str, str] | None:
    """Resolve a variant role name to (base_role, variant_name).

    Layer 3 variants live nested inside their base role directory:
    references/roles/<base>/<variant>/. The agent instance name uses
    a hyphen convention: dev-skill -> roles/dev/skill/.

    Returns (base, variant) or None if not a variant.

    Examples:
        dev-skill  -> ("dev", "skill")
        pm-ios     -> ("pm", "ios")
        pm         -> None (base role, not a variant)
        skill      -> None (legacy dev variant without hyphen)
    """
    if "-" not in role_name:
        return None
    base, variant = role_name.split("-", 1)
    variant_dir = ROLES_DIR / base / variant
    if variant_dir.is_dir() and (variant_dir / "instructions.md").exists():
        return base, variant
    # Fallback: check if base is a known identity
    identities = _list_known_role_identities()
    if base in identities and (ROLES_DIR / base / variant).is_dir():
        return base, variant
    return None


def _assemble_soul(role_name: str) -> str:
    """Assemble a flat SOUL.md from Layer 1 (base) + role SOUL.

    Layer 1: references/roles/SOUL.md (at roles root — shared agent identity)
    Role SOUL: for variants (dev-skill), try roles/dev/skill/SOUL.md first,
    then fall back to roles/dev/SOUL.md. For base roles, use roles/<role>/SOUL.md.

    Layer markers are embedded so upgrade_soul() can identify boundaries.
    """
    parts = []

    # Layer 1 — Base agent SOUL (at roles/ root)
    base_soul = BASE_ROLE_DIR / "SOUL.md"
    if base_soul.exists():
        parts.append(SOUL_LAYER_BASE_START)
        parts.append(base_soul.read_text(encoding="utf-8").rstrip())
        parts.append(SOUL_LAYER_BASE_END)
        parts.append("")

    # Layer 2 — Role SOUL (base role's SOUL.md)
    resolved = _resolve_variant(role_name)
    if resolved:
        base, variant = resolved
        # Variants always get the base role's SOUL (Layer 2)
        role_soul_path = ROLES_DIR / base / "SOUL.md"
    else:
        role_soul_path = ROLES_DIR / role_name / "SOUL.md"
        if not role_soul_path.exists():
            # Legacy dev variant fallback (skill -> dev)
            role_identity = _get_entry_file_for_role(role_name)
            role_soul_path = ROLES_DIR / role_identity / "SOUL.md"

    if role_soul_path.exists():
        parts.append(role_soul_path.read_text(encoding="utf-8").rstrip())

    # Layer 3 — Variant SOUL (variant-specific personality delta)
    if resolved:
        base, variant = resolved
        variant_soul_path = ROLES_DIR / base / variant / "SOUL.md"
        if variant_soul_path.exists():
            parts.append("")
            parts.append(variant_soul_path.read_text(encoding="utf-8").rstrip())

    return "\n".join(parts) + "\n"


def _assemble_and_write_soul(role_name: str, target_root: Path = None):
    """Assemble SOUL.md from 3 layers and write atomically."""
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)

    content = _assemble_soul(role_name)
    soul_path = target_root / ".squidsquad" / role_name / "SOUL.md"
    soul_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: .tmp then rename
    tmp_path = soul_path.with_suffix(".md.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(soul_path)


def upgrade_soul(role_name: str, target_root: Path = None) -> Path:
    """Re-render Layer 1 (base) of a deployed SOUL.md, preserving role content.

    This function is used during upgrades to pick up improvements to the
    base agent identity without clobbering the role's personality,
    Project Context, Project-Specific Responsibilities, or Project Adaptation.

    If no deployed SOUL.md exists, falls through to full assembly.
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)

    soul_path = target_root / ".squidsquad" / role_name / "SOUL.md"
    if not soul_path.exists():
        _assemble_and_write_soul(role_name, target_root)
        return soul_path

    existing = soul_path.read_text(encoding="utf-8")

    # Find role content boundary: everything after the base end marker
    # is role-specific content (preserved on upgrade).
    role_content = None
    if SOUL_LAYER_BASE_END in existing:
        idx = existing.index(SOUL_LAYER_BASE_END) + len(SOUL_LAYER_BASE_END)
        role_content = existing[idx:].lstrip("\n")
    else:
        # Legacy flat SOUL.md with no layer markers — treat entire file as role content
        role_content = existing

    # Re-render Layer 1 from current template
    parts = []
    base_soul = BASE_ROLE_DIR / "SOUL.md"
    if base_soul.exists():
        parts.append(SOUL_LAYER_BASE_START)
        parts.append(base_soul.read_text(encoding="utf-8").rstrip())
        parts.append(SOUL_LAYER_BASE_END)
        parts.append("")

    # Append preserved role content
    if role_content:
        parts.append(role_content.rstrip())

    content = "\n".join(parts) + "\n"

    # Atomic write
    tmp_path = soul_path.with_suffix(".md.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(soul_path)

    return soul_path


def generate_local_config(roles: list, target_root: Path = None,
                          clone_paths: dict = None) -> Path:
    """Generate .squidsquad/.local-config with clone paths for all agents.

    Args:
        roles: list of role/agent id strings.
        target_root: the primary repo root (where .squidsquad/ lives).
        clone_paths: optional dict mapping role -> relative path string
            (e.g. {"pm": ".", "skill": "../project-skill"}). When provided,
            paths are written as-is (relative). When omitted, all agents
            map to "." (single-repo fallback).
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root).resolve()

    lines = [
        "# Agent clone paths — auto-generated by compose.py",
        "# Format: - **role**: <relative-path>",
        "# Relative paths resolve against the primary repo root.",
        "",
    ]
    for role in roles:
        if clone_paths and role in clone_paths:
            path_str = clone_paths[role]
        else:
            path_str = "."
        lines.append(f"- **{role}**: {path_str}")

    config_path = target_root / ".squidsquad" / ".local-config"
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


TEMPLATES_DIR = REPO_ROOT / "references" / "templates"


def boot_role(role_name: str, target_root: Path = None) -> list:
    """Generate boot scripts (start-[role].sh and start-[role].ps1) from templates."""
    root = Path(target_root) if target_root else REPO_ROOT
    outputs = []
    for ext in ("sh", "ps1"):
        template_path = TEMPLATES_DIR / f"start-role.{ext}"
        if not template_path.exists():
            print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
            sys.exit(1)

        content = template_path.read_text(encoding="utf-8")
        content = content.replace("{{ROLE}}", role_name)

        output_path = root / ".squidsquad" / f"start-{role_name}.{ext}"
        # .sh files must use LF line endings (not CRLF on Windows)
        # .ps1 files need UTF-8 BOM so PowerShell parses Unicode correctly
        newline = "\n" if ext == "sh" else None
        enc = "utf-8-sig" if ext == "ps1" else "utf-8"
        output_path.write_text(content, encoding=enc, newline=newline)
        outputs.append(output_path)

    return outputs


def _collect_all_roles() -> list:
    """Return all configured roles: dev-agents from config + pm + dm (if present)."""
    agents = _read_config_value("dev-agents") or ""
    roles = [r.strip() for r in agents.split(",") if r.strip()]
    roles.append("pm")  # PM always present
    dm_dir = REPO_ROOT / ".squidsquad" / "dm"
    if dm_dir.exists():
        roles.append("dm")
    return roles


def boot_all() -> list:
    """Generate boot scripts for all configured roles."""
    roles = _collect_all_roles()
    all_outputs = []
    for role in roles:
        outputs = boot_role(role)
        all_outputs.extend(outputs)
    return all_outputs


def main():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        # List available role identities
        if ROLES_DIR.exists():
            roles = [
                d.name for d in ROLES_DIR.iterdir()
                if d.is_dir() and (d / "instructions.md").exists()
            ]
            print(f"Available roles: {', '.join(sorted(roles))}")
        sys.exit(0)

    cmd = args[0]

    if cmd == "all":
        content = compose_all()
        OUTPUT_FILE.write_text(content, encoding="utf-8")
        print(f"Composed agent-instructions.md ({len(content.splitlines())} lines)")

    elif cmd == "deploy":
        if len(args) < 2:
            print("Usage: compose.py deploy <role>", file=sys.stderr)
            print("  e.g.: compose.py deploy skill", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        try:
            output = deploy_role(role_name)
            lines = output.read_text(encoding="utf-8").count("\n")
            print(f"Deployed {role_name} CLAUDE.md ({lines} lines) -> {output.relative_to(REPO_ROOT)}")
        except (SystemExit, Exception) as e:
            print(f"ERROR: Failed to deploy role '{role_name}': {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "deploy-all":
        # Deploy all configured agents
        roles = _collect_all_roles()
        failed = []
        for role in roles:
            try:
                output = deploy_role(role)
                lines = output.read_text(encoding="utf-8").count("\n")
                print(f"  {role}: {lines} lines -> {output.relative_to(REPO_ROOT)}")
            except (SystemExit, Exception) as e:
                print(f"  {role}: FAILED — {e}", file=sys.stderr)
                failed.append(role)
        if failed:
            print(f"ERROR: {len(failed)} role(s) failed: {', '.join(failed)}", file=sys.stderr)
        # Generate .local-config for health check and auto-boot
        lc = generate_local_config(roles)
        print(f"  .local-config: {len(roles)} agents -> {lc.relative_to(REPO_ROOT)}")

    elif cmd == "upgrade-soul":
        if len(args) < 2:
            print("Usage: compose.py upgrade-soul <role>", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        soul_path = upgrade_soul(role_name)
        lines = soul_path.read_text(encoding="utf-8").count("\n")
        print(f"Upgraded {role_name} SOUL.md ({lines} lines) -> {soul_path.relative_to(REPO_ROOT)}")

    elif cmd == "boot":
        if len(args) < 2:
            print("Usage: compose.py boot <role>", file=sys.stderr)
            print("  e.g.: compose.py boot skill", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        outputs = boot_role(role_name)
        for out in outputs:
            print(f"Generated {out.relative_to(REPO_ROOT)}")

    elif cmd == "boot-all":
        outputs = boot_all()
        for out in outputs:
            print(f"  {out.relative_to(REPO_ROOT)}")

    else:
        # Treat as role entry file name
        content = compose_role(cmd)
        print(content)


if __name__ == "__main__":
    main()
