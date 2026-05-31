"""L1-L3 source frontmatter parser (#10487, PRD-A Story A2a).

Reads YAML frontmatter at the top of a markdown source file and returns
the ``slot`` + ``ordinal`` fields the v2 link stage needs for sort
ordering, plus any other frontmatter fields untouched.

Grammar (TRD §3 / §4 + the existing source-file convention in
``references/roles/<role>/<slot>.md``):

    ---
    slot: instructions
    ordinal: 20
    roles: [worker]
    step-ids: [step:cycle/triage, step:cycle/implement]
    ---

    # body content...

- ``slot`` must be one of the six legal slot names; reject otherwise.
- ``ordinal`` must be a non-negative ``int``; reject otherwise.
- Sources without frontmatter return ``None`` (some L1-L3 files may not
  yet carry frontmatter during the migration window — A2 callers decide
  how to handle that).

Pure additive. Existing v1 compose.py read sites ignore frontmatter
and are not touched by this module.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


# Duplicated from l4_parser.LEGAL_SLOTS — keeping the constant local so
# A2a doesn't import from A2b (the two PRs are independent and either
# may land first; a cross-module import would couple them). Tracker
# task to consolidate once both PRDs ship.
LEGAL_SLOTS = frozenset(
    {"identity", "responsibility", "soul", "instructions", "project-context", "vault"}
)

# The opening ``---`` must be at the very top. Horizontal whitespace
# (spaces/tabs) is tolerated on both delimiter lines per Jekyll
# convention, but the broader ``\s*`` would allow ``\n`` and create
# ambiguity around empty frontmatter blocks.
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n([\s\S]*?)\n---[ \t]*(?:\n|\Z)")
# An empty frontmatter block (``---\n---``) doesn't satisfy the regex
# above because the required ``\n`` before the closing ``---`` is already
# consumed by the opening. Detect that shape explicitly so it raises
# instead of silently returning ``None`` (DS finding).
_EMPTY_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n---[ \t]*(?:\n|\Z)")


try:
    import yaml as _yaml
except ImportError:
    _yaml = None


class FrontmatterError(ValueError):
    """Raised when frontmatter is present but invalid."""


@dataclass
class SourceFrontmatter:
    slot: str
    ordinal: int
    extras: dict = field(default_factory=dict)


def parse_source_frontmatter(path):
    """Read ``path`` and parse its top YAML frontmatter.

    Returns ``SourceFrontmatter`` on success, ``None`` when the file has
    no frontmatter. Raises :class:`FrontmatterError` when frontmatter is
    present but malformed, missing required fields, or carrying invalid
    ``slot`` / ``ordinal`` values. ``FileNotFoundError`` is left to
    propagate — callers can catch it explicitly.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_source_frontmatter_text(text, source=str(path))


def parse_source_frontmatter_text(text, source="<text>"):
    """Same as :func:`parse_source_frontmatter` but operates on a string."""
    m = _FRONTMATTER_RE.match(text)
    if m is None:
        if _EMPTY_FRONTMATTER_RE.match(text):
            raise FrontmatterError(
                f"{source}: frontmatter block is empty — required "
                f"`slot` and `ordinal` fields are missing."
            )
        return None
    raw = m.group(1)
    data = _yaml_load(raw, source)
    if not isinstance(data, dict):
        raise FrontmatterError(
            f"{source}: frontmatter must be a YAML mapping at top level; "
            f"got {type(data).__name__}."
        )
    slot = _validate_slot(data, source)
    ordinal = _validate_ordinal(data, source)
    extras = {k: v for k, v in data.items() if k not in ("slot", "ordinal")}
    return SourceFrontmatter(slot=slot, ordinal=ordinal, extras=extras)


def _yaml_load(raw, source):
    if _yaml is None:
        raise FrontmatterError(
            f"{source}: PyYAML is required to parse frontmatter "
            f"(install via `pip install pyyaml`)."
        )
    try:
        return _yaml.safe_load(raw)
    except _yaml.YAMLError as e:
        raise FrontmatterError(
            f"{source}: malformed YAML in frontmatter: {e}"
        ) from e


def _validate_slot(data, source):
    if "slot" not in data:
        raise FrontmatterError(
            f"{source}: frontmatter missing required `slot` field."
        )
    slot = data["slot"]
    if not isinstance(slot, str) or slot not in LEGAL_SLOTS:
        raise FrontmatterError(
            f"{source}: invalid `slot` value {slot!r} — must be one of "
            f"{sorted(LEGAL_SLOTS)}."
        )
    return slot


def _validate_ordinal(data, source):
    if "ordinal" not in data:
        raise FrontmatterError(
            f"{source}: frontmatter missing required `ordinal` field."
        )
    ordinal = data["ordinal"]
    # Reject ``True`` / ``False``: ``isinstance(True, int)`` is True in
    # Python, but a YAML scalar of ``true``/``false`` is not a numeric
    # ordinal value and would silently sort as 1 / 0.
    if isinstance(ordinal, bool) or not isinstance(ordinal, int):
        raise FrontmatterError(
            f"{source}: `ordinal` must be a non-negative integer; got "
            f"{ordinal!r} ({type(ordinal).__name__})."
        )
    if ordinal < 0:
        raise FrontmatterError(
            f"{source}: `ordinal` must be non-negative; got {ordinal}."
        )
    return ordinal
