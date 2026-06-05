"""Promote mandatory sub-skills from references to inline bodies in L1
orchestrator files (#11049 follow-on).

Per ``docs/sub-skill-catalog.md`` line 74: the *mandatory* sub-skills
(``boot-bootstrap`` / ``cycle-runner`` / ``context-pressure``) must
execute every cycle/boot. Pure description-matched Skill-tool invocation
is discretionary and cannot be relied on for procedures that have to
fire deterministically; the catalog explicitly says these "likely remain
inlined into the small composed CLAUDE.md".

The cycle-1591 migration converted these directives to
``→ run sub-skill: <name>`` references; ``compose.py`` then dropped the
bodies and ``tests/test_compose_9588`` 18 cases went red because the
bootstrap teaching is no longer in the composite.

This pass walks the four L1 ``instructions.md`` files and replaces each
``→ run sub-skill: <mandatory-name>`` line with the body of
``references/sub-skills/common/<mandatory-name>.md`` (frontmatter +
outer markers stripped). Idempotent; safe to re-run.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROLES_L1 = [
    REPO / "references" / "roles" / "worker" / "instructions.md",
    REPO / "references" / "roles" / "pm" / "instructions.md",
    REPO / "references" / "roles" / "verifier" / "instructions.md",
    REPO / "references" / "roles" / "dm" / "instructions.md",
]
SUB_SKILLS = REPO / "references" / "sub-skills" / "common"
MANDATORY = ["boot-bootstrap", "cycle-runner", "context-pressure"]

_FRONTMATTER_RE = re.compile(r"\A---\n[\s\S]*?\n---\n", re.MULTILINE)
_OUTER_MARKER_RE = re.compile(r"^<!-- /?sub-skill: [a-z][a-z0-9-]+ -->\s*\n", re.MULTILINE)


def _body(name: str) -> str:
    text = (SUB_SKILLS / f"{name}.md").read_text(encoding="utf-8")
    text = _FRONTMATTER_RE.sub("", text)
    text = _OUTER_MARKER_RE.sub("", text)
    return text.rstrip() + "\n"


def main() -> int:
    bodies = {name: _body(name) for name in MANDATORY}
    touched = 0
    for path in ROLES_L1:
        text = path.read_text(encoding="utf-8")
        new = text
        for name, body in bodies.items():
            pattern = re.compile(rf"^→ run sub-skill: {re.escape(name)}\s*\n", re.MULTILINE)
            new = pattern.sub(body, new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            touched += 1
            print(f"promoted mandatory bodies into {path.relative_to(REPO).as_posix()}")
    print(f"inlined {len(MANDATORY)} mandatory sub-skills across {touched} L1 files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
