#!/usr/bin/env python3
"""#13575 — comprehension-spec staleness baseline tooling.

``tests/comprehension/*_spec.json`` are permanent PASS-stamped records of a
fresh-agent comprehension check against LLM-consumed fragments *at authoring
time*. A later commit to a named fragment can silently overrule a spec's
recorded expectations (live case: #13569's Case E defer fix overruled
``13175_spec.json``'s honor-on-reach answer).

Model: a checked-in baseline (``tests/comprehension/.staleness-baseline.json``)
maps each spec to the git blob sha of every fragment it names, as of the last
review of that pair. The static gate (``tests/test_comprehension_spec_
staleness_13575.py``) fails when a fragment's committed blob sha drifts from
the baseline — meaning the fragment changed and nobody re-reviewed the specs
that depend on it. Remediation, in the SAME PR that changes the fragment:

- spec still valid  -> re-review, then ``python references/scripts/
  comprehension_staleness.py refresh <spec-name>...`` (or ``--all``) and commit
  the regenerated baseline entries.
- spec overruled    -> add ``"superseded_by": <issue>`` to the spec JSON (the
  gate then ignores it permanently; the spec stays as historical record).

Specs absent from the baseline fail the gate too — a new spec enters via
``refresh`` so the pairing is always a conscious act, never an implicit pass.

Usage:
    python references/scripts/comprehension_staleness.py check
    python references/scripts/comprehension_staleness.py refresh <spec>... | --all
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_DIR = REPO_ROOT / "tests" / "comprehension"
BASELINE = SPEC_DIR / ".staleness-baseline.json"

_PATH_RE = re.compile(
    r"(?:references|docs|\.squidsquad|tests)/[\w\-./{},]*\.(?:md|py|txt|json|yml|ps1|sh)")


def _expand_braces(path):
    """Full {a,b}-set expansion — loops until no group remains (cartesian for
    multiple groups) and strips whitespace in alternatives, so '{a, b}' or a
    two-group token can never silently drop a fragment from coverage."""
    out = [path]
    while True:
        nxt = []
        changed = False
        for p in out:
            m = re.search(r"\{([^{}]+)\}", p)
            if not m:
                nxt.append(p)
                continue
            changed = True
            nxt.extend(p[:m.start()] + alt.strip() + p[m.end():]
                       for alt in m.group(1).split(","))
        out = nxt
        if not changed:
            return out


def spec_fragment_paths(spec):
    """Existing-in-tree fragment paths a spec names (files/target/source_file)."""
    hay = []
    for key in ("files", "target", "source_file"):
        v = spec.get(key)
        if isinstance(v, list):
            hay.extend(str(x) for x in v)
        elif v:
            hay.append(str(v))
    out = []
    for token in _PATH_RE.findall(" ".join(hay)) if hay else []:
        for p in _expand_braces(token):
            p = p.rstrip(".,;:")
            if (REPO_ROOT / p).is_file() and p not in out:
                out.append(p)
    return out


def committed_blob_sha(rel_path):
    """Blob sha of the path at HEAD; None if untracked OR git is unavailable/
    hung. Bounded + exception-guarded per the repo's git-subprocess convention
    (#9890/#13262 class): this runs inside the fleet-wide static gate, so a
    single wedged git call must degrade to 'skip this fragment', never hang or
    crash every agent's gate."""
    try:
        res = subprocess.run(["git", "rev-parse", f"HEAD:{rel_path}"],
                             capture_output=True, text=True,
                             cwd=str(REPO_ROOT), timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    out = (res.stdout or "").strip()
    return out if res.returncode == 0 and len(out) == 40 else None


def load_specs():
    """{spec_name: parsed_json} for every parseable spec."""
    out = {}
    for p in sorted(SPEC_DIR.glob("*_spec.json")):
        try:
            out[p.name] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def load_baseline():
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def check():
    """Returns a list of human-readable violations (empty = clean)."""
    baseline = load_baseline()
    violations = []
    for name, spec in load_specs().items():
        if "superseded_by" in spec:
            continue
        frags = spec_fragment_paths(spec)
        if not frags:
            continue  # nothing checkable named
        entry = baseline.get(name)
        if entry is None:
            violations.append(
                f"{name}: not in baseline — run comprehension_staleness.py "
                f"refresh {name}")
            continue
        for frag in frags:
            live = committed_blob_sha(frag)
            if live is None:
                continue  # untracked fragment — not a committed-record drift
            if entry.get(frag) != live:
                violations.append(
                    f"{name} <- {frag} changed since last review "
                    f"(baseline {str(entry.get(frag))[:9]} != HEAD {live[:9]})")
    return violations


def refresh(names):
    """Regenerate baseline entries for the named specs (or all)."""
    baseline = load_baseline()
    specs = load_specs()
    live_names = set(specs)
    # Prune baseline entries for deleted specs — deliberately unconditional
    # (fires on scoped refreshes too): specs live in one flat directory that is
    # always fully present in a normal checkout, and a stale entry for a
    # deleted spec is pure noise. Keys starting with '_' (e.g. _note) are
    # metadata and always survive.
    for gone in [k for k in baseline if not k.startswith("_") and k not in live_names]:
        del baseline[gone]
    for name in names:
        if name not in specs:
            print(f"WARNING: no such spec {name}", file=sys.stderr)
            continue
        entry = {}
        for frag in spec_fragment_paths(specs[name]):
            sha = committed_blob_sha(frag)
            if sha:
                entry[frag] = sha
        baseline[name] = entry
    tmp = BASELINE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(baseline, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(BASELINE)
    print(f"baseline refreshed for {len(names)} spec(s) -> {BASELINE.name}")


def main():
    args = sys.argv[1:]
    if not args or args[0] == "check":
        v = check()
        for line in v:
            print(line)
        sys.exit(1 if v else 0)
    if args[0] == "refresh":
        rest = args[1:]
        if rest == ["--all"]:
            rest = sorted(load_specs())
        if not rest:
            print("Usage: comprehension_staleness.py refresh <spec>... | --all",
                  file=sys.stderr)
            sys.exit(2)
        refresh(rest)
        sys.exit(0)
    print(__doc__, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
