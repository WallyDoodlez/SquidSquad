# TEST-PLAN-9588 — Lazy-Load Mode-Specific Instructions at Boot

**Source**: GitHub issue #9588 Acceptance Criteria + `.squidsquad/pm/planning/CONTEXT-9588.md` (D1–D7).
**Derived without reading the diff.** ACs verified against the live install (composed CLAUDE.md on disk, source fragments on disk, manifests on disk, config.md, harness probe).

## AC list (from #9588 body)

- **AC-1**: `compose.py` no longer inlines mode-specific fragments. Bootstrap is the only mode-relevant content in composed CLAUDE.md.
- **AC-2**: Polling-mode agents Read `ralph-loop-overview.md` on boot via the bootstrap.
- **AC-3**: Event-mode agents: harness reachable → Read event fragments; unreachable → Read polling fragment.
- **AC-4**: Mode flip (config.md change) takes effect on next agent cycle boundary without recompose.
- **AC-5**: Composed CLAUDE.md size measurably smaller — at least 30% reduction expected (per CONTEXT §5: event-mode roles; polling-mode roles accept small net increase per locked design).
- **AC-6**: Regression test added.
- **AC-7**: Existing polling agents continue cycling correctly. Existing event-mode tests (#9398) continue to pass once bootstrap lands.
- **AC-CQ (#9184)**: Fresh agent given only the modified files can correctly answer observable questions about new boot behavior.

## Test Cases

### TC-1 (covers AC-1): Composed CLAUDE.md contains zero mode-specific markers
- **Precondition**: Branch `squidsquad/task/9588` checked out. Each of `.squidsquad/{skill,pm,qa,dm}/CLAUDE.md` exists.
- **Steps**: Read each deployed CLAUDE.md. Search for inlined sub-skill markers: `ralph-loop-overview`, `event-driven-workflow`, `l1-base`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`, `pr-merge-wait`.
- **Expected**: None of these `<!-- sub-skill: X -->` wrappers appear in any deployed CLAUDE.md.
- **Verification command**: `grep -l "<!-- sub-skill: ralph-loop-overview -->" .squidsquad/*/CLAUDE.md`

### TC-2 (covers AC-1): Composed CLAUDE.md contains the boot-bootstrap wrapper
- **Precondition**: Same as TC-1.
- **Steps**: Read each deployed CLAUDE.md, assert presence of `<!-- sub-skill: boot-bootstrap -->` and `## Boot — Mode Detection (#9588)`.
- **Expected**: Both substrings present in all 4 deployed files.
- **Verification command**: `grep -c "## Boot — Mode Detection (#9588)" .squidsquad/*/CLAUDE.md`

### TC-3 (covers AC-2): Bootstrap routes polling-mode agents to per-role ralph-loop-overview
- **Precondition**: Composed CLAUDE.md for each role.
- **Steps**: Inside the boot-bootstrap block, find the substituted polling-fragment path. Verify it equals `references/sub-skills/roles/{entry}/ralph-loop-overview.md` where entry is `dev` for `skill`, else the role name. Verify each named path exists on disk.
- **Expected**: skill → `roles/dev/...`; pm, qa, dm → `roles/{role}/...`. Files exist. No raw `[POLLING_FRAGMENT_PATH]` leakage.
- **Verification command**: `python -c "import pathlib,re; [print(p) for p in pathlib.Path('.squidsquad').glob('*/CLAUDE.md')]"` + path-exists checks.

### TC-4 (covers AC-3): Bootstrap names all 6 event-mode fragments + DM's pr-merge-wait
- **Precondition**: Composed CLAUDE.md.
- **Steps**: Inside the boot-bootstrap block, search for the 6 `references/sub-skills/common-events/*.md` paths and (for DM only) `roles/dm/events/pr-merge-wait.md`. Confirm each named source fragment exists on disk.
- **Expected**: All 6 event fragments are referenced in every role's bootstrap. `pr-merge-wait.md` referenced only in DM's. All referenced files exist.
- **Verification command**: grep + filesystem check.

### TC-5 (covers AC-3 fallback contract): Bootstrap fallback uses curl exit code only (no /dev/null)
- **Precondition**: Source `references/sub-skills/common/boot-bootstrap.md`.
- **Steps**: Read the bootstrap source. Confirm the harness-probe instruction uses `curl -sf --max-time 5 http://127.0.0.1:<port>/status` and explicitly tells the agent to inspect exit code only (no shell redirect to `/dev/null`).
- **Expected**: Probe wording uses `127.0.0.1` (not `localhost`), invokes `/status`, 5s timeout, and warns against `> /dev/null` for Windows compatibility.
- **Verification command**: Read bootstrap source, assert substrings.

### TC-6 (covers AC-3 fallback contract): l1-base.md degraded branch removed
- **Precondition**: Source `references/sub-skills/common-events/l1-base.md`.
- **Steps**: Confirm the old "proceed to degraded-mode operation" wording and `### Degraded-Mode Glossary` section are gone.
- **Expected**: Both strings absent.
- **Verification command**: grep on the file.

### TC-7 (covers AC-4): Recompose is not required to flip mode
- **Precondition**: Branch checked out, current `event-driven: no`.
- **Steps**: Verify the bootstrap text in the composed CLAUDE.md instructs the agent to **Read `.squidsquad/config.md` at runtime** (not at compose time) to determine mode. Verify Step 1 of the bootstrap is "Read `.squidsquad/config.md` …" and "Loaded mode is sticky" mentions flips take effect on next agent restart, not mid-cycle.
- **Expected**: Both phrasings present in composed CLAUDE.md. No compose-time mode hardcoding observable in the bootstrap block.
- **Verification command**: grep on composed CLAUDE.md.

### TC-8 (covers AC-4 / BLOCKER fix): `/loop` is owned exclusively by the bootstrap with substituted interval
- **Precondition**: Composed CLAUDE.md; source `ralph-loop-overview.md` files.
- **Steps**: (a) Composed CLAUDE.md contains `/loop <N>m execute one Ralph Loop cycle` with a concrete integer N matching `config.md` interval (30). (b) Composed CLAUDE.md does NOT contain the literal `[INTERVAL]` placeholder. (c) Source `ralph-loop-overview.md` files do NOT contain `/loop ` or `[INTERVAL]`.
- **Expected**: All three pass for all 4 roles.
- **Verification command**: grep + regex on composed and source files.

### TC-9 (covers AC-5): Composed size delta vs main
- **Precondition**: Branch `squidsquad/task/9588` checked out, `main` reachable via `git show`.
- **Steps**: Compute line counts of each composed `.squidsquad/{role}/CLAUDE.md` on branch vs main. Report deltas. Verify polling-mode delta is small (within ±100 lines) per CONTEXT-9588 §5's locked acceptance ("5–10% for polling roles"). Event-mode reduction (≥30%) is locked-but-deferred: it kicks in only when `event-driven: yes` and is verified structurally via TC-4 (bootstrap names 6 fragments not inlined).
- **Expected**: Each role's polling-mode CLAUDE.md is within tolerance vs main. Structural absence of the 6 event fragments establishes the locked event-mode reduction without requiring a runtime flip.
- **Verification command**: `wc -l` + comparison.

### TC-10 (covers AC-6): Regression test exists and runs green
- **Precondition**: `tests/test_compose_9588.py` exists.
- **Steps**: Run `python -m pytest tests/test_compose_9588.py -v`.
- **Expected**: All tests pass (currently 55).
- **Verification command**: pytest exit 0.

### TC-11 (covers AC-7): Existing test suite remains green
- **Precondition**: `tests/run_tests.py` exists.
- **Steps**: Run `python tests/run_tests.py`. Compare failures vs the documented pre-existing #9724 baseline.
- **Expected**: No new failures introduced by #9588. The 4 #9724 baseline failures (test_run_comprehension*) remain the only failures.
- **Verification command**: pytest output exit code + failure parse.

### TC-12 (covers AC-7): Bootstrap teaches runtime placeholder substitution
- **Precondition**: Composed CLAUDE.md for each role.
- **Steps**: Verify the "Placeholder substitution inside runtime-loaded fragments" section exists in every composed CLAUDE.md and explicitly tells the agent how to substitute the role-name placeholder it will encounter in the polling fragment at runtime (cites `SQUIDSQUAD_ROLE`).
- **Expected**: Section header + `SQUIDSQUAD_ROLE` mention present in all 4 composed files.
- **Verification command**: grep on composed CLAUDE.md.

### TC-13 (covers AC-3 event-mode wiring): Manifests no longer list mode-specific runtime-Read entries
- **Precondition**: All 8 manifest files (`includes.yml`, `includes-events.yml`) for the 4 roles.
- **Steps**: Confirm `common/boot-bootstrap` is the first include in every manifest. Confirm none of the manifests list `roles/<role>/ralph-loop-overview`, any `common-events/*`, or `roles/dm/events/pr-merge-wait`.
- **Expected**: Bootstrap first; mode-specific entries absent from manifests.
- **Verification command**: YAML parse + assertions.

### TC-14 (covers AC-3 fallback safety): RUNTIME_READ_FRAGMENTS frozenset defends against variant-resolution resurrection
- **Precondition**: `references/scripts/compose.py`.
- **Steps**: Confirm `RUNTIME_READ_FRAGMENTS` frozenset contains all 12 runtime-Read fragments (4 ralph-loop-overview + 6 common-events + 1 dm/pr-merge-wait + 1 event-driven-workflow). Confirm `_resolve_includes_with_manifest` short-circuits on this set before the variant heuristic runs.
- **Expected**: Frozenset present with correct entries; short-circuit precedes variant heuristic.
- **Verification command**: AST/regex inspection of compose.py.

## Coverage matrix

- AC-1 → TC-1, TC-2, TC-13
- AC-2 → TC-3, TC-12
- AC-3 → TC-4, TC-5, TC-6, TC-13, TC-14
- AC-4 → TC-7, TC-8
- AC-5 → TC-9
- AC-6 → TC-10
- AC-7 → TC-11, TC-12
- AC-CQ → handled in `## Comprehension Questions` below

Every AC has at least one TC.

## Comprehension Questions

This task modifies LLM-consumed instructions (every role's `CLAUDE.md` + the new `common/boot-bootstrap.md` fragment). The CQ verifies a fresh agent given only the modified files can correctly describe the new boot behavior from the files alone.

### CQ-1: Boot-step ordering
- **Files**: `references/sub-skills/common/boot-bootstrap.md`
- **Expected answer**: On a fresh session start, the agent runs four steps in order: (1) Read `.squidsquad/config.md` to determine wake mode, (2) probe harness reachability (event-mode candidate only) via `curl -sf --max-time 5 http://127.0.0.1:<port>/status`, (3) on event-mode confirmed Read the 6 event fragments (+ pr-merge-wait if role is dm), (4) on polling-mode confirmed run `tracker.py check-gh`, schedule `/loop` exactly once, then Read the per-role `ralph-loop-overview.md`.

### CQ-2: Harness-unreachable fallback
- **Files**: `references/sub-skills/common/boot-bootstrap.md`
- **Expected answer**: When the harness is unreachable for ANY reason (curl error, connection refused, timeout, HTTP non-2xx, curl missing from PATH, port file missing or unreadable, config file missing), the agent falls through to polling mode and Reads the `ralph-loop-overview.md` fragment.

### CQ-3: `/loop` invocation location
- **Files**: `references/sub-skills/common/boot-bootstrap.md`, `references/sub-skills/roles/dev/ralph-loop-overview.md`
- **Expected answer**: `/loop` is invoked exclusively from the bootstrap's Step 4b, NOT from the polling fragment. The polling fragment describes what each cycle DOES; the bootstrap describes how to schedule one. Re-invoking `/loop` from inside the polling fragment would stack cron entries.

### CQ-4: Sticky mode contract
- **Files**: `references/sub-skills/common/boot-bootstrap.md`
- **Expected answer**: Once the agent has completed Step 3 (event mode) or Step 4 (polling mode), the wake-mode contract is fixed for the session. Mid-session config changes do NOT trigger a re-check. Mode flips take effect on the next agent restart.

CQ spec also persisted at `tests/comprehension/9588_spec.json` for the comprehension runner.

## Live verification

Live-system pytest at `.squidsquad/qa/planning/TEST-9588-tests.py` exercises TC-1…TC-14 against the actual repo state (filesystem reads, grep, YAML parse, pytest invocation). Comprehension run is logged in `QA-RESULTS-9588.md` under `## Comprehension Tests`.
