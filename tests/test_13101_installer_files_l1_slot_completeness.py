"""#13101 — installer-files.txt must list every L1 base slot-source.

The top-level files under references/roles/ (NOT the role subdirs) are the L1
base slot-sources that compose.py's source-gather reads to populate each
composed CLAUDE.md slot (## Identity, ## Soul, ## Vault, instructions, ...).
A fresh `npx squidsquad` install fetches ONLY manifest-listed files, so an L1
slot-source absent from installer-files.txt means that composed section is
empty/degraded (or compose errors) on a clean install — invisible on a
self-hosted clone where the full tree is already present.

This is the L1-slot analogue of #12861/#12821's sub-skill manifest gate. It
caught identity.md (slot: identity) and vault.md (slot: vault) silently absent
while their siblings SOUL.md / instructions.md / LAYERS.md were listed (#13101).

The gate is keyed on `slot:` frontmatter, not on filename: any top-level
references/roles/*.md that declares a slot is a compose source and MUST ship.
Files without slot frontmatter (if any) are not slot-sources and are excluded.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "references" / "installer-files.txt"
ROLES = REPO / "references" / "roles"

_SLOT_RE = re.compile(r"^slot:\s*\S", re.MULTILINE)


def _manifest_paths():
    return {ln.strip() for ln in MANIFEST.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


def _rel(p):
    return str(p.relative_to(REPO)).replace("\\", "/")


def _declares_slot(p):
    """True if the file has a `slot:` line in its YAML frontmatter."""
    text = p.read_text(encoding="utf-8")
    # frontmatter is the first `---`-delimited block; scanning the whole head is
    # sufficient since slot: only ever appears in frontmatter for these sources.
    return bool(_SLOT_RE.search(text))


def test_all_l1_slot_sources_in_manifest():
    """Every top-level references/roles/*.md with slot: frontmatter must ship."""
    manifest = _manifest_paths()
    slot_sources = [p for p in sorted(ROLES.glob("*.md")) if _declares_slot(p)]
    # sanity: the known base slot-sources are present on disk
    assert slot_sources, "expected L1 base slot-sources under references/roles/"
    missing = [_rel(p) for p in slot_sources if _rel(p) not in manifest]
    assert not missing, (
        f"{len(missing)} L1 base slot-source(s) absent from installer-files.txt "
        f"(#13101) — fresh installs would compose empty/degraded slots: {missing}"
    )


def test_total_count_matches_listed_paths():
    """The `# Total: N files` header must equal the count of listed paths."""
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    declared = None
    for ln in lines:
        m = re.match(r"#\s*Total:\s*(\d+)\s*files", ln)
        if m:
            declared = int(m.group(1))
            break
    assert declared is not None, "installer-files.txt missing `# Total: N files` header"
    actual = len(_manifest_paths())
    assert declared == actual, (
        f"installer-files.txt header says {declared} files but {actual} paths are "
        f"listed — update the `# Total:` line when adding/removing manifest entries"
    )
