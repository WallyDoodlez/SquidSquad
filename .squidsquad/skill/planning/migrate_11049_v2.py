"""#11049 migration tool v2 — per PM Path A spec (cycle 1597).

Walks ``references/roles/**/*.md`` and rewrites every ``{{include: <path>}}``
into one of four outcomes, mapped from PM's mandatory-vs-situational
classification in the #11049 spec-clarification comment:

  1. **Mandatory inline** — boot-bootstrap / cycle-runner /
     context-pressure / resume-working-state / task-pickup /
     working-state / git-commit / agent-lifecycle / improvement-scan-slim
     / status-line. Body inlined verbatim (frontmatter + outer markers
     stripped). These are invoked deterministically every cycle / at
     boot before any tool use is available, so they MUST live in the
     composite — Skill-tool runtime invocation (#9968) isn't wired yet.

  2. **Reference** — every other catalog-matched sub-skill becomes
     ``→ run sub-skill: <catalog-name>``. Compose passes these through
     verbatim. Future #9968 work loads the body at runtime.

  3. **Domain-context inline** — uncataloged but active, small,
     L3-local. Body inlined verbatim. Unchanged from the cycle-1591
     pass.

  4. **D1 retired-inline** — uncataloged AND not domain-context but
     the source file still exists on disk (responsibility ×4,
     agent-boundaries, file-conventions ×4, status-line ×4,
     prohibitions ×4). Per PM Path A, default D1: inline verbatim with
     an HTML comment marker so the #10360 cleanup pass can find these
     for slot migration.

Tracks every replacement to
``.squidsquad/skill/planning/MIGRATE-11049-v2.log`` for auditability.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROLES = REPO / "references" / "roles"
SUB_SKILLS = REPO / "references" / "sub-skills"
CATALOG = REPO / "docs" / "sub-skill-catalog.md"
LOG_PATH = REPO / ".squidsquad" / "skill" / "planning" / "MIGRATE-11049-v2.log"

sys.path.insert(0, str(REPO / "references" / "scripts"))
from catalog_parser import parse_catalog  # noqa: E402


# PM's mandatory-inline set per the #11049 spec-clarification comment.
# These catalog names MUST stay inlined in the composite — every-cycle or
# at-boot invocation paths that can't tolerate a not-yet-implemented
# ``→ run sub-skill: <name>`` runtime resolution (#9968 future work).
MANDATORY_INLINE = frozenset({
    "boot-bootstrap",
    "cycle-runner",
    "context-pressure",
    "resume-working-state",
    "task-pickup",
    "working-state",
    "git-commit",
    "agent-lifecycle",
    "improvement-scan-slim",
    "status-line",
})

INCLUDE_RE = re.compile(r"\{\{include:\s*([^}]+?)\s*\}\}")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_OUTER_MARKER_RE = re.compile(
    r"^<!-- /?sub-skill: [a-z][a-z0-9-]+ -->\s*\n", re.MULTILINE
)


def _path_to_catalog_name(catalog: dict[str, str]) -> dict[str, str]:
    """Reverse the catalog: ``include-path-stem -> catalog-name``."""
    reverse: dict[str, str] = {}
    prefix = "references/sub-skills/"
    for name, src in catalog.items():
        assert src.startswith(prefix)
        stem = src[len(prefix):].removesuffix(".md")
        reverse[stem] = name
    return reverse


def _inline_body(path: Path, *, wrap_markers: bool = True) -> str:
    """Inline a sub-skill body. Strips frontmatter; preserves outer markers
    if requested (and synthesizes them if missing) so downstream tooling
    that slices on ``<!-- sub-skill: <name> -->`` boundaries still works.
    """
    text = path.read_text(encoding="utf-8")
    text = FRONTMATTER_RE.sub("", text)
    body = text.strip()
    if not wrap_markers:
        body = _OUTER_MARKER_RE.sub("", body).strip()
        return body + "\n"
    name = path.stem
    open_marker = f"<!-- sub-skill: {name} -->"
    close_marker = f"<!-- /sub-skill: {name} -->"
    # Source files may already carry their own outer markers (the compose
    # pipeline's wrap-on-inline convention). If both are present, keep
    # them as-is so the surface matches v1 ``_resolve_includes``.
    has_open = body.startswith(open_marker)
    has_close = body.endswith(close_marker)
    if has_open and has_close:
        return body + "\n"
    # Otherwise synthesize the wrap so downstream marker-slicing tooling
    # continues to work even when the source file omits them.
    inner = body
    if has_open:
        inner = inner[len(open_marker):].lstrip("\n")
    if has_close:
        inner = inner[: -len(close_marker)].rstrip("\n")
    return f"{open_marker}\n{inner}\n{close_marker}\n"


def _classify(include_path: str, reverse: dict[str, str]) -> tuple[str, str]:
    """Return ``(action, payload)`` for one directive.

    ``action`` is one of:
      ``cataloged_mandatory_inline`` — payload is the catalog name; body
          is inlined verbatim because every-cycle / boot-time invocation
          can't wait for #9968.
      ``cataloged_reference`` — payload is the catalog name; directive
          is rewritten to ``→ run sub-skill: <name>`` (pass-through).
      ``inline_domain_context`` — payload is the include path; body is
          inlined verbatim.
      ``inline_d1_retired`` — payload is the include path; body is
          inlined verbatim per PM Path A D1 (with a #10360 marker so
          the future cleanup can find it). Used when the source file
          exists on disk but the catalog doesn't list it.
      ``missing_file`` — payload is the include path; raise.
    """
    if include_path in reverse:
        catalog_name = reverse[include_path]
        if catalog_name in MANDATORY_INLINE:
            return ("cataloged_mandatory_inline", catalog_name)
        return ("cataloged_reference", catalog_name)

    src = SUB_SKILLS / f"{include_path}.md"
    if not src.is_file():
        return ("missing_file", include_path)
    if include_path.endswith("/domain-context"):
        return ("inline_domain_context", include_path)
    return ("inline_d1_retired", include_path)


def _process_file(
    path: Path, reverse: dict[str, str], log: list[str]
) -> tuple[str, int, dict[str, int]]:
    """Rewrite ``path`` in place. Returns ``(new_text, replaced_count, action_counts)``."""
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO).as_posix()
    replaced = 0
    action_counts: dict[str, int] = {}

    def _handle(match: re.Match) -> str:
        nonlocal replaced
        include_path = match.group(1).strip()
        action, payload = _classify(include_path, reverse)
        action_counts[action] = action_counts.get(action, 0) + 1
        replaced += 1

        if action == "cataloged_reference":
            log.append(f"  {rel}: {include_path} -> → run sub-skill: {payload}")
            return f"→ run sub-skill: {payload}"

        if action == "cataloged_mandatory_inline":
            body = _inline_body(SUB_SKILLS / f"{include_path}.md")
            log.append(
                f"  {rel}: {include_path} -> MANDATORY INLINE ({len(body.splitlines())} lines)"
            )
            return body.rstrip("\n")

        if action == "inline_domain_context":
            body = _inline_body(SUB_SKILLS / f"{include_path}.md")
            log.append(
                f"  {rel}: {include_path} -> DOMAIN-CONTEXT INLINE ({len(body.splitlines())} lines)"
            )
            return body.rstrip("\n")

        if action == "inline_d1_retired":
            body = _inline_body(SUB_SKILLS / f"{include_path}.md")
            marker = (
                f"<!-- #10360-cleanup: inlined retired sub-skill `{include_path}` "
                f"per #11049 PM Path A D1; migrate body to Identity/Responsibility "
                f"slot in #10360 -->"
            )
            log.append(
                f"  {rel}: {include_path} -> D1 RETIRED INLINE ({len(body.splitlines())} lines)"
            )
            return f"{marker}\n\n{body.rstrip()}"

        raise RuntimeError(f"{rel}: include target missing on disk: {include_path}")

    new_text = INCLUDE_RE.sub(_handle, text)
    return (new_text, replaced, action_counts)


def main() -> int:
    catalog = parse_catalog(str(CATALOG))
    reverse = _path_to_catalog_name(catalog)

    # Sanity check the mandatory set actually exists in the catalog.
    missing = MANDATORY_INLINE - set(catalog)
    if missing:
        print(
            f"WARNING: mandatory-inline names missing from catalog: "
            f"{sorted(missing)} — treated as inline_d1_retired fallback",
            file=sys.stderr,
        )

    targets = sorted(ROLES.rglob("*.md"))
    log: list[str] = []
    total = 0
    touched = 0
    totals: dict[str, int] = {}
    for path in targets:
        if "{{include:" not in path.read_text(encoding="utf-8"):
            continue
        log.append(f"\n[FILE] {path.relative_to(REPO).as_posix()}")
        new_text, replaced, action_counts = _process_file(path, reverse, log)
        if replaced:
            path.write_text(new_text, encoding="utf-8")
            total += replaced
            touched += 1
            for k, v in action_counts.items():
                totals[k] = totals.get(k, 0) + v

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "#11049 migration v2 log (per PM Path A spec)\n"
        f"{total} directives processed across {touched} files\n"
        f"action totals: {sorted(totals.items())}\n"
    )
    LOG_PATH.write_text(header + "\n".join(log) + "\n", encoding="utf-8")
    print(
        f"Migration v2 complete: {total} directives across {touched} files. "
        f"Action totals: {totals}. Log: {LOG_PATH.relative_to(REPO)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
