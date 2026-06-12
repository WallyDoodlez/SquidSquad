"""#11142 — compose-pipeline author-only HTML comments must not appear in
composed CLAUDE.md.

Author-only comments are HTML markdown comments that talk to template
authors or compose tooling, not to the reading agent. They consume
tokens, add noise above content the agent needs, and surface
compose-pipeline implementation detail (layer numbering, step-ID
conventions) that's irrelevant at runtime.

Regression contract:
- The denylist of author-only patterns must yield zero matches in any
  of the 4 composed CLAUDE.md files AND in the 4 CLAUDE.linked.md
  intermediates.
- Load-bearing tooling sentinels (``<!-- /project-adaptation -->``
  used by ``soul_adaptation.py``) MUST still survive — verified by
  separate positive assertion.
- ``<!-- sub-skill: NAME -->`` wrapper markers and
  ``<!-- #10360-cleanup: ... -->`` future-work pointers (preserved
  through #11137 / #11139) MUST still survive — verified by separate
  positive assertion.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE = REPO_ROOT / "references" / "scripts" / "compose.py"


# Denylist: author/installer-only comment shapes that #11142 strips
# from L1-L3 source. Each must yield zero matches in the composed
# output. Match shapes broadly so future re-introductions are caught
# even if the wording shifts slightly.
_AUTHOR_DENYLIST = [
    re.compile(r"<!-- Layer \d+:", re.MULTILINE),
    re.compile(r"<!-- This content is prepended", re.MULTILINE),
    re.compile(r"<!-- It defines what ANY", re.MULTILINE),
    re.compile(r"<!-- NOTE: step IDs below", re.MULTILINE),
    re.compile(r"<!-- L[1-3] [A-Za-z ]+(?:Skill )?instructions — H3 ops target", re.MULTILINE),
    re.compile(r"<!-- v2 compose-model slot ops", re.MULTILINE),
    re.compile(r"<!-- L1-EXCLUSIVE:", re.MULTILINE),
    re.compile(r"<!-- absorbed from feedback_", re.MULTILINE),
    re.compile(r"<!-- Note \(\d+", re.MULTILINE),
    # #9588-style multi-line "the directives below..."
    re.compile(r"<!--\s*\n\s*#\d+: the directives below", re.MULTILINE),
]


@pytest.fixture(scope="module")
def _deploy_all():
    """Run compose deploy-all once for the module so all composites exist."""
    result = subprocess.run(
        [sys.executable, str(COMPOSE), "deploy-all"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"compose deploy-all failed: {result.stderr}"
    )
    return result


@pytest.mark.parametrize("role", ["dm", "pm", "qa", "skill"])
@pytest.mark.parametrize(
    "pattern",
    _AUTHOR_DENYLIST,
    ids=[p.pattern[:40] for p in _AUTHOR_DENYLIST],
)
def test_no_author_comments_in_composed_claude_md(_deploy_all, role, pattern):
    """Composed .squidsquad/<role>/CLAUDE.md must contain zero matches
    for each author/installer-only HTML comment shape — they have no
    runtime semantic value and surface compose-pipeline implementation
    detail to the reading agent."""
    path = REPO_ROOT / ".squidsquad" / role / "CLAUDE.md"
    assert path.exists(), f"compose did not produce {path}"
    text = path.read_text(encoding="utf-8")
    matches = pattern.findall(text)
    assert not matches, (
        f"Author-only comment shape {pattern.pattern!r} leaked into "
        f"{path}: {matches!r}. Per #11142 these must be stripped from "
        f"L1-L3 source (see .squidsquad/skill/planning/migrate_11142.py)."
    )


@pytest.mark.parametrize("role", ["dm", "pm", "qa", "skill"])
@pytest.mark.parametrize(
    "pattern",
    _AUTHOR_DENYLIST,
    ids=[p.pattern[:40] for p in _AUTHOR_DENYLIST],
)
def test_no_author_comments_in_linked_intermediate(_deploy_all, role, pattern):
    """Same denylist guarantee for the .CLAUDE.linked.md intermediate."""
    path = REPO_ROOT / ".squidsquad" / role / "CLAUDE.linked.md"
    assert path.exists(), f"compose did not produce {path}"
    text = path.read_text(encoding="utf-8")
    matches = pattern.findall(text)
    assert not matches, (
        f"Author-only comment shape {pattern.pattern!r} leaked into "
        f"linked intermediate {path}: {matches!r}."
    )


@pytest.mark.parametrize("role", ["dm", "pm", "qa", "skill"])
def test_project_adaptation_footer_preserved(_deploy_all, role):
    """``<!-- /project-adaptation -->`` is a tooling sentinel used by
    soul_adaptation.py to delimit the replaceable region in SOUL.md.
    It must SURVIVE the #11142 cleanup — over-strip caught this in
    R0 (test_compose.py::test_project_adaptation_present)."""
    path = REPO_ROOT / ".squidsquad" / role / "CLAUDE.md"
    text = path.read_text(encoding="utf-8")
    assert "<!-- /project-adaptation -->" in text, (
        f"project-adaptation footer missing from {path}; #11142 strip "
        f"may have been over-eager. soul_adaptation.py relies on this "
        f"marker to find the replaceable region in SOUL.md."
    )


def test_sub_skill_wrapper_markers_preserved(_deploy_all):
    """``<!-- sub-skill: NAME -->`` / ``<!-- /sub-skill: NAME -->`` wrapper
    markers around inlined sub-skill bodies (preserved through #11137)
    must survive the #11142 cleanup — they're not author commentary,
    they're inlined-block boundary markers."""
    path = REPO_ROOT / "references" / "roles" / "worker" / "instructions.md"
    text = path.read_text(encoding="utf-8")
    # boot-bootstrap is the one mandatory-inline that #11137 kept
    assert "<!-- sub-skill: boot-bootstrap -->" in text, (
        "boot-bootstrap wrapper marker missing from worker/instructions.md "
        "— #11142 strip should not touch sub-skill wrappers."
    )


def test_10360_cleanup_markers_preserved(_deploy_all):
    """``<!-- #10360-cleanup: ... -->`` future-work pointers (preserved
    in #11137 R0 as load-bearing breadcrumbs) must survive #11142."""
    path = REPO_ROOT / "references" / "roles" / "worker" / "instructions.md"
    text = path.read_text(encoding="utf-8")
    assert "#10360-cleanup:" in text, (
        "#10360-cleanup markers missing from worker/instructions.md — "
        "#11142 strip should not touch the #10360 future-work pointers."
    )


def test_l4_curation_code_fence_examples_preserved():
    """l4-curation.md contains HTML comment examples INSIDE code fences
    that demonstrate L4 metadata trailers to readers. These are content,
    not source comments — #11142 must not touch this file."""
    path = REPO_ROOT / "references" / "sub-skills" / "common" / "l4-curation.md"
    text = path.read_text(encoding="utf-8")
    # The code fence example "authored-by: ..." metadata trailer must
    # still appear; if migrate_11142 walked this file, the
    # absorbed-style markers would survive (false positives are
    # not the concern here — the concern is that examples in code
    # fences not get stripped).
    assert "authored-by:" in text, (
        "l4-curation.md code-fence example missing — #11142 migration "
        "should skip this file."
    )
