#!/usr/bin/env python3
"""SquidSquad vault consumption pipeline -- deterministic seams (#13860, VAULT-ARCH 9.2-9.5).

The consumption steps are agent-performed, but every piece that can be decided
without judgment lives here so the verifier gate is a script, not a reading:

  - WHERE receipts go: exactly one plan/lineage file per issue (9.3 receipt
    location rule), resolved in a fixed order.
  - WHETHER receipts are well-formed: `check-receipts` is the 9.4 gate.
  - HOW the engine is reached: identity resolution + honest degradation when
    node or the engine is missing (9.9 -- never a fabricated "none relevant").

Usage:
    python scripts/vault_consume.py lineage-path <n>
    python scripts/vault_consume.py init-fix-plan <n> --role <alias>
    python scripts/vault_consume.py check-receipts <n> [--diff-base <ref>]
    python scripts/vault_consume.py search --alias <a> [--task N] [--entities ..] [--tags ..]
                                           [--terms ..] [--types ..] [--top N] [--no-write]
    python scripts/vault_consume.py cite --alias <a> --task N --slugs a,b

Exit codes:
    0 success / receipts pass (incl. engine-unavailable pass-with-note)
    1 receipts fail the gate
    2 usage error
    3 engine unavailable (search/cite) -- caller writes the honest receipt line
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SQ_DIR = REPO_ROOT / ".squidsquad"
VAULT_DIR = SQ_DIR / "vault"
INSTANCE_ID_FILE = SQ_DIR / ".instance-id"
UNPROVISIONED = "unprovisioned"

# Live install copy first (the SKILL.md invocation path), committed source second.
ENGINE_DIRS = (
    REPO_ROOT / ".claude" / "skills" / "vault-search" / "scripts",
    REPO_ROOT / "references" / "skills" / "vault-search" / "scripts",
)

CONTEXT_SECTION = "## Vault context consumed"
RULES_SECTION = "## Applicable rules"
RECEIPT_SECTIONS = (CONTEXT_SECTION, RULES_SECTION)

# The explicit none-variants each section accepts (9.3), and the 9.9
# degradation line both accept. Matched case-insensitively at bullet start.
NONE_PREFIX = {CONTEXT_SECTION: "none relevant", RULES_SECTION: "none matched"}
UNAVAILABLE_PREFIX = "engine unavailable"
WIKILINK_BULLET = re.compile(r"^\[\[[^\]\|]+(\|[^\]]*)?\]\]\s*(?:—|--|-|:)\s*\S")

FIX_PLAN_TEMPLATE = """# Fix plan -- #{n}

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

_What is actually wrong, with evidence (file:line, repro)._

## Intended direction

_The fix approach, and what it deliberately does not change._

## Impact

_Who/what the change touches; upgrade or migration notes._

{context}

{rules}
"""


# ---- lineage resolution --------------------------------------------------------

def _planning_dirs(sq_dir):
    """Every role's planning dir, PM's first (it authors CONTEXT + plan bodies)."""
    dirs = sorted(p for p in sq_dir.glob("*/planning") if p.is_dir())
    return sorted(dirs, key=lambda p: p.parent.name != "pm")


def resolve_lineage(n, sq_dir=None):
    """Resolve issue <n>'s single canonical lineage file.

    Order (first existing wins): per-task ``CONTEXT-<n>.md`` (planned task) ->
    ``<n>-body.md`` plan body (plan-in-PR, #12750) -> ``<n>-fix-plan.md``
    (bug flow, created at pickup). Returns ``{"path", "kind", "exists"}`` with a
    repo-relative forward-slash path, or ``None`` if nothing exists yet.
    """
    sq_dir = Path(sq_dir) if sq_dir else SQ_DIR
    for kind, name in (("context", f"CONTEXT-{n}.md"),
                       ("plan-body", f"{n}-body.md"),
                       ("fix-plan", f"{n}-fix-plan.md")):
        for d in _planning_dirs(sq_dir):
            p = d / name
            if p.is_file():
                return {"path": _rel(p, sq_dir), "kind": kind, "exists": True}
    return None


def _rel(path, sq_dir):
    return (Path(".squidsquad") / Path(path).relative_to(sq_dir)).as_posix()


def init_fix_plan(n, role, sq_dir=None):
    """Create the bug-flow lean fix-plan unless a lineage file already exists.

    Idempotent: an existing lineage file of any kind is returned untouched (a
    planned task already has its lineage -- a second file would split the 9.4
    gate's single canonical location)."""
    sq_dir = Path(sq_dir) if sq_dir else SQ_DIR
    existing = resolve_lineage(n, sq_dir)
    if existing:
        existing["created"] = False
        return existing
    p = sq_dir / role / "planning" / f"{n}-fix-plan.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(FIX_PLAN_TEMPLATE.format(
        n=n,
        context=CONTEXT_SECTION + "\n\n_Filled at pickup consultation._",
        rules=RULES_SECTION + "\n\n_Filled at pickup rules matching._"), encoding="utf-8")
    tmp.replace(p)
    return {"path": _rel(p, sq_dir), "kind": "fix-plan", "exists": True, "created": True}


# ---- receipt gate --------------------------------------------------------------

def _section_bullets(text, heading):
    """Bullet lines under ``heading`` up to the next ``## `` heading, or None if
    the heading is absent. The LAST occurrence wins (receipts append)."""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == heading]
    if not starts:
        return None
    bullets = []
    for ln in lines[starts[-1] + 1:]:
        if ln.startswith("## ") or ln.startswith("# "):
            break
        s = ln.strip()
        if s.startswith("- ") or s.startswith("* "):
            bullets.append(s[2:].strip())
    return bullets


def check_section(text, heading):
    """Classify one receipt section: ``cited`` | ``none`` | ``unavailable`` pass;
    ``missing`` | ``empty`` | ``malformed`` fail. Returns (status, detail)."""
    bullets = _section_bullets(text, heading)
    if bullets is None:
        return "missing", f"no '{heading}' section"
    if not bullets:
        return "empty", f"'{heading}' has no bullet lines"
    lowered = [b.lower() for b in bullets]
    if any(b.startswith(UNAVAILABLE_PREFIX) for b in lowered):
        if len(bullets) != 1:
            return "malformed", f"'{heading}': engine-unavailable line must stand alone"
        return "unavailable", bullets[0]
    if any(b.startswith(NONE_PREFIX[heading]) for b in lowered):
        if len(bullets) != 1:
            return "malformed", f"'{heading}': '{NONE_PREFIX[heading]}' cannot be mixed with citations"
        return "none", bullets[0]
    bad = [b for b in bullets if not WIKILINK_BULLET.match(b)]
    if bad:
        return "malformed", f"'{heading}': not a '[[note]] -- relevance' citation: {bad[0][:80]}"
    return "cited", f"{len(bullets)} citation(s)"


def _changed_files(base):
    res = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                         capture_output=True, text=True, cwd=str(REPO_ROOT))
    if res.returncode != 0:
        return None
    return set(res.stdout.split())


def check_receipts(n, sq_dir=None, diff_base=None, changed_files=None):
    """The 9.4 gate. Returns a verdict dict; ``verdict`` is ``pass``,
    ``pass-with-note`` (engine was unavailable -- 9.9) or ``fail``."""
    sq_dir = Path(sq_dir) if sq_dir else SQ_DIR
    lineage = resolve_lineage(n, sq_dir)
    if lineage is None:
        return {"verdict": "fail", "issue": n, "lineage": None,
                "problems": [f"no lineage file for #{n} (CONTEXT-{n}.md, {n}-body.md or {n}-fix-plan.md)"]}
    text = (sq_dir.parent / lineage["path"]).read_text(encoding="utf-8")
    sections, problems, notes = {}, [], []
    for heading in RECEIPT_SECTIONS:
        status, detail = check_section(text, heading)
        sections[heading] = {"status": status, "detail": detail}
        if status in ("missing", "empty", "malformed"):
            problems.append(detail)
        elif status == "unavailable":
            notes.append(f"{heading}: {detail}")
    if diff_base is not None:
        files = changed_files if changed_files is not None else _changed_files(diff_base)
        if files is None:
            problems.append(f"could not diff against {diff_base}")
        elif lineage["path"] not in files:
            problems.append(f"lineage file {lineage['path']} is not in the PR diff vs {diff_base}")
    verdict = "fail" if problems else ("pass-with-note" if notes else "pass")
    return {"verdict": verdict, "issue": n, "lineage": lineage, "sections": sections,
            "problems": problems, "notes": notes}


# ---- engine wrapper ------------------------------------------------------------

def instance_id(path=None):
    p = Path(path) if path else INSTANCE_ID_FILE
    try:
        v = p.read_text(encoding="utf-8").strip()
        return v or UNPROVISIONED
    except OSError:
        return UNPROVISIONED


def engine_script(name):
    for d in ENGINE_DIRS:
        p = d / name
        if p.is_file():
            return p
    return None


def run_engine(script_name, args, runner=subprocess.run):
    """Run an engine script. Returns (payload_dict, None) or (None, reason) --
    the reason is what the caller's honest 'Engine unavailable:' line states."""
    node = shutil.which("node")
    if node is None:
        return None, "node not installed"
    script = engine_script(script_name)
    if script is None:
        return None, f"engine script {script_name} not installed"
    try:
        proc = runner([node, str(script), *args], capture_output=True, text=True,
                      cwd=str(REPO_ROOT), timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"engine failed to run: {e}"
    if proc.returncode != 0:
        return None, f"engine exited {proc.returncode}: {(proc.stderr or '').strip()[:200]}"
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as e:
        return None, f"engine output unparseable: {e}"


def identity_args(alias, task=None):
    out = ["--instance-id", instance_id(), "--alias", alias]
    if task is not None:
        out += ["--task", str(task)]
    return out


def search(alias, task=None, entities=(), tags=(), terms=(), types=(), top=None,
           write=True, vault=None, runner=subprocess.run):
    args = identity_args(alias, task) + ["--vault", str(vault or VAULT_DIR)]
    for flag, vals in (("--entities", entities), ("--tags", tags),
                       ("--terms", terms), ("--types", types)):
        if vals:
            args += [flag, ",".join(vals)]
    if top is not None:
        args += ["--top", str(top)]
    if not write:
        args.append("--no-write")
    return run_engine("vault-query.mjs", args, runner)


def cite(alias, task, slugs, vault=None, runner=subprocess.run):
    """Record `used` events (6.1 -- consumers only) for notes cited in a receipt."""
    args = identity_args(alias, task) + ["--vault", str(vault or VAULT_DIR),
                                         "--slugs", ",".join(slugs)]
    return run_engine("record-consumption.mjs", args, runner)


# ---- CLI -----------------------------------------------------------------------

def _csv(values):
    out = []
    for v in values or []:
        out += [t.strip() for t in v.split(",") if t.strip()]
    return out


def _parser():
    p = argparse.ArgumentParser(prog="vault_consume.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("lineage-path")
    s.add_argument("n", type=int)
    s = sub.add_parser("init-fix-plan")
    s.add_argument("n", type=int)
    s.add_argument("--role", required=True)
    s = sub.add_parser("check-receipts")
    s.add_argument("n", type=int)
    s.add_argument("--diff-base")
    s = sub.add_parser("search")
    s.add_argument("--alias", required=True)
    s.add_argument("--task", type=int)
    for f in ("--entities", "--tags", "--terms", "--types"):
        s.add_argument(f, action="append")
    s.add_argument("--top", type=int)
    s.add_argument("--no-write", action="store_true")
    s = sub.add_parser("cite")
    s.add_argument("--alias", required=True)
    s.add_argument("--task", type=int, required=True)
    s.add_argument("--slugs", required=True)
    return p


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.cmd == "lineage-path":
        res = resolve_lineage(args.n)
        print(json.dumps(res or {"path": None, "kind": None, "exists": False}))
        return 0
    if args.cmd == "init-fix-plan":
        print(json.dumps(init_fix_plan(args.n, args.role)))
        return 0
    if args.cmd == "check-receipts":
        res = check_receipts(args.n, diff_base=args.diff_base)
        print(json.dumps(res, indent=2))
        return 1 if res["verdict"] == "fail" else 0
    if args.cmd == "search":
        entities, tags, terms = _csv(args.entities), _csv(args.tags), _csv(args.terms)
        if not (entities or tags or terms):
            print("error: at least one of --entities/--tags/--terms is required", file=sys.stderr)
            return 2
        payload, reason = search(args.alias, args.task, entities, tags, terms,
                                 _csv(args.types), args.top, write=not args.no_write)
    else:  # cite
        slugs = _csv([args.slugs])
        if not slugs:
            print("error: --slugs is empty", file=sys.stderr)
            return 2
        payload, reason = cite(args.alias, args.task, slugs)
    if payload is None:
        print(json.dumps({"engine_unavailable": True, "reason": reason}))
        return 3
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
