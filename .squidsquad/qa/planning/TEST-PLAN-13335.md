# TEST-PLAN-13335 — Context-threshold not enforced in event mode (default runtime)

**Source**: GitHub issue #13335 body (Behavior / Evidence / Impact / Notes for research). Operator-filed, severity:high, type:issue (auto-approved).
**Derived without reading the PR #13346 diff.** ACs are derived from the issue body's *expected behavior* statements (bugs carry no formal AC section).

## Derived Acceptance Criteria

- **AC1 — Enforcement actor exists in event mode.** When an event-mode agent's context pressure reaches/exceeds `context-threshold` (config.md, default 70), *something real* initiates the clean checkpoint-and-respawn path. (Issue: "Expected: at ~70% the agent checkpoints working-state.md and the harness respawns it with fresh context.")
- **AC2 — Threshold sourced from config.** The enforcement threshold comes from config.md `## Context Pressure / Threshold`, defaulting to 70 when absent.
- **AC3 — Documentation defect corrected.** `references/sub-skills/common-events/event-mode-contract.md` (the L119 claim) must describe the *actual implemented* mechanism, not a fictional one. `references/sub-skills/common/context-pressure.md` must distinguish the loop-mode (cycle_post exit-42) path from the event-mode actor.
- **AC4 — Regression test exists** (bug-fix standard): a test that would have caught the original bug — i.e., pins that the event-mode actor fires at/over threshold and NOT under it.
- **AC5 — Safe-enforcement guards** (derived from "Expected" + the harness's existing intent state machine): enforcement must not act on agents that cannot be respawned, must not re-trigger on already-stopping/restarting agents (would re-arm kill timers), must fail-open (never crash the enforcement host) on missing/unreadable/malformed pressure data, and must only act on agents actually running with boot complete.

## Test Cases

### TC-1 (covers AC1): enforcement actor is wired into a live event-mode code path
- **Precondition**: PR branch checked out.
- **Steps**: locate the enforcement actor in harness code; confirm it is *invoked* from a path that runs unconditionally in event mode (not cycle_pre/cycle_post, which event mode skips).
- **Expected**: actor exists and is called from a periodically-running harness loop.
- **Verification command**: grep + AST/read of `references/scripts/harness.py`.

### TC-2 (covers AC1): REAL execution — at/over threshold flips the restart intent
- **Precondition**: real temp filesystem with a clone dir containing `.squidsquad/<role>/context-pressure` = value ≥ threshold; agent state = running, bootup_complete=True, intent=running.
- **Steps**: execute the REAL enforcement function (no mocks of the system under test) against that state.
- **Expected**: intent flips to `restarting` (the existing graceful-restart machinery's trigger), state persisted; the respawn path downstream is the already-shipped intent state machine.
- **Verification command**: pytest TC in `.squidsquad/qa/planning/TEST-13335-tests.py` (real function, real files).

### TC-3 (covers AC2): threshold comes from config.md, default 70
- **Steps**: read threshold with no config section → expect 70; with `Threshold: 55` → enforcement fires at 55+ and not at 54.
- **Expected**: config-sourced, correct default.
- **Verification command**: pytest TC (real config read).

### TC-4 (covers AC1 boundary): pressure == threshold triggers
- **Expected**: `>=` semantics ("at ~70%" per issue body) — 70 with threshold 70 → fires.

### TC-5 (covers AC1 negative): pressure below threshold does NOT trigger
- **Expected**: 69 with threshold 70 → intent stays `running`.

### TC-6 (covers AC5): guards
- 6a: agent already `restarting`/`stopping` → no re-trigger (no intent_set_at re-arm).
- 6b: non-respawnable agent (no-auto-reboot class) → skipped.
- 6c: bootup_complete=False or status≠running → skipped.
- 6d: missing / malformed / unreadable `context-pressure` file → no exception escapes, no flip (fail-open).
- **Verification command**: pytest TCs (real function, real files).

### TC-7 (covers AC3): documentation matches reality
- **Steps**: read `event-mode-contract.md` context-pressure rule and `context-pressure.md`; cross-check every mechanism claim against the shipped code (TC-1/TC-2 findings).
- **Expected**: event-mode contract names the real actor (harness-side, event mode); no claim of per-event cycle_post wrappers doing pressure checks in event mode; context-pressure.md separates loop-mode exit-42 from the event-mode actor.
- **Verification command**: Read + grep; comprehension test (CQ section below) is the stronger gate.

### TC-8 (covers AC4): regression test exists and is green
- **Steps**: locate worker's test file for #13335 under `tests/`; confirm it pins threshold-fire + no-fire-under-threshold; run it.
- **Expected**: exists, green, would have caught the original bug (original bug = NO actor: a suite asserting the actor fires necessarily fails on pre-fix code).
- **Verification command**: `python -m pytest tests/<file> -v`.

### TC-9 (suite): full static gate green
- **Verification command**: `python tests/run_tests.py` — all pass, 0 failures/errors.

### TC-10 (landing safety): PR merge-safe
- **Steps**: PR #13346 base=main, mergeable, branch not materially behind base ([[learning-verify-squash-diff-additions-only-behind-branch]]); diff deletes no fleet/state artifacts.
- **Expected**: safe squash; deletions limited to intentional in-file edits.
- **Verification command**: `gh pr view/diff`, `git diff main...branch --diff-filter=D --stat`, behind-count via compare.

## Coverage matrix
- AC1 → TC-1, TC-2, TC-4, TC-5
- AC2 → TC-3
- AC3 → TC-7 + CQ-1..CQ-4
- AC4 → TC-8
- AC5 → TC-6a-d
- (suite/meta) → TC-9, TC-10

## Comprehension Questions (task touches LLM-consumed instructions)

Modified LLM-consumed files (per issue scope): `references/sub-skills/common-events/event-mode-contract.md`, `references/sub-skills/common/context-pressure.md`. Fresh agent, files only, no context.

### CQ-1: In event mode, WHO/WHAT enforces the context-pressure threshold, and where does that actor run?
- **Files**: event-mode-contract.md, context-pressure.md
- **Expected answer**: the harness (harness-side monitor/health-poller) — NOT the agent, NOT cycle_post.py per-event wrappers.

### CQ-2: What must the agent itself DO when the harness initiates a pressure restart?
- **Files**: event-mode-contract.md
- **Expected answer**: honor it at a task boundary — checkpoint working-state.md and halt (cease output); the harness force-kill net + respawn does the rest; the agent cannot self-terminate.

### CQ-3: Where does the threshold value come from and what is the default?
- **Files**: context-pressure.md (and/or event-mode-contract.md)
- **Expected answer**: config.md `Context Pressure / Threshold`, default 70.

### CQ-4: Does the loop-mode (polling) pressure path still exist, and what is it?
- **Files**: context-pressure.md
- **Expected answer**: yes — loop mode keeps the cycle_post.py wrapper-side detection / exit-42 path; event mode is the harness-actor path.

**Spec file**: verifier-owned canonical spec at `tests/comprehension/13335_spec.json` — worker authored one; verifier reviews it against the CQs above and treats divergence as a finding (spec ownership is verifier's per #9184).
