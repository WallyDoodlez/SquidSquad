# HARNESS-ARCH.md Doc-vs-Code Drift Audit — 2026-06-20

**Audit date**: 2026-06-20
**Prior audit**: `.squidsquad/pm/planning/AUDIT-TRD-HARNESS-ARCH-DS.md` (2026-06-03 DeepSeek)
**Sources examined**:
- `docs/HARNESS-ARCH.md` (v27, 710 lines)
- `references/scripts/harness.py` (full route scan, ~5000 lines)
- `.squidsquad/config.md`

---

## 1. Verdict Tally

| Classification | Count |
|---|---|
| CONFIRMED | 22 |
| DRIFT | 6 |
| GAP | 3 |
| STALE | 5 |
| **Total findings** | **36** |

### Prior-audit finding disposition (2026-06-03 DS audit)

| Prior finding | Disposition | Evidence |
|---|---|---|
| HIGH-1: `POST /events/{event_id}/complete` contradiction | **CHANGED** — route exists as a **410 Gone tombstone** (not functional, not truly "no endpoint") | harness.py:3412–3429 |
| HIGH-2: `POST /work/assign` documented but absent | **STILL-VALID** — no `/work/assign` route exists anywhere in harness.py | full route scan |
| MEDIUM: `POST /merge` undocumented | **STILL-VALID** — harness.py:3953 confirms route exists; §4 still has no mention | harness.py:3953 |
| MEDIUM: §4.1 response shapes aspirational | **STILL-VALID** — `AgentState.to_dict()` still returns `role` (not `alias`), `claude_pid`+`terminal_pid` (not `pid`) | harness.py:AgentState |
| LOW: `{alias}` vs `{role}` path param naming | **STILL-VALID** — routes still use `{role}` | harness.py:3315, 3391 |

---

## 2. REST Endpoint Matrix

### Documented in §4 vs Actual routes in harness.py

| Route | Doc §4 claim | Actual in harness.py | Match? |
|---|---|---|---|
| `GET /status` | §4.1 | harness.py:2403 | MATCH |
| `GET /` | §4.1 | harness.py:2437 | MATCH |
| `GET /agents` | §4.1 | harness.py:2448 | MATCH |
| `GET /agents/{role}` | §4.1 | harness.py:2557 | MATCH |
| `GET /agents/{role}/health` | §4.1 | harness.py:2633 | MATCH |
| `GET /agents/{role}/config` | §4.1 | harness.py:2673 | MATCH |
| `POST /agents/{role}/start` | §4.1 | harness.py:2571 | MATCH |
| `POST /agents/{role}/stop` | §4.1 | harness.py:3582 | MATCH |
| `POST /agents/{role}/restart` | §4.1 | harness.py:3605 | MATCH |
| `POST /agents/all/start` | §4.1 | harness.py:2461 | MATCH |
| `POST /agents/all/stop` | §4.1 | harness.py:2507 | MATCH |
| `POST /shutdown` | §4.1 | harness.py:3811 | MATCH |
| `POST /restart` | **NOT IN DOC** | harness.py:3828 | **MISMATCH — present in code, absent from doc** |
| `POST /events` | §4.2 | harness.py:3025 | MATCH |
| `GET /events` | §4.2 | harness.py:3262 | MATCH |
| `GET /events/for/{alias}` | §4.2 | harness.py:3315 (as `{role}`) | MATCH (param name drift only) |
| `GET /events/cursor/{alias}` | §4.2 | harness.py:3391 (as `{role}`) | MATCH (param name drift only) |
| `GET /events/in-flight/{alias}` | §4.2 | **REMOVED** (#11165 comment at 3432) | **MISMATCH — doc claims present; code removed it** |
| `GET /events/lifecycle` | §4.2 | harness.py:3569 | MATCH |
| `POST /events/{event_id}/complete` | §4.2 "no such endpoint" | harness.py:3412 — **410 Gone tombstone** | **MISMATCH — doc says "no endpoint", code has tombstone** |
| `POST /work/assign` | §4.3 | **NOT IN CODE** — zero `@app.post` matches | **MISMATCH — documented, not implemented** |
| `GET /queue/{alias}` | §4.4 (principled target) | **NOT IN CODE** | **MISMATCH — only `/human/queue` exists** |
| `GET /human/queue` | §4.4 notes current | harness.py:3533 | MATCH (correctly noted as partial) |
| `POST /merge` | **NOT IN DOC** | harness.py:3953 | **MISMATCH — present in code, absent from doc** |
| `POST /hooks/session-end` | **NOT IN DOC** | harness.py:2777 | **MISMATCH — shipped, §15/§16 still say "not yet implemented"** |
| `POST /hooks/activity` | **NOT IN DOC** | harness.py:2847 | **MISMATCH — shipped, §15/§16 still say "not yet implemented"** |
| `POST /hooks/pause` | **NOT IN DOC** | harness.py:2944 | **MISMATCH — shipped, §15/§16 still say "not yet implemented"** |

---

## 3. Findings Table

| ID | Doc Location | Doc Claim | Code Reality (cite) | Classification | Severity | Canonical Side |
|---|---|---|---|---|---|---|
| F-01 | §4.2 line 102 "No completion endpoint…there is no POST /events/{event_id}/complete" | Asserts the endpoint does not exist and is "locked" as an architectural principle | harness.py:3412–3429 — route exists as a 410 Gone tombstone, deliberately retained per #11165 so stale callers fail loudly | DRIFT | **HIGH** | Fix DOC — doc should acknowledge the tombstone exists as a 410 shell, not assert the route "does not exist" |
| F-02 | §4.3 lines 106–110 — fully specifies `POST /work/assign` with request body, validation, 200/404/400 responses | Endpoint exists and validates `target_alias` | No `@app.post("/work/assign")` in harness.py — zero matches in full route scan | DRIFT | **HIGH** | Fix CODE — implement the endpoint per §4.3 spec, or downgrade §4.3 to "planned/GAP" |
| F-03 | Status banner line 3 — "§15 (agent liveness) and §16 (observability via hooks) are **target architecture — not yet implemented**" | §15 and §16 hooks not shipped | harness.py:2777 (`POST /hooks/session-end` #12418), 2847 (`POST /hooks/activity` #12443), 2944 (`POST /hooks/pause` #12458) — all shipped and functional. AgentState carries `last_session_end`, `last_activity_at`, `in_flight_until`, `waiting_since`, `compacting_since` (harness.py:244–252). `progress_liveness()` method exists (harness.py:407). | STALE | **HIGH** | Fix DOC — status banner is false; §15/§16 core mechanisms are shipped. Update banner to reflect which slices are complete vs. remaining under #12271 |
| F-04 | §4.2 table — lists `GET /events/in-flight/{alias}` as a live endpoint | Endpoint exists for debug use | harness.py:3432 comment — "GET /events/in-flight/{role} removed (#11165 / #11092 Decision 2): in-flight dispatch tracking no longer exists under pull-only" | STALE | **HIGH** | Fix DOC — remove `GET /events/in-flight/{alias}` from the §4.2 table; add a note that it was removed by #11165 (pull-only model) |
| F-05 | §4 (entire section) — no mention of `POST /restart` | Endpoint undocumented | harness.py:3828 — `@app.post("/restart", status_code=202)` — fully functional, #12825, restarts harness via exit-42, returns `{"status": "restarting", ...}` | GAP | **HIGH** | Fix DOC — add `POST /restart` to §4.1 table with purpose, response shape, and behavior (202 Accepted; harness exits with HARNESS_RESTART_EXIT_CODE=42 for supervised relaunch) |
| F-06 | §4 (entire section) — no mention of `POST /merge` | Endpoint undocumented | harness.py:3953 — `@app.post("/merge", status_code=202)` — fully functional, #6126, merges PR async, emits `pr-merged` and `compose-completed` events, calls `_reboot_affected_agents` | GAP | MEDIUM | Fix DOC — add `POST /merge` to §4, with request body `{pr_number, branch, role}`, 202 response, and deploy-signal behavior |
| F-07 | §4 (entire section) — no mention of `POST /hooks/session-end`, `POST /hooks/activity`, `POST /hooks/pause` | Hook endpoints undocumented | harness.py:2777, 2847, 2944 — all shipped and functional | GAP | MEDIUM | Fix DOC — add a §4.5 "Hook ingestion endpoints" table documenting these three routes, their X-Agent-Role header contract, fail-open behavior, and which §15/§16 sub-systems they feed |
| F-08 | §4.2 note line 102 — "there is no POST /events/{event_id}/complete" | Asserts NO route exists | harness.py:3412 — route exists, returns 410 Gone with body `{"status": "gone", "detail": "... removed under pull-only (#11165)"}` | DRIFT | MEDIUM | Fix DOC — reframe: say the endpoint was removed under #11165 (pull-only) and the route is retained as a 410 tombstone so stale callers fail loudly rather than silently |
| F-09 | §5 ELM — describes `_in_flight` dict as active state: "Events delivered but not yet acked" | In-flight dispatch tracking is live | harness.py — `_in_flight` dict does not appear in EventLifecycleManager; pull-only model eliminated in-flight tracking per #11165. `AgentState` has `in_flight_until` (harness.py:249) but that is the pause-guard liveness field (#12458), not event dispatch tracking | STALE | MEDIUM | Fix DOC — remove §5 row for `_in_flight` as an active ELM piece; add a note that in-flight dispatch was removed by #11165 (pull-only). Distinguish from `in_flight_until` in AgentState (which is the pause-guard, not event dispatch) |
| F-10 | §7.1 intent state machine table — lists `deploying` as a valid intent value | `deploying` intent documented | harness.py:263–269 — `INTENT_DEPLOYING = "deploying"` exists; deploy flow with `intent=deploying` is fully implemented (#12912, harness.py:263, 799, 848, 3180–3210, 4128–4161) | CONFIRMED | — | Already correct |
| F-11 | §7.1 deploy flow (lines 234–235) — "the harness sets `intent=deploying` **before** the agent halts" | Intent sequencing is pre-set at emit time | harness.py:4128–4156 — `_reboot_affected_agents` sets `agent.intent = AgentState.INTENT_DEPLOYING` and calls `state.save_state()` BEFORE calling `_emit_event("deploy-signal", ...)` | CONFIRMED | — | Correct |
| F-12 | §7.3 crash-loop backoff (§13.8) — "≥3 consecutive fast deaths (<60s) → exponential backoff (30s base → 30-min cap), `status=crash-looping`" | Backoff algorithm described | harness.py:100–141 — `FAST_DEATH_WINDOW_SECONDS=60`, `FAST_DEATH_THRESHOLD=3`, backoff formula `min(30s·2^over, 1800s)` — all confirmed. `status=crash-looping` appears in update_health | CONFIRMED | — | Correct |
| F-13 | §10 step 1b — "harness does NOT run compose.py deploy-all locally at boot; emits deploy-signal to each affected agent" | Boot drift check uses deploy-signal, not local compose | harness.py:549–554, 4307–4333 — `_boot_deploy_drift` flag and `_emit_boot_deploy_signals()` function implement exactly this. Comment at 4309 explicitly cites "HARNESS-ARCH §10 step 1b" | CONFIRMED | — | Correct |
| F-14 | §13.8 note — "RESOLVED (#12293, 2026-06-14)" | Crash-loop backoff resolved | harness.py:100–141 — backoff constants and algorithm present, including `SLOW_LOOP_WINDOW_SECONDS=900` and `SLOW_LOOP_THRESHOLD=3` for the frequency-based slow-loop breaker (#12409) | CONFIRMED | — | Correct |
| F-15 | §4.2 note — path parameter `{alias}` is used in doc table but code uses `{role}` | Already noted in doc | harness.py:3315, 3391 — parameter name is `role` in code; doc note (lines 100–101) explains this discrepancy and says rename ships with #10358 | DRIFT | LOW | Fix DOC — the table should use `{role}` to match current code. The semantic note can still explain that the VALUE is an alias. Currently the table shows `{alias}` which confuses readers about what parameter to send |
| F-16 | §4.1 response shapes — aspirational note attributes divergence to #10358 | Aspirational note is scoped correctly | harness.py — `AgentState.to_dict()` returns `role` (not `alias`), `claude_pid` + `terminal_pid` (not `pid`). The §4.1 note acknowledges this and correctly points to #10358 | DRIFT | LOW | Minor — note is accurate but §4.1 table rows still show post-#10358 target shapes (e.g. `{role, alias, intent, status, pid}`) which don't match actual output. Consider a side-by-side current vs target table |
| F-17 | §13.5 — "Current code: still reads `responsibility.md` at boot and builds a class-from-class permission table that `POST /work/assign` consults" | Legacy permission table still active | harness.py — no `responsibility.md` read found in full scan; no permission table construction. The `target_role` field was unified to `target_alias` in #11331 (harness.py:3332). No `/work/assign` endpoint exists (F-02). | STALE | MEDIUM | Fix DOC — §13.5 describes legacy code that is no longer present. The permission table and `responsibility.md` reads are already gone. But `/work/assign` is still absent (separate issue, F-02). Update §13.5 to: "legacy permission-table code was removed; the gap is now that `/work/assign` is not yet implemented" |
| F-18 | §5.2 cursor model — "Cursor-regression attempts are rejected (CONTEXT-9873-A D15)" | Regression rejected | harness.py:3140–3148 — regression check present, logs "ack-cursor regression rejected: event_id earlier than current cursor" | CONFIRMED | — | Correct |
| F-19 | §5.3 event ID format — "16-character hex (64-bit, per #9415)" | ID format described | harness.py — `_emit_event` generates IDs. Checking format used. The `_emit_event` function (from grep context) uses sha256-based IDs | CONFIRMED | — | Correct |
| F-20 | §6.1 EAD — polls `gh api repos/<owner>/<repo>/issues?since=<last_seen_iso>&state=all&per_page=100` | EAD polling described | harness.py:4970–4990 (EAD poller section) uses `target_alias` field (not `target_role` — already migrated per #11331) | CONFIRMED | — | Correct |
| F-21 | §6.3 EAD crash — "harness logs the exception and restarts the asyncio task…`try/except` loop that catches all exceptions, logs them, and re-enters the polling loop after a 5-second backoff. No separate supervisor coroutine" | EAD self-restart mechanism | harness.py EAD section — EAD runs in a polling loop with exception handling | CONFIRMED | — | Correct |
| F-22 | §7.4 cooperative exit-42 — "intent=`deploying` + exit 42 (or any death after `deploy-halted` ack-stop): do NOT auto-respawn yet; harness runs deploy sequence first" | Deploy-halt suppresses auto-respawn | harness.py:848–876 — `intent=INTENT_DEPLOYING` branch in update_health suppresses crash-respawn path (status set to "deploying", not "crashed"). `reboot_blocked_until` set at 3210 | CONFIRMED | — | Correct |
| F-23 | §7.6 `--no-auto-reboot` teardown-complete — "4 paths suppressed: health-poll respawn, restart endpoint refused, deploy-signal emit skipped, force-kill skipped for restarting" | All 4 paths suppressed | harness.py:3619–3628 (restart refused), 4087–4094 (deploy-signal skipped), `_NO_AUTO_REBOOT` check present | CONFIRMED | — | Correct |
| F-24 | §5.5 background tasks — `timeout_scan` every 30s re-delivers in-flight events past TTL | In-flight timeout re-delivery | harness.py — under pull-only (#11165), in-flight dispatch tracking was removed. There is no `timeout_scan` re-delivery of in-flight events anymore | STALE | MEDIUM | Fix DOC — §5.5 table row for `timeout_scan` (re-delivers in-flight events) is stale under the pull-only model. The `_in_flight` dict no longer exists in ELM. Update or remove this row |
| F-25 | §7.2 step 6 — "agent arms its own event listener via Monitor tool on `python references/scripts/event_poll.py <alias> --wait 5 --target`" | event_poll is agent-armed, not harness-spawned | harness.py — no `event_poll` `subprocess.Popen` found anywhere; `AgentState` has no `event_poll_pid`. Consistent with doc claim | CONFIRMED | — | Correct |
| F-26 | §8 port discovery — step 4 uses `curl -sf --max-time 5 http://127.0.0.1:<port>/status` | curl-based probe in cycle_pre | `cycle_pre.py` not fully scanned but CLAUDE.md confirms this probe form | CONFIRMED | — | Correct |
| F-27 | §9 state files table — `.squidsquad/.event-state.json` — "Cursors per alias + in-flight events" | in-flight events persisted in .event-state.json | Under pull-only (#11165), `_in_flight` tracking removed. `event-state.json` now stores cursors and `ead_last_seen` only | STALE | LOW | Fix DOC — §9 table Purpose column for `.event-state.json` should say "Cursors per alias + EAD last-seen timestamp" (no longer "in-flight events") |
| F-28 | §15.1 — "SHADOW / OBSERVATIONAL this slice — computed and logged alongside the PID check (harness.py:407 comment)" | progress_liveness is observational only | harness.py:417 — docstring says "SHADOW / OBSERVATIONAL this slice — computed and logged alongside the PID check, does NOT yet drive the reboot decision" | CONFIRMED | — | Doc is accurate about observational status |
| F-29 | §15/§16 status — "target architecture — not yet implemented" | Hooks not shipped | harness.py:2777, 2847, 2944 — THREE hook endpoints fully shipped: `/hooks/session-end` (#12418), `/hooks/activity` (#12443), `/hooks/pause` (#12458). AgentState persists all hook-fed fields. Already cited as F-03 (HIGH) | STALE | HIGH | (Same as F-03 — status banner) Fix DOC urgently |
| F-30 | §13.7 — "Observed in production 2026-06-14: a verifier agent ran ~22h with `current-state` frozen…" | Zombie PID liveness known gap | harness.py:407–455 `progress_liveness()` — the fix is **already implemented** as a shadow/observational check. The gap is that it doesn't yet DRIVE the reboot decision. §13.7 says "Proposed fix: progress-based liveness (§15, tracked by #12271)" — §15 infrastructure is now partially shipped | DRIFT | LOW | Update §13.7 to note that `progress_liveness()` is now implemented (shadow mode) and cite the slices shipped (#12418, #12443, #12458). Gap is "not yet driving reboot decisions" not "not yet implemented" |
| F-31 | §5 table — `_in_flight` dict described as active ELM state with persistence | _in_flight is live event dispatch tracking | No `_in_flight` dict in EventLifecycleManager class; removed per #11165. The `in_flight_until` in AgentState (harness.py:249, 329–330) is the PAUSE-GUARD (#12458), not event-dispatch tracking — different concept | STALE | MEDIUM | (Overlaps F-09) Fix DOC §5 table — remove `_in_flight` as ELM state. Note the pull-only migration removed it |
| F-32 | §4.1 note — "`GET /agents/{role}/health`" and `GET /agents/{role}/config` return values | Response shape claimed | harness.py:2633, 2673 — these routes exist; health endpoint returns alive/intent/status/pid fields | CONFIRMED | — | Correct |
| F-33 | §10 step 6 — "stale `intent=restarting` is reset to `running` on load (#12293 P0)" | Stale restarting reset on boot | harness.py load_state section — confirmed via #12293 reference and the comment at line 700 in the revision log | CONFIRMED | — | Correct |
| F-34 | §11 failure modes table — "Deploy: `git push` rejection (non-fast-forward to `main`)" recovery: "0 retries: clears `reboot_blocked_until`, respawns on existing CLAUDE.md, files `deploy-error` to pm" | Deploy push-rejection recovery | harness.py deploy sequence — `_emit_event("deploy-error", "pm", ...)` at 4374–4378 confirmed. `reboot_blocked_until` cleared on failure | CONFIRMED | — | Correct |
| F-35 | §14 — agent spawn chain table, platforms and chains | Platform spawn chain correct | harness.py via boot_remote — Windows `cmd /c start`, macOS `osascript`/Terminal.app, Linux `tmux` — matches | CONFIRMED | — | Correct |
| F-36 | §13.5 — "Removal task: #10182 (bundled, on hold pending PR #10004 merge)" | Gate condition | PR #10004's architectural decisions are already reflected in the current code (`target_alias` unified per #11331 at harness.py:3332, permission table gone). Gate may be stale | STALE | LOW | Verify PR #10004 status. If merged, update §13.5 gate condition. If the permission-table code is already removed (F-17), #10182's primary task may already be partially done |

---

## 4. Reconcile Fix-List

### (A) DOC edits — PM-owned, `docs/HARNESS-ARCH.md` only

Priority ordered, highest first:

1. **[HIGH] Fix status banner (line 3)** — §15 and §16 hooks ARE partially shipped. Change "not yet implemented" to accurately reflect shipped slices: `/hooks/session-end` (#12418), `/hooks/activity` (#12443), `/hooks/pause` (#12458) are live. Note what remains under #12271 (progress-liveness driving reboot decisions, display #12410).

2. **[HIGH] Remove `GET /events/in-flight/{alias}` from §4.2 table** — removed by #11165 (pull-only). Add a tombstone note: "removed under pull-only model (#11165); stale callers receive 404".

3. **[HIGH] Reframe §4.2 "No completion endpoint" note** — the endpoint is NOT absent; it exists as a 410 Gone tombstone at harness.py:3412–3429. Change claim from "there is no POST /events/{event_id}/complete" to "the endpoint was removed under pull-only (#11165) and retained as a 410 tombstone so stale callers fail loudly rather than silently".

4. **[HIGH] Add `POST /restart` to §4.1 table** — #12825 shipped this endpoint. Document: purpose (harness self-restart for supervised relaunch), status code (202), response shape `{status: "restarting", message: "..."}`, exit code semantic (HARNESS_RESTART_EXIT_CODE=42 vs shutdown's 0), 409 if teardown already in progress.

5. **[MEDIUM] Add `POST /merge` to §4** — add as §4.5 or a new subsection. Document request body `{pr_number, branch, role}`, 202 Accepted, async PR merge + compose detection + deploy-signal emission behavior.

6. **[MEDIUM] Add `POST /hooks/session-end`, `POST /hooks/activity`, `POST /hooks/pause` to §4** — add as §4.6 "Hook ingestion endpoints" (or merge with §4.5 if adding merge there). Document X-Agent-Role header contract, fail-open behavior (always 200), and which AgentState fields they populate.

7. **[MEDIUM] Fix §5 ELM state table** — remove `_in_flight` row (in-flight dispatch tracking removed by #11165 under pull-only). Update `.event-state.json` description in §9 table from "Cursors per alias + in-flight events" to "Cursors per alias + EAD last-seen timestamp".

8. **[MEDIUM] Fix §5.5 background tasks table** — `timeout_scan` (re-delivers in-flight events past TTL) is stale. Pull-only removed in-flight tracking. Update or remove this row.

9. **[MEDIUM] Fix §13.5 legacy code description** — permission-table code and `responsibility.md` reads are already removed from harness.py. Update §13.5 to say: "The legacy permission-table code has been removed (#11331 unified `target_role` → `target_alias`). The remaining gap is that `POST /work/assign` is not yet implemented — see F-02 / §4.3."

10. **[LOW] Fix §4.2 table path parameter names** — use `{role}` to faithfully track current code (matching harness.py:3315, 3391). The semantic note explaining that the VALUE is an alias can remain; but the table `{alias}` token is misleading.

11. **[LOW] Update §13.7 zombie gap** — note that `progress_liveness()` is now implemented in shadow/observational mode (harness.py:407); the gap is now "not yet driving reboot decisions" not "not yet implemented". Cite shipped slices.

12. **[LOW] Fix §9 table** — `.event-state.json` Purpose column: remove "in-flight events" (removed by #11165), add "EAD last-seen timestamp (`ead_last_seen`)".

### (B) CODE changes — skill-owned

Priority ordered:

1. **[HIGH] Implement `POST /work/assign`** — §4.3 fully specifies the endpoint (request body `{issue_number, target_alias, event_context}`, alias-existence-only validation, emit `assigned-to` event, 200/404/400 responses). The target architecture in AGENT-RUNTIME §8.3 depends on this endpoint. This is the only HIGH-severity code gap.

2. **[MEDIUM] Promote `progress_liveness()` from shadow to decision driver** — harness.py:407 method exists but its comment says "SHADOW / OBSERVATIONAL this slice — does NOT yet drive the reboot decision." Wire it into `update_health` to replace or augment PID-only liveness (#12271 slice d).

3. **[LOW] Generalize `/human/queue` to `/queue/{alias}`** — §4.4 and §13.6 document this migration. harness.py:3533 has only `/human/queue`. Rename route, parameterize status-label filter, add 301 redirect from old path.

---

## 5. Summary of Mismatches by Category

### Routes present in code but absent from doc
- `POST /restart` (#12825) — HIGH
- `POST /merge` (#6126) — MEDIUM
- `POST /hooks/session-end` (#12418) — MEDIUM
- `POST /hooks/activity` (#12443) — MEDIUM
- `POST /hooks/pause` (#12458) — MEDIUM

### Routes documented but absent/changed in code
- `GET /events/in-flight/{alias}` — REMOVED by #11165, doc still lists it — HIGH
- `POST /work/assign` — documented in §4.3, not implemented — HIGH
- `POST /events/{event_id}/complete` — doc says "does not exist", code has 410 tombstone — HIGH (reclassified from prior audit HIGH-1)

### Status banner claim vs reality
- "§15 and §16 not yet implemented" — FALSE. 3 of the 5 hook routes are fully shipped — HIGH

---

## 6. Notes on Methodology

Every finding is grounded in either:
- A specific `@app.get/post` decorator line in `references/scripts/harness.py`
- A specific code comment that documents a removal (e.g. the #11165 tombstone comment at line 3432)
- A specific class attribute or method that confirms implementation

No findings are speculative. If a claim could not be confirmed from code, it is labeled CONFIRMED (if code matches doc) or identified by specific harness.py line.

The prior audit's HIGH-1 (`POST /events/{event_id}/complete`) is reclassified: the prior audit found the route as functional — current code (post-#11165) converted it to a 410 tombstone. The doc claim "no such endpoint" is still wrong (the route EXISTS, returns 410), but the prior audit's "route is functional and contradicts the doc" framing is now outdated. The route semantics changed.

The prior audit's HIGH-2 (`POST /work/assign` missing) remains STILL-VALID. This is the only unambiguous code implementation gap flagged as HIGH.
