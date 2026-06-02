"""D4: Catalog drift check (#10675, PRD-D Story D4).

Two-way orphan scan that confirms the catalog and the sub-skills source tree
agree on what exists. Drift = abort; dead-code = warn.

Scans run in three directions:

1. **Orphan catalog rows** — every catalog entry's ``source_path`` must
   exist on disk under ``references/sub-skills/``. A row that points at a
   missing file is an "orphan catalog row".

2. **Orphan source files** — every file under
   ``references/sub-skills/**/*.md`` must have a matching catalog row. A
   file with no catalog row is an "orphan source file".

3. **Dead-code candidates** — a catalog row whose name does not appear as
   an include in any role's ``includes.yml`` / ``includes-events.yml`` /
   ``includes-v2.yml`` is a dead-code candidate. Per PRD §8 Q-D3 this is
   warn-not-abort: the catalog row may be reserved for an in-flight role
   or a sub-skill not yet referenced.

The dead-code warning is **scoped to call-sites in role manifests** —
inline ``→ run sub-skill:`` references inside other sub-skill bodies are
not scanned (transitive references are surfaced by D3's compose-time
gate; D4 stays at the manifest layer to keep the abort surface
predictable, per AC5 independence).

Per AC5, D4 is **independent of D2/D3**: it runs against the source tree
only, never composes anything, and never reads the v2 link-stage output.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import catalog_parser as _cp

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover — yaml is a hard dep in compose
    _yaml = None


SUB_SKILLS_REL = "references/sub-skills"
# Files in the sub-skills tree that are not themselves sub-skills and so
# must be excluded from the "orphan source file" scan. ``manifest.md`` at
# the top of ``references/sub-skills/`` and any README-style index file
# fall in this bucket.
_NON_SUB_SKILL_BASENAMES = frozenset({"manifest.md", "README.md", "index.md"})
# Subdirectories under ``references/sub-skills/`` that are excluded from
# the orphan-source scan. ``project/`` holds L4 seed templates (the
# catalog parser already excludes them on the catalog-emit side via the
# ``_INCLUDED_DIRS`` allowlist — mirror that here so the two-way scan
# stays symmetric). ``capabilities/`` holds the {{capability: id}} body
# sources which compose.py resolves via a different path
# (_resolve_capability) and are not catalog-tracked.
_EXCLUDED_SUBDIRS = frozenset({"project", "capabilities"})

# Manifest filenames scanned for dead-code detection. Tracks both the v1
# split (polling vs event) and the post-D5 unified v2 file. Any subset
# may be absent on a given role — we read whatever exists.
_MANIFEST_FILENAMES = (
    "includes.yml",
    "includes-events.yml",
    "includes-v2.yml",
)


@dataclass
class DriftReport:
    """Structured result of a drift scan.

    Each field is a list so callers can render full reports (per AC3:
    "list ALL orphans, not just first").
    """

    orphan_catalog_rows: list[tuple[str, str]] = field(default_factory=list)
    """``(name, expected_source_path)`` per row whose file is missing."""

    orphan_source_files: list[str] = field(default_factory=list)
    """Repo-relative source paths with no matching catalog row."""

    dead_code_candidates: list[str] = field(default_factory=list)
    """Catalog names with no call-site in any role manifest. Warn only."""

    @property
    def has_drift(self) -> bool:
        """True iff there is at least one orphan (either direction)."""
        return bool(self.orphan_catalog_rows or self.orphan_source_files)

    @property
    def has_dead_code(self) -> bool:
        return bool(self.dead_code_candidates)

    def format(self) -> str:
        """Render a human-readable multi-section report.

        Empty sections are omitted. The output is stable-ordered so test
        assertions and reviewer diffs are deterministic.
        """
        lines = []
        if self.orphan_catalog_rows:
            lines.append("Orphan catalog rows (source file missing):")
            for name, path in sorted(self.orphan_catalog_rows):
                lines.append(f"  - `{name}` -> {path}")
        if self.orphan_source_files:
            if lines:
                lines.append("")
            lines.append("Orphan source files (no catalog row):")
            for path in sorted(self.orphan_source_files):
                lines.append(f"  - {path}")
        if self.dead_code_candidates:
            if lines:
                lines.append("")
            lines.append("Dead-code candidates (catalog row, no call-site):")
            for name in sorted(self.dead_code_candidates):
                lines.append(f"  - `{name}`")
        return "\n".join(lines)


def scan_drift(
    catalog_path,
    repo_root,
    *,
    roles_dir=None,
    manifest_filenames=_MANIFEST_FILENAMES,
):
    """Run the two-way drift scan + dead-code scan.

    ``catalog_path`` — the catalog markdown file (``docs/sub-skill-catalog.md``).
    ``repo_root`` — repository root; the sub-skills tree is read relative
    to it (``<repo_root>/references/sub-skills/**/*.md``).
    ``roles_dir`` — optional explicit roles directory (defaults to
    ``<repo_root>/references/roles``). The dead-code scan reads
    ``<roles_dir>/<role>/<manifest_filename>`` for each manifest filename.
    ``manifest_filenames`` — tuple of include-manifest basenames to scan
    for call-sites.

    Returns a populated :class:`DriftReport`. A
    :class:`catalog_parser.CatalogParseError` from the catalog raises
    through to the caller — D4 does not silently swallow upstream
    catalog defects.
    """
    catalog_path = Path(catalog_path)
    repo_root = Path(repo_root)
    sub_skills_root = repo_root / SUB_SKILLS_REL
    roles_dir = Path(roles_dir) if roles_dir is not None else (
        repo_root / "references" / "roles"
    )

    entries = _cp.parse_catalog_entries(catalog_path)
    catalog_by_name = {e.name: e for e in entries}
    catalog_source_paths = {e.source_path for e in entries}

    report = DriftReport()

    # Direction 1: catalog row -> file exists.
    for entry in entries:
        full_path = repo_root / entry.source_path
        if not full_path.is_file():
            report.orphan_catalog_rows.append(
                (entry.name, entry.source_path),
            )

    # Direction 2: source file -> catalog row exists.
    if sub_skills_root.is_dir():
        for md_path in sub_skills_root.rglob("*.md"):
            try:
                rel = md_path.relative_to(sub_skills_root)
            except ValueError:
                continue
            # Root-level non-sub-skill files (manifest.md, README.md,
            # index.md). Per DS review F4 — restricted to root so a
            # nested file with the same basename can't silently hide.
            if md_path.parent == sub_skills_root \
                    and md_path.name in _NON_SUB_SKILL_BASENAMES:
                continue
            # Excluded top-level subdir — symmetric with catalog
            # parser's allowlist (project/, capabilities/).
            if rel.parts and rel.parts[0] in _EXCLUDED_SUBDIRS:
                continue
            rel_to_repo = (
                Path(SUB_SKILLS_REL) / rel
            ).as_posix()
            if rel_to_repo not in catalog_source_paths:
                report.orphan_source_files.append(rel_to_repo)

    # Direction 3: catalog row -> referenced in any role manifest.
    referenced = _collect_manifest_references(roles_dir, manifest_filenames)
    for name in catalog_by_name:
        if _is_referenced(name, referenced):
            continue
        report.dead_code_candidates.append(name)

    return report


def _is_referenced(catalog_name, referenced):
    """Decide if a catalog name has a call-site in any role manifest.

    Match rules — symmetric with ``compose.py._resolve_includes`` which
    resolves an include path like ``common/boot-bootstrap`` to the
    catalog name ``boot-bootstrap`` via the source-path's last segment:

    - **Exact path match**: the catalog name appears verbatim in some
      manifest's ``includes:`` list (slash-bearing catalog names like
      ``roles/dm/events/pr-merge-wait`` are referenced this way).
    - **Basename match for plain names**: a non-slash catalog name like
      ``boot-bootstrap`` matches a manifest entry whose **last** path
      segment is the catalog name (e.g. ``common/boot-bootstrap``).
      Per DS review F5: only invoked for plain catalog names; slash-
      bearing catalog names must match exactly to avoid the asymmetric
      false-negative (``deep/X`` vs ``X``).
    """
    if catalog_name in referenced:
        return True
    if "/" not in catalog_name:
        # Plain catalog name; accept any manifest entry that ends in it.
        return any(
            inc.rsplit("/", 1)[-1] == catalog_name
            for inc in referenced
            if "/" in inc
        )
    return False


# Keys inside a role manifest yaml whose values are include-path lists.
# ``includes`` is the canonical key; ``additional_includes`` is the
# variant schema used by ``roles/<base>/<variant>/includes.yml``
# (compose.py:_load_manifest merges these with the base role's
# ``includes:`` list).
_MANIFEST_INCLUDE_KEYS = ("includes", "additional_includes")


def _collect_manifest_references(roles_dir, manifest_filenames):
    """Union of include-paths across every role manifest, recursively.

    Returns the set of include-path strings observed across every
    matching manifest file under ``roles_dir`` at any depth, reading
    both ``includes:`` AND ``additional_includes:`` keys (per DS review
    F1 — variant manifests at ``roles/<base>/<variant>/includes.yml``
    use ``additional_includes`` to extend the base role's list, and
    were silently skipped by the previous top-level-only scan).

    YAML import failure is fatal. Per DS review F2: unparseable
    manifest files emit a stderr warning before being skipped, so
    operators can investigate the false-positive dead-code candidates
    that result.
    """
    if _yaml is None:
        raise RuntimeError(
            "PyYAML is required for D4 catalog drift scan (manifest read).",
        )

    referenced = set()
    roles_dir = Path(roles_dir)
    if not roles_dir.is_dir():
        return referenced

    for fname in manifest_filenames:
        for mpath in roles_dir.rglob(fname):
            if not mpath.is_file():
                continue
            try:
                data = _yaml.safe_load(mpath.read_text(encoding="utf-8"))
            except _yaml.YAMLError as e:
                print(
                    f"WARNING: drift-check skipping unparseable manifest "
                    f"{mpath}: {e}",
                    file=sys.stderr,
                )
                continue
            if not isinstance(data, dict):
                continue
            for key in _MANIFEST_INCLUDE_KEYS:
                includes = data.get(key) or []
                if not isinstance(includes, list):
                    continue
                for inc in includes:
                    if isinstance(inc, str):
                        referenced.add(inc)
    return referenced
