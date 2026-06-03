"""Test-only deterministic expander for v2 link-stage ``{{include:}}`` directives.

The v2 link stage (``v2_link_stage.emit_v2_linked``) walks L1-L3
sources and concatenates them per the canonical slot order, but it
leaves ``{{include: path}}`` directives RAW. In production
``atomic_emit.assemble_and_emit`` (LLM polish) expands those
directives into the v1-style ``<!-- sub-skill: X --> body
<!-- /sub-skill: X -->`` form. Tests that assert body-content
invariants ("the agent-boundaries roster contains all 4 active
roles", "the pickup-comment-fidelity fragment includes 'State-file
filter'") need that expanded form — but assemble is non-hermetic
(requires a real LLM provider).

This helper does the deterministic part of what assemble does for
``{{include:}}`` expansion, with no LLM in the path. It mirrors v1's
``compose._resolve_includes`` semantics so tests migrated off v1's
``compose_role`` can keep their invariants verbatim:

- Same ``RUNTIME_READ_FRAGMENTS`` skip (the lazy-load fragments the
  bootstrap Reads at runtime, never inlined at compose).
- Same ``<!-- sub-skill: name -->`` / ``<!-- /sub-skill: name -->``
  wrapping around the source body.
- Same source cleanup (``_strip_yaml_frontmatter`` +
  ``_strip_outer_markers``) to avoid doubled markers / leaked
  frontmatter.

Scope: only ``{{include:}}`` directives. v2 link-stage output for
all four roles (pm / verifier / dm / worker) contains no
``{{capability:}}`` or ``{{runtime:}}`` directives (verified empirically
during the cycle-1550 cutover audit), so the simpler form is
sufficient. Retire this file alongside v1 in E6 #10685 Phase 3d.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402

_INCLUDE_RE = re.compile(r'^\s*\{\{include:\s*(.+?)\s*\}\}\s*$')


def expand_v2_includes(text: str, *, sub_skills_dir: Path = None) -> str:
    """Expand ``{{include: path}}`` directives in v2 link-stage text.

    Lines that aren't ``{{include: ...}}`` pass through unchanged.
    Runtime fragments (per ``compose.RUNTIME_READ_FRAGMENTS``) are
    dropped (the lazy-load contract). Missing source files yield an
    ``<!-- ERROR: Missing include: path -->`` placeholder — same as
    v1 ``_resolve_includes``.

    ``sub_skills_dir`` defaults to ``compose.SUB_SKILLS_DIR``
    (the production source tree). Test fixtures can override with a
    hermetic tmp_path.
    """
    if sub_skills_dir is None:
        sub_skills_dir = compose.SUB_SKILLS_DIR

    out_lines = []
    for line in text.splitlines():
        m = _INCLUDE_RE.match(line)
        if not m:
            out_lines.append(line)
            continue
        path = m.group(1)
        if path in compose.RUNTIME_READ_FRAGMENTS:
            continue
        full = Path(sub_skills_dir) / f"{path}.md"
        if not full.exists():
            out_lines.append(f"<!-- ERROR: Missing include: {path} -->")
            continue
        body = compose._strip_yaml_frontmatter(
            full.read_text(encoding="utf-8")
        ).rstrip()
        name = full.stem
        body = compose._strip_outer_markers(body, name)
        out_lines.append(f"<!-- sub-skill: {name} -->")
        out_lines.append(body)
        out_lines.append(f"<!-- /sub-skill: {name} -->")
    return "\n".join(out_lines)
