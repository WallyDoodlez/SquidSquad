"""One-shot migration tool for #11049.

Walks `references/roles/**/*.md`, replacing every `{{include: <path>}}`
directive with one of three outcomes:

  1. Cataloged sub-skill -> ``→ run sub-skill: <catalog-name>``.
  2. Domain-context L3 inline (uncataloged, active, small) -> body is
     inlined verbatim (frontmatter stripped) in place of the directive.
  3. Retired sub-skill (file exists on disk, NOT in the catalog and NOT
     a domain-context) -> the directive line is dropped. The catalog
     notes flag these for #10360 inlining into Identity / Responsibility
     slots. The composed CLAUDE.md loses the duplicate body that today's
     ``_resolve_includes_v2`` was re-inlining; the prose already in
     each role's instructions.md preserves the role-bearing content.

Tracks every replacement to ``.squidsquad/skill/planning/MIGRATE-11049.log``
for auditability.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROLES = REPO / "references" / "roles"
SUB_SKILLS = REPO / "references" / "sub-skills"
CATALOG = REPO / "docs" / "sub-skill-catalog.md"
LOG_PATH = REPO / ".squidsquad" / "skill" / "planning" / "MIGRATE-11049.log"

sys.path.insert(0, str(REPO / "references" / "scripts"))
from catalog_parser import parse_catalog  # noqa: E402


INCLUDE_RE = re.compile(r"\{\{include:\s*([^}]+?)\s*\}\}")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _path_to_catalog_name(catalog: dict[str, str]) -> dict[str, str]:
    """Reverse the catalog: file-stem-path -> catalog name."""
    reverse: dict[str, str] = {}
    for name, src in catalog.items():
        # src looks like ``references/sub-skills/common/foo.md``;
        # the include directive uses ``common/foo`` (no .md).
        prefix = "references/sub-skills/"
        assert src.startswith(prefix)
        stem = src[len(prefix):].removesuffix(".md")
        reverse[stem] = name
    return reverse


def _inline_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = FRONTMATTER_RE.sub("", text)
    return text.rstrip() + "\n"


def _classify(include_path: str, reverse: dict[str, str]) -> tuple[str, str | None]:
    """Return ``(action, payload)``.

    ``action`` is one of ``cataloged`` / ``inline_domain_context`` /
    ``retired_drop`` / ``missing_file`` (raise). ``payload`` is the
    catalog name for ``cataloged``, the relative source path for
    ``inline_domain_context``, ``None`` for ``retired_drop``.
    """
    if include_path in reverse:
        return ("cataloged", reverse[include_path])

    src = SUB_SKILLS / f"{include_path}.md"
    if not src.is_file():
        return ("missing_file", include_path)

    # Domain-context L3 inlines are the only legitimate uncataloged
    # active sub-skills. Anything else uncataloged is a retirement
    # target per catalog notes on agent-boundaries / file-conventions /
    # status-line / prohibitions / responsibility.
    if include_path.endswith("/domain-context"):
        return ("inline_domain_context", include_path)
    return ("retired_drop", None)


def _process_file(path: Path, reverse: dict[str, str], log: list[str]) -> tuple[str, int]:
    """Rewrite ``path`` in place. Returns ``(new_text, replaced_count)``."""
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO).as_posix()
    replaced = 0

    def _handle_directive_line(match: re.Match) -> str:
        nonlocal replaced
        include_path = match.group(1).strip()
        action, payload = _classify(include_path, reverse)
        if action == "cataloged":
            log.append(f"  {rel}: {include_path} -> → run sub-skill: {payload}")
            replaced += 1
            return f"→ run sub-skill: {payload}"
        if action == "inline_domain_context":
            body = _inline_body(SUB_SKILLS / f"{include_path}.md")
            log.append(f"  {rel}: {include_path} -> INLINED ({len(body.splitlines())} lines)")
            replaced += 1
            return body.rstrip("\n")
        if action == "retired_drop":
            log.append(f"  {rel}: {include_path} -> DROPPED (retired, no catalog entry; queued for #10360)")
            replaced += 1
            return "<<<DROP_LINE>>>"
        raise RuntimeError(f"{rel}: include target missing on disk: {include_path}")

    new_text = INCLUDE_RE.sub(_handle_directive_line, text)

    # Lines marked DROP_LINE collapse the whole physical line including
    # the trailing newline. We also collapse a following blank line so
    # the file doesn't accumulate orphan blank pairs.
    out_lines: list[str] = []
    skip_next_blank = False
    for line in new_text.splitlines(keepends=True):
        if "<<<DROP_LINE>>>" in line:
            skip_next_blank = True
            continue
        if skip_next_blank and line.strip() == "":
            skip_next_blank = False
            continue
        skip_next_blank = False
        out_lines.append(line)

    return ("".join(out_lines), replaced)


def main() -> int:
    catalog = parse_catalog(str(CATALOG))
    reverse = _path_to_catalog_name(catalog)

    targets = sorted(ROLES.rglob("*.md"))
    log: list[str] = []
    total = 0
    touched = 0
    for path in targets:
        if "{{include:" not in path.read_text(encoding="utf-8"):
            continue
        log.append(f"\n[FILE] {path.relative_to(REPO).as_posix()}")
        new_text, replaced = _process_file(path, reverse, log)
        if replaced:
            path.write_text(new_text, encoding="utf-8")
            total += replaced
            touched += 1

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(
        f"#11049 migration log\n{total} directives processed across {touched} files\n"
        + "\n".join(log) + "\n",
        encoding="utf-8",
    )
    print(f"Migration complete: {total} directives across {touched} files. Log: {LOG_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
