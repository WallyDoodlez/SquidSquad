# Working State

- **Task**: #9968 Phase 2 discussion mid-flight with human; key new dimension surfaced — L4 as runtime-writeable layer. Triaged #9970 (composed-output drift, DM-filed) as concrete evidence for #9968.
- **Status**: blocked on human (Phase 2 clarification continues)
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-23 12:23)
- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external
- 1 approved (long-running): #3 (DM lane, going-public) — no movement since 2026-05-21
- 2 in-progress:
  - #9965 (6274.2 — skill cycle 1305: AC2.2 phase 11 shipped, branch 18 commits, DS boundary review running)
  - #9968 (compose pipeline + composed-output structure review — Phase 2 mid-discussion)
- 1 pending (gated): #9966 (6274.3) — blocked on 6274.2 merge + 30d window
- 3 issues at status:open (queued, all related to compose-pipeline family):
  - #9967 (event-bus cursor bug) — gated behind 6274.2
  - #9969 (manifest.md naming) — subsidiary to #9968
  - #9970 (composed CLAUDE.md drift from #9925) — NEW; concrete evidence for #9968; resolution falls out of Phase 2; interim PR-check is a candidate quick-win
- All 4 agents healthy
- shipped_since_bump=6 of 10 — under threshold

## #9968 Phase 2 discussion state (cycle 1606)

### LOCKED so far
- **Authoring contract** (cycle 1604 Q2): each sub-skill declares slot + ordinal; compose.py sorts and merges.
- **L4 operations** (cycle 1606 Q2): L4 sub-skills support op = replace | insert-after | insert-before | append, with target = <step-id>. Override + interleave + append (full power).
- **L4 is runtime-writeable by the agent** (NEW this cycle, human directive): when human gives new instructions in conversation, agent decides whether they override existing L1-L3 step OR interleave between steps, persists decision to L4 with structured frontmatter, runs compose so the canonical ordered checklist updates. This means L4 evolves continuously, not just at install time. Architectural shift — much bigger than original Phase 1 scope. Bears on existing memory feedback files (would migrate into L4 or coexist).

### Tentative top-level structure (human is still clarifying)
```
## Identity        ← function, team SquidSquad, harness-governed
## Soul            ← inlined directly (not a reference link)
## Instructions    ← ONE ordered checklist; composed from L1-L4
                     with L4 override/interleave power; agent reads
                     top-to-bottom and executes
## Project Context ← project-specific facts
## Vault           ← description of shared memory layer
```

### PENDING clarification
- Where do today's protocols (Issue Filing, Task Lifecycle, Discussion, Working State, Vault commands) and rules (What You Must Never Do, File Conventions, Status Line) live in the new structure?
  - PM's tentative proposal: procedures fold into Instructions as sub-procedures; constraints/conventions get a small Constraints section (or fold into Identity).
- Confirmation of L4 runtime-write semantics (PM restated; human to confirm).

### Next PM action
- Wait for human clarification on protocols/rules placement + L4 runtime-write confirmation.
- Then write CONTEXT-9968.md (locked decisions) → DS-review → present for approval gate.
- Phase 2 discussion + write should sequence with #9965 shipping (which is rewriting the same L1-L4 files).

## #9970 — concrete evidence for #9968 (NEW this cycle)
- DM cycle 1314 doc scan found: f3a0e94e (#9925 4-layer responsibility model) changed 45 sub-skill/role files but did NOT include regenerated composed outputs. Net delta: dm/CLAUDE.md +75, qa/CLAUDE.md +77, skill/CLAUDE.md +43 / -13.
- Root gap: workflow has no checkpoint that enforces source-output sync. Sub-skill source edits can ship without composed outputs being committed; agents read pre-#9925 CLAUDE.md until next recompose.
- 3 suggested directions (all inside #9968 Phase 2 scope): PR-check, auto-recompose on merge, pre-ship gate.
- PM stance: hold-and-link to #9968; consider PR-check as interim quick-win.
- DM correctly preserved the drift as a reproducible artifact (did NOT silently recompose).

## #9965 progress trail (skill cycles 1296-1305)
- 1296-1300: AC2.2 phases 1-6b (path-only refs → template routing → Python role-sets → D11 prose → foundational L3 prose → large-body prose sweep)
- 1301: DS review of phase 2.2.2-3 boundary; filed #9969 out-of-scope
- 1302: F11 boundary loop CLEAN (DS NO_FINDINGS); branch 14 commits
- 1303-1304: (cycles passed; details in skill working state)
- 1305: AC2.2 phase 11 shipped (9130f8a4) — pm/* + dm/* + common/* prose audit, 16 files, 48 substitutions across 2 passes; down from 39 stale grep hits to 0 (only 2 intentional dual-aware-shim refs remain); pm/task-intake.md (23 subs), pm/responsibility.md (6), pm/pipeline-sentinel.md (7). Branch at 18 commits. DS boundary review running.
- Still ahead: F5/F6 (manifest.md composition-order), phase 7 (compose.py shim-docstring), phase 8 (mandatory-team enums + wizard D4), phase 9 (WIZARD.md + wizard.py), AC2.3 (L4 stub renames), AC2.4-2.7 (wizard work), AC2.8 (live-system smoke), AC2.9 (cutover-date populator as last commit)
- No PR yet per D9 full-sweep-before-PR

## Cursor advancement note (unchanged)
- Last Processed Event ID stays at df9f33751a6a — bus refuses to surface events newer than that cursor until #9967 is fixed

## #9966 — gated, do not approve yet (unchanged)
- Conditions to unblock: (a) 6274.2 PR merged, (b) cutover date in migration-6274-cutover vault note has passed
