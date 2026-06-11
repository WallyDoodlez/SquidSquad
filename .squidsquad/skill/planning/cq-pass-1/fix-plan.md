# CQ Pass 1 — Consolidated Fix Plan

Date: 2026-06-11
Source findings: `findings-{pm,qa,dm,skill}.md` in this dir.

## Cross-role consolidation

| Issue | PM | QA | DM | Skill | Class |
|---|---|---|---|---|---|
| L2 flat-top legacy block | n/a | YES (Item 9 FAIL cause) | YES | YES (3 contradictions) | **CRITICAL** |
| step:cycle/ds-review marker typo | n/a | n/a | n/a | YES | **CRITICAL** |
| PM lacks step:cycle/context-pressure | YES (GAP) | n/a | n/a | n/a | DESIGN |
| PM L44 vs L195 RCA contradiction | YES | n/a | n/a | n/a | **CRITICAL** |
| Verifier vault read vs write | n/a | YES (FAIL) | n/a | n/a | **CRITICAL** |
| Verifier TEST-PLAN ownership in prohibitions | n/a | YES | n/a | n/a | MEDIUM |
| DM delivery:skip label vs Discussion | n/a | n/a | YES | n/a | **CRITICAL** |
| Tracker.py comment one-liner not inlined | HEDGE | HEDGE | n/a | OK | LOW |
| Cross-role create-issue command not inlined | n/a | HEDGE | n/a | OK | LOW |
| Commit-before-transition order not stated | HEDGE | HEDGE | HEDGE | HEDGE | LOW |
| Context-pressure working-state schema not inlined | n/a | HEDGE | HEDGE | HEDGE | LOW |

## Root-cause analysis

### Defect cluster A: L2 flat-top legacy block (affects QA/DM/skill)

`references/roles/{worker,verifier,dm}/instructions.md` lines 7-50 (varies) contain a flat cycle sequence that predates the L1 Steps 1-7 structured cycle. The flat-top duplicates `step:cycle/run`, `step:cycle/context-pressure`, `step:cycle/resume`, `step:cycle/checkpoint` and adds extra sub-skill markers that mostly belong elsewhere in L1 or in proper layered ops.

**Per-role unique markers in flat-top:**

| Sub-skill | Worker | Verifier | DM | Covered by L1 or L2 layered op? |
|---|---|---|---|---|
| `ralph-loop-overview` | yes | yes | yes | Already loaded by L1 POLLING boot block |
| `cycle-runner` | yes | yes | yes | Loop-mode contract; covered by `roles/<role>/ralph-loop-overview` runtime-loaded fragment |
| `context-pressure` | yes | yes | yes | Wrapper-side (cycle_post.py exits 42); L1 Step 7 self-restart describes agent response |
| `resume-working-state` | yes | yes | yes | L1 Step 2 |
| `interval-sync` | yes | yes | yes | Stale — loop interval is literal-substituted at compose; event mode has no interval |
| `triage-issues` | yes | — | — | L2 layered op `insert-after step:cycle/resume → step:cycle/triage-issues` (worker) |
| `verification` | — | yes | — | L2 layered op `### append → #### Step 7.1 step:cycle/verify` (verifier) |
| `issue-triage` | — | — | yes | L2 layered op `insert-after step:cycle/resume → step:cycle/issue-triage` (dm) |
| `delivery-packaging` | — | — | yes | L2 layered op `### append → #### Step 7.1 step:cycle/delivery-packaging` (dm) |
| `version-bumps` | — | — | yes | L2 layered op `#### Step 7.2 step:cycle/version-bump` (dm) |
| `doc-improvement-loop` | — | — | yes | L2 layered op `#### Step 7.3 step:cycle/doc-improvement` (dm) |
| `pr-merge-wait` | — | — | yes | L1 EVENT-mode contract block already includes `<!-- if role:dm -->` for this |
| `implement-tasks` | yes | — | — | L2 layered op `### append → #### Step 7.1 step:cycle/implement` (worker) |
| `pickup-comment-fidelity` | yes | — | — | **NOT covered** — needs new layered op |
| `improvement-scan` | yes | yes | — | L1 Step 6 has `improvement-scan-slim`; full scan via L2 `roles/<role>/improvement-scan` invocation in idle-cool-down loop |
| `vault-remember` | yes | yes | yes | L1 Step 6 cleanup invokes vault-remember inline |
| `vault-optimize` | yes | yes | yes | PM owns Step 6.5 `step:cycle/vault-optimize`; per catalog also worker; verifier/dm don't need |
| `git-commit` | yes | yes | yes | L1 Step 5 |
| `self-restart` | yes | yes | yes | L1 Step 7 |

**Fix**: delete the L2 flat-top in all 3 roles. Add one new layered op per role to preserve unique behavior NOT already covered:

- worker: add `insert-after step:cycle/pickup → step:cycle/pickup-comment-fidelity → pickup-comment-fidelity` 
- verifier: nothing additional (verification, vault-remember, improvement-scan all already covered)
- dm: nothing additional (all DM-unique sub-skills already via layered ops)

Cascading resolutions:
- **Verifier vault read/write FAIL** (Item 9): the flat-top's `vault-remember` invocation is gone; only L3 verifier read-only rule + L1 cleanup vault-remember remain. Verifier still has a residual concern: L1 Step 6 says "run vault-remember if real work occurred" but L3 says read-only. **Sub-fix**: add a verifier-specific exception note to vault.md L1 OR add to L3 verifier project-adaptation directing to skip vault-remember.
- **Skill dual step:cycle/resume**: gone after deletion.
- **Skill dual step:cycle/checkpoint**: gone after deletion.
- **DM orphan step:cycle/run**: gone.

### Defect cluster B: Step 7.2 ds-review marker typo (skill)

`references/roles/worker/skill/instructions.md:62`:
```
#### step:cycle/ds-review

→ run sub-skill: improvement-scan   <-- WRONG: copy-paste error
```

There is no `ds-review` sub-skill. The prose at L64 carries the DS-review instruction. The marker line is dead and misdirects.

**Fix**: delete the marker line. Prose stands alone.

### Defect cluster C: PM L44 vs L195 RCA contradiction

PM CLAUDE.md:
- L44 (Responsibility): "Does NOT do root-cause analysis when filing bugs. PM describes observed behavior + impact + reproduction; the assigned agent does the RCA as part of fixing."
- L195 (Project Adaptation Boundaries): "Never file a bug without investigating root cause first (Bug Discussion Flow)."

These directly contradict. "Bug Discussion Flow" is referenced but never defined anywhere in the doc.

**Fix**: clarify L195 to align with L44. The correct posture is: PM investigates enough to confirm observable behavior + impact + ownership domain, then files to the owning role for them to do the technical RCA. The reference to "Bug Discussion Flow" should be removed (orphan reference) or replaced with `→ run sub-skill: roles/pm/issue-filing` which is the actual flow.

### Defect cluster D: DM delivery:skip canonical signal

DM composed:
- Step 2.1 (line 458): "Check `delivery:skip` **label** before starting packaging."
- Delivery Flow (line 604): "If the task's **Discussion** contains `delivery: skip`…"

Different signals — label is the GitHub-native machine-readable convention used everywhere else (per Tracker Protocol + role:* labels). Discussion-comment as a signal is fragile (parsing required) and contradicts the deterministic-scripts-over-prose principle.

**Fix**: canonical = label. Update DM L2 + L3 to consistently say label. Drop Discussion-comment fallback.

### Defect cluster E: Verifier TEST-PLAN ownership

Verifier prohibitions (L561) implies TEST-PLAN.md is a planning artifact PM produces. Per #9184, verifier owns TEST-PLAN derivation independently of PM.

**Fix**: rewrite the prohibition to drop TEST-PLAN.md from the PM-produced list. Keep RESEARCH.md and CONTEXT.md (PM-owned per file conventions).

### Defect cluster F: PM lacks step:cycle/context-pressure

PM CLAUDE.md has no `step:cycle/context-pressure` step. But after Cluster A fix (delete flat-top from worker/verifier/dm), neither will any other role. This is consistent with L1's design where context-pressure is wrapper-side (cycle_post.py exits 42; agent responds via self-restart at Step 7).

**Fix**: no action needed beyond Cluster A. After Cluster A, all 4 roles uniformly route context-pressure through the wrapper. Step 7 self-restart already documents this. Working-state expectation (per CQ hedges) should be made explicit at L1 Step 7 prose — one sentence: "the wrapper commits whatever working-state.md contains at the moment of exit-42, so keep it fresh at every checkpoint."

### Defect cluster G (LOW): inline one-liners

Worker composed has Discussion Protocol inline-bodied with the tracker.py comment example. PM/QA/DM composed don't (they have role-specific sub-skill markers only). This causes HEDGEs across 3 roles on Item 5 (Discussion comment received).

**Fix**: replace `roles/{pm,verifier,dm}/discussion-protocol` markers with a shared `common/discussion-protocol` inline block similar to worker's. OR add a one-line inline example next to each role's marker.

**Decision**: inline a one-line example. Don't restructure the sub-skill hierarchy. Smaller diff, faster convergence.

## Fix order (commits)

1. **Iter 49 — Defect cluster A**: delete L2 flat-top in worker/verifier/dm; add pickup-comment-fidelity layered op to worker; add Step 7 working-state expectation line in L1.
2. **Iter 50 — Defect cluster B**: delete ds-review marker typo line.
3. **Iter 51 — Defect cluster C**: PM L44/L195 RCA reconciliation.
4. **Iter 52 — Defect cluster D**: DM delivery:skip canonical signal (label).
5. **Iter 53 — Verifier vault read-only exception**: add explicit verifier exception in vault.md or L3 verifier.
6. **Iter 54 — Defect cluster E**: Verifier TEST-PLAN ownership in prohibitions.
7. **Iter 55 — Defect cluster G**: inline tracker.py comment one-liner for PM/QA/DM.

Compose tests + DS audit on each substantive prose change. Convergence CQ pass after all 7 ship.
