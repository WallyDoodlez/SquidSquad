# QA-RESULTS-9588 — Lazy-Load Mode-Specific Instructions at Boot

**Issue**: #9588
**PR**: #9726
**Branch**: squidsquad/task/9588
**Verified by**: qa-lead
**Date**: 2026-05-20
**Verdict**: **PASS** (with one documented gap on AC-5 — human-approved override; see §3)

## 1. Live-system pytest

Run: `python -m pytest .squidsquad/qa/planning/TEST-9588-tests.py -q`

```
75 passed in 5.24s
```

All 75 test cases (TC-1 … TC-14 + parametrizations) PASS against the deployed state of the repo (composed `.squidsquad/<role>/CLAUDE.md` files, source fragments, manifests, config.md, compose.py).

### TC summary table

| TC | Covers | Result | Evidence |
|----|--------|--------|----------|
| TC-1 | AC-1 | PASS (32/32) | No mode-specific `<!-- sub-skill: X -->` markers in any deployed CLAUDE.md |
| TC-2 | AC-1 | PASS (4/4) | `<!-- sub-skill: boot-bootstrap -->` + `## Boot — Mode Detection (#9588)` in all 4 |
| TC-3 | AC-2 | PASS (4/4) | `[POLLING_FRAGMENT_PATH]` substituted per-role; dev variant resolves to `roles/dev/...` |
| TC-4 | AC-3 | PASS (5/5) | All 6 common-events fragments referenced; dm/pr-merge-wait only in DM |
| TC-5 | AC-3 | PASS | curl probe uses `127.0.0.1` + `--max-time 5` + `/status`; no `> /dev/null` |
| TC-6 | AC-3 | PASS | l1-base.md degraded-mode block + Degraded-Mode Glossary removed |
| TC-7 | AC-4 | PASS (4/4) | Bootstrap text instructs runtime Read of `.squidsquad/config.md`; "Loaded mode is sticky" + "next agent restart" present |
| TC-8 | AC-4 | PASS (8/8) | `/loop 30m execute one Ralph Loop cycle` substituted; `[INTERVAL]` absent; source fragments have no `/loop` |
| TC-9 | AC-5 | PASS (structural) | Polling-mode delta vs main within locked tolerance — see §3 for the AC-5 gap discussion |
| TC-10 | AC-6 | PASS | `tests/test_compose_9588.py` 55/55 green |
| TC-11 | AC-7 | PASS | Changed-area suites (`test_compose`, `test_compose_9588`, `test_manifest`, `test_event_mode_fragments`) all green |
| TC-12 | AC-7 | PASS (4/4) | Placeholder-substitution teaching + `SQUIDSQUAD_ROLE` cite present in all composed CLAUDE.md |
| TC-13 | AC-1, AC-3 | PASS (8/8) | All 8 manifests put `common/boot-bootstrap` first; no manifest re-inlines a runtime-Read fragment |
| TC-14 | AC-3 | PASS | `RUNTIME_READ_FRAGMENTS` frozenset present with all 12 entries; short-circuits before the variant heuristic |

## 2. Comprehension Tests (CQ — #9184)

Task touches LLM-consumed instructions (every role's `CLAUDE.md` + new `common/boot-bootstrap.md`). Spawned a fresh sonnet agent with only the 2 modified files (`boot-bootstrap.md` + dev's `ralph-loop-overview.md`) and zero codebase context.

| CQ | Topic | Result | Notes |
|----|-------|--------|-------|
| CQ-1 | Boot-step ordering + which step decides mode | PASS | Agent listed all 4 steps in order; correctly named Steps 1+2 as the joint decision point with quoted evidence |
| CQ-2 | Why probe avoids `> /dev/null` | PASS | Identified Windows-shell incompatibility + permanent-polling-fallback consequence with direct quote |
| CQ-3 | Polling-fallback circumstances | PASS | Enumerated all 4 paths (config missing/unreadable/unparseable, event-driven not yes, probe fails for any reason) with quotes |
| CQ-4 | `/loop` ownership | PASS | Identified bootstrap as sole scheduler; cited the cron-stacking + runtime-Read-can't-substitute-INTERVAL reasoning |
| CQ-5 | Sticky-mode contract + when flip takes effect | PASS | Quoted "Once Steps 3 or 4 complete, your wake-mode contract is fixed for this session" + "next agent restart" |

**5/5 CQ PASS.** A fresh agent can correctly describe the new boot behavior from the modified files alone.

## 3. AC walk (against #9588 issue body)

| AC | Verdict | Evidence |
|----|---------|----------|
| AC-1 (no inline of mode-specific fragments) | PASS | TC-1, TC-2, TC-13 |
| AC-2 (polling-mode agents Read ralph-loop-overview via bootstrap) | PASS | TC-3, TC-12 |
| AC-3 (event-mode reachable→event fragments, unreachable→polling fragment) | PASS | TC-4, TC-5, TC-6, TC-13, TC-14 |
| AC-4 (mode flip takes effect on next agent cycle boundary without recompose) | PASS | TC-7, TC-8. Bootstrap reads config.md at runtime; mode-uniform composed CLAUDE.md confirmed structurally by re-running compose under both wake modes (1492 lines polling vs 1383 lines events — same bootstrap, same absence of mode-specific markers) |
| AC-5 (composed CLAUDE.md size measurably smaller — at least 30% reduction expected) | **PARTIAL — human-approved override** | See §3.1 |
| AC-6 (regression test added) | PASS | `tests/test_compose_9588.py` 55/55 + new regression contract documented in test docstring |
| AC-7 (existing polling agents continue cycling correctly; existing event-mode tests pass) | PASS | TC-11; PR self-reports 219/219 pre-existing tests still green; 4 unrelated `test_run_comprehension*` failures are pre-existing #9724 baseline |
| AC-CQ (#9184 implicit) | PASS | §2 above — 5/5 CQ PASS |

### 3.1 AC-5 gap — documented override

**Issue body AC-5 text**: "Composed CLAUDE.md size measurably smaller — at least 30% reduction expected by moving the larger of the two fragment sets out."

**Measured**:
- Polling-mode skill compose: 1492 lines (was 1441 on main → +51 lines, ~+3.5% INCREASE)
- Event-mode skill compose (forced via monkey-patch): 1383 lines (vs polling 1492 → -109 lines, ~-7% reduction)
- Lines that would have been inlined under the old design but are now runtime-Read: 6 common-events fragments × ~46 lines avg = ~275 lines; bootstrap adds 93 lines; net structural saving in event-mode ~182 lines (~11% of an old event-mode compose)
- PR body self-reports ~22% for event-mode roles "per #9588 estimate, kicks in when `event-driven: yes`"

The strict 30% threshold is not met. The actual saving is 7-22% depending on measurement methodology, and polling mode incurs a small net increase (accepted per CONTEXT-9588 §5 locked design).

**Human override (inline session, 2026-05-20)**: Wallace selected "Met-in-spirit, ship" with the reasoning that:
1. CONTEXT-9588 §5 labels the 30% number as a RESEARCH-derived estimate (`per RESEARCH-9588.md §3 estimates`), not a hard threshold.
2. The structural goal — mode-specific content out of compose-time inlining, lazy-load architecture, mode-uniform composed CLAUDE.md — is fully achieved.
3. Polling mode's small net increase is explicitly locked-and-accepted in CONTEXT-9588 §5.
4. PR body honestly self-reports the actual delta; no hidden divergence.

This override is also logged on the GitHub Issue and the PR for audit.

## 4. Setup & Upgrade Sync Check

- New config values: N/A
- New files/directories: N/A — new sub-skill fragment lives under existing `references/sub-skills/common/`
- Modified template structure: YES — `compose.py:RUNTIME_READ_FRAGMENTS` short-circuit + `[POLLING_FRAGMENT_PATH]` substitution. Existing recompose flow (`compose.py deploy <role>`) handles it; no upgrade-flow changes needed.
- Added/removed sub-skills: YES — `common/boot-bootstrap` added to all 8 manifests; `common-events/*` and `roles/<role>/ralph-loop-overview` and `roles/dm/events/pr-merge-wait` removed from manifests. Manifests updated in this PR.
- Changed role composition: N/A — manifest-level only, no new roles.
- Upgrade path documented? YES — CONTEXT-9588 D5 locks hard cutover; agents pick up new CLAUDE.md on next session start (cycle restart or context-pressure respawn). No bespoke migration.

## 5. Decision

**Verdict**: PASS with human-approved AC-5 override.

- Promote `TEST-9588-tests.py` → `tests/test_feat_9588_lazy_load_bootstrap.py`
- Comprehension spec `tests/comprehension/9588_spec.json` stays in place (canonical location)
- Approve PR #9726
- Auto-merge per project config (auto-merge: yes, no `review:human-required` label)
- Transition #9588 pending-test → pending-ship
- Increment `Shipped Since Last Bump`
