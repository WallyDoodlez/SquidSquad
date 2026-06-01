#!/usr/bin/env python3
"""SquidSquad sub-skill composition engine.

Reads role entry files, resolves {{include: path}} directives by inlining
the referenced sub-skill content, and wraps each inclusion with
<!-- sub-skill: name --> section markers.

Usage:
    python scripts/compose.py worker-agent     # Compose worker agent template
    python scripts/compose.py pm-agent         # Compose PM/Verifier template
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

import config as _config_module  # A5 alias-registry parser, used by --v2 (#10386).

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
    "roles/worker/ralph-loop-overview",
    "roles/pm/ralph-loop-overview",
    "roles/verifier/ralph-loop-overview",
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
    """Delegate to canonical config.get_wake_mode (#9745).

    Thin wrapper kept so existing compose-internal callers don't need
    import-path churn. See ``config.get_wake_mode`` for the resolution
    rules — that is the single source of truth referenced by bootstrap.md.
    """
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from config import get_wake_mode
    except Exception:
        return "polling"
    return get_wake_mode(role_name)


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
            # #9588 belt-and-suspenders (DS cycle 1301 phase d4c44589 F1): the
            # manifest-aware path filters RUNTIME_READ_FRAGMENTS explicitly;
            # this manifest-less fallback must do the same, otherwise a yaml
            # parse error / pyyaml-absent install silently inlines runtime
            # fragments and defeats the lazy-load design.
            if include_path in RUNTIME_READ_FRAGMENTS:
                continue
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

    # Try nested variant path first (worker-skill -> worker/skill/<manifest>;
    # dev-skill is also accepted via the 6274.1 dual-aware shim)
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
            # #6274 dual-aware: belt-and-suspenders alias fallback (DS finding
            # cycle 1301 phase 2.2.2-3 F3). If role_name is in _BASE_ALIAS_6274
            # (e.g., "dev" → "worker", "qa" → "verifier"), retry against the
            # aliased identity. Defense in depth — phase 2.2.1 already updated
            # all base_role: values in variant includes.yml to new names; this
            # catches any legacy caller that still passes "dev"/"qa".
            # #6274.2 (3b) disk-check shim: `_resolve_manifest_path` already
            # tests `.exists()` on the resolved file, so this fallback safely
            # returns None when the alias directory is absent on disk — making
            # the dual-aware behavior consistent between pre- and post-rename
            # installs (no spurious successes against ghost role names).
            if role_name in _BASE_ALIAS_6274:
                aliased = _BASE_ALIAS_6274[role_name]
                aliased_dir = ROLES_DIR / aliased
                if aliased_dir.is_dir():
                    manifest_path = _resolve_manifest_path(aliased_dir)
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
            # prefix matches this role's identity (or its #6274 alias).
            if file_prefix and file_prefix != "shared" and file_prefix in known_prefixes:
                # #6274 D2: L4 prefix routing dual-aware. A `worker-` prefixed
                # file routes to the `dev`-identity consumer (and vice-versa);
                # `verifier-` / `qa-` likewise. Without this, AC1.1's
                # identity-set widening makes `worker-foo.md` pass the
                # known-prefix gate but silently skip the dev-identity role
                # because `file_prefix != role_identity`. The alias table
                # canonicalizes both sides to the same form for the comparison.
                if (
                    file_prefix != role_identity
                    and _BASE_ALIAS_6274.get(file_prefix) != role_identity
                    and _BASE_ALIAS_6274.get(role_identity) != file_prefix
                ):
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


# #9925: cache manifest reads within a single compose run so the
# role-roster injection doesn't re-parse the same manifest.yaml once per
# active role per composed agent (would be N×N parses for N active roles).
_ROLE_MANIFEST_CACHE: dict = {}


def _read_role_manifest(role_id: str) -> dict | None:
    """#9925 D2/D7: read a role's manifest.yaml metadata (id/display_name/
    tagline/description). Cached within a single compose run.

    Returns None on missing file or parse failure (caller's degraded path).
    """
    if role_id in _ROLE_MANIFEST_CACHE:
        return _ROLE_MANIFEST_CACHE[role_id]
    manifest_path = ROLES_DIR / role_id / "manifest.yaml"
    if not manifest_path.exists() or yaml is None:
        _ROLE_MANIFEST_CACHE[role_id] = None
        return None
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(
            f"WARNING: #9925 — failed to parse {manifest_path}: {e}",
            file=sys.stderr,
        )
        _ROLE_MANIFEST_CACHE[role_id] = None
        return None
    _ROLE_MANIFEST_CACHE[role_id] = data if isinstance(data, dict) else None
    return _ROLE_MANIFEST_CACHE[role_id]


def _active_roles_for_roster() -> list[str]:
    """#9925 D2/F4: return the list of role identities active in THIS
    install's config.md, sorted alphabetically (D8). Sources:
      - PM, verifier, DM — always present per #6261 mandatory team.
        (#6274: was {pm, qa, dm}; "qa" → "verifier" per D5.)
      - Worker agents — from `Workers:` (or legacy `Dev Agents:`) line in
        config.md (parsed via config.py get-field 'workers', falling back
        to a regex on config.md if config.py is unavailable).
    Roles whose manifest.yaml doesn't exist in references/roles/ are
    dropped silently — the roster only lists roles that can be
    described from a manifest.
    """
    roles = {"pm", "verifier", "dm"}  # mandatory team — #6274 renamed qa→verifier
    workers_raw = _read_config_value("workers")  # dual-aware: shim falls back to deprecated `Dev Agents:` key
    if workers_raw:
        for token in workers_raw.split(","):
            t = token.strip()
            if t:
                roles.add(t)
    # Filter to roles that actually have a manifest.yaml — D8 degraded mode.
    # Worker variants (e.g. "skill", "be") fall back to the worker base
    # manifest (#6274: was "dev"). Dual-aware: try both "worker" and "dev"
    # in case the install hasn't been re-composed yet.
    return sorted(r for r in roles if (ROLES_DIR / r / "manifest.yaml").exists()
                  or ((ROLES_DIR / "worker" / "manifest.yaml").exists()
                      or (ROLES_DIR / "dev" / "manifest.yaml").exists())
                  and r not in {"pm", "verifier", "dm"})


def _render_role_roster() -> str:
    """#9925 D7 item 3 + D8: render the L1 roster block by reading each
    active role's manifest.yaml and emitting display_name + tagline +
    description in alphabetical (id) order.

    Returns the markdown block (no leading/trailing newlines).
    """
    active = _active_roles_for_roster()
    if not active:
        # D8 degraded mode: no active roles discoverable — skip roster.
        print(
            "WARNING: #9925 — no active roles found for role-roster injection; "
            "leaving {{role-roster}} marker in composed output",
            file=sys.stderr,
        )
        return "## Your Teammates' Responsibilities\n\n_(no active roles discoverable; check config.md `Workers:` field — 6274.1 shim also reads the deprecated `Dev Agents:` key)_"

    lines = ["## Your Teammates' Responsibilities", ""]
    for role_id in active:
        # Worker variants like "skill" don't have their own manifest.yaml —
        # fall through to worker's manifest for the roster entry (#6274 dual-aware
        # also accepts dev/ as a fallback during the migration window).
        manifest = _read_role_manifest(role_id)
        if manifest is None:
            # #6274 dual-aware (DS cycle 1301 phase cfa512ff F3): check both
            # worker/ (new canonical) and dev/ (pre-rename) so worker variants
            # like "skill"/"be" resolve via either parent manifest.
            if (ROLES_DIR / "worker" / "manifest.yaml").exists():
                manifest = _read_role_manifest("worker")
            elif (ROLES_DIR / "dev" / "manifest.yaml").exists():
                manifest = _read_role_manifest("dev")
        if manifest is None:
            print(
                f"WARNING: #9925 — no manifest for active role {role_id!r}; "
                "skipping in roster (D8 degraded mode)",
                file=sys.stderr,
            )
            continue

        display = manifest.get("display_name")
        if not display:
            # D8: missing display_name is a BUILD ERROR (per AC11).
            print(
                f"ERROR: #9925 — role {role_id!r} manifest is missing required "
                "`display_name` field; cannot render roster",
                file=sys.stderr,
            )
            raise SystemExit(2)

        tagline = manifest.get("tagline", "")
        description = manifest.get("description", "")
        if not tagline:
            print(
                f"WARNING: #9925 — role {role_id!r} manifest has no `tagline`; "
                "rendering with empty tagline",
                file=sys.stderr,
            )
        if not description:
            print(
                f"WARNING: #9925 — role {role_id!r} manifest has no "
                "`description`; rendering with empty description",
                file=sys.stderr,
            )

        if tagline:
            lines.append(f"### {display} — {tagline}")
        else:
            lines.append(f"### {display}")
        lines.append("")
        if description:
            # Manifest YAML uses block scalars (`>` folded) — strip and re-flow.
            lines.append(description.strip())
        lines.append("")

    # Drop the trailing blank.
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _inject_role_roster(content: str, role_name: str) -> str:
    """#9925 D7 item 3 + F6: post-process the composed content to replace
    the `{{role-roster}}` marker with the rendered roster. Runs AFTER
    `_resolve_includes_with_manifest` to avoid tangling with the
    existing `{{include:}}` / `{{runtime:}}` / `{{capability:}}`
    resolvers and to avoid firing inside code blocks of unrelated files
    that happen to mention the marker.
    """
    if "{{role-roster}}" not in content:
        # D8 degraded mode: marker absent — likely agent-boundaries.md was
        # not included for this role. Emit a warning and continue without
        # substitution.
        print(
            f"WARNING: #9925 — no {{{{role-roster}}}} marker in composed "
            f"{role_name} output; skipping roster injection (likely "
            "common/agent-boundaries not in includes.yml)",
            file=sys.stderr,
        )
        return content
    roster = _render_role_roster()
    return content.replace("{{role-roster}}", roster)


def compose_role(role_name: str) -> str:
    """Compose a role's full CLAUDE.md from 3-layer assembly + include resolution.

    Step 1: Assemble the template from Layer 1 + Layer 2 + Layer 3 CLAUDE.md
            source files (same concatenation pattern as SOUL.md).
    Step 2: Resolve {{include:}}, {{runtime:}}, {{capability:}} directives
            using the role's includes.yml manifest.
    Step 3 (#9925): inject the role roster by replacing the
            ``{{role-roster}}`` marker introduced via L1
            ``common/agent-boundaries`` include.

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

    # Step 3 (#9925 D7 item 3): role-roster post-processing.
    composed = _inject_role_roster(composed, role_name)

    return composed


def compose_all() -> str:
    """Compose the worker-agent template as the default agent-instructions.md."""
    # agent-instructions.md is the worker template (primary output)
    header = "<!-- GENERATED FILE — DO NOT EDIT. -->\n"
    header += "<!-- Source: references/roles/worker/instructions.md + sub-skills/ -->\n"
    header += "<!-- Regenerate with: python references/scripts/compose.py all -->\n\n"
    composed = compose_role("worker")
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

    #6274 dual-aware window (sub-phases 6274.1 + 6274.2): also include
    `worker` and `verifier` as known identities regardless of disk
    state, plus `dev` and `qa` for backward-compatibility. This lets
    `_resolve_variant("worker-skill")` and `_resolve_variant("dev-skill")`
    both pass the base-in-identities check during the migration. Removed
    in 6274.3 — see `references/sub-skills/common/migration-6274-cutover`.
    """
    if not ROLES_DIR.exists():
        return _DUAL_AWARE_IDENTITIES_6274.copy()
    on_disk = {
        d.name for d in ROLES_DIR.iterdir()
        if d.is_dir() and (d / "instructions.md").exists()
    }
    return on_disk | _DUAL_AWARE_IDENTITIES_6274


# #6274 D2: dual-aware window identity set. After 6274.3 (cutover),
# this constant + the `|` above are deleted and the function returns
# `on_disk` directly. Inventory of dual-aware surfaces lives in
# CONTEXT-6274.md D2.
_DUAL_AWARE_IDENTITIES_6274 = frozenset({"worker", "verifier", "dev", "qa"})


def _get_entry_file_for_role(role_name: str) -> str:
    """Map an agent instance to its role identity for composition.

    After Q-new22 each role has its own self-contained directory at
    `references/roles/<role>/`. For any role that exists in the registry
    the identity equals the role name. Anything else is resolved via:
    1. Suffix-strip: pm-skill -> pm (Layer 3 variant of any base role)
    2. Base-role fallback: skill, be, fe -> worker (post-6274.2 canonical),
       with dev as dual-aware fallback during the migration window.

    After #328 Phase H the identity list is read from the manifest
    registry, not hardcoded — adding a new role directory under
    `references/roles/` automatically makes it a first-class identity
    without any compose.py edit.
    """
    identities = _list_known_role_identities()
    # #6274 D2: identities now includes dual-aware aliases ({worker,
    # verifier}). For input normalization, prefer the on-disk canonical
    # over the alias. Specifically: if the input matches a dual-aware
    # alias AND its canonical form has an on-disk template, return the
    # canonical form. (Without this, `_get_entry_file_for_role('worker')`
    # would return 'worker' pre-rename even though only roles/dev/
    # exists on disk, and compose would fail to find the template.)
    if role_name in identities:
        # If role_name is a dual-aware alias and its target directory
        # exists, return the target. Otherwise return as-is.
        if role_name in _BASE_ALIAS_6274:
            alias_target = _BASE_ALIAS_6274[role_name]
            target_dir = ROLES_DIR / alias_target
            if target_dir.is_dir() and (target_dir / "instructions.md").exists():
                return alias_target
            # Alias target doesn't exist on disk — own directory must;
            # fall through to returning role_name unchanged.
        return role_name
    # Layer 3 variant: resolve nested directory (worker-skill -> worker/skill/;
    # legacy dev-skill also routes here via 6274.1 alias)
    resolved = _resolve_variant(role_name)
    if resolved:
        base, _ = resolved
        return base
    # Worker variants (skill, be, fe, bespoke names) compose from the
    # `worker` role template (post-6274.2). Pre-rename installs that still
    # have `roles/dev/` work via the 6274.1 alias shim — `dev` stays in
    # `identities` as a dual-aware alias and `_BASE_ALIAS_6274` maps it
    # to `worker` at the call sites that need the on-disk canonical.
    # #6274.2 (3b) disk-check shim: `worker`/`dev` are dual-aware identities
    # regardless of disk state, so the literal `in identities` check fires
    # in both pre- and post-rename installs. Confirm the target directory
    # actually has an entry template before returning it; otherwise fall
    # through to the other side of the alias pair.
    if "worker" in identities and (ROLES_DIR / "worker").is_dir() and (ROLES_DIR / "worker" / "instructions.md").exists():
        return "worker"
    if "dev" in identities and (ROLES_DIR / "dev").is_dir() and (ROLES_DIR / "dev" / "instructions.md").exists():
        return "dev"
    # No registry, or no `worker`/`dev` identity — fall back to the literal
    # role name so at least the error message points at the right file.
    return role_name


def _substitute_placeholders(content: str, role_name: str, entry_file: str) -> str:
    """Substitute role-specific placeholders in composed content.

    [ROLE] and [ROLE_UPPER] are substituted for ALL roles (needed by
    cycle-runner sub-skill which is shared across all agents).
    [ROLE_TEST_CMD], [OTHER_ROLES] are worker-only (6274.2: was dev-only;
    `is_dev` below accepts both "dev" and "worker" entry_file values).
    """
    is_dev = entry_file in ("dev", "worker")  # #6274 dual-aware

    # Universal substitution — all roles need [ROLE] for cycle-runner paths
    content = content.replace("[ROLE]", role_name)
    content = content.replace("[ROLE_UPPER]", role_name.upper())

    # #9588: the boot-bootstrap fragment needs the per-role polling-fragment
    # path. Worker variants (skill, ios, android, web, fullstack) share one file
    # at roles/worker/ralph-loop-overview.md — so we substitute by entry_file
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
        all_agents = _read_config_value("workers") or role_name
        other = [r.strip() for r in all_agents.split(",") if r.strip() != role_name]
        content = content.replace("[OTHER_ROLES]", ", ".join(other) if other else "(none)")

    # Shared placeholders (all roles)
    interval = _read_config_value("interval") or "30"
    content = content.replace("[INTERVAL]", interval)

    # PM/DM-specific
    if not is_dev:
        active_agents = _read_config_value("workers") or ""
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


# A4 (#10388): in-memory compose + on-disk diff. Shared between deploy_role
# (when paired with agent_compose + write) and check_role (read-only).
def _compose_role_to_string(role_name: str, output_name: str = None,
                            regenerate_cmd: str = None) -> str:
    """Produce the would-be-deployed file content as a string.

    Deterministic — does NOT run ``agent_compose`` (the LLM polish step).
    ``check_role`` relies on determinism for a reliable diff; when
    ``agent-compose`` is enabled in config, the on-disk file may carry
    LLM polish that this string lacks, and the diff will flag the role
    as drifted. ``check_role`` warns in that case.
    """
    if output_name is None:
        output_name = role_name
    entry_file = _get_entry_file_for_role(role_name)
    composed = compose_role(role_name)
    final = _substitute_placeholders(composed, output_name, entry_file)
    header = f"# SquidSquad -- {output_name} Lead\n\n"
    regenerate_display = regenerate_cmd if regenerate_cmd else role_name
    header += f"<!-- GENERATED by compose.py deploy {regenerate_display}. DO NOT EDIT. -->\n"
    header += f"<!-- Regenerate: python references/scripts/compose.py deploy {regenerate_display} -->\n\n"
    return header + final


def _diff_compose_output(expected: str, on_disk: str) -> list:
    """Identify which top-level ``## …`` sections diverge between expected and on-disk.

    Returns a sorted list of unique section headings whose content
    differs. Lines before the first ``## `` heading are attributed to the
    synthetic section ``<preamble>``. An empty list means the two strings
    are byte-identical.
    """
    import difflib
    if expected == on_disk:
        return []
    expected_lines = expected.splitlines(keepends=True)
    ondisk_lines = on_disk.splitlines(keepends=True)
    # Map expected_lines index -> nearest preceding ## heading text.
    expected_section = []
    current = "<preamble>"
    for ln in expected_lines:
        if ln.startswith("## "):
            current = ln.strip().lstrip("#").strip().rstrip("#").strip()
        expected_section.append(current)
    # Same map for on-disk, used when the diverging region exists only in on-disk.
    ondisk_section = []
    current = "<preamble>"
    for ln in ondisk_lines:
        if ln.startswith("## "):
            current = ln.strip().lstrip("#").strip().rstrip("#").strip()
        ondisk_section.append(current)
    sm = difflib.SequenceMatcher(None, expected_lines, ondisk_lines)
    diffed = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for idx in range(i1, i2):
            if idx < len(expected_section):
                diffed.add(expected_section[idx])
        for idx in range(j1, j2):
            if idx < len(ondisk_section):
                diffed.add(ondisk_section[idx])
    return sorted(diffed)


# Distinct exit codes (per AC) so a future CI/harness consumer can tell
# "the compose was clean", "some role drifted, re-run deploy", and "we
# couldn't even read sources" apart.
CHECK_EXIT_CLEAN = 0
CHECK_EXIT_DRIFT = 1
CHECK_EXIT_ERROR = 2


def check_role(role_name: str, target_root: Path = None,
               output_name: str = None) -> tuple:
    """Compare in-memory compose for ``role_name`` against the on-disk file.

    Returns ``(status, diff_summary)`` where ``status`` is one of
    ``"clean"`` / ``"drift"`` / ``"missing"``. ``diff_summary`` is the list
    of diverging section headings (empty when ``clean`` or ``missing``).
    Raises any exception from ``_compose_role_to_string`` so the CLI can
    translate that to exit code 2.
    """
    if target_root is None:
        target_root = REPO_ROOT
    target_root = Path(target_root)
    if output_name is None:
        output_name = role_name
    expected = _compose_role_to_string(role_name, output_name=output_name)
    on_disk_path = target_root / ".squidsquad" / output_name / "CLAUDE.md"
    if not on_disk_path.exists():
        return "missing", []
    on_disk = on_disk_path.read_text(encoding="utf-8")
    if expected == on_disk:
        return "clean", []
    return "drift", _diff_compose_output(expected, on_disk)


def deploy_role(role_name: str, target_root: Path = None,
                output_name: str = None,
                output_filename: str = "CLAUDE.md",
                regenerate_cmd: str = None) -> Path:
    """Full pipeline: compose entry file -> substitute placeholders -> write CLAUDE.md.

    Args:
        role_name: the role composition source (e.g. "skill", "worker-ios", "pm";
            legacy "dev-ios" still accepted via 6274.1 alias).
            Resolves to a role identity via `_get_entry_file_for_role`.
        target_root: base directory that will contain `.squidsquad/<output_name>/`.
            Defaults to REPO_ROOT (the installed repo). Tests override to
            write into a scratch directory without touching the real install.
        output_name: the agent instance id for the output directory. Defaults
            to role_name. Use this when the compose source differs from the
            agent directory (e.g. compose from "worker-ios" but output to "skill").
        output_filename: the filename to write under
            ``.squidsquad/<output_name>/``. Defaults to ``"CLAUDE.md"`` so the
            v1 path is byte-identical to pre-A6. The ``--v2`` branch (#10386)
            passes ``"CLAUDE.linked.v2.md"`` so the v2 path lands beside v1
            without disturbing it.

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
    # `regenerate_cmd` lets v2 callers override the human-readable
    # regenerate hint so it points at the alias + --v2 (the command that
    # actually rewrites this file) instead of the v1 role-class shorthand.
    regenerate_display = regenerate_cmd if regenerate_cmd else role_name
    header += f"<!-- GENERATED by compose.py deploy {regenerate_display}. DO NOT EDIT. -->\n"
    header += f"<!-- Regenerate: python references/scripts/compose.py deploy {regenerate_display} -->\n\n"

    output_path = target_root / ".squidsquad" / output_name / output_filename
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


# v2 output filename per PRD-B §9a coexistence and PM's narrowed-scope
# comment on #10386: A6 writes the v2 LINKED output (assemble will add
# CLAUDE.v2.md once PRD-B ships).
_V2_LINKED_FILENAME = "CLAUDE.linked.v2.md"
# Aliases come from config.md but `parse_aliases_registry` doesn't
# character-validate them, so anything in the alias cell flows into a
# filesystem path. Defense-in-depth allowlist matches the convention
# in `.squidsquad/<alias>/` directory names already used by v1.
_V2_ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def deploy_alias_v2(alias, registry=None):
    """Deploy an alias under the v2 path (#10386 PRD-A/A6, --v2 branch).

    Resolves the alias via the A5 ``parse_aliases_registry`` to a
    ``(role_class, l3_domain)`` pair, then runs the existing v1 compose
    pipeline against the role-class and writes the output at
    ``.squidsquad/<alias>/CLAUDE.linked.v2.md``.

    The composed body is the v1 link logic as a deliberate placeholder
    (per PM's narrowed scope on #10386). When A2 ships the v2 link stage,
    A2's PR swaps the body inside this function; A6's CLI wiring stays.

    Aborts with ``SystemExit(1)`` if the registry is malformed, the
    alias contains disallowed characters, or the alias is not present —
    that is the abort path AC #10386 calls for.

    ``registry`` is an optional pre-parsed registry; ``deploy-all --v2``
    passes the registry it iterated to avoid re-parsing per alias and to
    close the TOCTOU window where ``config.md`` could be rewritten
    between the iterate-list parse and the per-alias resolve.

    Per #10358, the variable name ``role`` is preserved in code
    signatures (here the public arg is named ``alias`` because the
    caller passes an alias, but the inner variable that holds the
    role-class is still called ``role``).
    """
    if not isinstance(alias, str) or not _V2_ALIAS_RE.match(alias):
        print(
            f"ERROR: alias '{alias}' contains disallowed characters "
            f"(must match {_V2_ALIAS_RE.pattern}).",
            file=sys.stderr,
        )
        sys.exit(1)
    if registry is None:
        try:
            registry = _config_module.parse_aliases_registry()
        except Exception as e:  # AliasesRegistryError or downstream config-read error
            print(
                f"ERROR: cannot resolve alias '{alias}': failed to parse "
                f"`## Aliases` registry: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
    if alias not in registry:
        print(
            f"ERROR: alias '{alias}' not found in `## Aliases` registry. "
            f"Known aliases: {sorted(registry)}",
            file=sys.stderr,
        )
        sys.exit(1)
    role, _l3_domain = registry[alias]
    return deploy_role(
        role,
        output_name=alias,
        output_filename=_V2_LINKED_FILENAME,
        regenerate_cmd=f"{alias} --v2",
    )


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

    #6274 D2 dual-aware shim (F3 resolution): input normalization is
    independent of directory state; the return value tracks whichever
    directory exists on disk.

    - Pre-6274.2 (only `references/roles/dev/` exists):
        `_resolve_variant("dev-skill")` -> ("dev", "skill")
        `_resolve_variant("worker-skill")` -> ("dev", "skill")
    - Post-6274.2 (only `references/roles/worker/` exists):
        `_resolve_variant("dev-skill")` -> ("worker", "skill")
        `_resolve_variant("worker-skill")` -> ("worker", "skill")
    - Same rule for `qa`/`verifier`.

    The shim accepts both old and new prefixes throughout the migration
    and is removed in 6274.3.

    Examples:
        dev-skill     -> ("dev", "skill")     (pre-rename on-disk)
        worker-skill  -> ("dev", "skill")     (pre-rename on-disk, input alias)
        pm-ios        -> ("pm", "ios")
        pm            -> None (base role, not a variant)
        skill         -> None (legacy dev variant without hyphen)
    """
    if "-" not in role_name:
        return None
    base, variant = role_name.split("-", 1)

    # #6274 D2: input-normalize base via dual-aware alias table. The
    # canonical (on-disk) base is tried first; if its directory does
    # not exist, fall through to the alias. This makes the shim a
    # one-line addition with no behavior change pre-migration.
    candidates_in_order = [base]
    alias = _BASE_ALIAS_6274.get(base)
    if alias is not None:
        candidates_in_order.append(alias)

    identities = _list_known_role_identities()
    for candidate_base in candidates_in_order:
        variant_dir = ROLES_DIR / candidate_base / variant
        if variant_dir.is_dir() and (variant_dir / "instructions.md").exists():
            return candidate_base, variant
        # Fallback: known identity + variant dir (no instructions.md required)
        if (
            candidate_base in identities
            and (ROLES_DIR / candidate_base / variant).is_dir()
        ):
            return candidate_base, variant
    return None


# #6274 D2 dual-aware base alias table. Bidirectional: pre-rename
# `worker -> dev`/`verifier -> qa` lets new names fall back to old
# directories; post-rename `dev -> worker`/`qa -> verifier` lets old
# names fall back to new directories. `_resolve_variant` tries the
# input as-given first, then the alias — so the return value always
# tracks whichever directory exists on disk (F3). Deleted in 6274.3.
_BASE_ALIAS_6274 = {
    "worker": "dev",
    "verifier": "qa",
    "dev": "worker",
    "qa": "verifier",
}


def _assemble_soul(role_name: str) -> str:
    """Assemble a flat SOUL.md from Layer 1 (base) + role SOUL.

    Layer 1: references/roles/SOUL.md (at roles root — shared agent identity)
    Role SOUL (Layer 2): for variants (e.g. worker-skill), use the base
    role's SOUL.md — `roles/worker/SOUL.md` post-6274.2, or `roles/dev/SOUL.md`
    via 6274.1 alias for pre-rename installs. For base roles, use
    `roles/<role>/SOUL.md`. (Layer 3 variant-level SOUL files are NOT read
    here — the variant gets the base role's SOUL only, per the
    `_resolve_variant` branch below.)

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
            # Legacy worker-variant fallback (skill -> worker, or skill -> dev for pre-6274 installs)
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





MANDATORY_ROLES = {"pm", "verifier", "dm"}  # #6055/#6274: always present (qa→verifier per D5)


def _collect_all_roles() -> list:
    """Return all configured roles: worker-agents from config + pm + verifier + dm."""
    agents = _read_config_value("workers") or ""
    roles = [r.strip() for r in agents.split(",") if r.strip()]
    # Mandatory roles — always required (#6055/#6274: qa→verifier per D5)
    for role in ("pm", "verifier", "dm"):
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

    # #10386 PRD-A/A6: --v2 is recognized on `deploy` and `deploy-all`.
    # Strip the flag from positional args so the rest of the dispatch
    # works unchanged in v1 mode (v1 byte-equivalence is the §9a coexistence
    # contract).
    v2_mode = "--v2" in args
    args = [a for a in args if a != "--v2"]

    # #10388 PRD-A/A4: --check runs in-memory compose and diffs against
    # on-disk CLAUDE.md without writing. Recognized on `deploy` and
    # `deploy-all` (mirrors --v2 placement). Mutually exclusive with --v2
    # for now — A4.5 (#10395) layers v2 + staged-content semantics on top.
    check_mode = "--check" in args
    args = [a for a in args if a != "--check"]

    cmd = args[0]
    if v2_mode and cmd not in ("deploy", "deploy-all"):
        print(
            f"WARNING: --v2 has no effect on `compose.py {cmd}` (only "
            f"`deploy` and `deploy-all` honor it).",
            file=sys.stderr,
        )
    if check_mode and cmd not in ("deploy", "deploy-all"):
        print(
            f"WARNING: --check has no effect on `compose.py {cmd}` (only "
            f"`deploy` and `deploy-all` honor it).",
            file=sys.stderr,
        )
    if check_mode and v2_mode:
        print(
            "ERROR: --check + --v2 combination is reserved for A4.5 "
            "(#10395) and not implemented here. Use `--check` alone for "
            "v1 drift detection.",
            file=sys.stderr,
        )
        sys.exit(CHECK_EXIT_ERROR)

    if cmd == "all":
        content = compose_all()
        OUTPUT_FILE.write_text(content, encoding="utf-8")
        print(f"Composed agent-instructions.md ({len(content.splitlines())} lines)")

    elif cmd == "deploy":
        if len(args) < 2:
            print("Usage: compose.py deploy <role> [--v2|--check]", file=sys.stderr)
            print("  e.g.: compose.py deploy skill", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        if check_mode:
            try:
                status, sections = check_role(role_name)
            except Exception as e:
                print(f"ERROR: cannot check role '{role_name}': {e}", file=sys.stderr)
                sys.exit(CHECK_EXIT_ERROR)
            if status == "missing":
                print(f"  {role_name}: MISSING — .squidsquad/{role_name}/CLAUDE.md does not exist", file=sys.stderr)
                sys.exit(CHECK_EXIT_DRIFT)
            if status == "drift":
                summary = ", ".join(sections) if sections else "<whole file>"
                print(f"  {role_name}: DRIFT — sections: {summary}", file=sys.stderr)
                sys.exit(CHECK_EXIT_DRIFT)
            print(f"  {role_name}: clean")
            sys.exit(CHECK_EXIT_CLEAN)
        if v2_mode:
            try:
                output = deploy_alias_v2(role_name)
                lines = output.read_text(encoding="utf-8").count("\n")
                print(f"Deployed {role_name} (v2) {_V2_LINKED_FILENAME} ({lines} lines) -> {output.relative_to(REPO_ROOT)}")
            except SystemExit:
                # deploy_alias_v2 already printed a diagnostic; propagate exit.
                raise
            except Exception as e:
                print(f"ERROR: Failed to deploy alias '{role_name}' (v2): {e}", file=sys.stderr)
                sys.exit(1)
            # v2 path skips event-contract derivation — that's a v1 side-effect
            # tied to the v1 agent-instructions tree. Re-evaluate when the v2
            # switch PR (end of PRD A-E family) makes v2 the default.
            return
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
        if check_mode:
            try:
                roles = _collect_all_roles()
            except Exception as e:
                print(f"ERROR: cannot iterate roles for --check: {e}", file=sys.stderr)
                sys.exit(CHECK_EXIT_ERROR)
            drifted = []
            for role in roles:
                try:
                    status, sections = check_role(role)
                except Exception as e:
                    print(f"ERROR: cannot check role '{role}': {e}", file=sys.stderr)
                    sys.exit(CHECK_EXIT_ERROR)
                if status == "missing":
                    print(f"  {role}: MISSING — .squidsquad/{role}/CLAUDE.md does not exist", file=sys.stderr)
                    drifted.append(role)
                elif status == "drift":
                    summary = ", ".join(sections) if sections else "<whole file>"
                    print(f"  {role}: DRIFT — sections: {summary}", file=sys.stderr)
                    drifted.append(role)
                else:
                    print(f"  {role}: clean")
            if drifted:
                sys.exit(CHECK_EXIT_DRIFT)
            sys.exit(CHECK_EXIT_CLEAN)
        if v2_mode:
            try:
                registry = _config_module.parse_aliases_registry()
            except Exception as e:
                print(f"ERROR: cannot iterate aliases (v2): failed to parse `## Aliases` registry: {e}", file=sys.stderr)
                sys.exit(1)
            failed = []
            for alias in sorted(registry):
                try:
                    output = deploy_alias_v2(alias, registry=registry)
                    lines = output.read_text(encoding="utf-8").count("\n")
                    print(f"  {alias} (v2): {lines} lines -> {output.relative_to(REPO_ROOT)}")
                except SystemExit:
                    failed.append(alias)
                except Exception as e:
                    print(f"  {alias} (v2): FAILED — {e}", file=sys.stderr)
                    failed.append(alias)
            if failed:
                print(f"ERROR: {len(failed)} alias(es) failed: {', '.join(failed)}", file=sys.stderr)
                sys.exit(1)
            return
        # Deploy all configured agents
        roles = _collect_all_roles()
        # #6055: Check mandatory roles are present
        missing = _check_mandatory_roles(roles)
        if missing:
            print(f"ERROR: Mandatory role(s) missing: {', '.join(missing)}", file=sys.stderr)
            print(f"Every SquidSquad team requires PM, Verifier, and DM.", file=sys.stderr)
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
