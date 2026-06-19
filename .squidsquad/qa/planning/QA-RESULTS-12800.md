# QA-RESULTS-12800 — VERDICT: PASS → pending-ship

- **Verified**: 2026-06-19 11:10 (cy363, POLLING session)
- **Task**: #12800 (type:task/high, role:skill) — `human` as a non-agent role.
- **PR**: #12902, branch `squidsquad/task/12800` @ e3e83a0c7 (MERGEABLE/CLEAN, single commit, **NO closing keyword**).
- **Result**: **8/8 ACs PASS + CQ HARD GATE 5/5 PASS + zero regressions.** Append-only; not edited after publication.

## AC walk (independent live evidence)

- **AC1 (alias registers) — PASS.** `config.parse_aliases_registry` parses `('human',None)` for multiple humans in BOTH table (`| alias | role-class | L3 domain |`) and legacy bullet (`- **alias**: value`) forms. **Negative control**: an unknown role-class (`wizard`) is rejected → the acceptance gate is real, not over-accepting. `tracker.FEEDBACK_ROLES` includes `human` (harness.py:829); role labels are free-form `f"role:{role}"` → `role:human` valid. Role-class constants split: `AGENT_ROLE_CLASSES={pm,worker,verifier,dm}`, `NON_AGENT_ROLE_CLASSES={human}`, `ALIASES_ROLE_CLASSES=union`.
- **AC2 (compose skips human) — PASS.** `deploy_alias_v2('wallace'/'alice', registry=…)` → returns `None`, prints skip notice, writes **no** CLAUDE.md (verified `wallace/CLAUDE.md` absent). Guard at compose.py:1150 (`deploy_alias_v2`) + 1052 (`check_alias_staged_l4`); `deploy`/`deploy-all` treat `None` as clean no-op (2233-2236). Agents still compose — on-main `deploy-all` (shipped separately) updated all 4 agent CLAUDE.md (seen in this session's `git pull`).
- **AC3 (routing flip) — PASS.** Direct read of `harness._STATUS_ROUTING`: `pending-human-review` + `pending-human-setup` → `("role_class","human")` (was pm). `is_handoff` (harness.py:4174) requires `routing[1] in AGENT_ROLE_CLASSES`, so human is **excluded** → emits once for forge/audit, NO #12442 re-emit pileup (human not on bus). `_alias_for_role_class('human')` resolves via registry or falls back to `human`. Worker tests assert `target_alias=="human"` ×2 + no-reemit (real assertions, 48 EAD/routing tests green). `human-comment`→pm is documented (AGENT-RUNTIME §8.3) as **spec-only / not-yet-EAD-implemented** — pre-existing "unchanged" state, correctly NOT flipped.
- **AC4 (inline status bar) — PASS.** Live: `cycle.py status-bar-self inline ""` → current-state `inline|`; clear → `idle|`. Mechanism (`status_bar_self`, reads `SQUIDSQUAD_ROLE`) pre-existed; this task updated the **instruction text** in `references/roles/instructions.md` §8 + all four `references/sub-skills/roles/{dm,pm,verifier,worker}/ralph-loop-overview.md` to direct the self-write + clear-on-end + #9358-superseded.
- **AC5 (return path) — PASS.** `LEGAL_TRANSITIONS` + `ROLE_AUTHORITY`: `pending-human-review`→`in-progress` legal, authority `{pm,_assignee}`; `pending-human-setup`→`in-progress` legal `{pm}`. `work_queue("skill")` surfaces a re-assigned in-progress ticket (test #77, real assertion). This matches **locked design C2** (return path is human-mediated/inline — the agent is already awake during the inline turn, re-assigns to itself, and the forge queue is the resume mechanism). The skill correctly implemented C2 over the design doc's loose "assigned-to fires" parenthetical (a human is not on the event bus) and disclosed it. **Consistent — not a gap.**
- **AC6 (docs reconcile) — PASS.** AGENT-RUNTIME rev-17 added (records the code/doc-reconcile); §3 "Monitoring impact" reworded to mark #9358 superseded; composed CLAUDE.md carries async-no-pause (`Never Block on a Human` present in on-main `qa/CLAUDE.md`) + inline status-bar §8. No dangling refs introduced. **Non-blocking note → PM** (below).
- **AC7 (installer-files.txt) — PASS.** `git diff --name-status main...branch` shows **no added files** (all in-place edits) → `installer-files.txt` correctly unchanged.
- **AC8 (DS-audit) — PASS.** `.squidsquad/skill/planning/DS-REVIEW-12800.md` present, **NO_FINDINGS**, 8 traced paths (composition / health-poll / spawn-stop-restart / EAD routing / hooks / doc-consistency / role-class-set consistency / `_get_entry_file_for_role` fallback unreachable for human).

## Comprehension HARD GATE — 5/5 PASS
Authored `tests/comprehension/12800_spec.json` (verifier-owned, independent). Fresh sonnet agent given ONLY the modified instruction text (no prior context). All 5 CQs correct, no anti-patterns: CQ1 self-write `inline` because wrappers don't fire; CQ2 clear on inline-session end → normal idle/working; CQ3 #9358 superseded (explicit state replaces stale-bar tolerance); CQ4 don't wait — assign ticket to `human` alias + pending-human-* via transition, continue; CQ5 agent-mediated return, human never makes the forge transition.

## Regression
- `tests/test_harness.py` full: **282 passed**.
- `test_config_aliases_registry_10385` + `test_compose_a2f_10492` + `test_cycle` + `test_tracker` + `test_tracker_authority`: **235 passed**.
- `run_tests.py static` (junit-backed session-finish gate per #12408): **4621 gated tests PASS, 0 failures, 0 errors.** The 2 allowlist-excluded known-failures (`test_agent_boundaries`, `test_compose_author_comments_11142`) are pre-existing, blocked on OPEN #10360 — NOT introduced by #12800.

## Non-blocking finding → PM (subjective doc-consistency, PM-owned doc)
**AGENT-RUNTIME.md revision log has two entries both numbered "rev 16"** — line ~1343 (`2026-06-07`, #11328) and line ~1327 (`2026-06-18`, human-as-role design-lock). This is **pre-existing on main** (PR #12902 added only rev-17 + reworded §3; it touched neither rev-16 entry). "rev 16" is already cross-referenced for both #11328 and the human-as-role design across the corpus, so renumbering now would create *more* dangling refs. PM owns AGENT-RUNTIME; flagging for PM to decide. **Does NOT block #12800** (not introduced by this PR, not a dangling ref, not a live-spec contradiction).

## Disposition
- **VERDICT: PASS → pending-ship (DM).** Zero gaps.
- Merge **deferred to DM** — PR #12902 has NO closing keyword → a QA-merge would NOT auto-close, and DM owns delivery + the post-merge L1 recompose (instructions.md/SOUL composed-output change ⇒ all-roles restart-required).
- **Ship counter NOT bumped** — DM owns the counter.
- TEST-PLAN + QA-RESULTS + `12800_spec.json` committed to main.
