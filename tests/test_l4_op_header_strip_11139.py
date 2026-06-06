"""#11139 — L4-op-syntax H3 headers must not survive into composed CLAUDE.md.

L1/L2/L3 source files contain `### append`, `### insert-after step:cycle/<id>`,
etc. as authoring markers, but at the L1-L3 compose layer they have no
semantic value (only L4 ops are processed at compose time). They were
surviving into the rendered CLAUDE.md output where the consuming agent
saw meaningless compose-machinery headings interleaved with content.

Fix: `v2_link_stage._strip_l4_op_headers` strips them from each L1-L3
source body before `_join_bodies` concatenates. L4 ops are unaffected
because they are parsed from `.squidsquad/project/<role>.md` separately
and applied AFTER join.

Regression contract:
- `^### (append|replace|insert-after step:cycle/<id>|insert-before step:cycle/<id>|replace step:cycle/<id>)$`
  must yield ZERO matches in any of the 4 composed CLAUDE.md files
  AND in the 4 CLAUDE.linked.md intermediates.
- L4 append ops continue to apply their body content into the
  correct slot (the body's content shows up; only the op-type header
  is dropped).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE = REPO_ROOT / "references" / "scripts" / "compose.py"

# Match the four L4 op-type H3 directives. Same shape as
# l4_parser._OP_RE except expressed as a top-of-line H3 heading.
_OP_HEADER_RE = re.compile(
    r"^### (?:append|replace|"
    r"(?:replace|insert-before|insert-after)\s+step:cycle/[A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)


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
def test_no_op_type_headers_in_composed_claude_md(_deploy_all, role):
    """Composed .squidsquad/<role>/CLAUDE.md must contain zero matches
    for L4-op-syntax H3 headings — they have no semantic value at the
    L1-L3 compose layer and confuse the consuming agent."""
    path = REPO_ROOT / ".squidsquad" / role / "CLAUDE.md"
    assert path.exists(), f"compose did not produce {path}"
    text = path.read_text(encoding="utf-8")
    leaks = _OP_HEADER_RE.findall(text)
    assert not leaks, (
        f"L4-op-syntax H3 headers leaked into {path}: {leaks!r}. "
        f"Per #11139 these should be stripped from L1-L3 source bodies "
        f"in v2_link_stage._join_bodies before joining."
    )


@pytest.mark.parametrize("role", ["dm", "pm", "qa", "skill"])
def test_no_op_type_headers_in_linked_intermediate(_deploy_all, role):
    """Same guarantee for the .CLAUDE.linked.md intermediate the
    verbatim emitter consumes — strip happens at v2_link_stage.emit time
    so both files inherit the cleanup."""
    path = REPO_ROOT / ".squidsquad" / role / "CLAUDE.linked.md"
    assert path.exists(), f"compose did not produce {path}"
    text = path.read_text(encoding="utf-8")
    leaks = _OP_HEADER_RE.findall(text)
    assert not leaks, (
        f"L4-op-syntax H3 headers leaked into linked intermediate "
        f"{path}: {leaks!r}."
    )


def test_l4_append_op_body_still_flows_into_composite():
    """Smoke check: the L4 file `.squidsquad/project/pm.md` has an
    `### append` op under `## Identity` whose body is the recognizable
    'You are PM on SquidSquad — the framework that builds itself.'
    sentence. After the strip fix, that BODY must still appear in the
    composed pm CLAUDE.md — only the op-type header gets removed,
    not the content the op applied."""
    path = REPO_ROOT / ".squidsquad" / "pm" / "CLAUDE.md"
    text = path.read_text(encoding="utf-8")
    sentinel = "You are PM on SquidSquad"
    assert sentinel in text, (
        f"L4 append op body missing from {path}; the strip fix may "
        f"have removed too much. Expected sentinel: {sentinel!r}."
    )


def test_strip_helper_is_idempotent():
    """_strip_l4_op_headers should be a no-op on an already-clean body."""
    sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
    from v2_link_stage import _strip_l4_op_headers
    clean = "## Identity\n\nYou are a SquidSquad agent.\n\n### Boundaries\n\n- bullet\n"
    assert _strip_l4_op_headers(clean) == clean


def test_strip_helper_removes_append_with_trailing_blank():
    sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
    from v2_link_stage import _strip_l4_op_headers
    body = "## Identity\n\n### append\n\nYou are PM.\n"
    expected = "## Identity\n\nYou are PM.\n"
    assert _strip_l4_op_headers(body) == expected


def test_strip_helper_removes_insert_after_step():
    sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
    from v2_link_stage import _strip_l4_op_headers
    body = (
        "### insert-after step:cycle/resume\n\n"
        "#### step:cycle/triage-issues\n\n"
        "Triage prose.\n"
    )
    expected = "#### step:cycle/triage-issues\n\nTriage prose.\n"
    assert _strip_l4_op_headers(body) == expected


def test_strip_helper_preserves_non_op_h3_headings():
    """Boundaries, What this role does, etc. must not be stripped."""
    sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
    from v2_link_stage import _strip_l4_op_headers
    body = "### Boundaries\n\n- bullet\n\n### What this role does\n\n- bullet\n"
    assert _strip_l4_op_headers(body) == body
