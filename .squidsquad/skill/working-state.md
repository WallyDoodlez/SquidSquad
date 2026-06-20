# Working State

- **Task**: **#11140 IN-PROGRESS** — RCA done + design LOCKED (comment posted), implementation pending fresh budget (CQ-gated, 6 source files, 4-role recompose). FOUR harness fixes delivered this session; no open HIGH items remain.
- **Updated**: 2026-06-20 (skill — event-mode; 4 harness fixes done, #11140 design locked)
- **Quiet Cycle Counter**: 0

## #11140 — RCA + LOCKED DESIGN (resume target)
Add orientation prose under each major composed H2 (Identity/Responsibility/Soul/Project Context/Agent Functions/Vault). Mechanism: `v2_link_stage.emit_v2_linked` (v2_link_stage.py:165) emits `## {slot}\n\n{body}`; orientation = leading para of the lowest-ordinal L1 source per slot.
- **L1 files exist** for identity/SOUL/instructions/vault (`references/roles/*.md`) → prepend 1-2 sentence orientation para to each (1 edit → all 4 roles).
- **responsibility + project-context have NO L1** → create new L1 orientation-only files `references/roles/responsibility.md` + `references/roles/project-context.md` (slot: + ordinal LOWER than role-level L2; body = orientation para only).
- **CQ-gated** → spec 11140 (fresh agent states each section's purpose from orientation alone). Fleet impact: L1 edits change all 4 composed CLAUDE.md → recompose ×4 + verify each H2 has prose; deploy-signal propagates.
- Steps: author paras → 4 edits + 2 new L1 files → compose.py deploy ×4 + verify → CQ spec → DS review → full gate. Use `git switch -c squidsquad/task/11140` BEFORE editing ([[feedback_create_branch_before_code_edits]]).

## DELIVERED this session (2026-06-20) — harness reliability cluster
1. **#12294 SHIPPED + CLOSED** — .claude-pid authoritative across harness restart (image-verified liveness C+A). PR #13033 merged. `process_utils.is_claude_process_alive` / `image_name_for_pid` now on main. Residual psutil orphan re-adoption → **#13034** (human decision).
2. **#13032 pending-test** — deploy-signal halt must END session (/quit) so respawn isn't singleton-blocked. PR #13037 merged to main. Part A contract (CQ 13032 3/3) + Part B respawn PID-death wait + honest-fail. Follow-ups (respawn outside _deploy_lock F3 + refresh claude_pid post-spawn F4) → **#13036**.
3. **#12409 pending-test** — frequency-based slow reboot-loop breaker (lifetime-agnostic, complements #12244). PR #13039 (merged to main). Asks 2/3 routed → #12271 / #12363; inert-framing → #12820.
4. **#12363 pending-test** — kill process TREE/GROUP in `_kill_process` so the Monitor-spawned event_poll.py sidecar is reaped (Windows /T; POSIX killpg w/ own-group safety fallback). PR #13040. DS review NO_FINDINGS.

All four: full static gate 0 failures; DS/Claude review cycles folded per commit. NOTE: feature-branch discipline — twice slipped editing code on main this session; saved memory [[feedback_create_branch_before_code_edits]]. Always `git switch -c squidsquad/task/<n>` before code edits.

## SECONDARY in-progress (parked)
- **#12451** (status-bar) S1+S3 on branch (PR #13024); S2 PARKED on PM CQ-AC via **#13031**. Resume S2 when PM lands the CQ-coverage AC.

## Gated / parked (externally blocked)
- **#12801** (Textual TUI) — needs textual dep + interactive terminal.
- **#12493** (pipeline-sentinel HALT) — PR #12494 HELD pending §8.3 backstop (PR #12507 unmerged).
- **#12450** (installer unit-test strategy) — S3/S4 PM-gated.

## NEXT actionable (open, non-urgent)
Medium: **#11140** (composed CLAUDE.md header orientation prose — CQ-gated; skill-domain doc/instruction, lower blast), **#10540** (DM batch-ship race), **#12495** (medium), **#12854** (medium — part-1 folded into #12451).
Low: #12971/#12861/#12846/#12747/#12519/#11716.
Pending (human-gated): #302, #303 (low).

## Recurring meta-risk
Clone chronically behind origin. Always `git pull --ff-only` before compose/commit. Push via `git -c credential.helper='!gh auth git-credential' push` (manager helper wedges silently). Feature work on `squidsquad/task/<n>` branch; working-state commits direct-to-main (#11511 guard).

## Improvement Scan
Status: eligible (idle). Last completed: (none — productive session).
