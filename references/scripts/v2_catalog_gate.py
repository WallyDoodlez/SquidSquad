"""D3: Catalog gate at v2 compose time (#10674, PRD-D Story D3).

Every `→ run sub-skill: <name>` reference that v2 compose emits MUST
resolve via D1's catalog parser to a source-path that exists on disk.
The gate runs against the composed v2 output AFTER `emit_v2_linked`
returns but BEFORE the file is written, so a drift produces zero
partial artifacts on disk (consistent with PRD-A A2f's atomic-write
contract).

Two distinct failure modes are surfaced (AC2 + AC3):

- **unresolved** — the reference name has no row in
  `docs/sub-skill-catalog.md`. PM-side action: add or rename the
  catalog row, OR remove the orchestrator reference.
- **missing-file** — the catalog row resolves to a `source_path`
  that does not exist on disk. PM-side action: restore the source
  file or update the catalog row.

Per AC4 the gate reports **all** issues, not just the first. Callers
raise `CatalogGateError` whose `issues` field is the full list and
whose `__str__` is a multi-line block suitable for direct stderr
printing.

Per AC5 the gate is v2-only. v1 compose inlines bodies and has no
`→ run sub-skill:` references in its output, so calling the gate on
v1 output would always pass; we intentionally don't wire it there.

Per AC6 tests cover: clean run, single unresolved, multiple
unresolved, file-missing, and mixed clean/file-missing/unresolved.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import catalog_parser as _cp


# Match `→ run sub-skill: <name>` anywhere on a line. The name token
# allows lowercase letters, digits, hyphens, underscores, and SLASHES
# (slash-bearing catalog names like `roles/dm/events/pr-merge-wait`
# are valid per D1). Capture only the name; trailing whitespace and
# the optional comment tail are not part of the lookup key.
_REF_RE = re.compile(
    r"→\s+run\s+sub-skill:\s+([a-z][a-z0-9/_-]*)"
)


@dataclass
class GateIssue:
    """One unresolved or missing-file finding.

    ``kind`` is ``"unresolved"`` or ``"missing-file"``. ``name`` is the
    reference text as it appeared in the composed output. ``source_path``
    is the resolved path (``None`` for ``unresolved`` rows).
    """

    kind: str
    name: str
    source_path: str | None = None


@dataclass
class GateResult:
    """Result of a single ``validate_v2_compose`` pass.

    Empty issues list = the gate passed; ``has_issues`` is False; the
    caller writes the composite to disk. Non-empty = abort.
    """

    issues: list[GateIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

    def format(self) -> str:
        """Render a multi-line abort report grouping issues by kind.

        Empty sections are omitted. Stable-ordered so reviewer diffs
        and test assertions are deterministic.
        """
        if not self.issues:
            return ""
        unresolved = sorted(
            {(i.name,) for i in self.issues if i.kind == "unresolved"}
        )
        missing = sorted(
            (i.name, i.source_path)
            for i in self.issues if i.kind == "missing-file"
        )
        lines = []
        if unresolved:
            lines.append(
                "Unresolved sub-skill references (no catalog row):"
            )
            for (name,) in unresolved:
                lines.append(f"  - `{name}`")
        if missing:
            if lines:
                lines.append("")
            lines.append(
                "Catalog row resolves but source file missing on disk:"
            )
            for name, path in missing:
                lines.append(f"  - `{name}` -> {path}")
        return "\n".join(lines)


class CatalogGateError(Exception):
    """Raised by the gate when the composed v2 output has drift.

    ``result`` holds the full :class:`GateResult` so callers can
    inspect the individual issues. ``__str__`` returns the rendered
    multi-issue report — printing the exception body directly is the
    canonical abort surface (used by ``compose.py deploy_alias_v2``).
    """

    def __init__(self, result, *, alias=None):
        self.result = result
        self.alias = alias
        prefix = (
            f"catalog gate FAILED for alias '{alias}':"
            if alias else "catalog gate FAILED:"
        )
        super().__init__(f"{prefix}\n{result.format()}")


def find_references(text):
    """Extract every ``→ run sub-skill: <name>`` reference from ``text``.

    Returns the list of name strings in source order. Duplicates are
    preserved — a name appearing twice in the orchestrator surfaces as
    two references in the result so the caller can decide whether
    duplication itself is an issue (D3 does not flag duplicates; the
    gate cares only about resolution).
    """
    return _REF_RE.findall(text)


def validate_v2_compose(text, *, catalog_path, repo_root):
    """Run the catalog gate against composed v2 output.

    ``text`` is the body returned by ``v2_link_stage.emit_v2_linked``
    (or the assembled v2 output once PRD-B's assemble stage feeds in).
    ``catalog_path`` is ``docs/sub-skill-catalog.md`` (or a fixture in
    tests). ``repo_root`` is the install root; source paths from the
    catalog are checked relative to it.

    Returns a :class:`GateResult`. Callers convert non-empty results
    to ``CatalogGateError`` via ``raise CatalogGateError(result, alias=...)``.

    A catalog parse error bubbles through unchanged — that is a
    D1/parser concern and not a D3 finding.
    """
    catalog_path = Path(catalog_path)
    repo_root = Path(repo_root)

    catalog = _cp.parse_catalog(catalog_path)
    result = GateResult()

    seen_unresolved = set()
    seen_missing = set()

    for name in find_references(text):
        source_path = catalog.get(name)
        if source_path is None:
            # AC2: unresolved -> abort. Dedup so a name referenced N
            # times produces a single line in the report.
            if name in seen_unresolved:
                continue
            seen_unresolved.add(name)
            result.issues.append(GateIssue(
                kind="unresolved",
                name=name,
            ))
            continue
        # AC3: resolved but file missing on disk -> abort.
        full = repo_root / source_path
        if full.is_file():
            continue
        key = (name, source_path)
        if key in seen_missing:
            continue
        seen_missing.add(key)
        result.issues.append(GateIssue(
            kind="missing-file",
            name=name,
            source_path=source_path,
        ))
    return result
