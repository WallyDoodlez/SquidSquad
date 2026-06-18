# QA-RESULTS #12750 — Plan-in-PR (L2 instruction)

## Verification (cy315, 2026-06-17) — verdict: PASS → pending-ship (DM)
Branch squidsquad/task/12750 @ origin tip, PR #12751 (the dogfood — this task ships through its own
plan-in-PR flow). All 7 ACs pass; the git_ops state-guard exemption is verified narrow.

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | ✅ PASS | task-intake.md Phase 3B: branch FIRST (`task-begin`, branch-before-write to avoid checkout clobber) → write plan to `.squidsquad/[PM_ALIAS]/planning/[N]-body.md` → commit 1 `plan(#[N]): [title]` → push + open DRAFT PR. Explicit "Never commit the plan straight to `main`"; "do not add other `.squidsquad/` state". |
| TC2 | AC2 | ✅ PASS | task-pickup.md step 4: "Adopt the plan-seeded branch … checks out that EXISTING branch. Do NOT create a fresh branch; your implementation commits ride on top of the plan commit." Step 10: flip draft PR to ready (`pr-ready`) then task-end. |
| TC3 | AC3 | ✅ PASS (structural; full co-location at DM merge) | `git log main..HEAD --reverse`: commit 1 = `23b7b244e plan(#12750): plan-in-PR …`; code commits on top; plan body `12750-body.md` + code both in PR #12751. On merge the plan lands in main co-located — the dogfood IS the sample merge. |
| TC4 | AC4 | ✅ PASS | AGENT-RUNTIME / ARCHITECTURE describe only the STATUS state machine + label routing — no "PM commits the plan file to main" description exists, so grep-clean by default ("if applicable" met). |
| TC5 | AC5 | ✅ PASS | `installer-files.txt` contains no `planning` / `*-body.md` paths — plan files stay project-local. |
| TC6 | AC6 | ✅ PASS | `compose.py deploy-all` green (dm 656 / pm 732 / qa 654 / skill 815; .local-config 4 agents). (task-intake/task-pickup are runtime-loaded sub-skills → composed CLAUDE.md unchanged, consistent with no deploy diff. The `Dev Agents:` warning is pre-existing config-field deprecation, unrelated.) |
| TC7 | AC7 | ✅ PASS | Authored `tests/comprehension/12750_spec.json`. Fresh **sonnet** PM (3/3) + worker (2/2), ZERO misreads: PM → plan onto task branch commit 1 / draft PR, never main, branch-first to avoid clobber, only plan body (no other state); worker → no, adopt existing plan-seeded branch, commit on top, plan body commit 1 = source of truth, RESEARCH/CONTEXT not on branch. |
| TC-GUARD | risk | ✅ PASS | `_is_plan_body` matches ONLY `.squidsquad/<role>/planning/<digits>-body.md` (4 parts, numeric stem). Carve-out is GUARD-LOCAL (`commit_code`/`commit_state`/`_auto_resolve` still treat plan bodies as state). 19/19 tests, incl. negatives (working-state, iterations, vault, RESEARCH/CONTEXT, non-numeric stem, wrong depth all NOT exempted) + `test_plan_body_survives_state_siblings_stripped` (merge-spiral protection intact). |
| TC-REG | regression | ✅ PASS | test_git_ops 146/146 + test_12750 19/19 (165). Compose/sub-skill surface: only the pre-existing #10360-blocked known failures (4× test_agent_boundaries L1-awareness + 1× test_compose_author_comments markers) — fail on main too; **zero NEW failures from #12750**. |

### Disposition
PASS — zero gaps. All 7 ACs have observable evidence; the dogfood (plan committed as commit 1 +
opened as a draft PR carrying the code) demonstrates the flow end-to-end. The git_ops guard exemption
is correctly narrow and cannot reintroduce the #11511 merge-spiral (state siblings still stripped).
Comprehension spec authored + committed (preserved). Merge deferred to DM (no closing keyword on PR
#12751); DM's merge is the AC3 co-location confirmation. Ship counter NOT bumped (DM owns).
