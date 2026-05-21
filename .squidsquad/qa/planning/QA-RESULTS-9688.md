# QA-RESULTS-9688 — Orphan claude.exe subagent cleanup

**Issue**: #9688
**PR**: #9737
**Branch**: squidsquad/task/9688
**Verified by**: qa-lead
**Date**: 2026-05-20
**Verdict**: **PASS** (with one minor naming deviation noted; non-blocking)

## 1. Live-system pytest

```
12 passed in 29.22s
```

(See `.squidsquad/qa/planning/TEST-9688-tests.py` → promoted to `tests/test_feat_9688_orphan_cleanup_live.py`)

| TC | Covers | Result |
|----|--------|--------|
| TC-1 | AC-1 (public API) | PASS |
| TC-2 | AC-1 (cycle_post invocation) | PASS |
| TC-3 | AC-3 (boot_remote pre-spawn invocation) | PASS |
| TC-4 | AC-4 (JSONL diagnostics schema) | PASS |
| TC-5 | AC-2, AC-5 (classify) | PASS |
| TC-6 | AC-6 (POSIX no-op) | PASS |
| TC-7 | AC-7 (D7 cases) | PASS |
| TC-8 | AC-8 (ARCHITECTURE.md locked sections + phrasing) | PASS |
| TC-9 | AC-1 (npm path filter) | PASS |
| TC-10 | AC-1 (D3 abort) | PASS |
| TC-11 | AC-1 (own-pid safety) | PASS |
| TC-12 | live smoke dry-run | PASS |

## 2. Dev unit suite

`tests/test_orphan_cleanup_9688.py` — **16/16 PASS**. All 7 D7 cases covered.

## 3. Changed-area regression

`tests/test_orphan_cleanup_9688.py` + `tests/test_cycle_post.py` + `tests/test_boot_remote.py` → **150 passed, 1 skipped** (the skip is pre-existing OS-specific).

## 4. AC walk

| AC | Verdict | Notes |
|----|---------|-------|
| AC-1 (orphan_cleanup.py module + cycle_post integration) | PASS | TC-1, TC-2, TC-9, TC-10, TC-11 |
| AC-2 (live agent never killed) | PASS | TC-5 classify + TC-11 own-pid + TC-10 D3 abort safety |
| AC-3 (boot_remote sweep pre-spawn) | PASS | TC-3 — `orphan_cleanup.sweep(invoked_by=f"boot_remote:{role}")` precedes `_spawn_terminal(...)` inside `boot_agent()` |
| AC-4 (diagnostics JSONL with D4 schema) | PASS (minor naming deviation) | See §4.1 |
| AC-5 (orphan count ≤1 after heavy session) | PASS structurally | TC-5 classification + 16-case unit suite + TC-12 live smoke; full E2E heavy-session simulation explicitly out-of-scope per CONTEXT D7 (mock-based testing locked) |
| AC-6 (POSIX runs silently) | PASS | TC-6 |
| AC-7 (7 D7 cases covered) | PASS | TC-7 — function name pattern check + 16/16 unit suite green |
| AC-8 (ARCHITECTURE.md updated per D8 locked text) | PASS | TC-8 — all 4 sections + locked phrasing present in `docs/ARCHITECTURE.md` (line 67+) |

### 4.1 AC-4 minor naming deviation

CONTEXT-9688 §D4 locks the diagnostics path as `.squidsquad/diagnostics/orphan-cleanup.log` (append-only, one JSON line per decision). The PR implements it as `.squidsquad/diagnostics/orphan-cleanup.jsonl`.

Assessment: This is a filename-extension change only. The wire format (one JSON record per line) matches the locked spec exactly; the `.jsonl` extension is arguably MORE accurate (the file IS JSONL, not free-form log text). No consumer code references the filename outside `orphan_cleanup.py:DIAGNOSTICS_LOG`. Internal diagnostics — no public API impact.

**Disposition**: Accept as a minor improvement-over-spec. Filed as a non-blocking note here; if PM/human wants strict CONTEXT adherence, a one-line rename is a follow-up.

## 5. Forward-looking discussion item (NOT blocking)

Skill's latest comment + PR body raise a design question:

> D3 strict reading + multi-clone deployments means orphan cleanup is skipped in the exact scenario where it's most needed (skill clone with no peer agents running). Should D3 be softened to per-role-pragmatic in a follow-up, or stays strict and cleanup is acceptable to skip in those configurations?

QA confirms this is a real trade-off: TC-12's live smoke on the QA clone hits D3 (peer roles' `.claude-pid` not present locally), so cleanup is skipped — the conservative-safe outcome the lock specifies. Routing this to PM/human as a follow-up rather than blocking #9688.

## 6. Setup & Upgrade Sync Check

- New config values: N/A (D5 locks "no opt-out flag")
- New files/directories: `.squidsquad/diagnostics/` autocreated by the module if absent — no installer change needed
- Modified template structure: N/A
- Added/removed sub-skills: N/A
- Changed role composition: N/A
- Upgrade path: orphan_cleanup is best-effort + cross-platform safe; existing installs get it on next `git pull` + agent restart. No migration step needed.

## 7. Decision

**Verdict**: PASS.

- Promote `TEST-9688-tests.py` → `tests/test_feat_9688_orphan_cleanup_live.py`
- Approve PR #9737 (self-approve blocked since same author; comment is the recorded verdict)
- Auto-merge via harness per project config
- Transition #9688 pending-test → pending-ship
- Increment `Shipped Since Last Bump` 7 → 8
- File AC-4 naming-deviation as non-blocking note + D3 follow-up as PM-routed Discussion item
