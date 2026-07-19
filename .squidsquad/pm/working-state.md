# Working State

- **Task**: #10003 (VAULT-ARCH.md v2 TRD rewrite — in-progress, resumable)
- **Status**: deploy-halt checkpoint
- **Updated**: 2026-07-18 22:14

_Lean shape per #13562/#13579 (≤8KB). History in git._

## Session note (EVENT boot 2026-07-18 ~07:43 → deploy-halt ~22:15)

Long productive session, ended by a deploy-signal after #13565 (composed-prompt re-diet) merged — my own composed instructions changed (task-intake hot/cold split, event-mode-contract split), halting for recompose+respawn.

**Token-efficiency batch COMPLETE this session**: #13563 (BRIEFING diet), #13564 (cycle-input diet), #13566 (scan-history pruning), #13565 (prompt re-diet; I revised AC1 mid-flight after verifying the composed-size premise was wrong — v2_link_stage.py D2/Q-D2 never inlines sub-skill bodies) all SHIPPED. #13567/#13568 remain pending (blocked on #13561 P3 telemetry / measure-first).

**Vault-v2 redesign is the ACTIVE WORKSTREAM** (operator-collaborative, inline):
- Direction locked: port dmp-web's consumption-pipeline + telemetry-driven ranking as domain-agnostic infra; NOT its SWE taxonomy. PARAG kept for our own profile; hub layer (`systems/`) added. All in `.squidsquad/pm/planning/VAULT-COMPARISON-DMPWEB.md` §9+§10 (READ §10 FULLY on resume — it supersedes parts of §9).
- Decisions locked: drop `confidence`+`source`+`links` frontmatter; engine via Skill-tool invocation of the portable dmp-web extraction (2 verifications still pending, §10.3); telemetry = git-tracked per-harness-instance append-only JSONL shards + `merge=union` + read-time event-id dedupe (§10.5 — PM-recommended, operator was reviewing when deploy hit; CONFIRM LOCK-IN with operator on resume).
- TRD draft: `docs/VAULT-ARCH.md` v2 on branch `squidsquad/task/10003`, draft PR #13708. §1–§4 drafted+pushed. NEXT: §5 (BRIEFING, mostly survives) + §6 (telemetry — use §10.5 shard design, NOT §9.4). Then §7/§8 (blocked on the 2 Skill-invocation verifications), §9-cycle-integration, §10 target-state reframe, §11 gaps, §12–13.
- 10 superseded vault tickets closed this session; #10003 is the single TRD ticket (reopened, rescoped).

## HITL standing (advertise each check-in)

- **#13263** — behind-clone squash-merge, pending-human-review, KEEP OPEN.
- **Vault-v2 §10.5 telemetry design** — awaiting operator lock-in (asked right before deploy-halt).
- **~130 `status:pending` backlog tasks** awaiting operator go-ahead (advertise by count).

## PM queue

- work_queue(pm approved) = #10690 only, GATED (E7/#10686 OPEN) — not pickable.
- #10003 is my in-progress task (see above).
- Parked coord-holds: #11092 / #10839 / #9968.
- Idle-driver: cancelled at cap earlier; state in .subloop-driver.json; re-arm on next idle.
