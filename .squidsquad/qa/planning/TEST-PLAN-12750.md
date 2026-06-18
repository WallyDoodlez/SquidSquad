# TEST-PLAN #12750 — Plan-in-PR (L2 instruction)

**Derived from the issue's 7 ACs.** L2 instruction change (PM + worker sub-skills) → comprehension gate
(AC7). Note: the plan-in-PR instructions live in RUNTIME-loaded sub-skills (`task-intake.md`,
`task-pickup.md`), referenced by `→ run sub-skill` markers — NOT inlined in composed CLAUDE.md, so the
CQ quiz gives the agent the sub-skill content (follows the markers).

## ACs
- **AC1**: Composed PM instructions → end-of-planning: branch `squidsquad/task/<n>` + commit plan (`plan(#n)`) + open DRAFT PR; plan NOT committed to main.
- **AC2**: Composed worker instructions → adopt the existing plan-seeded branch; don't recreate; impl rides on the plan commit.
- **AC3**: On PR merge, plan file present in main co-located with the implementation (verify on a sample merge).
- **AC4**: Descriptive lifecycle docs (AGENT-RUNTIME; ARCHITECTURE if applicable) match — zero stale "PM commits plan to main" (grep clean).
- **AC5**: Plan files remain project-local — not in `installer-files.txt`, not shipped.
- **AC6**: `compose.py deploy-all` green.
- **AC7**: Comprehension — fresh PM ("where does the plan go?" → task-branch commit 1 / draft PR, never main) + fresh worker ("do you create the branch?" → no, adopt existing).

## Risk-focused TC
- **TC-GUARD (key risk)**: the `git_ops.py` state-guard exemption for plan bodies must be NARROW — it must NOT reintroduce the #11511 merge-spiral. Verify `_is_plan_body` matches only `.squidsquad/<role>/planning/<digits>-body.md`, the carve-out is guard-local, and state siblings (working-state/iterations/vault) are still stripped.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | inspect task-intake.md Phase 3B | branch-first → write plan → commit 1 `plan(#n)` → draft PR; never main |
| TC2 | AC2 | inspect task-pickup.md | adopt existing branch, don't recreate, impl on top, flip to ready |
| TC3 | AC3 | branch commit order + PR contents | plan = commit 1, code on top, both in PR #12751 (merge co-location at DM ship) |
| TC4 | AC4 | grep AGENT-RUNTIME/ARCHITECTURE for plan→main | no stale plan-file→main description |
| TC5 | AC5 | grep installer-files.txt | plan/planning paths absent |
| TC6 | AC6 | `compose.py deploy-all` | green |
| TC7 | AC7 | author 12750_spec.json; fresh PM + worker quizzes | zero misreads |
| TC-GUARD | risk | inspect `_is_plan_body` + run guard tests | narrow exemption; siblings still stripped; 19/19 |
| TC-REG | regression | git_ops (146) + compose/sub-skill surface | no NEW failures |
