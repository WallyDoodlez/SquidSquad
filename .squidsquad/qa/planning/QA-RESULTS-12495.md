# QA-RESULTS-12495

**Issue**: #12495 — AGENT-RUNTIME §8.3 documents work-assign / POST /work/assign — neither implemented
**PR**: #13161 (branch squidsquad/task/12495 @ e86882011, base main, +519/-46; harness.py + tracker.py + AGENT-RUNTIME/COMPOSE/HARNESS/INSTALLER docs + tests/test_12495_work_assign.py)
**Verdict**: ❌ **FAIL — 1 gap (full static gate fails: PR-introduced orphan route)** → back to in-progress (skill)
**Verified by**: verifier (qa), 2026-06-21 17:35
**Method**: Independent TEST-PLAN; verified on a clean worktree of the PR branch incl. full static gate.

## AC Walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 endpoint | ✅ PASS | harness.py `@app.post("/work/assign")` → `_emit_event("assigned-to","harness",payload=...)`, returns `{status:"ok", event_id}`; no transition, no role:* write |
| TC2 | AC2 guards | ✅ PASS | self-assign emitter==target → 400 (via X-Squidsquad-Alias); unknown alias → 404 (+known_aliases); malformed/missing target_alias → 400; config-unreadable falls open |
| TC3 | AC3 CLI | ✅ PASS | tracker.py work_assign present; sets `headers["X-Squidsquad-Alias"]=caller_alias` (L1711); returns event_id; usage line added |
| TC4 | AC4 doc accuracy | ✅ PASS | AGENT-RUNTIME §8.3 reconciled to as-built (universal-router design "never built"; documents EAD transition-routing vs the manual /work/assign primitive; "agents never call /work/assign for transition handoffs"). COMPOSE/HARNESS/INSTALLER consistently updated (HARNESS-ARCH §13 documents the endpoint precisely) |
| TC5 | AC5 static gate | ❌ **FAIL** | `python tests/run_tests.py static` → **1 failed, 4875 passed**. `test_harness_route_contract.py::test_every_harness_route_has_manifest_entry`: **Orphan harness route `('POST','/work/assign')`** — no manifest entry in EXPECTED_CALLERS. PR-introduced (origin/main has only the comment, no route → passes on main) |
| TC6 | AC5 feature test | ✅ PASS | test_12495_work_assign.py: 15 passed (covers endpoint + CLI + guards) |

## Finding (blocker)

**Full static gate FAILS — orphan route.** The PR adds `POST /work/assign` to harness.py but does NOT register it in `tests/test_harness_route_contract.py::EXPECTED_CALLERS`. The route-contract test is purpose-built to catch this: *"A new route added to harness without a manifest update is an orphan route — flagging it here forces the developer to declare callers (or explicitly mark _EXTERNAL) on the same PR that registers the route."* This is a NEW failure introduced by this PR (not a known-failure; origin/main passes the test). The worker's own feature test (test_12495_work_assign, 15 pass) is green — but the separate route-contract test in the full suite fails; this is exactly the regression the full static gate catches that a feature-only run misses.

The implementation itself is excellent — route, CLI (with the X-Squidsquad-Alias self-assign header), guards (400/404), and all four doc reconciliations are correct. The SOLE blocker is the missing manifest entry.

## Remedy (one-cycle, trivial)

Add the route to `EXPECTED_CALLERS` in `tests/test_harness_route_contract.py`, e.g.:
```python
('POST', '/work/assign'): ['tracker'],   # tracker.py work-assign CLI (add _EXTERNAL too if operator/curl callers are expected)
```
The canonical caller is `tracker.py`'s `work_assign`. Then re-run `python tests/run_tests.py static` to confirm green. Re-verification will be fast — only TC5 needs to re-pass; all other ACs already confirmed.

## Disposition

Verdict FAIL → transition pending-test → in-progress (skill). TEST-PLAN-12495 + QA-RESULTS-12495 on qa planning. No comprehension spec needed (AGENT-RUNTIME.md is a TRD reference doc, not a composed agent instruction; no CLAUDE.md/sub-skill/SOUL changed).

---

## RE-VERIFICATION ADDENDUM (2026-06-21 18:25) — ✅ PASS

Skill resolved the single blocker exactly as recommended: added `("POST", "/work/assign"): ["tracker"]` to EXPECTED_CALLERS in tests/test_harness_route_contract.py (L87; commit e6988ba6d; branch also merged main).

Re-verified on a fresh worktree:
- `test_harness_route_contract.py::test_every_harness_route_has_manifest_entry` → **1 passed** (was failing).
- Full static gate → **4907 gated PASS, 0 fail, 0 error**.

All other ACs (AC1 endpoint, AC2 guards, AC3 CLI+header, AC4 doc accuracy, AC5 feature test) confirmed in the first pass remain valid. **Corrected verdict: PASS** → transition pending-test → pending-ship.
