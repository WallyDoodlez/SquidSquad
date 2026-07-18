# QA-RESULTS-12527

## Summary
REJECTED — back to in-progress. Not a nitpick: skill's own load-bearing positive claim ("compose engine is foreign-repo-safe, zero self-references") is falsified by a decisive, independently-traced finding. AC1/AC2 mechanics and 2 of 3 filed bugs (#13592, #13593) are accurate and stand; #13594's stated root cause is factually wrong, and the REAL underlying defect is more severe than what it describes.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS (mechanically) | "Blocked at gh/label/commit+harness-boot" is a real, code-confirmed limitation (FG-2 verified: `_run(["gh","repo","view"...])` and `ensure_labels()` never thread `target_dir` into `cwd=`) |
| AC2 | PASS (doc exists) — content needs revision | `.squidsquad/skill/planning/FINDINGS-12527.md` committed on main |
| AC3 | PARTIAL | #13592 (FG-1) accurate — verified against `generate_default_spec` code directly. #13593 (FG-2) accurate — verified against `_run`/`ensure_labels` call sites. **#13594 (FG-3) is INACCURATE** — see below. |
| AC4 | FAIL (positive claim falsified) | See below |

## Decisive finding — #13594 misdiagnosed; real defect is broader (filed as #13595, high)

Reproduced #13594's claim directly: `wizard.build_config_md(spec)` generates config.md text containing NEITHER `Dev Agents` NOR `Workers` as a literal string (confirmed by printing the full generated text — it uses the v2 `## Agents` schema exclusively). The claimed root cause ("scaffolded config.md uses deprecated field... build_config_md — the worker/agents section that writes Dev Agents:") does not match the code.

The warning skill observed IS real (reproduced: fires twice during a live `scaffold_install` run) — but traced to a different, more severe cause via a monkeypatched `config.get_field` stack trace:

```
scaffold_install -> compose.deploy_role_v2(target_root=<foreign>) -> _substitute_placeholders
  -> _read_config_value('workers') -> config.get_field('workers') -> config.CONFIG_PATH
```

`config.CONFIG_PATH = REPO_ROOT / '.squidsquad' / 'config.md'`, and `REPO_ROOT = SCRIPT_DIR.parent.parent` — computed ONCE at `config.py` import time, relative to wherever `config.py` itself lives on disk (the **installing clone's own repo root**). It never honors `target_root`. So every `_read_config_value()` call inside `_substitute_placeholders` during a foreign `deploy_role_v2` compose reads the **installing clone's own config.md**, not the target's freshly-scaffolded one. The leaked value in this run was my own qa clone's literal `Dev Agents: skill` line — which is what triggered the dual-aware deprecation-warning fallback in `config.get_field`. The warning is a *symptom* of the leak, not evidence of what the scaffolder writes.

**Scope**: `_substitute_placeholders` calls `_read_config_value()` for at least `workers` (×3 call sites), `{role}-tests`, `interval`, `alias-pm`/`alias-qa`/`alias-dm`, `e2e-tests`, `agent-compose`, `project-name` — all subject to the identical leak.

**Why the "zero self-references" positive check missed this**: that check searched composed output for literal path/repo/clone-name strings and correctly found none. This is a *data* leak (a config field's value), not a *string* leak — it's invisible to a literal-string diff whenever the leaked value happens to coincide with what the target's own default would have produced. In this run, the leaked `workers` value ("skill") coincidentally matches the target spec's own hardcoded worker id (see #13592/FG-1: the default spec always names the worker "skill" regardless of stack) — masking the leak. A differently-configured installing clone (multiple workers, real project name, populated aliases) would silently stamp its own identity into a stranger's foreign install with no warning at all for most of those fields (the deprecation-warning is a coincidental tripwire specific to the `workers`/`Dev Agents` dual-aware shim; the other 7+ leaked fields have no equivalent warning).

Filed **#13595** (high) with full evidence and location. Commented on **#13594** with the correction (did not edit the issue body — not verifier's lane; recommended skill close/retitle it as superseded_by:13595).

## Zero-gap check
FAILS. AC4's positive verdict ("free of source-clone leakage") is the task's central deliverable and is now shown incomplete by a decisive, independently-traced counter-example. This is not a minor/cosmetic gap — it's exactly the class of defect #12527 exists to surface, just in a form the original check didn't cover.

## What's needed to re-pass (narrow, does not require fixing #13595 itself)
1. Correct `FINDINGS-12527.md`'s verdict to accurately state the compose-engine leak (reference #13595) rather than claiming "free of source-clone leakage."
2. Resolve #13594's mis-diagnosis (close as superseded_by:13595, retitle, or otherwise correct — skill's call).
3. Re-submit. Fixing #13595 itself is a separate, larger engineering task and not required to close #12527 — the task's own scope is "capture breakage, file bugs," which #13595 already satisfies once the findings doc and #13594 are corrected to match.

## Verdict
FAIL. Back to In Progress with the above narrow, concrete fix list.
