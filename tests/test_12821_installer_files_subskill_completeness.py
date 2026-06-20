"""#12821 / #12915 — installer-files.txt must list every sub-skill the install
actually needs, so the wizard ships a complete tree.

A sub-skill .md must be in the manifest if it is either:
  (a) runtime-loadable — referenced in docs/sub-skill-catalog.md, so an agent
      resolves it via a `→ run sub-skill: <name>` marker at runtime; OR
  (b) a wizard L4 seed — a worker-*/verifier-* stub the wizard copies from
      references/sub-skills/project/ into a new install's .squidsquad/project/
      (wizard.py `_copy_l4_seed_stubs`).

Files that are NEITHER (e.g. the orphaned pm-*/dm-* project stubs the wizard
explicitly skips — "leave other seeds alone") are intentionally NOT shipped and
are excluded here. Without this test the gap went unnoticed: 21 catalog/seed
fragments were absent from the manifest (#12915).
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "references" / "installer-files.txt"
CATALOG = REPO / "docs" / "sub-skill-catalog.md"
SUBSKILLS = REPO / "references" / "sub-skills"


def _manifest_paths():
    return {ln.strip() for ln in MANIFEST.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


def _rel(p):
    return str(p.relative_to(REPO)).replace("\\", "/")


def _in_catalog(rel_path):
    text = CATALOG.read_text(encoding="utf-8")
    stem = Path(rel_path).stem
    return rel_path in text or stem in text


def _is_wizard_seed(rel_path):
    name = Path(rel_path).name
    return (rel_path.startswith("references/sub-skills/project/")
            and (name.startswith("worker-") or name.startswith("verifier-")))


def test_all_catalog_subskills_in_manifest():
    """Every catalog-referenced sub-skill on disk must be shipped (runtime-loadable)."""
    manifest = _manifest_paths()
    missing = [_rel(p) for p in sorted(SUBSKILLS.rglob("*.md"))
               if _in_catalog(_rel(p)) and _rel(p) not in manifest]
    assert not missing, (
        f"{len(missing)} runtime-loadable (catalog) sub-skill(s) absent from "
        f"installer-files.txt (#12915): {missing}"
    )


def test_all_wizard_seed_stubs_in_manifest():
    """Every worker-*/verifier-* L4 seed the wizard copies must be shipped."""
    manifest = _manifest_paths()
    missing = [_rel(p) for p in sorted(SUBSKILLS.rglob("*.md"))
               if _is_wizard_seed(_rel(p)) and _rel(p) not in manifest]
    assert not missing, (
        f"{len(missing)} wizard L4 seed stub(s) absent from installer-files.txt "
        f"(#12915): {missing}"
    )


def test_manifest_count_header_matches_payload():
    """The `# Total: N files` header must equal the payload line count (the
    same invariant #12525 checks — re-asserted here so a bulk add can't drift)."""
    text = MANIFEST.read_text(encoding="utf-8")
    m = re.search(r"# Total:\s*(\d+)\s*files", text)
    assert m, "manifest must carry a `# Total: N files` header"
    payload = [ln for ln in text.splitlines()
               if ln.strip() and not ln.lstrip().startswith("#")]
    assert int(m.group(1)) == len(payload), (
        f"header says {m.group(1)} but manifest lists {len(payload)}"
    )


def test_no_duplicate_manifest_entries():
    payload = [ln.strip() for ln in MANIFEST.read_text(encoding="utf-8").splitlines()
               if ln.strip() and not ln.lstrip().startswith("#")]
    dupes = sorted({p for p in payload if payload.count(p) > 1})
    assert not dupes, f"duplicate manifest entries: {dupes}"
