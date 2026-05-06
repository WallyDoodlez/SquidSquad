Now I have a complete picture. Let me compile the research.

---

# FEAT-PM-5888-AUDIT2 Research — Decouple wizard.py/add_role.py from compose.py

## Summary

This audit examined the second proposal: strip ALL `compose.py` calls from `wizard.py` and `add_role.py`, making them scaffolding-only scripts. The `/squidsquad-compose` skill becomes the single entry point for composition. Orchestration becomes: setup skill calls `wizard.py scaffold` (directories + config.md only), then `/squidsquad-compose` (composition + validation). Add-role skill calls `add_role.py` (clone + directory) then `/squidsquad-compose`.

The decoupling is **feasible with caveats**. Three compose.py dependencies exist in `wizard.py` (`deploy_role`, `generate_local_config`, `boot_role`) and two in `add_role.py` (subprocess calls to `deploy` and `boot`). Of these, `boot_role` is already a no-op (#4966) and can be removed with zero impact. The `generate_local_config` call is purely additive — it writes `.local-config` — and can be cleanly relocated. The `deploy_role` call is the hard one: it writes CLAUDE.md and SOUL.md, and the SOUL.md seeding logic (lines 956–987) runs immediately afterward, patching the files `deploy_role` just wrote. Removing `deploy_role` from `scaffold_install()` requires either moving SOUL.md seeding to the compose step or having scaffold write placeholder SOUL.md files that compose later patches. The `setup-yes`/CI path currently gets composition "for free" through `scaffold_install` and would need to become a two-step process.

The primary risk is the SOUL.md seeding pipeline: it currently chains scaffold → deploy_role (writes SOUL.md) → wizard patches SOUL.md with project context. Breaking this chain requires careful restructuring.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" is the driving priority. This decoupling is prerequisite infrastructure (the skill wrapper needs a clean single entry point for validation hooks). #5557 "Composed CLAUDE.md edit prohibition" constrains this — composed files must never be manually edited; the compose skill is the sole writer.

- **Related decisions**: [[decision-sub-skill-architecture]] — Reminder that composition is build-time concatenation from `references/sub-skills/`. The compose skill is NOT a sub-skill; it's a Claude Code slash command orchestrating `compose.py`. [[decision-local-config-priority]] — `generate_local_config()` in compose.py writes `.local-config` which takes priority over global clones; the skill wrapper must preserve this behavior.

- **Related patterns**: [[pattern-windows-utf8-subprocess]] — Any new subprocess calls in the compose skill wrapper must use `encoding="utf-8", errors="replace"`.

- **Human preferences**: "Never ship with failed TCs" — the test suite must pass before merging. "Prefers direct/mechanical checks over indirect state files" — the compose validation step should verify actual file output, not just exit codes.

- **Related learnings**: [[learning-atomic-migration-strategy]] — The entire migration (wizard.py changes + add_role.py changes + test updates + SKILL.md updates) must ship atomically. Agents mid-cycle during a partial deploy would get broken scaffolding.

## Impact Analysis

- **Files touched**:
  - `references/scripts/wizard.py` — Remove 3 compose imports/calls (lines 882–887, 945, 1048–1055, 1058–1067), restructure SOUL.md seeding (lines 956–987)
  - `references/scripts/add_role.py` — Remove 2 compose subprocess calls (lines 263–266, 269–273), update dry-run messaging (lines 209–216)
  - `tests/test_wizard.py` — 3 test classes affected: `TestScaffoldInstall*` (lines 819–1017), `TestSoulMdSeeding` (lines 1677–1761 with explicit compose mocks)
  - `tests/test_add_role.py` — `TestAddRoleFixesRemote.test_clone_sets_upstream_origin` (lines 212–240) and dry-run test (line 64–73) may need updates
  - `tests/test_wizard_runbook.py` — `_COMPOSE_COMMANDS` constant (line 40) may need updating
  - `SKILL.md` — Setup Instructions (lines 284–323), Upgrade Instructions (lines 327–395) updated to reference `/squidsquad-compose`
  - `.claude/commands/squidsquad-upgrade.md` — Entire file is stale (parallel-subagent flow), must be rewritten to use `/squidsquad-compose`
  - NEW: `.claude/commands/squidsquad-compose.md` — Slash command definition for the compose skill
  - `references/wizard/WIZARD.md` — Step 7 references compose; may need updating if orchestration changes

- **Behavior changes**:
  1. `scaffold_install()` no longer composes CLAUDE.md or SOUL.md — it only creates directory structure, writes config.md, working-state.md, clones repos, saves install-spec
  2. `add_role()` no longer runs `compose.py deploy` or `compose.py boot` — it only clones, configures `.active-role`, and syncs `.local-config`
  3. `cmd_setup_yes` (CI path) goes from 1-step to 2-step: scaffold then compose
  4. SOUL.md seeding (project context, responsibilities) moves from wizard.py to a post-compose step (either in the compose skill or in compose.py itself)
  5. `.local-config` generation moves from wizard.py's `scaffold_install` to the compose skill

- **Dependencies**:
  - `compose.py` `deploy_role()` function — MUST remain importable by Python (tests, CI scripts that bypass the skill). The proposal is about removing calls FROM wizard/add_role, not about removing the function.
  - `compose.py` `generate_local_config()` — same, must remain importable
  - `wizard.py` `scaffold_install()` — the `deploy_role` call must be removed but the function signature should not change (callers pass target_root, which deploy_role also needs)
  - The `/squidsquad-compose` slash command — needs to exist before wizard and add-role skills can reference it

## Side Effects

- **Risk 1: SOUL.md seeding pipeline breakage** — Severity: **H** — Currently `scaffold_install` calls `deploy_role` at line 945, which writes SOUL.md. Immediately after (lines 956–987), wizard.py reads SOUL.md back, seeds the "Project Context" placeholder with domain context, and seeds "Project-Specific Responsibilities" from the repo scan. If `deploy_role` is removed from scaffold, SOUL.md won't exist yet, and the seeding code will either crash or silently skip. **Mitigation**: Either (a) move the SOUL.md seeding logic into `compose.py`'s `deploy_role` function so it happens during composition, or (b) have `scaffold_install` write a minimal placeholder SOUL.md that the compose step later detects and patches, or (c) add a post-compose seeding step to the `/squidsquad-compose` skill wrapper. Option (a) is cleanest — `deploy_role` already has the domain context available and already writes SOUL.md.

- **Risk 2: setup-yes CI path becomes two-step** — Severity: **M** — `cmd_setup_yes` (wizard.py lines 2124–2203) currently calls `scaffold_install()` which internally composes. After decoupling, CI must run `wizard.py scaffold` then separately trigger composition (either `compose.py deploy-all` directly or via the skill). This is a CI pipeline change. **Mitigation**: Document the two-step CI process clearly. The `setup-yes` command could optionally chain to composition if compose.py is importable, but that defeats the decoupling goal.

- **Risk 3: add_role dry-run becomes misleading** — Severity: **L** — `add_role.py` lines 210–215 print "Would deploy CLAUDE.md + SOUL.md" and "Would generate boot scripts" in dry-run mode. After removing compose calls, these messages are stale. **Mitigation**: Update dry-run output to say "Would register clone directory (composition handled by /squidsquad-compose skill)".

- **Risk 4: `.claude/commands/squidsquad-upgrade.md` is already stale** — Severity: **M** — This file (lines 19–31) still describes pre-compose.py parallel-subagent template regeneration. If not fixed atomically with this change, agents reading the slash command file directly would execute a conflicting flow. **Mitigation**: Rewrite `squidsquad-upgrade.md` in the same atomic change to use `/squidsquad-compose`.

## Edge Cases

- **Scaffold without compose (offline/no gh auth)**: Currently `scaffold_install` fails if `deploy_role` fails (caught at line 947 with a warning). After decoupling, scaffold can succeed even when gh auth is missing (since it only writes directories + config.md). The compose step would fail later, but that's a separate, clearer error. This is actually cleaner.

- **add_role with --force on existing clone**: Currently `add_role` git-clones then runs compose. After decoupling, the clone happens, `.active-role` is written, but composition is deferred. If the user boots the agent before composition runs, the agent has a `.squidsquad/<role>/` directory with no CLAUDE.md. This is a real edge case — the add-role skill must ensure composition completes before telling the user to boot.

- **Partial scaffold failure**: If `scaffold_install` creates directories but fails partway (e.g., clone step fails), the compose step needs to handle a partially-initialized `.squidsquad/` tree. Currently this is handled because scaffold is all-or-nothing (if deploy_role fails, it continues with a warning). After decoupling, the compose skill should verify directories exist before composing.

- **wizard.py re-run with overwrite_existing=True**: Currently re-running scaffold with `overwrite_existing=True` re-composes CLAUDE.md. After decoupling, re-running scaffold is a no-op for composition — only the compose step refreshes templates. This is actually desired behavior (separation of concerns).

- **agent-compose config flag**: `compose.py`'s `agent_compose()` (line 550) can invoke Claude via subprocess for coherence polishing. If `/squidsquad-compose` is itself running inside Claude and triggers this, there's a recursive agent-in-agent risk. The compose skill must check the `agent-compose` config flag and suppress LLM polishing when running inside Claude.

## Integration Risks

- **PM post-merge recompose flow**: The PM sub-skill `references/sub-skills/roles/pm/post-merge-recompose.md` currently instructs PM to run `python references/scripts/compose.py deploy-all` directly (line 25). Changing this to reference `/squidsquad-compose` means PM must understand the slash command as a trigger. This is a sub-skill text change, not a code change — low risk but must be consistent.

- **Harness integration**: The harness currently has no awareness of compose. After decoupling, nothing changes — the harness spawns agents via `thin_launcher.py` which reads CLAUDE.md directly. The compose step is a setup-time concern, not a runtime concern.

- **Upgrade flow**: Currently SKILL.md Step 3 (lines 342–352) runs `python references/scripts/compose.py deploy-all` directly. Changing to `/squidsquad-compose` means the upgrade agent triggers the compose skill instead. The slash command must propagate exit codes so the upgrade flow knows whether compose succeeded before proceeding to config patching.

- **Vault candidates from previous research**: The prior FEAT-PM-5888 research (`.squidsquad/pm/planning/FEAT-PM-5888-RESEARCH.md`) already recommended NOT changing wizard.py/add_role.py (Q2 in Open Questions). This audit's proposal explicitly changes that recommendation — wizard.py and add_role.py ARE stripped. This is a deliberate design escalation.

## Upgrade & Migration

- **New config values**: none required

- **New files**: 
  - `.claude/commands/squidsquad-compose.md` — slash command definition for the compose skill
  - Potentially: `references/sub-skills/capabilities/squidsquad-compose/` if the compose skill follows the capability sub-skill pattern

- **Template changes**: 
  - `SKILL.md` lines 298–306: Setup Instructions "mechanical helpers" list changes — compose.py shifts from being listed alongside wizard.py to being encapsulated behind `/squidsquad-compose`
  - `SKILL.md` lines 342–352: Upgrade Step 3 changes from inline `compose.py deploy-all` to `/squidsquad-compose` invocation
  - `.claude/commands/squidsquad-upgrade.md`: Entire file rewritten (stale parallel-subagent flow → compose-skill-based flow)
  - `references/sub-skills/roles/pm/post-merge-recompose.md` line 25: Inline bash changed to skill invocation

- **Upgrade steps**:
  1. Users with existing installs get the new slash command on `git pull`
  2. Agent recompose picks up new wizard.py (without compose calls) automatically
  3. The stale `squidsquad-upgrade.md` must be fixed atomically — old flow would spawn parallel subagents that conflict with the new single-process compose
  4. `.install-spec.json` remains the source of truth for agent configuration across upgrades
  5. No schema version bump required — config.md schema unchanged

- **Graceful degradation**: If a user hasn't upgraded and runs the old `squidsquad-upgrade.md` (parallel subagent flow), compose.py's deterministic output would still be correct but the parallel approach wastes API calls. The old wizard.py (with embedded compose calls) still works — it's just not decoupled. No breakage for existing installs until they pull the new code.

## Open Questions

- **Q1**: Where does SOUL.md seeding move? — **Why**: Currently wizard.py seeds SOUL.md with project context and responsibilities AFTER `deploy_role` writes it (lines 956–987). Options: (a) move seeding into `compose.py`'s `deploy_role()`, (b) add a post-compose seeding step to the `/squidsquad-compose` skill wrapper, (c) have scaffold write placeholder SOUL.md that compose patches. Option (a) is cleanest — `deploy_role` already reads config.md (for placeholder substitution), so it has access to domain context. The repo-scan data would need to be passed through or read from `.squidsquad/.repo-scan.json`.

- **Q2**: Should `setup-yes` chain to compose, or should CI call two separate commands? — **Why**: If `setup-yes` chains to compose internally, the decoupling is incomplete (wizard still triggers compose). If CI calls two separate commands, it's a pipeline change. The cleanest answer: `setup-yes` should only scaffold, and CI/SKILL.md should call compose separately. This keeps the separation of concerns pure.

- **Q3**: Should `add_role.py` run compose as a subprocess (keeping the Python-to-CLI bridge), or should it truly have zero compose awareness? — **Why**: If add_role.py has zero compose awareness, the add-role skill MUST call `/squidsquad-compose` after add_role.py. This is a two-step process but cleaner separation. If add_role.py runs compose as a subprocess, it's still doing composition, just through a different mechanism (subprocess instead of import). The proposal says "stripped of ALL compose.py calls" — so the answer is zero compose awareness.

- **Q4**: Does the `/squidsquad-compose` skill need to handle the `agent-compose` config flag for recursive Claude invocation? — **Why**: `compose.py agent_compose()` (line 550) can call Claude as a subprocess to polish output. If `/squidsquad-compose` runs inside Claude, and compose.py also invokes Claude, it could deadlock or waste API calls. The skill should likely disable `agent-compose` when running within a Claude session.

## Recommendation

**Feasible with caveats.** The mechanical removal is straightforward — 5 call sites across 2 files, 2 of which are already no-ops. The real work is:

1. **SOUL.md seeding relocation** (the hard part) — move the domain context and responsibilities seeding from wizard.py lines 956–987 into compose.py's `deploy_role()` or into the compose skill wrapper.
2. **Test restructure** — 3 test classes in `test_wizard.py` mock compose explicitly; the `TestSoulMdSeeding` class (lines 1677–1761) needs the most rework.
3. **Atomic delivery** — wizard.py changes + add_role.py changes + test updates + SKILL.md updates + new slash command + squidsquad-upgrade.md rewrite must ship together.
4. **CI pipeline update** — `setup-yes` becomes a two-step process: scaffold then compose.

The bootstrap deadlock is genuinely solved: wizard.py creates `.squidsquad/` directories and config.md FIRST, then `/squidsquad-compose` runs SECOND with a fully-initialized filesystem. compose.py's `deploy_role` reads config.md and writes to `.squidsquad/<agent>/CLAUDE.md` — both paths exist after wizard scaffold runs.

## Vault Candidates

- **Type**: pattern — "Python scripts serve dual role: importable library + CLI subprocess — prefer import for same-process, subprocess for cross-repo" — **Why**: add_role.py uses subprocess to call compose.py (cross-repo, the clone doesn't have compose.py in its Python path). wizard.py uses import (same-process, same directory). This dual-use pattern is intentional and should be documented to prevent future confusion about which approach to use.

- **Type**: learning — "Slash command files can drift from SKILL.md when both describe the same workflow" — **Why**: `squidsquad-upgrade.md` still describes the pre-compose.py parallel-subagent approach while SKILL.md has been updated. Two sources of truth for the same workflow without a sync mechanism is a process gap. Document to prevent recurrence.

- **Type**: decision — "Scaffolding and composition are distinct lifecycle phases: scaffold creates structure, compose creates content" — **Why**: This task formalizes a distinction that currently doesn't exist — wizard.py conflates scaffolding (directories, config.md, clones) with composition (CLAUDE.md, SOUL.md). Formalizing this as an architectural decision prevents future features from blurring the boundary again.

- **Type**: pattern — "SOUL.md has a three-phase lifecycle: compose writes template → wizard seeds context → agent customizes at runtime" — **Why**: The SOUL.md seeding pipeline is the trickiest part of this decoupling. Capturing the three-phase pattern documents why SOUL.md can't be trivially moved and what invariants each phase must preserve.

- **Type**: learning — "No-op functions should be fully removed, not just emptied — boot_role has been a no-op since #4966 but is still imported and called" — **Why**: `boot_role` in compose.py prints "no-op" and returns [] (line 946–949). wizard.py still imports and calls it (lines 1058–1067). This is dead code that complicates decoupling. Remove it fully during this change.