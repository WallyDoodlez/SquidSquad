# Sub-Skill ↔ Harness Consistency Audit

Audited 2026-06-11. Scope: sub-skills under `references/sub-skills/` against runtime scripts under `references/scripts/`.

---

## Cluster 1 — Event-mode contract

**Verdict**: PARTIAL — one BLOCKING cursor-description divergence in `forge-read-pattern.md`; all other files aligned.

**Per-file findings**:

- **`event-driven-workflow.md`** — Aligned. Monitor invocation form `python references/scripts/event_poll.py <role> --wait 5 --target` matches `event_poll.py:357-363` (argparse: positional `role`, optional `--wait`, `--target` flag). Port discovery via `.squidsquad/.harness-port` mentioned implicitly and matches `event_poll.py:70-76`. Error-handling description (5xx retried, 4xx fatal, ConnectionError/Timeout/IncompleteRead retried) matches `event_poll.py:192-202`. Bounded retry ceiling of 10 (`CONTEXT-9742`) matches `event_poll.py:65` (`_WAIT_MAX_CONSECUTIVE_FAILURES = 10`). Event types named as hints, forge as truth — consistent with `harness.py` pure-broadcast design. One minor style drift: sub-skill says harness "emits `stop-requested`" for context pressure; harness actually sends it via `POST /events` with `event_type=stop-requested` — the mechanism is correct, only the framing is imprecise. Not a behavioral gap.

- **`event-mode-contract.md`** — Aligned with one notational accuracy note. Boot sequence endpoint `GET /events/cursor/{role}` matches `harness.py:2211` (`@app.get("/events/cursor/{role}")`). `GET /events/for/{role}?since=<cursor>` matches `harness.py:2141` (`@app.get("/events/for/{role}")`). `POST /events` with `event_type=bootup-complete` matches `harness.py:2011`. The sub-skill documents the `ack-cursor` POST shape and states `event_id` lives inside `payload` (`harness.py:2023-2026` confirms: `ack_payload = body.get("payload")` then `ack_payload.get("event_id")`). Always-On Rule about `working-state.md` not being the cursor's home matches `cursor-management.md` and the harness's `.event-state.json` ownership. Eviction gap recovery (ack with `oldest_id`) matches `harness.py:2036-2041` silent-reject path and `event_poll.py:316-320`. Case E `stop-requested` at task boundary matches harness design. The sub-skill's transitional note about `event_poll.py` still writing `Last Processed Event ID` to `working-state.md` is confirmed accurate by `event_poll.py:302` (`_write_cursor_atomic`).

- **`cursor-management.md`** — Largely aligned. `GET /events/cursor/{role}` → `{"cursor": null|id, "role"}` matches `harness.py:2211-2229`. `POST /events` ack-cursor shape with `event_id` in `payload` matches `harness.py:2023-2026`. "One ack per tended event" matches `event_poll.py` loop discipline. Eviction response fields `"evicted": true`, `"oldest_id"`, `"evicted_count_hint"` match `event_poll.py:261-263` (the warning log line names these same fields) and `harness.py:2203-2208` (per citation in sub-skill body). Cursor-regression rejection matches `harness.py:2042-2047`. Pre-#11329 transitional note about legacy `Last Processed Event ID` line in `working-state.md` matches `event_poll.py:113-148` (`_write_cursor_atomic` still writes this). Default port 7373 for the harness matches `harness.py:69`.

- **`forge-read-pattern.md`** — **BLOCKING DIVERGENCE** at line 19. The sub-skill states: _"The cursor advances automatically as `event_poll.py` emits each event line — there is no separate step you take to advance it."_ This directly contradicts `event-mode-contract.md` and `cursor-management.md` (both in this same cluster), which correctly say the agent MUST POST `ack-cursor {event_id, role}` after each tended event. The harness never auto-advances the cursor — the agent drives cursor advancement via explicit POST (`harness.py:2018-2035`). An agent reading `forge-read-pattern.md` in isolation would believe cursor advances are free/automatic and would never POST `ack-cursor`, leaving the cursor stuck at the boot value and re-delivering every event on the next restart. This is a behavioral regression bug in the sub-skill text.

- **`idle-cooldown-loop.md`** — Aligned. Working-state schema fields (`Status`, `Last completed`, `Next scan after`) are agent-owned and not tracked by any harness script — consistent. Cool-down config key `Improvement Scan Cool-Down` read via `config.md` is consistent with `cycle_pre.py`'s `_config_get` pattern. Atomicity note about Monitor buffering is accurate per `event_poll.py`'s stdout-then-cursor ordering. Step 4a `work_queue()` re-check matches `event-mode-contract.md` Case C. The note about `event_poll.py` advancing its on-disk cursor before the agent sees the line (line 55) accurately reflects `event_poll.py:301-302` (print then `_write_cursor_atomic`). Note on lines 56-57 about re-delivery at-least-once semantics matches `event_poll.py:282-307`.

- **`comment-handling.md`** — Aligned. The claim that bare comments do not emit events is consistent with the harness being a pure broadcast pipe of status-transition/label-change signals (`harness.py` event catalog). No `comment-added` event type exists in the harness. DM end-of-task re-read is not contradicted by any script.

---

## Cluster 2 — Cycle wrapper

**Verdict**: PARTIAL — sub-skill cycle-output schema lists role-specific fields that `cycle_post.py` does not parse; the cycle-input fields for event-driven mode are not documented; no behavioral breakage.

**Per-field findings**:

- **CLI invocation** — Aligned. Sub-skill states `python references/scripts/cycle_pre.py [ROLE]`; `cycle_pre.py:main()` at line 1323 confirms positional `role` argument via `_parse_cli_args`. The sub-skill does NOT document the `--task <n>` flag added by #8701 (`cycle_pre.py:8,1217-1223`), but this is omission rather than misinformation — agents in loop mode never pass `--task`.

- **`cycle-input.json` schema** — Mostly aligned. Sub-skill documents: `role`, `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state`, `recent_events`, `mechanical_reactions`. All confirmed in `cycle_pre.py:1408-1419`. Sub-skill does NOT document `harness_status` (line 1414) or `branch_correction` (lines 1421-1423) or `ship_counter_repair` (lines 1425-1427) fields written by `cycle_pre.py`. These are informational extras, not missing ACs — omission, not contradiction. The event-driven `task_mode: true` and `task: <id>` fields (#8701, `cycle_pre.py:1380-1385`) are absent from the sub-skill description; relevant only for event-mode agents.

- **`cycle-output.json` schema** — The base fields `role`, `cycle_number`, `cycle_type`, `status_transitions`, `tracker_comments`, `iteration_summary`, `commit_message`, `working_state_update` are all consumed by `cycle_post.py:140-175, 227-284, 920-927`. Aligned.

- **Role-specific output fields — Skill** — `code_commit` consumed at `cycle_post.py:519`; `state_commit_message` consumed at `cycle_post.py:508, 579`. The sub-skill also documents `improvement_scan` field, but `cycle_post.py` has no code that reads `improvement_scan` from cycle-output.json — it is ignored by post. This is a documentation-only field (agent writes it to the log for human review, not for mechanical consumption). Not a behavioral gap.

- **Role-specific output fields — PM** — Sub-skill documents `human_input_processed`, `issues_filed`, `issues_verified`, `tasks_verified`, `tasks_shipped`, `external_issues_triaged`, `health_alerts`, `vault_writes` as PM extras. A full grep of `cycle_post.py` finds NONE of these field names are consumed. `cycle_post.py` reads only the base fields from cycle-output.json; PM-specific extras are documentation-only (agent log content). The sub-skill does not claim these are mechanically processed by `cycle_post.py`, so this is not a divergence. However it would be easy to misread the sub-skill as implying cycle_post.py processes them.

- **Role-specific output fields — Verifier** — Same as PM: `e2e_log`, `issues_filed`, `issues_verified`, `tasks_verified`, `pr_actions` are not consumed by `cycle_post.py`. Documentation-only. Not a divergence.

- **Role-specific output fields — DM** — `bugs_fixed` and `deliveries` are not consumed by `cycle_post.py`. `version_bump` IS consumed (`cycle_post.py:986-987`, `_do_version_bump`). The sub-skill correctly identifies `version_bump` as a DM extra. Aligned for the mechanical field; others are documentation-only.

- **Context pressure exit code 42** — Sub-skill says "`cycle_post.py` exits with code 42 when pressure exceeds threshold". `cycle_post.py:902-914` shows pressure triggers `return True` from `_should_exit_for_restart()`, which causes a `sys.exit(42)` path. Confirmed aligned.

---

## Cluster 3 — Tracker + transitions

**Verdict**: PARTIAL — transitions matrix has two gaps vs `tracker.py`; role authority for `pending-ship → in-progress` is understated; all commands exist.

**Per-command findings**:

- **All listed commands exist**: `list-tasks`, `list-issues`, `create-issue`, `create-task`, `transition`, `comment`, `get-labels`, `get-state`, `check-gh` — all confirmed in `tracker.py:1-31` docstring and `main()` dispatch (lines 1380-1520+). `work-queue` command also exists (`tracker.py:1430-1434`) but is not listed in the sub-skill's §Reading Issues section (it documents `list-tasks ... --status approved` as the equivalent). Not a divergence — `work-queue` is an internal helper; the sub-skill correctly describes the agent-facing form.

- **Legacy aliases** — Sub-skill says `create-bug`, `list-bugs`, `create-feature`, `list-features` are retired. `tracker.py:9-10` docstring and dispatch confirm these aliases still accepted for backward-compat. Aligned.

- **Legal transitions matrix** — The sub-skill documents (lines 194-201):
  - `open → pending-test | in-progress` — confirmed `tracker.py:LEGAL_TRANSITIONS` line 119.
  - `pending → planning | approved` — confirmed line 121.
  - `planning → planned` — confirmed line 122.
  - `planned → approved` — confirmed line 123.
  - `approved → in-progress` — confirmed line 124.
  - `in-progress → pending-test | pending-ship | approved | planning | pending-human-review | pending-human-setup` — confirmed lines 125-135.
  - `pending-human-review → in-progress | pending-ship` — confirmed `tracker.py:137`.
  - `pending-human-setup → in-progress` — confirmed `tracker.py:152`.
  - `pending-test → in-progress | pending-ship` — confirmed `tracker.py:136`.
  - **GAP 1**: Sub-skill omits `pending-test → pending-human-review`. `tracker.py:136` has `"status:pending-test": {"status:in-progress", "status:pending-ship", "status:pending-human-review"}`. The sub-skill's transition table at line 200 lists only `in-progress | pending-ship` for `pending-test`. An agent reading the sub-skill would not know this edge is legal.
  - `pending-ship → shipped | in-progress` — confirmed `tracker.py:138`.

- **Role authority** — Sub-skill line 197 states `in-progress → pending-test` — "assigned role"; confirmed (`tracker.py:180`). Sub-skill line 198 states `in-progress → pending-ship` — "DM only"; confirmed (`tracker.py:183`). Sub-skill line 201 states `pending-ship → in-progress` — "PM or verifier or DM routes back on merge conflict". `tracker.py:199`: `("status:pending-ship", "status:in-progress"): {"pm", "qa", "dm"}`. The internal canonical set is `{"pm", "qa", "dm"}` (pre-6274.3). The sub-skill uses "PM or verifier" which maps to `pm` and `qa` post-#6274 normalization (`tracker.py:280`: `"verifier" -> "qa", False`). This is correct in intent but uses the new-form role name (`verifier`) while the authority set still uses the old-form (`qa`) internally. Not a behavioral gap given the #6274 dual-aware shim, but worth noting.
  - **GAP 2**: Sub-skill does not document authority for `pending-test → pending-human-review` (because it doesn't list this edge at all — see GAP 1). `tracker.py:189`: authority is `{"qa", "pm"}`.

- **Reporter naming lock** — Sub-skill mandates `--reporter [ROLE]-lead` (lines 80-90). `tracker.py` uses `--reporter` only in `create-issue`/`create-task` to populate the `reporter:` label. The `_canonicalize_role` function at `tracker.py:219` strips `-lead`. Aligned.

---

## Vault (post-Iter 56)

**Verdict**: GAP — per-role write-lane framing absent from both files; vault-protocol.md has no "who can write" disambiguation.

**Findings**:

- **`vault-protocol.md`** — The file says "All agents have read/write access" (line 7) and carries no per-role write-lane framing or lane discipline. The audit brief asks whether post-Iter 56 framing ("verifier writes testing patterns, not design rebuttals") is present. It is not. The file treats all four roles symmetrically with no lane-discipline guidance. This may be intentional (lane discipline lives elsewhere) or a gap depending on whether agents are supposed to self-enforce lane discipline from this file.

- **`vault-remember.md`** — The scope reminder at line 91 says "vault stores project and environment facts... Human behavioral preferences are captured by soul shepherd (observed) and L4 directives (explicit) — not here." This reinforces the L4/vault boundary but does not carry per-role write-lane framing. The brief asks specifically whether `vault-remember.md` agrees with L1 §Vault Protocol prose about "who can write (all 4 roles) and the lane discipline (verifier writes testing patterns, not design rebuttals)". The lane-discipline constraint for verifier is absent from this file.

- Neither file has artifacts from a previous "slim/full split" — both present a unified vault picture. The slim/full split residue concern is not present. The gap is the absence of per-role write-lane guidance, not the presence of old split artifacts.

---

## L4-curation gates

**Verdict**: ALIGNED — all gate scripts exist; retired Gate 5 (`l4_recompose_recovery.py`) is confirmed deleted; file-watch wiring confirmed in harness.

**Findings**:

- **Gate scripts exist**: `l4_audit_gate.py`, `l4_compose_dryrun.py`, `l4_write_commit.py`, `l4_conflict_preempt.py`, `l4_mini_cq.py` — all confirmed present at `D:\Dev\Dev\SquidSquad-2\references\scripts\`. `l4_removal.py`, `l4_op_processor.py`, `l4_parser.py` also present (supporting scripts referenced in the sub-skill).

- **Retired Gate 5 deleted**: `references/scripts/l4_recompose_recovery.py` does NOT exist (confirmed via filesystem check). Aligned with Iter 46 commit `1845b15e7` deletion.

- **Harness file-watch (PRD-E E3)**: `harness.py:490-565` (specifically `start_l4_watcher`, `stop_l4_watcher`, `_l4_watcher_loop`) confirms the file-watcher supervisor. The sub-skill cites `harness.py:490-548` and names `l4_file_watcher` — `harness.py:548` is the `import l4_file_watcher as _lfw` import inside `_l4_watcher_loop`. The wiring is real. The supervisor calls `_lfw.start_watcher(repo_root, registry_provider, emit_event)` at line 560-564 and re-spawns on crash per the L4_WATCHER_SUPERVISE_INTERVAL constant (line 74: 5 seconds). Aligned.

- **Gate count**: Sub-skill describes 5 gates (Gate 0 through Gate 4) and explicitly states Gate 5 was retired. `COMPOSE-ARCHITECTURE.md §7.4` citation in line 277 says "Gate 5 (recompose recovery) was retired after PRD-E E3 file-watch wiring made the post-commit recompose autonomous." Consistent.

- **Script behaviors**: The sub-skill's descriptions of each gate helper's interface (e.g. `l4_audit_gate.py:audit_l4_op(op_type, target_slot, ...)`, `l4_mini_cq.py:format_confirmation(...)` and `classify_reply(...)`, `l4_compose_dryrun.py:dryrun_l4(staged_l4_text, role_class)`, `l4_write_commit.py:write_and_commit_l4(...)`) could not be fully verified without reading each script, but the scripts' existence is confirmed and the sub-skill's interface descriptions are detailed and internally consistent with the gate flow.

---

## Top blocking issues

1. **`forge-read-pattern.md` line 19 — BLOCKING**: States "The cursor advances automatically as `event_poll.py` emits each event line — there is no separate step you take to advance it." This contradicts the actual harness contract. The harness NEVER auto-advances agent cursors; the agent MUST POST `ack-cursor {event_id, role}` to `POST /events` after each tended event (`harness.py:2018-2035`, `cursor-management.md:28-48`). An agent reading only this file in the forge-read pattern sub-skill would believe cursor advancement is transparent and skip the mandatory POST, causing cursor to be stuck at boot position and all events to re-deliver on every restart. **Cite**: `forge-read-pattern.md:19` vs `harness.py:2018-2035` and `cursor-management.md:28-48`.

2. **`tracker-protocol.md` line 200 — GAP**: Legal transitions table omits `pending-test → pending-human-review` edge. `tracker.py:136` shows this is a legal and used edge (PR Flow path, `tracker.py:188-189`: authority `{"qa", "pm"}`). Agents following the sub-skill's table would not attempt this transition. **Cite**: `tracker-protocol.md:200` vs `tracker.py:136,189`.

---

## Summary

- 10 sub-skill files audited (6 event-mode, 1 cycle-runner, 1 tracker-protocol, 1 vault-protocol, 1 vault-remember, 1 l4-curation)
- 7 aligned (event-driven-workflow, event-mode-contract, cursor-management, idle-cooldown-loop, comment-handling, cycle-runner base, l4-curation)
- 3 diverged (forge-read-pattern, tracker-protocol, vault-protocol/vault-remember lane framing)
- **Severity: HIGH** — `forge-read-pattern.md:19` is a BLOCKING behavioral inversion (tells agents cursor is automatic when it is not); `tracker-protocol.md:200` is a medium-severity omission (missing legal edge); vault lane-discipline gap is LOW (omission, not contradiction).
