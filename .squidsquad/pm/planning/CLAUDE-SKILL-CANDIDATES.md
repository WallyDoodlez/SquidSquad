# CLAUDE-SKILL-CANDIDATES — Phase 1 Classification

PM Phase 1 deliverable for [#11052](https://github.com/WallyDoodlez/SquidSquad/issues/11052): classify every sub-skill under `references/sub-skills/` as Tier 1 (Claude Skill candidate), Tier 2 (stay composed), or Tier 3 (hybrid — operator decision).

Companion: [`docs/COMPOSE-ARCHITECTURE.md`](../../../docs/COMPOSE-ARCHITECTURE.md) §3.2 (slot + ordinal), §4.5 (sub-skill reference resolution), §4.6 (assemble).

## Summary

- **Total sub-skill files**: 116 (excluding `manifest.md`)
- **Tier 1 — Claude Skill candidates**: 18
- **Tier 2 — Stay as composed sub-skills**: 91
- **Tier 3 — Hybrid (operator decision)**: 7

**Headline recommendation**: promote the 18 Tier 1 sub-skills to Claude Skills under `.claude/skills/<name>/SKILL.md`. They're discrete, user-invocable capabilities with self-contained input/output contracts. Keep the 91 Tier 2 sub-skills as composed content (cycle-loop infra, always-on norms, L4 templates, per-domain inline). Resolve the 7 Tier 3 hybrids with operator — most likely answer is "both" (composed cycle-tick + invocable on demand), needing a new pattern that doesn't exist today.

**Earlier "DRY violation" claim retracted (cycle 2137)**: I previously flagged 24 role-specific norm files as duplicates of 9 `common/` norms. On inspection that's wrong — they're L2 role-specific layers (different `ordinal: 20`, `roles: [pm]` filter) intentionally adding role-tailored rules on top of common L1 base. Same H2 heading IS the real problem (composed output has two `## What You Must Never Do` sections — one from common, one from role-specific). That's exactly what §4.6 assemble was designed to merge into a single coherent voice. The "duplication" smell is the cost of the verbatim-default that we picked when retiring the API-based assemble. Resolution path: agent-spawn assemble per #11053 (covers this case automatically); no DRY cleanup task needed.

---

## Tier 1 — Claude Skill candidates (18)

Sub-skills that are **invocable on demand**, have **discrete input/output contracts**, and are **self-contained** enough to operate as `.claude/skills/<name>/SKILL.md`. Each could be invoked by `Skill({skill: "<name>"})` from any agent (or by the human directly as `/<name>`) and produce a useful result without needing the agent's full Ralph Loop context loaded.

### Reactive / capability-shaped (10)

| Current path | Proposed Claude Skill name | Proposed description (≤140 chars) | Input → Output |
|---|---|---|---|
| `common/l4-curation.md` | `l4-curation` | Author L4 project-customization entries from human durable directives. Use when human says "from now on..." | human directive → L4 op (replace/insert-after/append) committed |
| `common/vault-remember.md` | `vault-remember` | Persist a fact or decision into the agent vault for future-session recall. | fact text → vault entry |
| `common/vault-optimize.md` | `vault-optimize` | Compact / dedupe / index the vault. Quiet-cycle utility. | vault dir → optimized vault dir |
| `common/improvement-scan.md` | `improvement-scan` | Full quiet-cycle improvement scan for workflow / process gaps. | scope (templates/CLAUDE.md/vault) → finding list |
| `common/issue-filing.md` | `file-issue` | File a structured tracker issue with correct labels + role routing. | symptom + reporter → tracker issue # |
| `common/self-restart.md` | `self-restart` | Relaunch this agent's claude.exe with a clean session. | (none) → new claude.exe pid |
| `common/boot-remote-agents.md` | `boot-agents` | Boot dead or missing SquidSquad agents (dm/skill/qa/verifier) in their clones. | role(s) → spawn result |
| `roles/pm/task-intake.md` | `task-intake` | Run the 5-phase task intake (research → discussion → planning → approval → execution). | human request → approved task |
| `roles/verifier/verification.md` | `verify` | Run verification against a pending-test item's ACs. | task # → PASS/FAIL + QA-RESULTS |
| `roles/worker/implement-tasks.md` | `implement-task` | Pick up and implement an approved task end-to-end. | task # → PR |

### Role-specific procedural / runbook-shaped (8)

| Current path | Proposed Claude Skill name | Proposed description (≤140 chars) | Input → Output |
|---|---|---|---|
| `roles/pm/pipeline-sentinel.md` | `pipeline-sentinel` | Scrutinize tracker for stalled/orphan items; nudge or transition. | (none) → tracker comments/transitions |
| `roles/pm/soul-shepherd.md` | `soul-shepherd` | Audit SOUL.md across agents for drift; flag updates. | role list → drift report |
| `roles/pm/vault-synthesis.md` | `vault-synthesis` | Synthesize vault notes into BRIEFING.md / vault summary. | vault dir → BRIEFING.md update |
| `roles/pm/health-check.md` | `agent-health-check` | Check each agent's last-cycle, current-state, .claude-pid liveness. | (none) → health report |
| `roles/pm/own-domain-autofix.md` | `own-domain-autofix` | Auto-fix small PM-domain issues (working-state drift, etc.) inline. | scan finding → committed fix |
| `roles/dm/delivery-packaging.md` | `package-delivery` | Build delivery artifact for a shipped task (docs, CHANGELOG entry). | task # → delivery package |
| `roles/dm/issue-triage.md` | `triage-external-issue` | Triage human-filed issues (no `squidsquad` label) to correct role. | issue # → labeled + assigned |
| `roles/dm/version-bumps.md` | `bump-version` | Apply version bump after N ships per `feedback_ds_review_per_change`. | bump kind → new version + commit |

---

## Tier 2 — Stay composed (91)

These sub-skills MUST remain in the composed CLAUDE.md (or runtime-loaded for mode-specific fragments) because they govern every cycle, lifecycle phase, or always-on agent behavior. They cannot be on-demand — pure description-matched invocation cannot fire deterministically.

### Cycle-loop infra (10) — MANDATORY INLINE per #11049 spec

`boot-bootstrap`, `cycle-runner`, `context-pressure`, `resume-working-state`, `task-pickup`, `working-state`, `git-commit`, `agent-lifecycle`, `improvement-scan-slim`, `status-line`.

Already specified in [#11049](https://github.com/WallyDoodlez/SquidSquad/issues/11049) cycle 2135 spec note as the mandatory inline set. Restated here for completeness.

### Mode-specific runtime fragments (6) — Read at boot, not composed

`common-events/comment-handling`, `common-events/cursor-management`, `common-events/event-driven-workflow`, `common-events/forge-read-pattern`, `common-events/idle-cooldown-loop`, `common-events/l1-base`.

These are runtime-Read by `boot-bootstrap.md` Step 3 (event-mode contract). They're not composed but also not Claude Skills — they're mode-conditional instruction fragments the agent reads at boot before any tool use.

### Always-on norms (33: 9 common L1 + 24 role-specific L2)

**common/ (9)**: `agent-boundaries`, `chat-etiquette`, `consensus-protocol`, `discussion-protocol`, `file-conventions`, `interval-sync`, `mention-protocol`, `pickup-comment-fidelity`, `prohibitions`. These are L1 base (no `roles:` filter, `ordinal: 10`) — apply to every role.

**roles/{dm,pm,verifier,worker}/ (24 L2 role-layers)**: per-role variants of `discussion-protocol`, `file-conventions`, `issue-filing`, `prohibitions`, `ralph-loop-overview`, `responsibility`, `status-line`, `task-pickup` for each of 3-4 roles. These have `ordinal: 20` + `roles: [<role>]` and intentionally add role-specific rules under the same H2 heading as the L1 base (e.g., `roles/pm/prohibitions.md` adds PM-specific "Never approve a task without explicit human confirmation" under the same `## What You Must Never Do` as `common/prohibitions.md`).

These govern how the agent behaves at all times. Cannot be on-demand because they don't have an "invoke me" trigger — they're constraints, not actions.

**Same-H2-heading layering is by design** (§3.2 slot + ordinal). Composed output today has both L1 and L2 H2 sections back-to-back (`## What You Must Never Do` from L1, then `## What You Must Never Do` from L2). §4.6 assemble was designed to merge these into a single coherent voice. With assemble currently verbatim, the duplicate H2 stays in the composed output — cosmetic noise, not a content bug. Resolution: agent-spawn assemble per #11053 handles this case automatically when operator opts the `instructions` slot in.

### L4 templates / project-customization seeds (16)

`project/{dm,pm,verifier,worker}-{instructions,responsibility,soul-directives}` (12) + `project/setup-upgrade-gate` + `project/shared-{instructions,responsibility,soul-directives}` (3) + 1 setup gate.

These are seed templates copied into `.squidsquad/project/<role>.md` during setup. They're not invocable; they're the L4 starting content the project customizes.

### L3 domain-context (20)

`roles/{dm,pm,verifier,worker}/{android,ios,fullstack,skill,web}/domain-context.md`.

Per-domain inline content (skill's existing #11049 choice — stays). Tightly coupled to host instructions.md.

### Role-specific runbooks that need cycle-tick invocation (6)

`roles/pm/checkin`, `roles/pm/delivery`, `roles/pm/discussion-protocol` (-> also in norms), `roles/pm/github-issues`, `roles/pm/testing-and-verification`, `roles/dm/events/pr-merge-wait`, `roles/dm/doc-improvement-loop`.

These are step:cycle/* contents — referenced from the cycle's work phase prose, can't be on-demand because the cycle script triggers them as part of mechanical flow.

---

## Tier 3 — Hybrid / unclear (7)

Each runs as a cycle-phase activity AND could plausibly be invoked on demand. Per-candidate operator decision needed: does it stay Tier 2 with a Tier 1 twin (e.g., `pipeline-sentinel` cycle-tick + `/pipeline-sentinel` skill), or does the cycle-tick caller learn to invoke the Tier 1 skill (compose stays thin)?

| Sub-skill | Cycle role | On-demand shape | Operator question |
|---|---|---|---|
| `roles/pm/pipeline-sentinel` | every PM cycle | `/pipeline-sentinel` skill | Both, or cycle-tick invokes skill? |
| `roles/pm/health-check` | every quiet cycle | `/agent-health-check` skill | Both, or cycle-tick invokes skill? |
| `roles/pm/soul-shepherd` | periodic | `/soul-shepherd` skill | Both, or cycle-tick invokes skill? |
| `roles/pm/vault-synthesis` | quiet cycle | `/vault-synthesis` skill | Both, or cycle-tick invokes skill? |
| `common/improvement-scan` (full) | quiet-cycle option | `/improvement-scan` skill | Tier 2 has `improvement-scan-slim` for inline cycle use; full = Tier 1? |
| `common/vault-remember` | every-cycle on real work | `/vault-remember` skill | Cycle gate stays inline; skill is for on-demand? |
| `roles/dm/issue-triage` | DM cycle on external issues | `/triage-external-issue` skill | Both, or cycle-tick invokes skill? |

**Lean recommendation**: "cycle-tick invokes skill" (one authoring location, called from two surfaces). The cycle-loop infra wraps a `Skill({skill: "pipeline-sentinel"})` call in the appropriate phase. Composed CLAUDE.md stays thin. Operator confirm.

---

## Cross-cutting concerns surfaced during classification

1. ~~**Role-norm DRY violation** (24 duplicate norm files)~~ — **retracted** (see updated §Tier 2 Always-on norms above). This is L1+L2 layering working as designed; the duplicate H2 in composed output is a cosmetic side-effect of verbatim default, resolved by #11053 agent-spawn assemble when operator opts the `instructions` slot in.

2. **`improvement-scan` vs `improvement-scan-slim`**: the slim version is in mandatory inline (per #11049 spec); the full version is Tier 1 candidate. Naming suggests this was the original intent — slim for cycle gate, full for on-demand. Confirms the Tier 3 "cycle-tick invokes skill" pattern is workable for at least one case.

3. **`vault-protocol` vs `vault-protocol-slim`**: same pattern as improvement-scan, but currently `vault-protocol-slim` is in reactive bucket. Re-classify: slim should be Tier 2 (inline gate), full should be Tier 1 candidate. Already accounted for in tables above by listing `vault-protocol` separately; flagging the split here.

4. **L3 domain-context as Claude Skills?**: out of scope but worth flagging — `roles/pm/skill/domain-context.md` reads like "what PM should know when their domain is skill-development." Could conceptually become a Claude Skill scoped to that domain. Punt to a future investigation.

---

## Open questions for operator decision

1. **Tier 3 disposition** (7 candidates): "both Tier 2 inline + Tier 1 skill" vs "cycle-tick invokes Tier 1 skill, no Tier 2 inline." Lean: the latter.

2. **Per-agent vs project-level Claude Skills**: does each agent have its own `.claude/skills/`, or is there one project-level `.claude/skills/` all agents share? Tier 1 candidates like `task-intake` are PM-specific; `implement-task` is worker-specific. If shared, the skill itself enforces role-gating internally.

3. **Multi-agent invocation pattern**: when PM calls `/pipeline-sentinel`, does PM run it (read-only inspection + comment) or does it spawn a separate agent? Lean: PM runs it; pipeline-sentinel is observation + tracker mutation, not heavy compute.

4. **#10781 disposition**: this was the original "make sub-skills invokable Claude Skills" tracker (un-parked post-E6). #11052 supersedes #10781 with this classification; close #10781 as "addressed by #11052 classification + Phase 2 per-candidate promotion tasks."

---

## What Phase 2 would scope

Per Tier 1 candidate, file a follow-up TASK for skill (the role that owns code + skill creation):

- Create `.claude/skills/<name>/SKILL.md` with proposed name + description + the full sub-skill body as the skill content
- Remove from any `{{include:}}` / `→ run sub-skill:` references in orchestrator files (Tier 1 doesn't live in composed CLAUDE.md anymore)
- Update `docs/sub-skill-catalog.md` to reflect the new location (or remove the entry if catalog only tracks composed sub-skills)
- Update agent prose to invoke via `Skill({skill: "<name>"})` instead of reference

Recommend filing as ONE Phase 2 umbrella task, not 18 separate ones — bulk migration with per-Tier 1 sub-bullets.
