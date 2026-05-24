# Working State

- **Task**: #10003 in-progress — interactive massage of docs/VAULT-ARCH.md; consolidation deferred behind doc-completion gate per plan-first rule
- **Status**: active; draft PR #10004 on branch squidsquad/pm/10003 (MERGEABLE); arch-closure audit + NEW sub-skill scope decision pending
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-24 16:42, cycle 1658)
- 1 PR open: #10004 (draft, MERGEABLE)
- 0 pending-test, 0 pending-ship, 0 external
- 1 approved (DM lane): #3
- 3 in-progress: #9965 (awaiting STOP-lift), #9968 (HELD), #10003 (active PM)
- 4 pending tasks (PM): #9996, #9998, #10001, #10009
- 1 pending (gated): #9966
- 2 planning (skill, stale): #9874, #9875
- 1 planned (skill, stale): #9845
- 6 issues at status:open: #9969, #9970, #10002, #10005, #10006, #10007
- shipped_since_bump = 8 of 10

## Plan-first gate (#feedback_plan_first)
No close/fold/umbrella moves until arch doc set is demonstrably complete + gap audit passes. Now also gated on sub-skill-scope decision below — many arch docs reference sub-skill model.

## NEW — Sub-skill surface scope (cycle 1658, awaiting human confirmation)

**Human proposal**: sub-skills (the `references/sub-skills/**` fragments) are internal composition units only — NOT a publicly authorable surface. External extension = normal Claude Skills (`.claude/skills/<name>/SKILL.md`), nothing SquidSquad-specific.

**Conflicts with prior captured decisions (memory)**:
- `project_subskill_directory` — "Sub-skills live in separate repos linked from a public directory website" → would be superseded
- `project_marketplace` — "Skill marketplace = Phase E demo + monetization vehicle (open core + paid premium sub-skills)" → conflicts, needs reframe or scrap

**Affects**:
| Item | Today | After |
|---|---|---|
| `docs/sub-skill-guide.md` | user-facing authoring guide | internal contributor doc |
| `docs/sub-skill-catalog.md` | reference for consumers | internal index |
| #4378 (capabilities-vs-sub-skills section) | Tier 1 close-via-doc gap | de-prioritized (internal-only distinction) |
| Sub-skill directory website | active Phase E item | scrapped or pivoted |
| Marketplace project | open core + paid premium sub-skills | reframe as Claude Skills marketplace, or scrap |
| Public-launch story | mentions sub-skill authoring | must not advertise sub-skill authoring as a feature |

**4 questions surfaced to human**:
1. `docs/sub-skill-guide.md` placement: keep in `docs/` as internal contributor doc, or move to `references/CONTRIBUTING-sub-skills.md`?
2. Does the marketplace project survive in any form?
3. Public-launch focus (project_going_public_focus) — does this affect v1.0.0 launch materials?
4. Capture as decision-note (vault/memory) now vs. file as formal Pending task with discussion phase?

## Arch-closure audit (still in flight)
Proposal posted to umbrella #9968 (cycle 1654) with 21 tickets in 4 tiers.

### Tier-1 older-four audit findings
- **#4082** → OBSOLETE: designer role removed
- **#4085** → DISPOSITION RECORDED: fold into #10001 gap-audit (cycle 1656)
- **#4378** → partial; awaiting disposition; now likely re-tiered DOWN due to sub-skill scope decision above
- **#7694** → OBSOLETE

### Pending human input (carried forward)
1. Sub-skill surface scope confirmation + 4 questions (NEW, cycle 1658) — gates downstream items
2. #4378 disposition (may be re-tiered)
3. Approval to update #9968 umbrella comment with corrected rationales
4. Whether to walk newer Tier-1 four (#9968, #8702, #9969, #9970)
5. Tier 2 case-by-case pass

## Doc set status
- ARCHITECTURE.md (280 lines)
- AGENT-RUNTIME.md (1059 lines)
- COMPOSE-ARCHITECTURE.md (1042 lines)
- INSTALLER-ARCH.md (511 lines)
- VAULT-ARCH.md (529 lines, in PR #10004)
- sub-skill-catalog.md (281 lines)
- sub-skill-guide.md (322 lines)
- Possibly missing: event-arch (was authored, archived?), harness-arch (per #9874)

## #10003 next-step menu (still awaiting human pick)
- Continue VAULT-ARCH polish (sections 4-12 untouched)
- Switch to a different arch doc
- Run first-pass gap audit on current doc set
- Add capabilities section to sub-skill-guide.md (closes #4378 inline) — now lower priority
- NEW: file sub-skill-scope decision as formal task + run intake
