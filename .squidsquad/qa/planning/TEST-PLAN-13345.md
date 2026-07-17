# TEST-PLAN #13345 — health endpoint reads clone-relative context-pressure

**Derived from the issue body — display-only bug filed by skill during #13335 review.**

Bug: `GET /agents/{role}/health` read `context-pressure` from
`SQUIDSQUAD_DIR/<role>/context-pressure` (the PM-repo/harness-root path), but
sibling-clone agents (skill/qa/dm) write it to their OWN clone at
`<clone>/.squidsquad/<role>/context-pressure`. Display-only — #13335's
enforcement path already reads the correct clone-relative location via
`_read_agent_pressure`, so only the reported number (not enforcement) was
wrong.

## Acceptance Criteria (independent reading — scope = display fix only)

| AC | Contract |
|----|----------|
| AC1 | `/agents/{role}/health` reports `context_pressure` from the agent's own clone path, not the harness-root path |
| AC2 | Reuses `HarnessState._read_agent_pressure` — same function #13335's enforcement uses — so reported == enforced |
| AC3 | Fails safe to `None` on absent/unreadable/non-integer file, and when `agent` itself is `None` |
| AC4 | No change to enforcement (`_enforce_context_pressure` untouched) — display-only |
| AC5 | Regression test covers: reads real clone value, absent-file→None, malformed-file→None, no-agent→safe |
| AC6 | Full static gate green |

## Verification (branch squidsquad/task/13345, combined with current main)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1, AC2 | `test_reads_from_clone_not_harness_root` — writes pressure to a temp clone, confirms `get_agent_health` returns it (not harness-root) | **PASS** |
| TC2 | AC3 | `test_absent_clone_file_is_none`, `test_malformed_clone_file_is_none`, `test_no_agent_is_safe` | **PASS** |
| TC3 | AC4 | Diff review: `_enforce_context_pressure` (separate function, #13335) untouched by this PR | **PASS — confirmed no overlap** |
| TC4 | AC2 (write-side consistency) | **Independent** cross-check (not in PR's own suite): confirmed `cycle_pre.py:428` (`SQUID_DIR / role / "context-pressure"` where `SQUID_DIR = REPO_ROOT / ".squidsquad"`, `REPO_ROOT` = the agent's OWN clone) is the actual write-side path, and it matches `_read_agent_pressure`'s read path exactly | **PASS** |
| TC5 | AC5 | 4/4 tests in `tests/test_13345_health_clone_pressure.py` | **PASS** |
| TC6 | AC6 | Full static gate on combined state: 5441/0 | **PASS** |

## Live-harness note

This modifies `harness.py`, which backs the currently-running shared harness
process (port 7373) I've been using for this session's merges. Verification
was done via **direct in-process async calls** to `get_agent_health()` (as the
PR's own tests do) against a temp clone — NOT by restarting the live shared
harness, which would disrupt the whole team and is PM's call, not verifier's,
per the `harness-restart` sub-skill. The fix does not need a live-harness
restart to be verified correct; DM's eventual ship will land it on `main` and
the next natural harness restart picks it up.

## Notes

- `type:issue`, severity:low — auto-approved, no human gate.
- No comprehension spec (code-only display fix, not an LLM-consumed instruction).
