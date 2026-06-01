"""Six-slot v2 link stage (#10490, PRD-A Story A2d).

Implements ``emit_v2_linked(role_class, l3_domain)`` per
[[compose-link-stage]] §4.1 + §4.2 and COMPOSE-ARCHITECTURE §4.1-§4.2:

1. Walk L1-L3 source files (``references/roles/`` + ``references/sub-skills/``)
   scoped to the role class + optional L3 domain.
2. Parse YAML frontmatter via :func:`source_frontmatter.parse_source_frontmatter`.
3. Skip files that lack frontmatter — they are not yet migrated under
   #10394 and the v2 path treats unmigrated files as opt-out content.
4. Apply the optional ``roles:`` extras filter (default = applies to all).
5. Stable sort by ``(slot_index, ordinal, path)``.
6. Group bodies by slot.
7. For each slot present in the L4 file at
   ``.squidsquad/project/<role_class>.md``, apply ops via
   :func:`l4_op_processor.apply_l4_ops`.
8. Emit exactly six H2 sections in canonical order:
   ``Identity``, ``Responsibility``, ``Soul``, ``Instructions``,
   ``Project Context``, ``Vault``.

Pure additive. A2f (#10492) is the caller that wires this into
``deploy_alias_v2``. This module does no I/O beyond ``read_text`` on the
walked source files and the L4 file.
"""

import re
from pathlib import Path

from source_frontmatter import (  # noqa: E402
    LEGAL_SLOTS,
    parse_source_frontmatter_text,
)
from l4_parser import L4Document, parse_l4_file  # noqa: E402
from l4_op_processor import apply_l4_ops  # noqa: E402
from link_stage_validator import LinkStageSource  # noqa: E402


# Canonical slot ordering — TRD §3.3 + AC bullet "exactly six H2 sections
# in canonical order". Display names map the lowercase slot key (used by
# frontmatter) to the ``## <Heading>`` text emitted in the linked output.
CANONICAL_SLOT_ORDER = (
    "identity",
    "responsibility",
    "soul",
    "instructions",
    "project-context",
    "vault",
)
SLOT_DISPLAY = {
    "identity": "Identity",
    "responsibility": "Responsibility",
    "soul": "Soul",
    "instructions": "Instructions",
    "project-context": "Project Context",
    "vault": "Vault",
}
SLOT_INDEX = {slot: i for i, slot in enumerate(CANONICAL_SLOT_ORDER)}


# Frontmatter delimiter — same shape as source_frontmatter._FRONTMATTER_RE
# but kept local so this module can strip the block from each file's text
# without re-coupling to A2a's internals.
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n[\s\S]*?\n---[ \t]*\n?")


def emit_v2_linked(role_class, l3_domain, *, repo_root=None, l4_path=None):
    """Walk L1-L3 sources for ``role_class`` and emit the v2 linked composite.

    ``role_class`` — e.g. ``"worker"`` / ``"pm"`` / ``"dm"`` / ``"verifier"``.
    ``l3_domain`` — e.g. ``"skill"`` / ``"ios"`` / ``"fe"`` / ``None``.
    ``repo_root`` — override for tests; defaults to the parent of the
    parent of this file (the live repo root in normal use).
    ``l4_path`` — override the L4 file path; defaults to
    ``<repo_root>/.squidsquad/project/<role_class>.md``.

    Returns the composed string. Output is byte-stable across re-runs
    given unchanged inputs (deterministic sort, no time/random sources).
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
    repo_root = Path(repo_root)
    if l4_path is None:
        l4_path = repo_root / ".squidsquad" / "project" / f"{role_class}.md"

    parsed = _parse_all_applicable_sources(repo_root, role_class, l3_domain)
    # Stable sort by (slot_index, ordinal, posix path). Path tie-break
    # gives byte-stable output even when two files share the same
    # (slot, ordinal) — which #10394 migration must avoid but the link
    # stage shouldn't crash on if it happens.
    parsed.sort(key=lambda r: (r[0], r[1], r[2]))

    slot_bodies = {slot: [] for slot in CANONICAL_SLOT_ORDER}
    for slot_idx, _ordinal, _path, body in parsed:
        slot_bodies[CANONICAL_SLOT_ORDER[slot_idx]].append(body)

    if Path(l4_path).is_file():
        l4_doc = parse_l4_file(l4_path)
    else:
        l4_doc = L4Document.empty()

    out_chunks = []
    for slot in CANONICAL_SLOT_ORDER:
        combined = _join_bodies(slot_bodies[slot])
        ops = l4_doc.slots.get(slot, [])
        if ops:
            combined = apply_l4_ops(combined, ops)
        # Every H2 section starts with the canonical heading and a blank
        # line. If the slot is empty, the section is still emitted to
        # satisfy the "exactly six H2 sections" AC.
        out_chunks.append(f"## {SLOT_DISPLAY[slot]}\n\n{combined}".rstrip() + "\n")
    return "\n".join(out_chunks)


def _parse_all_applicable_sources(repo_root, role_class, l3_domain):
    """Walk the source paths, parse frontmatter, return entries to sort.

    Returns ``[(slot_index, ordinal, posix_path, body), ...]`` for every
    source file that (a) carries frontmatter, (b) declares a legal slot,
    and (c) passes the optional ``roles:`` extras filter.
    """
    entries = []
    for path in _walk_applicable_paths(repo_root, role_class, l3_domain):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # A non-readable source file is a real install pathology;
            # link-stage should not silently include it. But the link
            # stage owns "skip on missing frontmatter", not "raise on
            # I/O" — so skip-with-no-record matches the unmigrated path.
            continue
        try:
            fm = parse_source_frontmatter_text(text, source=str(path))
        except Exception:
            # FrontmatterError on a present-but-malformed block: today's
            # unmigrated sources have no frontmatter and return None.
            # A4.5/A2e own enforcement; A2d's job is to assemble, so
            # we treat malformed frontmatter as opt-out (skip) here.
            continue
        if fm is None:
            continue
        if fm.slot not in LEGAL_SLOTS:
            continue  # paranoia; source_frontmatter already validates
        if not _is_applicable_by_roles_filter(fm, role_class):
            continue
        body = _strip_frontmatter(text)
        # POSIX path string for stable cross-OS sort.
        posix_path = path.relative_to(repo_root).as_posix()
        entries.append((SLOT_INDEX[fm.slot], int(fm.ordinal), posix_path, body))
    return entries


def _walk_applicable_paths(repo_root, role_class, l3_domain):
    """Yield .md paths for ``role_class`` + ``l3_domain``.

    Path classes:
    - L1: ``references/roles/*.md`` (top-level base files).
    - L1: ``references/sub-skills/common/**/*.md``.
    - L1: ``references/sub-skills/common-events/**/*.md`` (event-mode
      common fragments; harmless to walk in polling-mode composes too,
      they're frontmatter-filtered).
    - L2: ``references/roles/<role_class>/*.md`` (direct children only).
    - L2: ``references/sub-skills/roles/<role_class>/*.md``.
    - L3 (if ``l3_domain`` is set): the equivalent ``<l3_domain>/**`` subtrees.

    Other ``references/roles/<role_class>/<other_l3>/**`` subtrees are
    intentionally excluded — those belong to OTHER L3 domains.
    """
    refs = repo_root / "references"

    # L1 (top-level)
    roles_root = refs / "roles"
    if roles_root.is_dir():
        for p in roles_root.glob("*.md"):
            yield p
    common = refs / "sub-skills" / "common"
    if common.is_dir():
        yield from common.rglob("*.md")
    common_events = refs / "sub-skills" / "common-events"
    if common_events.is_dir():
        yield from common_events.rglob("*.md")

    # L2 (role-class direct children)
    role_dir = roles_root / role_class
    if role_dir.is_dir():
        for p in role_dir.glob("*.md"):
            yield p
    sk_role_dir = refs / "sub-skills" / "roles" / role_class
    if sk_role_dir.is_dir():
        for p in sk_role_dir.glob("*.md"):
            yield p

    # L3 (specific domain only)
    if l3_domain:
        l3_dir = role_dir / l3_domain
        if l3_dir.is_dir():
            yield from l3_dir.rglob("*.md")
        sk_l3_dir = sk_role_dir / l3_domain
        if sk_l3_dir.is_dir():
            yield from sk_l3_dir.rglob("*.md")


def _classify_layer(posix_path, role_class):
    """Map a walked source path to its layer label ``"L1"`` / ``"L2"`` / ``"L3"``.

    - L1: top-level ``references/roles/*.md`` (no subdir) or anywhere
      under ``references/sub-skills/common`` / ``common-events``.
    - L2: ``references/roles/<role_class>/*.md`` (direct child) or
      ``references/sub-skills/roles/<role_class>/*.md`` (direct child).
    - L3: anything deeper under the role_class subtree
      (``references/roles/<role_class>/<l3>/...`` or the matching
      ``sub-skills/roles/<role_class>/<l3>/...``).
    """
    parts = posix_path.split("/")
    # references/sub-skills/common/** or common-events/** -> L1
    if (
        len(parts) >= 3
        and parts[0] == "references"
        and parts[1] == "sub-skills"
        and parts[2] in ("common", "common-events")
    ):
        return "L1"
    # references/roles/<file>.md (top-level) -> L1
    if len(parts) == 3 and parts[0] == "references" and parts[1] == "roles":
        return "L1"
    # references/roles/<role_class>/... -> L2 if direct child, else L3
    if (
        len(parts) >= 4
        and parts[0] == "references"
        and parts[1] == "roles"
        and parts[2] == role_class
    ):
        return "L2" if len(parts) == 4 else "L3"
    # references/sub-skills/roles/<role_class>/... -> L2 if direct child, else L3
    if (
        len(parts) >= 5
        and parts[0] == "references"
        and parts[1] == "sub-skills"
        and parts[2] == "roles"
        and parts[3] == role_class
    ):
        return "L2" if len(parts) == 5 else "L3"
    # Defensive fallback: treat as L1 (most permissive). The walk filters
    # already ensure unrelated paths aren't yielded.
    return "L1"


def collect_sources_for_validation(role_class, l3_domain, *, repo_root=None):
    """Walk the L1-L3 sources and return a list of ``LinkStageSource`` records.

    Used by A2f orchestration: the same record list is passed to
    ``validate_link_stage`` (A2e) BEFORE the emit step, so validation
    failures abort without a partial write.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
    repo_root = Path(repo_root)
    sources = []
    for path in _walk_applicable_paths(repo_root, role_class, l3_domain):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            fm = parse_source_frontmatter_text(text, source=str(path))
        except Exception:
            continue
        if fm is None:
            continue
        if fm.slot not in LEGAL_SLOTS:
            continue
        if not _is_applicable_by_roles_filter(fm, role_class):
            continue
        body = _strip_frontmatter(text)
        posix_path = path.relative_to(repo_root).as_posix()
        sources.append(LinkStageSource(
            layer=_classify_layer(posix_path, role_class),
            path=posix_path,
            slot=fm.slot,
            body=body,
        ))
    return sources


def _is_applicable_by_roles_filter(fm, role_class):
    """Apply the optional ``roles:`` extras filter (default = applies to all)."""
    roles = fm.extras.get("roles")
    if roles is None:
        return True
    return role_class in roles


def _strip_frontmatter(text):
    """Remove the leading YAML frontmatter block, if present."""
    m = _FRONTMATTER_RE.match(text)
    if m is None:
        return text
    return text[m.end():]


def _join_bodies(bodies):
    """Concatenate per-file bodies with a single blank line between them.

    Each body is stripped of leading/trailing whitespace so the joined
    output has predictable spacing regardless of how each source file
    terminates.
    """
    cleaned = [b.strip() for b in bodies if b.strip()]
    return "\n\n".join(cleaned)
