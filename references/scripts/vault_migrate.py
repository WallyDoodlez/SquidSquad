#!/usr/bin/env python3
"""SquidSquad vault v1 -> v2 migration (VAULT-ARCH 10, #13862).

The mechanical, judgment-free parts of the M-track, as one deterministic,
idempotent, dry-runnable tool (the vault_check.py treatment):

    python scripts/vault_migrate.py inventory [--out <json>]              # M0: input inventory
    python scripts/vault_migrate.py transform [--dry-run] [--report <json>] # M1: mechanical transform
    python scripts/vault_migrate.py apply-manifest <manifest.json> [--dry-run]  # M3: apply the approved M2 manifest
    python scripts/vault_migrate.py reconcile <inventory.json> <manifest.json>  # M3: verification gates

All commands accept ``--vault <dir>`` (default: this repo's .squidsquad/vault),
which is how the rehearsal runs the whole walk on a scratch copy first.

M1 (VAULT-ARCH 10.2 + 4.3):
  - drops confidence / source / links (and the Claude-memory `name` /
    `metadata` duplicates of slug / type)
  - adds empty community / subcommunity / last_optimized
  - owner labels -> bare role-class (skill/skill-lead/dev -> worker, qa* /
    verifier-lead -> verifier, pm-lead -> pm, dm-lead -> dm); a missing owner
    comes from author/role when that maps to a class, else `shared`
  - fills a missing status (archives/ -> archived, else active), type (from
    metadata / registry prefix / archives folder) and updated (= created)
  - style-* notes fold into pattern-* (redirect map + vault-wide wikilink
    rewrite; out-of-vault references are flagged, not rewritten)
  - drops posture tags; deletes .relevance-index.json
  - appends one changelog entry per migrated note
Keys outside the 4.3 schema that carry content (description, author, ...)
are kept and reported for M2 -- deciding what to do with them is judgment.

Exit codes: 0 success, 1 gate/validation failure, 2 usage error.
"""

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
VAULT_DIR = REPO_ROOT / ".squidsquad" / "vault"

TASK_REF = "#13862"
MIGRATED_MARK = "migrated to vault v2"
DROP_KEYS = ("confidence", "source", "links", "name", "metadata")
CANONICAL = ("type", "tags", "created", "updated", "status", "owner",
             "community", "subcommunity", "last_optimized")
ADD_EMPTY = ("community", "subcommunity", "last_optimized")
OWNER_MAP = {
    "pm": "pm", "pm-lead": "pm",
    "worker": "worker", "skill": "worker", "skill-lead": "worker",
    "dev": "worker", "dev-lead": "worker",
    "verifier": "verifier", "verifier-lead": "verifier",
    "qa": "verifier", "qa-lead": "verifier",
    "dm": "dm", "dm-lead": "dm",
    "shared": "shared",
}
PREFIX_TYPES = {"decision-": "decision", "pattern-": "pattern",
                "learning-": "learning", "rule-": "rule", "style-": "pattern"}
POSTURE_TAGS = ("posture", "pattern-posture")
SKIP_FILES = ("BRIEFING.md",)
_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):(.*)$")


# ---------------------------------------------------------------------------
# Frontmatter model: ordered [(key, [raw lines])], continuation lines attach
# to the key above them, so values are carried byte-for-byte unless changed.
# ---------------------------------------------------------------------------

def _split(text):
    """-> (entries, body, nl) or None when the note has no frontmatter."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    entries = []
    for line in lines[1:end]:
        m = _KEY_RE.match(line)
        if m:
            entries.append([m.group(1), [line]])
        elif entries:
            entries[-1][1].append(line)
        else:
            entries.append(["", [line]])
    return entries, nl.join(lines[end + 1:]), nl


def _value(entry_lines):
    """First-line scalar value with any trailing ' # comment' removed."""
    v = entry_lines[0].split(":", 1)[1]
    return re.sub(r"\s+#.*$", "", v).strip().strip("'\"")


def _get(entries, key):
    for k, ls in entries:
        if k == key:
            return ls
    return None


def _render(entries, body, nl):
    out = ["---"]
    for _, ls in entries:
        out.extend(ls)
    out.append("---")
    return nl.join(out) + nl + body


def _slug(rel):
    return Path(rel).stem


def _notes(vault):
    for p in sorted(vault.rglob("*.md")):
        rel = p.relative_to(vault).as_posix()
        if p.name in SKIP_FILES or any(part.startswith(".") for part in Path(rel).parts):
            continue
        yield rel, p


def _read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def _write(p, text):
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    tmp.replace(p)


def _append_changelog(body, nl, line):
    """Append ``line`` to the note's ## Changelog section (created if absent)."""
    lines = body.split(nl)
    idx = next((i for i, l in enumerate(lines) if l.strip().lower() == "## changelog"), None)
    if idx is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## Changelog", "", line, ""]
        return nl.join(lines)
    end = next((i for i in range(idx + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    insert = end
    while insert > idx + 1 and not lines[insert - 1].strip():
        insert -= 1
    lines.insert(insert, line)
    return nl.join(lines)


# ---------------------------------------------------------------------------
# M0 -- inventory
# ---------------------------------------------------------------------------

def inventory(vault=None):
    vault = Path(vault or VAULT_DIR)
    notes, by = {}, {"type": Counter(), "owner": Counter(), "status": Counter(),
                     "folder": Counter()}
    for rel, p in _notes(vault):
        parsed = _split(_read(p))
        fm = {}
        if parsed:
            for k, ls in parsed[0]:
                if k and k != "metadata":
                    fm[k] = _value(ls)
        row = {"path": rel, "type": fm.get("type", ""), "owner": fm.get("owner", ""),
               "status": fm.get("status", "")}
        notes[_slug(rel)] = row
        by["type"][row["type"]] += 1
        by["owner"][row["owner"]] += 1
        by["status"][row["status"]] += 1
        by["folder"][rel.split("/")[0] if "/" in rel else "."] += 1
    return {"generated": datetime.now().strftime("%Y-%m-%d"), "vault": str(vault),
            "count": len(notes), "distributions": {k: dict(v) for k, v in by.items()},
            "notes": notes}


# ---------------------------------------------------------------------------
# M1 -- mechanical transform
# ---------------------------------------------------------------------------

def _git_created(rel):
    """Date of the first commit that added this vault note (the live repo's
    history, keyed by vault-relative path -- so a rehearsal copy resolves
    the same dates). None when git has no record."""
    try:
        proc = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%as", "--",
             f".squidsquad/vault/{rel}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT), timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    dates = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    return dates[-1] if proc.returncode == 0 and dates else None


def _owner_from(entries):
    for key in ("author", "role", "roles"):
        ls = _get(entries, key)
        if ls:
            cand = _value(ls).strip("[]").split(",")[0].strip().lower()
            if cand in OWNER_MAP:
                return OWNER_MAP[cand]
    return "shared"


def transform_note(rel, text, today):
    """Pure M1 transform of one note -> (new_text, new_rel, notes[list])."""
    parsed = _split(text)
    if parsed is None:
        return text, rel, ["no frontmatter -- left untouched"]
    entries, body, nl = parsed
    log, new_rel = [], rel
    name = Path(rel).name

    meta_type = None
    meta = _get(entries, "metadata")
    if meta:
        for l in meta[1:]:
            m = re.match(r"^\s+type:\s*(.+)$", l)
            if m:
                meta_type = m.group(1).strip()
    dropped = [k for k, _ in entries if k in DROP_KEYS]
    entries = [e for e in entries if e[0] not in DROP_KEYS]
    if dropped:
        log.append(f"dropped {','.join(sorted(set(dropped)))}")

    def setv(key, value):
        ls = _get(entries, key)
        line = f"{key}: {value}" if value != "" else f"{key}:"
        if ls is None:
            entries.append([key, [line]])
        else:
            ls[:] = [line]

    if name.startswith("style-"):
        new_rel = str(Path(rel).with_name("pattern-" + name[len("style-"):])).replace("\\", "/")
        setv("type", "pattern")
        log.append(f"style folded into pattern: {_slug(rel)} -> {_slug(new_rel)}")
    elif not (_get(entries, "type") and _value(_get(entries, "type"))):
        inferred = meta_type or next((t for p, t in PREFIX_TYPES.items() if name.startswith(p)), None)
        if not inferred and rel.startswith("archives/"):
            inferred = "archive"
        if inferred:
            setv("type", inferred)
            log.append(f"type filled: {inferred}")
        else:
            log.append("FLAG: type missing and not inferable")

    owner = _get(entries, "owner")
    if owner is None or not _value(owner):
        derived = _owner_from(entries)
        setv("owner", derived)
        log.append(f"owner filled: {derived}")
    else:
        raw = _value(owner).lower()
        mapped = OWNER_MAP.get(raw)
        if mapped is None:
            log.append(f"FLAG: unknown owner '{raw}'")
        elif mapped != _value(owner):
            setv("owner", mapped)
            log.append(f"owner {raw} -> {mapped}")

    status = _get(entries, "status")
    if status is None or not _value(status):
        filled = "archived" if rel.startswith("archives/") else "active"
        setv("status", filled)
        log.append(f"status filled: {filled}")
    elif status[0] != f"status: {_value(status)}" and len(status) == 1:
        setv("status", _value(status))  # strip v1 template comments

    if not (_get(entries, "created") and _value(_get(entries, "created"))):
        born = _git_created(rel)
        if born:
            setv("created", born)
            log.append(f"created filled from first git commit: {born}")
        else:
            log.append("FLAG: created missing and no git history")
    if _get(entries, "updated") is None and _get(entries, "created"):
        setv("updated", _value(_get(entries, "created")))
        log.append("updated filled from created")

    tags = _get(entries, "tags")
    if tags and len(tags) == 1:
        v = tags[0].split(":", 1)[1].strip()
        if v.startswith("[") and v.endswith("]"):
            items = [t.strip() for t in v[1:-1].split(",") if t.strip()]
            kept = [t for t in items if t.strip("'\"") not in POSTURE_TAGS]
            if kept != items:
                setv("tags", "[" + ", ".join(kept) + "]")
                log.append("posture tag dropped")
            if not kept:
                log.append("FLAG: no tags (4.3 needs a domain tag)")
    elif not tags:
        log.append("FLAG: no tags (4.3 needs a domain tag)")

    for key in ADD_EMPTY:
        if _get(entries, key) is None:
            entries.append([key, [f"{key}:"]])

    order = {k: i for i, k in enumerate(CANONICAL)}
    extras = [k for k, _ in entries if k and k not in order]
    if extras:
        log.append(f"non-schema keys kept for M2: {','.join(extras)}")
    entries.sort(key=lambda e: order.get(e[0], len(order)))  # stable: extras keep order

    new_body = body
    if MIGRATED_MARK not in body:
        new_body = _append_changelog(body, nl, f"- **{today}** — {MIGRATED_MARK} ({TASK_REF}).")
    return _render(entries, new_body, nl), new_rel, log


def _rewrite_links(text, redirects):
    def sub(m):
        target = m.group(1)
        return "[[" + redirects[target] + m.group(2) + "]]" if target in redirects else m.group(0)
    return re.sub(r"\[\[([^\]|#]+)([^\]]*)\]\]", sub, text)


def transform(vault=None, dry_run=False, today=None, repo_root=None):
    vault = Path(vault or VAULT_DIR)
    repo_root = Path(repo_root or REPO_ROOT)
    today = today or datetime.now().strftime("%Y-%m-%d")
    changed, renamed, per_note, redirects = [], [], {}, {}
    results = []
    for rel, p in _notes(vault):
        old = _read(p)
        new, new_rel, log = transform_note(rel, old, today)
        results.append((rel, p, old, new, new_rel))
        if log:
            per_note[_slug(rel)] = log
        if new_rel != rel:
            if (vault / new_rel).exists():
                per_note[_slug(rel)].append(f"FLAG: rename target {new_rel} exists -- not renamed")
                continue
            redirects[_slug(rel)] = _slug(new_rel)
    for rel, p, old, new, new_rel in results:
        if redirects:
            new = _rewrite_links(new, redirects)
        target = vault / (new_rel if _slug(rel) in redirects else rel)
        if new != old or target != p:
            changed.append(rel)
            if not dry_run:
                _write(p, new)
                if target != p:
                    p.replace(target)
                    renamed.append([rel, target.relative_to(vault).as_posix()])
    relevance = vault / ".relevance-index.json"
    removed_index = relevance.exists()
    if removed_index and not dry_run:
        relevance.unlink()
    outside = _external_references(repo_root, vault, redirects)
    return {"dry_run": dry_run, "date": today, "changed": len(changed),
            "changed_notes": changed, "renamed": renamed, "redirects": redirects,
            "relevance_index_removed": removed_index, "external_references": outside,
            "flags": {s: [l for l in log if l.startswith("FLAG")]
                      for s, log in per_note.items() if any(l.startswith("FLAG") for l in log)},
            "per_note": per_note}


def _external_references(repo_root, vault, redirects):
    """Out-of-vault mentions of renamed slugs: flagged for a human, never
    rewritten (a doc may quote the old name on purpose)."""
    if not redirects:
        return []
    hits = []
    vault = vault.resolve()
    for sub in ("docs", "references", ".squidsquad"):
        root = repo_root / sub
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in (".md", ".json", ".py", ".txt", ".yml"):
                continue
            try:
                if vault in p.resolve().parents:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for old in redirects:
                if old in text:
                    hits.append({"file": p.relative_to(repo_root).as_posix(), "slug": old})
    return hits


# ---------------------------------------------------------------------------
# M3 -- apply the operator-approved manifest, then reconcile
# ---------------------------------------------------------------------------
#
# Manifest (M2 output, operator-reviewed):
#   {"notes": {"<slug>": {"disposition": "keep" | "merge-into" | "prune",
#                         "target": "<slug>"   (merge-into only),
#                         "reason": "<one line>",
#                         "hubs": ["<system hub slug>", ...]}},
#    "merged_drafts": {"<target slug>": "<draft body file>"},
#    "new_hubs": {"<hub slug>": "<full note file incl. frontmatter>"},
#    "link_fixes": {"<slug>": {"<dangling target>": "<new slug>" | null}},
#                  (null unlinks: [[x]] -> x, text kept)
#    "add_tags": {"<slug>": ["<tag>", ...]},
#    "redirects": {<M1 redirect map, so reconcile follows renames>}}
# Retirement is a status flip in place (VAULT-ARCH 3.4) -- nothing is deleted.

DISPOSITIONS = ("keep", "merge-into", "prune")


def _set_field(entries, key, value):
    ls = _get(entries, key)
    if ls is None:
        entries.append([key, [f"{key}: {value}"]])
    else:
        ls[:] = [f"{key}: {value}"]


def validate_manifest(manifest, slugs):
    problems = []
    notes = manifest.get("notes", {})
    for slug, d in notes.items():
        disp = d.get("disposition")
        if disp not in DISPOSITIONS:
            problems.append(f"{slug}: bad disposition {disp!r}")
        if disp == "merge-into":
            tgt = d.get("target")
            if not tgt or (tgt not in slugs and tgt not in manifest.get("new_hubs", {})):
                problems.append(f"{slug}: merge target {tgt!r} does not exist")
            elif notes.get(tgt, {}).get("disposition") in ("prune", "merge-into"):
                problems.append(f"{slug}: merge target {tgt} is itself retired")
        if slug not in slugs:
            problems.append(f"{slug}: not in the vault")
    new_hubs = set(manifest.get("new_hubs", {}))
    for slug, fixes in manifest.get("link_fixes", {}).items():
        if slug not in slugs:
            problems.append(f"link_fixes {slug}: not in the vault")
        for old, new in fixes.items():
            if new is not None and new not in slugs and new not in new_hubs:
                problems.append(f"link_fixes {slug}: [[{old}]] -> {new!r} does not exist")
    for slug in manifest.get("add_tags", {}):
        if slug not in slugs:
            problems.append(f"add_tags {slug}: not in the vault")
    return problems


def _fix_links(body, fixes):
    """Rewrite or unlink wikilinks keyed exactly as vault_check reads them:
    the text before any `|` alias (so `[[#13030]]` and `[[a#h]]` match)."""
    def sub(m):
        target, sep, alias = m.group(1).partition("|")
        key = target.strip()
        if key not in fixes:
            return m.group(0)
        new = fixes[key]
        if new is None:
            return alias.strip() or key
        return "[[" + new + sep + alias + "]]"
    return re.sub(r"\[\[([^\]]+)\]\]", sub, body)


def _add_tags(entries, tags):
    ls = _get(entries, "tags")
    items = []
    if ls and len(ls) == 1:
        v = ls[0].split(":", 1)[1].strip()
        if v.startswith("[") and v.endswith("]"):
            items = [t.strip() for t in v[1:-1].split(",") if t.strip()]
    for t in tags:
        if t not in items:
            items.append(t)
    _set_field(entries, "tags", "[" + ", ".join(items) + "]")


def apply_manifest(manifest_path, vault=None, dry_run=False, today=None):
    vault = Path(vault or VAULT_DIR)
    today = today or datetime.now().strftime("%Y-%m-%d")
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    paths = {_slug(rel): p for rel, p in _notes(vault)}
    briefing = vault / "BRIEFING.md"  # outside the note inventory, but its
    if briefing.exists():             # wikilinks count toward the M3 gate
        paths["BRIEFING"] = briefing
    problems = validate_manifest(manifest, set(paths))
    if problems:
        return {"applied": False, "problems": problems}
    actions = []

    for hub, draft in manifest.get("new_hubs", {}).items():
        dest = vault / "systems" / f"{hub}.md"
        if dest.exists():
            actions.append(f"hub {hub}: exists, skipped")
            continue
        actions.append(f"hub {hub}: created")
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            _write(dest, _read(base / draft))
        paths[hub] = dest

    for slug, d in manifest.get("notes", {}).items():
        p = paths[slug]
        parsed = _split(_read(p))
        if parsed is None:
            actions.append(f"{slug}: no frontmatter, skipped")
            continue
        entries, body, nl = parsed
        disp, reason = d["disposition"], d.get("reason", "").strip()
        if disp == "prune":
            _set_field(entries, "status", "archived")
            body = _append_changelog(body, nl, f"- **{today}** — archived at vault v2 distillation ({TASK_REF}): {reason}")
        elif disp == "merge-into":
            tgt = d["target"]
            _set_field(entries, "status", "superseded")
            body = _append_changelog(body, nl, f"- **{today}** — superseded by [[{tgt}]] at vault v2 distillation ({TASK_REF}).")
        new = _render(entries, body, nl)
        actions.append(f"{slug}: {disp}")
        if not dry_run:
            _write(p, new)

    for tgt, draft in manifest.get("merged_drafts", {}).items():
        p = paths[tgt]
        parsed = _split(_read(p))
        if parsed is None:
            continue
        entries, _, nl = parsed
        _set_field(entries, "updated", today)
        body = _read(base / draft).replace("\r\n", "\n").replace("\n", nl)
        if not body.startswith(nl):
            body = nl + body  # blank line after the frontmatter fence
        body = _append_changelog(body, nl, f"- **{today}** — merged distillation draft applied ({TASK_REF}).")
        actions.append(f"{tgt}: merged draft applied")
        if not dry_run:
            _write(p, _render(entries, body, nl))

    # Last pass, after merged drafts replaced bodies: hub links (keep only),
    # dangling-link fixes, tag additions.
    hubs = {s: d["hubs"] for s, d in manifest.get("notes", {}).items()
            if d.get("disposition") == "keep" and d.get("hubs")}
    touch = set(manifest.get("link_fixes", {})) | set(manifest.get("add_tags", {})) | set(hubs)
    for slug in sorted(touch):
        p = paths[slug]
        parsed = _split(_read(p))
        if parsed is None:  # BRIEFING.md: no frontmatter -- links only
            fixes = manifest.get("link_fixes", {}).get(slug) or {}
            actions.append(f"{slug}: {len(fixes)} link fix(es)")
            if fixes and not dry_run:
                _write(p, _fix_links(_read(p), fixes))
            continue
        entries, body, nl = parsed
        fixes = manifest.get("link_fixes", {}).get(slug)
        if fixes:  # frontmatter too: vault_check reads links in the whole file
            body = _fix_links(body, fixes)
            for e in entries:
                e[1][:] = [_fix_links(l, fixes) for l in e[1]]
            actions.append(f"{slug}: {len(fixes)} link fix(es)")
        for hub in hubs.get(slug, []):
            if f"[[{hub}]]" not in body:
                body = _add_related(body, nl, hub)
                actions.append(f"{slug}: linked to hub {hub}")
        tags = manifest.get("add_tags", {}).get(slug)
        if tags:
            _add_tags(entries, tags)
            actions.append(f"{slug}: tags + {','.join(tags)}")
        if not dry_run:
            _write(p, _render(entries, body, nl))
    return {"applied": not dry_run, "dry_run": dry_run, "actions": actions}


def _add_related(body, nl, hub):
    lines = body.split(nl)
    idx = next((i for i, l in enumerate(lines) if l.strip().lower() == "## related"), None)
    if idx is None:
        cl = next((i for i, l in enumerate(lines) if l.strip().lower() == "## changelog"), len(lines))
        lines[cl:cl] = ["## Related", "", f"- [[{hub}]]", ""]
    else:
        end = next((i for i in range(idx + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        while end > idx + 1 and not lines[end - 1].strip():
            end -= 1
        lines.insert(end, f"- [[{hub}]]")
    return nl.join(lines)


def reconcile(inventory_path, manifest_path, vault=None, run_checks=True):
    """M3 gates: every M0 note is dispositioned (renames followed through the
    M1 redirect map), plus the vault_check sweep and the wikilink check."""
    inv = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    redirects = manifest.get("redirects", {})
    notes = manifest.get("notes", {})
    counts = Counter()
    missing = []
    for slug in inv["notes"]:
        d = notes.get(redirects.get(slug, slug))
        if d is None:
            missing.append(slug)
        else:
            counts[d["disposition"]] += 1
    result = {"m0_count": inv["count"], "dispositions": dict(counts),
              "undispositioned": missing,
              "reconciled": not missing and sum(counts.values()) == inv["count"]}
    if run_checks:
        result["checks"] = vault_checks(vault)
        result["passed"] = result["reconciled"] and result["checks"]["passed"]
    return result


def vault_checks(vault=None):
    """Run vault_check's full sweep + wikilink check against ``vault``
    (in-process with its VAULT_DIR pointed there, so a rehearsal copy is
    checked -- not the live vault)."""
    import contextlib
    import io
    sys.path.insert(0, str(SCRIPT_DIR))
    import vault_check
    saved = vault_check.VAULT_DIR
    vault_check.VAULT_DIR = Path(vault or VAULT_DIR)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            valid = vault_check.validate()
            broken = vault_check.check_wikilinks()
    finally:
        vault_check.VAULT_DIR = saved
    return {"validate": bool(valid), "broken_links": broken,
            "passed": bool(valid) and not broken}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _opt(args, flag):
    if flag in args:
        i = args.index(flag) + 1
        if i < len(args):
            return args[i]
    return None


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, vault = args[0], _opt(args, "--vault")
    if cmd == "inventory":
        out = inventory(vault)
        text = json.dumps(out, indent=2)
        if _opt(args, "--out"):
            Path(_opt(args, "--out")).write_text(text + "\n", encoding="utf-8")
        print(text if not _opt(args, "--out") else json.dumps({"count": out["count"]}))
        return 0
    if cmd == "transform":
        out = transform(vault, dry_run="--dry-run" in args)
        if _opt(args, "--report"):
            Path(_opt(args, "--report")).write_text(json.dumps(out, indent=2) + "\n",
                                                   encoding="utf-8")
        summary = {k: out[k] for k in ("dry_run", "changed", "renamed", "redirects",
                                       "relevance_index_removed", "external_references",
                                       "flags")}
        print(json.dumps(summary, indent=2))
        return 0
    if cmd == "apply-manifest" and len(args) > 1:
        out = apply_manifest(args[1], vault, dry_run="--dry-run" in args)
        print(json.dumps(out, indent=2))
        return 0 if not out.get("problems") else 1
    if cmd == "reconcile" and len(args) > 2:
        out = reconcile(args[1], args[2], vault)
        print(json.dumps(out, indent=2))
        return 0 if out.get("passed") else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
