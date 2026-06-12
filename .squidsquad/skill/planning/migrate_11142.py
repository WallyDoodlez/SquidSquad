#!/usr/bin/env python3
"""#11142 — strip compose-pipeline author-only HTML comments from L1-L3 source.

Removes HTML comments that talk to template authors or compose tooling,
not to the reading agent. Keeps semantically load-bearing comments
(``<!-- sub-skill: NAME -->`` wrappers, ``<!-- #10360-cleanup: ... -->``
future-work pointers, code-fence example content).

Patterns removed (each as a whole line + trailing blank when present):
- ``<!-- Layer N: ... -->`` (compose-layer labels)
- ``<!-- This content is prepended ... -->`` / ``<!-- It defines what ANY ... -->``
- ``<!-- NOTE: step IDs below ... -->`` (multi-line)
- ``<!-- L[1-3] {Role} instructions — H3 ops target ... -->`` (template-author guide)
- ``<!-- v2 compose-model slot ops ... -->``
- ``<!-- /project-adaptation -->`` (orphan compose-tool closer)
- ``<!-- L1-EXCLUSIVE: ... -->``
- ``<!-- Note (NUMBER ... ): ... -->`` (multi-line author-only note)
- Multi-line ``<!-- #NUMBER: the directives below ... -->`` (#9588-style author notes)

Inline strips:
- ``<!-- absorbed from feedback_X -->`` markers at end of bullet lines.

NOT touched: code-fence content in references/sub-skills/common/l4-curation.md.

Run with: python .squidsquad/skill/planning/migrate_11142.py
"""

from __future__ import annotations

import re
from pathlib import Path

# Whole-line comment patterns (each pattern matches a self-contained
# ``<!-- ... -->`` whose entire content is author/installer guidance).
# Applied with re.MULTILINE; the regex strips the comment line plus a
# single trailing blank line if present.
_WHOLE_LINE_AUTHOR_PATTERNS = [
    # "Layer N: ..." labels at top of L1 base files.
    r"<!-- Layer \d+:[^>]*-->",
    # "This content is prepended ..." install-time notes.
    r"<!-- This content is prepended[^>]*-->",
    # "It defines what ANY ..." install-time notes.
    r"<!-- It defines what ANY[^>]*-->",
    # "L1/L2/L3 ... instructions — H3 ops target ..." template-author guides.
    r"<!-- L[1-3] [A-Za-z ]+(?:Skill )?instructions — H3 ops target[^>]*-->",
    # "v2 compose-model slot ops ..." compose-tool comments.
    r"<!-- v2 compose-model slot ops[^>]*-->",
    # Note: ``<!-- /project-adaptation -->`` is intentionally NOT stripped —
    # it's a load-bearing sentinel used by `soul_adaptation.py` to
    # delimit the replaceable region in SOUL.md (see soul_adaptation
    # line 211: ``if ADAPTATION_FOOTER in content``).
    # L1-EXCLUSIVE slot ownership markers.
    r"<!-- L1-EXCLUSIVE:[^>]*-->",
]

# Multi-line comment patterns — ``<!--`` and ``-->`` on different lines.
# Each match consumes its full multi-line span plus the following blank line.
_MULTILINE_AUTHOR_PATTERNS = [
    # "NOTE: step IDs below ..." (in references/roles/instructions.md)
    re.compile(
        r"<!-- NOTE: step IDs below[\s\S]*?-->\n(?:\n)?",
        re.MULTILINE,
    ),
    # "#NUMBER: the directives below ..." (#9588-style worker/instructions.md
    # multi-line author note).
    re.compile(
        r"<!--\n\s+#\d+: the directives below[\s\S]*?-->\n(?:\n)?",
        re.MULTILINE,
    ),
    # "Note (NUMBER dual-aware window): ..." (verifier/instructions.md
    # author-only retention note).
    re.compile(
        r"<!-- Note \(\d+[^)]*\):[\s\S]*?-->\n(?:\n)?",
        re.MULTILINE,
    ),
]

# Inline trailing comment ``<!-- absorbed from feedback_X -->`` at end of
# bullet lines. Strips the comment and the single space that precedes
# it; preserves the bullet's terminating newline.
_INLINE_ABSORBED_RE = re.compile(
    r" <!-- absorbed from [a-zA-Z_]+ -->"
)

# Whole-line variant: ``<!-- absorbed from feedback_X -->`` on its own
# line above a bullet. Strip the line plus its trailing newline.
_WHOLE_LINE_ABSORBED_RE = re.compile(
    r"^<!-- absorbed from [a-zA-Z_]+ -->\n",
    re.MULTILINE,
)


def _strip_whole_line_comment(text: str, pattern_src: str) -> str:
    """Strip a whole-line author comment matching ``pattern_src`` plus a
    single trailing blank line. Idempotent."""
    pattern = re.compile(
        rf"^{pattern_src}\s*\n(?:\n)?",
        re.MULTILINE,
    )
    return pattern.sub("", text)


def convert(text: str) -> tuple[str, int]:
    """Strip author-only HTML comments from a single source body.
    Returns (new_text, total_substitutions)."""
    total = 0
    for pat in _WHOLE_LINE_AUTHOR_PATTERNS:
        before = text
        text = _strip_whole_line_comment(text, pat)
        if text != before:
            total += before.count("<!--") - text.count("<!--")
    for ml in _MULTILINE_AUTHOR_PATTERNS:
        new_text, n = ml.subn("", text)
        text = new_text
        total += n
    new_text, n = _INLINE_ABSORBED_RE.subn("", text)
    text = new_text
    total += n
    new_text, n = _WHOLE_LINE_ABSORBED_RE.subn("", text)
    text = new_text
    total += n
    return text, total


def _iter_target_files(repo_root: Path):
    """Yield source files in scope. Skips l4-curation.md (its HTML examples
    are code-fence content, not source comments)."""
    refs = repo_root / "references"
    skip = {
        refs / "sub-skills" / "common" / "l4-curation.md",
    }
    for path in (refs / "roles").rglob("*.md"):
        if path in skip:
            continue
        yield path
    # Sub-skills: nothing in scope today; the only author-only HTML
    # comments live in role files. Walking sub-skills would risk
    # touching code-fence content.


def main(repo_root: Path | None = None) -> int:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    total_files = 0
    total_subs = 0
    for path in _iter_target_files(repo_root):
        text = path.read_text(encoding="utf-8")
        new_text, n = convert(text)
        if n == 0:
            continue
        path.write_text(new_text, encoding="utf-8")
        print(f"WROTE {path.relative_to(repo_root)} ({n} strips)")
        total_files += 1
        total_subs += n
    print(f"---\nTotal files touched: {total_files}; total comment strips: {total_subs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
