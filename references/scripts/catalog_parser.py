"""D1: Sub-skill catalog parser (#10672, PRD-D Story D1).

Parses ``docs/sub-skill-catalog.md`` and returns a ``{name: source_path}``
mapping that v2 compose uses to resolve every ``→ run sub-skill: <name>``
reference (per COMPOSE-ARCHITECTURE.md §4.5).

The catalog is authored as multiple Markdown tables grouped under H2
section headings that name the source directory (e.g. ``## `common/` —``,
``## `common-events/` —``, ``## `roles/<role>/` —``). For ``roles/``,
each H3 sub-section pins a specific role-class (e.g.
``### PM (`roles/pm/`)``), giving the per-role source path.

Parser semantics:

- For each H2 matching the directory pattern, every table row under it
  produces ``{name: f"references/sub-skills/{dir}/{name}.md"}``.
- The ``project/`` H2 is EXCLUDED — those rows are L4 seed templates,
  not sub-skills resolved by compose (per §4.5 the catalog gate
  operates only on referenced sub-skill names; L4 seed templates are
  install-time scaffolding).
- Optional table columns beyond ``name`` (e.g. one-liner, used-by)
  are read for the ``description`` field but never required (forward-
  compatible per AC2's "Optional columns ignored gracefully").
- Source-path validation per AC4: must be relative under
  ``references/sub-skills/``, no ``..`` traversal segments, ends in
  ``.md``. The parser derives the path so the only invalid shape
  would be a malformed directory token in the H2.

NEVER raises silently — every malformed-row condition raises
``CatalogParseError`` with a structured diagnostic naming the offending
line + the violated rule (AC3). Callers (D3/D4/D8) catch these and
surface them as compose-time aborts.
"""

import re
from dataclasses import dataclass
from pathlib import Path


class CatalogParseError(ValueError):
    """Raised when the catalog file violates the row schema."""


@dataclass
class CatalogEntry:
    """One catalog row resolved to ``(name, source_path, description)``.

    ``source_path`` is the relative path rooted at the repo root
    (e.g. ``references/sub-skills/common/boot-bootstrap.md``).
    ``description`` is the one-liner from the table's second column;
    empty when the catalog row omits it.
    """

    name: str
    source_path: str
    description: str = ""


# H2 headings naming a directory: ``## \`<dir>/\` —`` (with literal
# backticks around the directory token, em-dash separator). The catalog
# uses this convention to declare which directory rows under the H2
# resolve to.
_H2_DIR_RE = re.compile(
    r"^##\s+`([a-z][a-z0-9_-]*(?:/[a-z<>][a-z0-9_<>-]*)*?)/`\s*[—-]",
)

# H3 headings under ``## \`roles/<role>/\`` that pin a specific
# role-class via a parenthesized directory: ``### NAME (\`roles/<role>/\`)``.
# The directory inside the parens is the actual source-path prefix used
# for rows under this H3.
_H3_ROLE_DIR_RE = re.compile(
    r"^###\s+\S+.*?\(\s*`([a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)*?)/`\s*\)",
)

# Markdown table delimiter row — `| --- | --- | --- |` style.
_TABLE_DELIM_RE = re.compile(r"^\s*\|(\s*:?-+:?\s*\|)+\s*$")

# A sub-skill name in the catalog rows: lowercase, hyphen-separated,
# enclosed in backticks. e.g. `boot-bootstrap` or `vault-protocol`.
# Slash-bearing names like ``roles/dm/events/pr-merge-wait`` ARE valid —
# they encode the source path inline (the catalog name IS the
# `→ run sub-skill: <name>` lookup key per compose.py:53 + the
# matching `{{include: roles/dm/events/pr-merge-wait}}` reference in
# the role's L2 instructions). Strikethrough/tilde-wrapped names
# (`~~`removed-name`~~`) are ignored because those rows are
# retirement notes, not active entries.
_NAME_CELL_RE = re.compile(r"^`([a-z][a-z0-9/_-]*)`$")

# A "row that looks like it MIGHT be a catalog entry" — first cell
# starts with a backtick at any depth. Used to distinguish silent-skip
# (retirement annotation like ``~~`x`~~``) from malformed-entry (e.g.
# `` `Boot-bootstrap` `` with a capital letter, or HTML strikethrough
# ``<s>`x`</s>``) which the reviewer asked us to raise on.
_BACKTICK_ANYWHERE_RE = re.compile(r"`[^`]+`")

# Allowlist of directories whose H2 entries the parser MUST emit. An
# allowlist (vs. the previous denylist) keeps intent self-documenting:
# the parser knows exactly which trees feed v2 compose, and a future
# catalog edit adding ``## \`docs/\` —`` for non-sub-skill content
# won't silently leak entries into the mapping.
_INCLUDED_DIRS = frozenset({"common", "common-events", "roles"})


def parse_catalog(catalog_path):
    """Parse ``catalog_path`` and return ``{name: source_path}``.

    See module docstring for the schema and validation rules. Returns
    a plain dict so callers can do quick ``in`` / ``get`` membership
    checks; the richer ``CatalogEntry`` list is available via
    :func:`parse_catalog_entries`.
    """
    return {e.name: e.source_path for e in parse_catalog_entries(catalog_path)}


def parse_catalog_entries(catalog_path):
    """Parse ``catalog_path`` and return a list of :class:`CatalogEntry`.

    Per AC6 the parser aborts on:

    - Malformed row that looks like a sub-skill entry but breaks the
      table shape.
    - Duplicate ``name`` across catalog rows.
    - Source path containing ``..`` segments, missing ``.md`` suffix,
      or not rooted under ``references/sub-skills/``.

    Raises :class:`CatalogParseError` on any of the above.
    """
    catalog_path = Path(catalog_path)
    if not catalog_path.is_file():
        raise CatalogParseError(f"catalog file not found: {catalog_path}")

    text = catalog_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    entries = []
    seen_names = {}

    current_h2_dir = None
    current_h3_dir = None
    in_table = False
    table_header_cols = None
    description_col_index = None

    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.rstrip()

        # H2 boundary — reset H3 + table state, capture new directory
        h2_match = _H2_DIR_RE.match(stripped)
        if h2_match is not None:
            current_h2_dir = h2_match.group(1)
            current_h3_dir = None
            in_table = False
            table_header_cols = None
            description_col_index = None
            continue

        # H3 boundary — may pin a role-specific directory; otherwise
        # carry the H2 directory forward.
        if stripped.startswith("### "):
            h3_match = _H3_ROLE_DIR_RE.match(stripped)
            current_h3_dir = h3_match.group(1) if h3_match else None
            in_table = False
            table_header_cols = None
            description_col_index = None
            continue

        # Detect the start of a table by spotting the delimiter row;
        # the preceding line is the header.
        if _TABLE_DELIM_RE.match(stripped):
            header_line = lines[lineno - 2] if lineno >= 2 else ""
            header_cols = _split_row(header_line)
            if header_cols and header_cols[0].lower() in (
                    "sub-skill", "name", "subskill"):
                in_table = True
                table_header_cols = [c.lower() for c in header_cols]
                description_col_index = _resolve_description_column(
                    table_header_cols,
                )
                continue
            in_table = False
            table_header_cols = None
            description_col_index = None
            continue

        # Inside a table: parse rows, derive source path, validate.
        if in_table and stripped.startswith("|") and not _TABLE_DELIM_RE.match(stripped):
            cols = _split_row(stripped)
            if not cols:
                continue
            name_cell = cols[0].strip()
            name_match = _NAME_CELL_RE.match(name_cell)
            if name_match is None:
                # Two distinct cases here, per C7 review C1:
                #   1. The first cell has NO backticks at all OR is
                #      tilde-wrapped (~~`x`~~ retirement note). Silent
                #      skip is correct — these are intentional non-rows.
                #   2. The first cell contains a backtick-wrapped name
                #      but doesn't match the strict regex (e.g.
                #      `Boot-bootstrap` with capital, HTML-wrapped
                #      `<s>`x`</s>`, or some future formatting we don't
                #      handle yet). Silent skip would mask a PM typo OR
                #      a real catalog entry that v2 compose will fail
                #      to resolve. RAISE so the catalog defect surfaces
                #      at parser-build time, not compose time.
                if name_cell.startswith("~~"):
                    continue
                if "`" in name_cell and _BACKTICK_ANYWHERE_RE.search(name_cell):
                    raise CatalogParseError(
                        f"catalog row at line {lineno} has first cell "
                        f"`{name_cell}` that contains a backtick-wrapped "
                        f"name but does not match the strict-name regex "
                        f"(lowercase, hyphen/slash/underscore only). "
                        f"Either fix the catalog entry or add a retirement "
                        f"strikethrough (`~~`...`~~`) if the row is no "
                        f"longer active."
                    )
                continue
            name = name_match.group(1)
            # B1 fix: slash-bearing names override H2/H3 derivation.
            # Catalog convention: `roles/dm/events/pr-merge-wait`
            # encodes both the lookup key (the name as-is) and the
            # relative source-path under references/sub-skills/.
            if "/" in name:
                source_path = f"references/sub-skills/{name}.md"
            else:
                source_dir = _resolve_source_dir(
                    h2_dir=current_h2_dir,
                    h3_dir=current_h3_dir,
                    lineno=lineno,
                    name=name,
                )
                if source_dir is None:
                    # Row appears under a section the allowlist excludes
                    # (e.g. ``project/``), OR outside any H2 — skip the
                    # excluded case silently, raise in the dangling case.
                    if current_h2_dir is None:
                        raise CatalogParseError(
                            f"catalog row at line {lineno} has name `{name}` "
                            f"but no enclosing ## `<dir>/` H2 — cannot derive "
                            f"source-path."
                        )
                    continue
                source_path = f"references/sub-skills/{source_dir}/{name}.md"
            _validate_source_path(source_path, lineno, name)
            if name in seen_names:
                prior_lineno, prior_source_path = seen_names[name]
                raise CatalogParseError(
                    f"duplicate catalog entry `{name}` at line {lineno} "
                    f"(`{source_path}`); first seen at line {prior_lineno} "
                    f"(`{prior_source_path}`). PM: disambiguate by renaming "
                    f"one of the two variants."
                )
            seen_names[name] = (lineno, source_path)
            description = ""
            if description_col_index is not None \
                    and description_col_index < len(cols):
                description = cols[description_col_index].strip()
            # D8 (#10679): every catalog row MUST have a non-empty
            # description so v2 compose can render the catalog as the
            # operator-facing `→ run sub-skill: <name>` documentation
            # surface. Empty cells in the description column are
            # treated as a missing required column per AC3.
            _validate_row_schema(
                name=name,
                description=description,
                cols=cols,
                description_col_index=description_col_index,
                lineno=lineno,
            )
            entries.append(CatalogEntry(
                name=name,
                source_path=source_path,
                description=description,
            ))

    return entries


def _validate_row_schema(*, name, description, cols, description_col_index,
                         lineno):
    """D8: enforce the required-columns schema on one catalog row.

    Required columns: ``name`` (already extracted by ``_NAME_CELL_RE``)
    + ``source-path`` (derived by ``_resolve_source_dir`` + checked by
    ``_validate_source_path``) + ``description`` (the one-liner
    column). This helper closes the loop on the third required field
    so a row with a valid name + path but no description aborts per
    AC2/AC3.

    Optional columns (``Used by`` etc.) are NOT enforced — they're
    forward-compatible per AC4 of D1 + AC4 of D8. Future PRDs may add
    ``role-scope`` / ``slot`` columns; this helper stays narrow.
    """
    if description_col_index is None or description_col_index >= len(cols):
        raise CatalogParseError(
            f"catalog row at line {lineno} for `{name}` is missing the "
            f"required `description` column (the one-liner / second "
            f"column). Add a description so v2 compose can render the "
            f"catalog as the operator-facing reference surface."
        )
    if not description:
        raise CatalogParseError(
            f"catalog row at line {lineno} for `{name}` has an empty "
            f"`description` value. Required columns cannot be empty — "
            f"either fill the description or mark the row as retired "
            f"via ``~~`{name}`~~``."
        )


def _split_row(row_line):
    """Split a Markdown table row into cell strings.

    Strips outer pipes + per-cell whitespace. Returns ``[]`` on rows
    that don't look like Markdown tables.
    """
    line = row_line.strip()
    if not line.startswith("|"):
        return []
    if line.endswith("|"):
        line = line[:-1]
    parts = line.split("|")[1:]  # drop leading empty
    return [p.strip() for p in parts]


def _resolve_description_column(header_cols):
    """Return the index of the one-liner / description column, or None.

    Tolerates several common header names so future catalog edits
    don't break the parser.
    """
    candidates = ("one-liner", "description", "purpose", "summary")
    for i, h in enumerate(header_cols):
        if h in candidates:
            return i
    if len(header_cols) >= 2:
        # Default: column index 1 (second column) is the description in
        # the current catalog format.
        return 1
    return None


def _resolve_source_dir(*, h2_dir, h3_dir, lineno, name):
    """Pick the directory token to use for a row's source path.

    Priority: H3-pinned directory (e.g. ``roles/pm/``) wins, falling
    back to the enclosing H2 directory. Returns ``None`` when the row
    falls outside the allowlisted set (``_INCLUDED_DIRS``) — caller
    skips. The allowlist (vs. an exclusion list) keeps intent self-
    documenting: only ``common/`` / ``common-events/`` / ``roles/``
    feed v2 compose.
    """
    if h2_dir is None:
        return None
    # H2's first path segment must be on the allowlist. For
    # ``roles/<role>/`` placeholder H2s, the first segment is
    # ``roles`` which IS allowlisted.
    h2_root = h2_dir.split("/", 1)[0]
    if h2_root not in _INCLUDED_DIRS:
        return None
    # H2 is ``roles/<role>/`` (literal angle-bracketed placeholder) —
    # the H3 MUST pin a real directory like ``roles/pm/`` for rows
    # under it to be resolvable.
    if "<" in h2_dir or ">" in h2_dir:
        if h3_dir is None:
            raise CatalogParseError(
                f"catalog row at line {lineno} has name `{name}` under "
                f"placeholder H2 `## \\`{h2_dir}/\\` —` but no H3 "
                f"pinning a concrete `<role>` directory — cannot derive "
                f"source-path."
            )
        return h3_dir
    return h2_dir


def _validate_source_path(source_path, lineno, name):
    """Per AC4: rooted at ``references/sub-skills/``, no ``..``, ends ``.md``."""
    if not source_path.startswith("references/sub-skills/"):
        raise CatalogParseError(
            f"catalog row at line {lineno} for `{name}` resolves to "
            f"`{source_path}` which is not rooted at "
            f"`references/sub-skills/`."
        )
    if ".." in Path(source_path).parts:
        raise CatalogParseError(
            f"catalog row at line {lineno} for `{name}` resolves to "
            f"`{source_path}` which contains a `..` path-traversal "
            f"segment."
        )
    if not source_path.endswith(".md"):
        raise CatalogParseError(
            f"catalog row at line {lineno} for `{name}` resolves to "
            f"`{source_path}` which does not end in `.md`."
        )
    # AC5: `.claude/skills/` paths are NEVER valid catalog entries.
    # Defensive guard against a future catalog edit that adds an H2
    # named `.claude/skills/` — the source-path derivation would
    # produce a path starting with `.claude/` which fails the
    # `references/sub-skills/` prefix check above. This belt-and-
    # suspenders check is also defensive against a slash-bearing name
    # that contains `.claude/`.
    if ".claude/" in source_path:
        raise CatalogParseError(
            f"catalog row at line {lineno} for `{name}` resolves to "
            f"`{source_path}` — `.claude/skills/` paths are NEVER valid "
            f"catalog entries (AC5; only the authored "
            f"`references/sub-skills/` path is the catalog's source)."
        )
