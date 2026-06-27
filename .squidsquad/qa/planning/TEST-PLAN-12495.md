# TEST-PLAN-12495

**Issue**: #12495 — AGENT-RUNTIME §8.3 documents tracker.py work-assign / POST /work/assign — neither is implemented
**Type**: type:issue (auto-approved), severity:medium, role:skill
**PR**: #13161 (branch squidsquad/task/12495, base main, +519/-46; 7 files: harness.py, tracker.py, 4 docs, test). Resolution = option (a) IMPLEMENT the primitive.
**Authored by**: verifier (qa), derived from issue's two resolution options + doc-accuracy requirement.

## Derived Acceptance Criteria

- **AC1 (endpoint)**: `POST /work/assign` exists; emits `assigned-to` to target_alias WITHOUT a transition; returns event_id.
- **AC2 (guards)**: self-assign invariant (emitter==target → 400 via X-Squidsquad-Alias); unknown alias → 404; malformed/missing target_alias → 400.
- **AC3 (CLI)**: `tracker.py work-assign` exists, POSTs the endpoint, sends X-Squidsquad-Alias (caller), returns event_id.
- **AC4 (doc accuracy)**: AGENT-RUNTIME §8.3 (+ COMPOSE/HARNESS/INSTALLER) now describe the AS-BUILT primitive (no longer a non-existent command); EAD transition-routing vs manual /work/assign clearly distinguished.
- **AC5 (no regression)**: full static gate green; feature test covers the primitive.

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | Read harness /work/assign route | emits `_emit_event("assigned-to",...)`, returns {status, event_id} |
| TC2 | AC2 | Read route guards | self-assign 400, unknown alias 404, malformed 400 |
| TC3 | AC3 | Read tracker.py work_assign + usage | CLI present; sets X-Squidsquad-Alias header (L1711) |
| TC4 | AC4 | Read §8.3 + 3 other docs | as-built reconciliation; EAD vs /work/assign distinct |
| TC5 | AC5 | `python tests/run_tests.py static` | PASS |
| TC6 | AC5 | Run test_12495_work_assign.py | pass |
