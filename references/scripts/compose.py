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

import json
import re
import subprocess
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

# #9588: fragments the boot-bootstrap Reads at runtime. These MUST stay
# out of every composed CLAUDE.md regardless of what the manifest looks
# like — even a future manifest entry whose stem matches one of these
# names via the variant-resolution fallback in
# `_resolve_includes_with_manifest` would otherwise silently re-inline a
# mode-specific fragment and defeat the lazy-load design. Checked
# explicitly before the variant heuristic so the heuristic cannot win.
RUNTIME_READ_FRAGMENTS = frozenset({
    "roles/dev/ralph-loop-overview",
    "roles/pm/ralph-loop-overview",
    "roles/qa/ralph-loop-overview",
    "roles/dm/ralph-loop-overview",
    "common-events/event-driven-workflow",
    "common-events/l1-base",
    "common-events/cursor-management",
    "common-events/forge-read-pattern",
    "common-events/idle-cooldown-loop",
    "common-events/comment-handling",
    "roles/dm/events/pr-merge-wait",
})


def _get_wake_mode(role_name: str) -> str:
    """Determine a role's wake mode from config.md (#8697).

    Lookup precedence: `event-driven-<role>` → `event-driven` → default `polling`.
    Values normalize to `event-driven` (yes/true/1) or `polling`.

    `config.get_field` prints `ERROR: Field 'X' not found` to stderr and
    calls `sys.exit(1)` for missing fields. Field absence is the documented
    default for both wake-mode fields, so suppress stderr while probing —
    QA's `test_malformed_repo_scan_warns_not_crashes` (#8697 R3 retro fix)
    asserts no spurious ERROR output during normal compose.
    """
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from config import get_field
    except Exception:
        return "polling"
    import contextlib
    import io
    for field in (f"event-driven-{role_name}", "event-driven"):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                v = (get_field(field) or "").strip().lower()
        except BaseException:
            # config.get_field calls sys.exit(1) on missing field — caught
            # via SystemExit. Also tolerate FileNotFoundError/PermissionError
            # from a config.md TOCTOU race (matches the defensive pattern in
            # `_read_config_value` further down this file).
            v = ""
        if v in ("yes", "true", "1", "event-driven"):
            return "event-driven"
        if v in ("no", "false", "0", "polling"):
            return "polling"
    return "polling"


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


def _resolve_includes(entry_file: Path, wake_mode: str = "polling") -> str:
    """Resolve all {{include: path}} directives in an entry file.

    Manifest-less fallback path used when no includes.yml exists or pyyaml
    is unavailable. This path does NOT perform mode-aware filtering — every
    `{{include:}}` directive in the template is rendered. Mode filtering
    requires the manifest to know which fragments are mode-specific
    (#8697 design). `wake_mode` is accepted for API symmetry with
    `_resolve_includes_with_manifest` but currently has no effect here.
    """
    # `wake_mode` is intentionally unused; see docstring.
    del wake_mode  # silence "unused" linters; keeps the signature stable
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


def _load_manifest(role_name: str, wake_mode: str = "polling") -> list | None:
    """Load the role's wake-mode-specific manifest with variant inheritance.

    `wake_mode='polling'`  → `includes.yml`           (default; pre-existing)
    `wake_mode='event-driven'` → `includes-events.yml` (falls back to
                                 `includes.yml` if it doesn't exist yet)

    Per PM directive (#8697): parallel manifests with NO mode-conditional
    logic inside fragments. compose.py selects the entire manifest based on
    the role's wake mode; the chosen manifest is rendered in full.

    Returns a list of include paths (e.g. ['common/cycle-runner', ...]) or
    None if no manifest exists.

    Supports two schemas:
    - Base role (Layer 2): ``includes: [list]``
    - Variant (Layer 3): ``base_role: <base>`` + ``additional_includes: [list]``
      Recursively loads the base role's manifest and appends additional includes.
    """
    if yaml is None:
        return None

    # #8697: choose the right manifest filename based on wake mode.
    primary_name = "includes-events.yml" if wake_mode == "event-driven" else "includes.yml"
    fallback_name = "includes.yml"  # used when event-driven manifest absent

    def _resolve_manifest_path(role_dir: Path) -> Path | None:
        primary = role_dir / primary_name
        if primary.exists():
            return primary
        if primary_name != fallback_name:
            fallback = role_dir / fallback_name
            if fallback.exists():
                return fallback
        return None

    # Try nested variant path first (dev-skill -> dev/skill/<manifest>)
    resolved = _resolve_variant(role_name)
    if resolved:
        base, variant = resolved
        manifest_path = _resolve_manifest_path(ROLES_DIR / base / variant)
    else:
        manifest_path = _resolve_manifest_path(ROLES_DIR / role_name)
    if manifest_path is None:
        # Legacy dev variant inheritance: fall back to dev manifest
        identities = _list_known_role_identities()
        if role_name not in identities and "dev" in identities:
            manifest_path = _resolve_manifest_path(ROLES_DIR / "dev")
        if manifest_path is None:
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
        base_includes = _load_manifest(base_role, wake_mode)
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


def _resolve_includes_with_manifest(entry_file: Path, manifest: list, wake_mode: str = "polling") -> str:
    """Resolve includes using manifest order, preserving inline content.

    The manifest declares which sub-skills to include. The entry file's
    {{include:}} directives are replaced with manifest-resolved content.
    Inline (non-include) content is preserved in its original position.

    Mode separation (#8697): wake_mode is resolved upstream by _load_manifest
    which selects an entire mode-specific manifest. By design, fragments
    themselves have no mode-conditional logic — the manifest IS the gate.
    `wake_mode` is threaded here only so future template-side directives
    (e.g. `{{include: mode-specific/foo}}`) can take advantage of it.
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

            # #9588: short-circuit before the variant heuristic for any
            # fragment the boot-bootstrap Reads at runtime. The variant-
            # resolution fallback below (`m_base.startswith(base + "-") …`)
            # is otherwise liberal enough to resurrect, e.g.,
            # `common-events/l1-base` if some future manifest entry has
            # the stem `l1-base-…`.
            if include_path in RUNTIME_READ_FRAGMENTS:
                continue

            # Check if the manifest overrides this include
            # (e.g. vault-protocol -> vault-protocol-slim)
            resolved_path = include_path
            if include_path not in manifest_set:
                # Check for a variant in the manifest that shares the
                # same base name (e.g. vault-protocol-slim for vault-protocol)
                base = include_path.rsplit("/", 1)[-1] if "/" in include_path else include_path
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

    # Layer 4 — Project sub-skills (PM-owned, role-filtered)
    # Live project content is in .squidsquad/project/ (project-local).
    # references/sub-skills/project/ holds seed templates only.
    # Filtering: shared-*.md → all roles, <identity>-*.md → matching role
    # only, unprefixed files → all roles.
    project_skills_dir = REPO_ROOT / ".squidsquad" / "project"
    if project_skills_dir.is_dir():
        role_identity = _get_entry_file_for_role(role_name)
        known_prefixes = _list_known_role_identities()
        for skill_file in sorted(project_skills_dir.glob("*.md")):
            name = skill_file.stem
            # Determine the file's target prefix (text before first hyphen)
            file_prefix = name.split("-", 1)[0] if "-" in name else None
            # Include if: shared, unprefixed, prefix not a known role, or
            # prefix matches this role's identity
            if file_prefix and file_prefix != "shared" and file_prefix in known_prefixes:
                if file_prefix != role_identity:
                    continue
            content = skill_file.read_text(encoding="utf-8").rstrip()
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

    # Write to a temp file for include resolution (reuses existing logic).
    # Use NamedTemporaryFile to avoid TOCTOU race from deprecated mktemp (#4918).
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w",
                                     encoding="utf-8") as tf:
        tf.write(assembled)
        tmp = Path(tf.name)

    try:
        # Step 2: Resolve includes
        wake_mode = _get_wake_mode(role_name)
        manifest = _load_manifest(role_name, wake_mode)
        if manifest is not None:
            composed = _resolve_includes_with_manifest(tmp, manifest, wake_mode)
        else:
            composed = _resolve_includes(tmp, wake_mode)
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

    # #9588: the boot-bootstrap fragment needs the per-role polling-fragment
    # path. Dev variants (skill, ios, android, web, fullstack) share one file
    # at roles/dev/ralph-loop-overview.md — so we substitute by entry_file
    # (the role identity that owns the polling fragment file), not role_name.
    polling_fragment = (
        f"references/sub-skills/roles/{entry_file}/ralph-loop-overview.md"
    )
    content = content.replace("[POLLING_FRAGMENT_PATH]", polling_fragment)

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


def _is_agent_compose_enabled() -> bool:
    """Check if agent-driven composition is enabled in config."""
    try:
        val = _read_config_value("agent-compose")
        return (val or "").strip().lower() == "yes"
    except Exception:
        return False


def _extract_code_blocks(text: str) -> list[tuple[int, int, str]]:
    """Extract fenced code blocks and their positions for preservation.

    Returns list of (start, end, content) tuples.
    """
    blocks = []
    for m in re.finditer(r'(```[^\n]*\n.*?\n```)', text, re.DOTALL):
        blocks.append((m.start(), m.end(), m.group(0)))
    return blocks


def _extract_markers(text: str) -> list[str]:
    """Extract all HTML comment markers for preservation check."""
    return re.findall(r'<!--.*?-->', text)


def _generate_cqs_from_sources(layer_sources: dict[str, str]) -> list[dict]:
    """Dynamically generate comprehension questions from layer source headings.

    Scans each layer source for ## and ### headings and generates questions
    that verify the composed output covers those topics.

    Returns list of {question, source_heading, layer} dicts.
    """
    cqs = []
    for layer_name, content in layer_sources.items():
        headings = re.findall(r'^#{2,3}\s+(.+)$', content, re.MULTILINE)
        for heading in headings:
            # Skip generic headings
            if heading.strip() in ("", "---"):
                continue
            cqs.append({
                "question": f"Does the composed output address '{heading.strip()}'?",
                "source_heading": heading.strip(),
                "layer": layer_name,
            })
    return cqs


def derive_event_contract(composed_text: str, role_name: str) -> dict | None:
    """Derive event contract for a role from its composed instructions.

    Calls Claude CLI to read the role's full instruction set and derive
    what events it should emit and react to. Returns a dict:
    {"emits": [str], "reacts_to": [str]} or None on failure.

    Runs unconditionally on every compose (#5868 AC-3).
    """
    try:
        from event_catalog import EMITTED, RECOGNIZED

        # Build the catalog reference for the prompt
        emitted_names = ", ".join(sorted(EMITTED.keys()))
        recognized_names = ", ".join(sorted(RECOGNIZED.keys()))

        prompt = (
            f"You are analyzing agent instructions for the '{role_name}' role "
            f"to derive its event bus contract.\n\n"
            f"VALID EVENT TYPES (use ONLY these):\n"
            f"  Infrastructure-emitted: {emitted_names}\n"
            f"  Planned/recognized: {recognized_names}\n\n"
            f"RULES:\n"
            f"- emits: events this role's ACTIONS cause to be produced "
            f"(e.g. if the role runs tracker transitions, it causes status-transition events). "
            f"Do NOT include infrastructure events the role merely triggers indirectly "
            f"(e.g. git-pull, cycle-start are emitted by scripts, not by roles).\n"
            f"- reacts-to: events this role should RECEIVE and act on based on its responsibilities.\n"
            f"- Use ONLY event types from the valid list above. Never invent new types.\n"
            f"- Output ONLY valid JSON. No explanation, no markdown, no code fences.\n\n"
            f"OUTPUT FORMAT (JSON only):\n"
            f'{{"emits": ["event-type-1", "event-type-2"], '
            f'"reacts_to": ["event-type-3", "event-type-4"]}}\n\n'
            f"INSTRUCTIONS TO ANALYZE:\n\n{composed_text[:8000]}"
        )

        result = subprocess.run(
            ["claude", "-p", "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )

        if result.returncode != 0:
            print(f"  WARNING: Event contract derivation failed for {role_name} "
                  f"(exit {result.returncode})", file=sys.stderr)
            return None

        raw = result.stdout.strip()
        if not raw:
            print(f"  WARNING: Event contract derivation returned empty for {role_name}",
                  file=sys.stderr)
            return None

        # Parse JSON — strip any markdown fences the LLM might add
        clean = raw
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
        if clean.endswith("```"):
            clean = "\n".join(clean.split("\n")[:-1])
        clean = clean.strip()

        contract = json.loads(clean)

        # Validate structure
        if not isinstance(contract, dict):
            print(f"  WARNING: Event contract for {role_name} is not a dict",
                  file=sys.stderr)
            return None

        emits = contract.get("emits", [])
        reacts_to = contract.get("reacts_to", [])

        if not isinstance(emits, list) or not isinstance(reacts_to, list):
            print(f"  WARNING: Event contract for {role_name} has invalid lists",
                  file=sys.stderr)
            return None

        # Filter to only valid event types (reject hallucinations with warning)
        valid = set(EMITTED.keys()) | set(RECOGNIZED.keys())
        dropped = [e for e in emits if isinstance(e, str) and e not in valid]
        dropped += [r for r in reacts_to if isinstance(r, str) and r not in valid]
        if dropped:
            print(f"  WARNING: {role_name} derivation produced unknown event types "
                  f"(dropped {len(dropped)}): {', '.join(dropped[:5])}", file=sys.stderr)
        emits = [e for e in emits if isinstance(e, str) and e in valid]
        reacts_to = [r for r in reacts_to if isinstance(r, str) and r in valid]

        return {"emits": emits, "reacts_to": reacts_to}

    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError,
            OSError, ImportError) as e:
        print(f"  WARNING: Event contract derivation error for {role_name}: {e}",
              file=sys.stderr)
        return None


def derive_and_write_event_contracts(roles: list[str] = None,
                                     target_root: Path = None) -> bool:
    """Derive event contracts for all roles and write to config.md.

    Calls derive_event_contract for each role, writes results to the
    Event Reactions section, then runs cross-agent validation.
    Returns True if validation passes, False on errors.
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)

    if roles is None:
        # Discover all deployed roles
        sqdir = target_root / ".squidsquad"
        roles = [
            d.name for d in sorted(sqdir.iterdir())
            if d.is_dir() and (d / "CLAUDE.md").exists()
        ]

    if not roles:
        print("  No roles found for event contract derivation.", file=sys.stderr)
        return True  # No roles = nothing to validate

    contracts = {}
    for role in roles:
        claude_md = target_root / ".squidsquad" / role / "CLAUDE.md"
        if not claude_md.exists():
            continue

        print(f"  Deriving event contract for {role}...")
        text = claude_md.read_text(encoding="utf-8")
        contract = derive_event_contract(text, role)
        if contract:
            contracts[role] = contract
        else:
            print(f"  WARNING: Could not derive contract for {role}, skipping",
                  file=sys.stderr)

    if not contracts:
        print("  No event contracts derived. Skipping validation.")
        return True

    # Merge with existing contracts (preserve roles that failed derivation)
    try:
        from config import get_event_reactions, write_event_reactions
        existing = get_event_reactions()
        if existing:
            merged = dict(existing)
            merged.update(contracts)  # New derivations override, others preserved
            contracts = merged
        # Sort event type lists for idempotency
        for role_data in contracts.values():
            role_data["emits"] = sorted(role_data.get("emits", []))
            role_data["reacts_to"] = sorted(role_data.get("reacts_to", []))
        write_event_reactions(contracts)
        print(f"  Event contracts written for {len(contracts)} role(s).")
    except Exception as e:
        print(f"  WARNING: Could not write event contracts: {e}", file=sys.stderr)
        return True  # Graceful degradation

    # Run cross-agent validation
    try:
        from event_validator import validate_and_print
        exit_code = validate_and_print()
        return exit_code == 0
    except ImportError:
        print("  WARNING: event_validator not available, skipping validation",
              file=sys.stderr)
        return True


def agent_compose(deterministic_output: str, role_name: str,
                  layer_sources: dict[str, str] = None) -> str:
    """Polish deterministic compose output using an LLM coherence agent.

    Args:
        deterministic_output: the raw concatenated output from compose_role()
        role_name: the agent role being composed
        layer_sources: dict of {layer_name: content} for CQ generation

    Returns polished output, or deterministic_output unchanged on failure.
    """
    if not _is_agent_compose_enabled():
        return deterministic_output

    try:
        # Extract code blocks and markers for preservation verification
        original_markers = _extract_markers(deterministic_output)
        original_code_blocks = _extract_code_blocks(deterministic_output)

        # Build the coherence prompt
        prompt = (
            f"You are a technical editor polishing agent instructions for the "
            f"'{role_name}' role. Below is a mechanically-assembled document from "
            f"multiple layers. Rewrite the PROSE sections for coherence, natural "
            f"flow, and deduplication. Remove redundant paragraphs.\n\n"
            f"CRITICAL RULES:\n"
            f"- NEVER modify fenced code blocks (```...```)\n"
            f"- NEVER modify HTML comment markers (<!-- ... -->)\n"
            f"- NEVER modify bash commands, file paths, or Python scripts\n"
            f"- NEVER modify placeholder tags like [ROLE] or {{{{include:}}}}\n"
            f"- PRESERVE all behavioral instructions — change wording, not meaning\n"
            f"- Deduplicate: if the same instruction appears twice, keep ONE\n"
            f"- Resolve contradictions: if two sections conflict, keep the more "
            f"specific one\n\n"
            f"Document to polish:\n\n{deterministic_output}"
        )

        # Call Claude via the claude CLI — pipe prompt via stdin to avoid
        # Windows command-line length limits (WinError 206 / MAX_PATH).
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )

        if result.returncode != 0:
            print(f"  WARNING: Agent compose failed (exit {result.returncode}), "
                  f"using deterministic output", file=sys.stderr)
            return deterministic_output

        polished = result.stdout.strip()
        if not polished:
            print("  WARNING: Agent compose returned empty, using deterministic",
                  file=sys.stderr)
            return deterministic_output

        # Verify code blocks and markers preserved
        polished_markers = _extract_markers(polished)
        polished_code_blocks = _extract_code_blocks(polished)

        if len(polished_code_blocks) < len(original_code_blocks):
            print(f"  WARNING: Agent compose lost code blocks "
                  f"({len(original_code_blocks)} → {len(polished_code_blocks)}), "
                  f"using deterministic", file=sys.stderr)
            return deterministic_output

        # Generate and run CQ verification if layer sources provided
        if layer_sources:
            cqs = _generate_cqs_from_sources(layer_sources)
            if cqs:
                # Verify a sample of CQs (max 5 for speed)
                sample = cqs[:5]
                for cq in sample:
                    if cq["source_heading"].lower() not in polished.lower():
                        print(f"  WARNING: CQ fail — '{cq['source_heading']}' "
                              f"missing from polished output", file=sys.stderr)
                        # Don't fail on CQ — just warn. Full CQ runs at deploy time.

        return polished

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"  WARNING: Agent compose error ({e}), using deterministic",
              file=sys.stderr)
        return deterministic_output


def deploy_role(role_name: str, target_root: Path = None,
                output_name: str = None) -> Path:
    """Full pipeline: compose entry file -> substitute placeholders -> write CLAUDE.md.

    Args:
        role_name: the role composition source (e.g. "skill", "dev-ios", "pm").
            Resolves to a role identity via `_get_entry_file_for_role`.
        target_root: base directory that will contain `.squidsquad/<output_name>/`.
            Defaults to REPO_ROOT (the installed repo). Tests override to
            write into a scratch directory without touching the real install.
        output_name: the agent instance id for the output directory. Defaults
            to role_name. Use this when the compose source differs from the
            agent directory (e.g. compose from "dev-ios" but output to "skill").

    Returns the absolute path of the composed CLAUDE.md.
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)
    if output_name is None:
        output_name = role_name

    entry_file = _get_entry_file_for_role(role_name)
    composed = compose_role(role_name)
    final = _substitute_placeholders(composed, output_name, entry_file)

    # Agent-driven coherence polish (if enabled in config)
    final = agent_compose(final, output_name)

    header = f"# SquidSquad -- {output_name} Lead\n\n"
    header += f"<!-- GENERATED by compose.py deploy {role_name}. DO NOT EDIT. -->\n"
    header += f"<!-- Regenerate: python references/scripts/compose.py deploy {role_name} -->\n\n"

    output_path = target_root / ".squidsquad" / output_name / "CLAUDE.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Guard: warn if composed file has manual edits (#5557)
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        if "GENERATED by compose.py" in existing and existing != header + final:
            # Check if the file has uncommitted changes (manual edits)
            try:
                diff = subprocess.run(
                    ["git", "diff", "--name-only", str(output_path.relative_to(target_root))],
                    capture_output=True, text=True, check=False,
                    cwd=str(target_root),
                )
                if output_path.relative_to(target_root).as_posix() in diff.stdout:
                    print(f"WARNING: {output_path.relative_to(target_root)} has uncommitted "
                          f"manual edits that will be overwritten by compose. "
                          f"Edit source templates instead.", file=sys.stderr)
            except Exception:
                pass  # Guard is best-effort

    output_path.write_text(header + final, encoding="utf-8")

    # Assemble SOUL.md from 3 layers if missing (#3465 layered architecture).
    # Never overwrite an existing local SOUL.md — use upgrade_soul() for that.
    soul_path = target_root / ".squidsquad" / output_name / "SOUL.md"
    if not soul_path.exists():
        _assemble_and_write_soul(role_name, target_root, output_name)

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


def _assemble_and_write_soul(role_name: str, target_root: Path = None,
                             output_name: str = None):
    """Assemble SOUL.md from 3 layers and write atomically."""
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)
    if output_name is None:
        output_name = role_name

    content = _assemble_soul(role_name)
    soul_path = target_root / ".squidsquad" / output_name / "SOUL.md"
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


def is_pre_layer_install(target_root: Path = None) -> bool:
    """Detect whether this is a pre-layer install (no L1 base files).

    Pre-layer installs have .squidsquad/ but no references/roles/instructions.md
    (the L1 base entry file added by the layered architecture).
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)
    base_entry = target_root / "references" / "roles" / "instructions.md"
    squid = target_root / ".squidsquad"
    return squid.exists() and not base_entry.exists()


def extract_project_adaptation(role_name: str, target_root: Path = None) -> str:
    """Extract ## Project Adaptation section from a deployed SOUL.md.

    Returns the extracted content (without the heading), or empty string
    if not found. Used during upgrade to preserve accumulated signals.
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)

    soul_path = target_root / ".squidsquad" / role_name / "SOUL.md"
    if not soul_path.exists():
        return ""

    text = soul_path.read_text(encoding="utf-8")
    marker = "## Project Adaptation"
    if marker not in text:
        return ""

    idx = text.index(marker) + len(marker)
    # Find next ## heading or end of file
    rest = text[idx:]
    next_heading = rest.find("\n## ")
    if next_heading >= 0:
        content = rest[:next_heading]
    else:
        content = rest

    return content.strip()


def _read_existing_local_config(config_path: Path) -> dict:
    """Parse existing .local-config into {role: path_str} dict."""
    result = {}
    if config_path.exists():
        try:
            for line in config_path.read_text(encoding="utf-8").splitlines():
                m = re.match(r"-\s*\*\*([\w-]+)\*\*:\s*(.+)", line)
                if m:
                    result[m.group(1).strip()] = m.group(2).strip()
        except OSError:
            pass
    return result


def generate_local_config(roles: list, target_root: Path = None,
                          clone_paths: dict = None) -> Path:
    """Generate .squidsquad/.local-config with clone paths for all agents.

    Args:
        roles: list of role/agent id strings.
        target_root: the primary repo root (where .squidsquad/ lives).
        clone_paths: optional dict mapping role -> relative path string
            (e.g. {"pm": ".", "skill": "../project-skill"}). When provided,
            paths are written as-is (relative). When omitted, existing
            .local-config entries are preserved and new roles default to
            sibling clone paths (../{project-name}-{role}).
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root).resolve()

    config_path = target_root / ".squidsquad" / ".local-config"

    # When clone_paths not provided, preserve existing entries
    if clone_paths is None:
        existing = _read_existing_local_config(config_path)
        project_name = _read_config_value("project-name") or target_root.name
        clone_paths = {}
        for role in roles:
            if role in existing:
                clone_paths[role] = existing[role]
            elif role == "pm":
                clone_paths[role] = "."
            else:
                clone_paths[role] = f"../{project_name}-{role}"

    lines = [
        "# Agent clone paths — auto-generated by compose.py",
        "# Format: - **role**: <relative-path>",
        "# Relative paths resolve against the primary repo root.",
        "",
    ]
    for role in roles:
        path_str = clone_paths.get(role, ".")
        lines.append(f"- **{role}**: {path_str}")

    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path





MANDATORY_ROLES = {"pm", "qa", "dm"}  # #6055: always present, no fallbacks


def _collect_all_roles() -> list:
    """Return all configured roles: dev-agents from config + pm + qa + dm."""
    agents = _read_config_value("dev-agents") or ""
    roles = [r.strip() for r in agents.split(",") if r.strip()]
    # Mandatory roles — always required (#6055)
    for role in ("pm", "qa", "dm"):
        if role not in roles:
            roles.append(role)
    return roles


def _check_mandatory_roles(roles: list) -> list[str]:
    """Check that all mandatory roles are present. Returns list of missing roles."""
    return [r for r in MANDATORY_ROLES if r not in roles]



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
        # Event contract derivation + cross-agent validation (#5868)
        print("Deriving event contracts...")
        if not derive_and_write_event_contracts():
            print("WARNING: Event contract validation found errors. "
                  "Review and fix, or re-run compose.", file=sys.stderr)

    elif cmd == "deploy-all":
        # Deploy all configured agents
        roles = _collect_all_roles()
        # #6055: Check mandatory roles are present
        missing = _check_mandatory_roles(roles)
        if missing:
            print(f"ERROR: Mandatory role(s) missing: {', '.join(missing)}", file=sys.stderr)
            print(f"Every SquidSquad team requires PM, QA, and DM.", file=sys.stderr)
            print(f"Add missing roles with: /squidsquad-setup or manually create .squidsquad/{missing[0]}/", file=sys.stderr)
            sys.exit(1)
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
        # Event contract derivation + cross-agent validation (#5868)
        print("Deriving event contracts...")
        if not derive_and_write_event_contracts(roles):
            print("WARNING: Event contract validation found errors. "
                  "Review and fix, or re-run compose.", file=sys.stderr)

    elif cmd == "upgrade-soul":
        if len(args) < 2:
            print("Usage: compose.py upgrade-soul <role>", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        soul_path = upgrade_soul(role_name)
        lines = soul_path.read_text(encoding="utf-8").count("\n")
        print(f"Upgraded {role_name} SOUL.md ({lines} lines) -> {soul_path.relative_to(REPO_ROOT)}")

    else:
        # Treat as role entry file name
        content = compose_role(cmd)
        print(content)


if __name__ == "__main__":
    main()
