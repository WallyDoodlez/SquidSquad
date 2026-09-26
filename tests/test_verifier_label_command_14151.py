"""#14151 -- the verifier's HUMAN-REQUIRED gate names the label command.

The gate said "add the blocked:human-action label" without a command. The
obvious `gh issue edit --add-label` failed under a read-only gh identity, and
the verifier had to find `tracker.py add-labels` (the pinned-identity route) by
reading tracker.py. The gate now names it.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERIFIER = REPO / "references" / "sub-skills" / "roles" / "verifier"
CMD = "tracker.py add-labels [NUMBER] blocked:human-action"


def _gate(text):
    start = text.index("**HUMAN-REQUIRED gate**")
    return text[start:text.index("\n\n", start)]


def test_human_required_gate_names_the_command():
    gate = _gate((VERIFIER / "verification-templates.md").read_text(encoding="utf-8"))
    assert f"python references/scripts/{CMD}" in gate
    assert "Never use bare `gh issue edit --add-label`" in gate


def test_finding_categories_names_the_command():
    text = (VERIFIER / "skill" / "finding-categories.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("| **Test infrastructure**"))
    assert CMD in row


def test_no_verifier_fragment_instructs_bare_gh_add_label():
    for md in VERIFIER.rglob("*.md"):
        for ln in md.read_text(encoding="utf-8").splitlines():
            if re.search(r"gh issue edit[^`]*--add-label", ln):
                assert "Never use bare" in ln, f"{md}: {ln}"


def test_tracker_add_labels_cli_exists():
    src = (REPO / "references" / "scripts" / "tracker.py").read_text(encoding="utf-8")
    assert 'elif cmd == "add-labels":' in src
