Now I have all the information to produce the final audit. Let me compile it.

```markdown
# FEAT-PM-5888-AUDIT3 Research — Final Audit of Locked Decisions for #5888

## Summary

This audit challenges all six locked decisions for #5888 against the actual codebase. **Two decisions have critical contradictions that must be resolved before implementation**: Decision 3 (Wizard keeps SOUL.md seeding) conflicts directly with Decision 2 (wizard.py loses compose.py calls) because the SOUL.md seeding code at `references/scripts/wizard.py:956–987` depends on `deploy_role()` having just written SOUL.md at line 945. Remove `deploy_role` and the seeding code silently no-ops on `soul_path.exists()` returning `False`. Decision 6 (CI two-step) is mechanically sound but the `setup-yes` post-setup summary prints boot instructions prematurely — it assumes agents are composed. The remaining four decisions are sound with manageable caveats. **The compose skill slash command file does not exist yet** (`.claude/commands/squidsquad-compose.md`) — this is the entire orchestration target and must be created before any caller migration.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" is the driving priority behind this work. #5557 "Composed CLAUDE.md edit prohibition + compose.py guard" constrains: composed files must never be manually edited.
- **Related decisions**: [[decision-sub-skill-architecture]] — composition is build-time concatenation; the compose skill is NOT a sub-skill, it's a Claude Code slash command. [[decision-local-config-priority]] — `.local-config` written by compose.py takes priority; the compose skill must preserve this.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — the compose skill wrapper should prefer Python verification over LLM-based validation for correctness checks. [[learning-atomic-migration-strategy]] — wizard.py changes + add_role.py changes + test updates + new slash command + squidsquad-upgrade.md rewrite must ship atomically.
- **Human preferences**: "Never ship with failed TCs" — test suite must pass. "Prefers direct/mechanical checks over indirect state files" — compose validation should verify actual file content, not just exit codes.
- **Related learnings**: [[learning-atomic-migration-strategy]] — partial migrations break coordination across running agents; ship as single atomic unit.

## Impact Analysis

- **Files touched**:
  - `references/scripts/compose.py` — Remove `agent_compose()` (lines 550–637), `_is_agent_compose_enabled()` (lines 499–505), `_extract_code_blocks()` (lines 508–517), `_extract_markers()` (lines 520–524), `_generate_cqs_from_sources()` (lines 526–547), call at line 667. Remove `boot_role()` (lines 941–949) if not already.
  - `references/scripts/wizard.py` — Remove `deploy_role` import+call (lines 882–887, 945), `generate_local_config` import+call (lines 1048–1055), `boot_role` import+call (lines 1058–1067). Extract SOUL.md seeding (lines 956–987) or restructure. Update `cmd_setup_yes` (lines 2124–2203) to not assume composition happened.
  - `references/scripts/add_role.py` — Remove `compose.py deploy` subprocess call (lines 261–266), `compose.py boot` subprocess call (lines 268–273). Update dry-run messages (lines 210–216).
  - `references/scripts/config.py` — `agent-compose` config field (line 66) becomes dead; optionally remove or mark deprecated.
  - `tests/test_compose.py` — Remove `TestAgentComposeDisabled` (lines 787–793), `TestExtractCodeBlocks` (lines 796–806), `TestExtractMarkers` (lines 808–816), `TestGenerateCQs` (lines 819–836), `TestAgentComposeEnabled` (lines 839–881).
  - `tests/test_wizard.py` — `TestScaffoldInstallDesignPreset` (lines 819–874), `TestScaffoldInstallDevVariants` (lines 876–912), `TestScaffoldInstallSafetyAndIdempotency` (lines 915–940) all assert CLAUDE.md/SOUL.md exist after scaffold — these break. `TestSoulMdSeeding` (lines 1677–1761) patches `sys.modules["compose"]` — may need update if import structure changes.
  - `tests/test_add_role.py` — `TestAddRoleFixesRemote` (lines 212–240) patches `_run` to mock compose subprocess call — needs update if call removed.
  - `tests/test_wizard_runbook.py` — `_COMPOSE_COMMANDS` constant (line 40) may need updating.
  - **NEW**: `.claude/commands/squidsquad-compose.md` — slash command definition (does not exist yet).
  - `SKILL.md` — Setup Instructions (lines 298–306) reference compose.py directly; upgrade instructions (lines 342–352) run `compose.py deploy-all` inline. Both must reference `/squidsquad-compose`.
  - `.claude/commands/squidsquad-upgrade.md` — Entire file (lines 1–53) is stale (parallel-subagent flow, pre-compose.py). Must be rewritten.
  - `references/wizard/WIZARD.md` — Lines 587–591, 704–705 reference compose.py directly. Must be updated.
  - `references/sub-skills/roles/pm/post-merge-recompose.md` — Line 25 runs `compose.py deploy-all` inline. Must reference `/squidsquad-compose`.
- **Behavior changes**:
  1. `scaffold_install()` no longer creates CLAUDE.md or SOUL.md — only directories, config.md, working-state.md, clones, install-spec
  2. `add_role()` no longer runs compose — only clones, writes `.active-role`, syncs `.local-config`
  3. `/squidsquad-compose` is the only way to regenerate CLAUDE.md/SOUL.md
  4. `cmd_setup_yes` goes from 1 command (scaffold+compose+labels+summary) to scaffolding only; CI must invoke composition separately
  5. Agent-compose coherence polish is fully removed — no LLM-based output polishing
- **Dependencies**:
  - `.claude/commands/squidsquad-compose.md` must exist before any caller can reference it
  - `compose.py deploy_role()` must remain importable (tests, CI, any Python scripts)
  - Setup skill → wizard scaffold → compose skill chain must be documented in SKILL.md
  - Add-role skill → add_role.py → compose skill chain must be documented

## Side Effects

- **Risk 1: SOUL.md seeding silently breaks** — Severity: **H** — `wizard.py:956–987` seeds Project Context and Project-Specific Responsibilities into SOUL.md. It checks `soul_path.exists()` (line 960) before patching. Currently `deploy_role()` writes SOUL.md at compose.py:699–700, so it exists. After removing `deploy_role` from `scaffold_install`, SOUL.md won't exist, the `exists()` check fails, and **seeding is silently skipped with no error**. All agents get unseeded SOUL.md placeholders on first compose. **Mitigation**: Three options: (A) `scaffold_install` writes a minimal SOUL.md with placeholders, seeds it, then compose skill sees existing SOUL.md and skips (compose.py:699 `if not soul_path.exists()`). This breaks the "wizard never composes" rule since wizard must assemble SOUL.md from layers. (B) Move SOUL.md seeding into `compose.py`'s `deploy_role()` — `deploy_role` already has access to `target_root` and could read `.install-spec.json` or `.repo-scan.json` to seed. This makes SOUL.md seeding a composition concern, contradicting Decision 3. (C) Make SOUL.md seeding a separate post-compose step in the setup skill runbook (wizard scaffold → compose skill → wizard seed-soul). This is three-step and fragile. **Recommendation: Option B — move seeding into compose.py**. The boundary is cleaner: compose owns file content, wizard owns filesystem structure.

- **Risk 2: `generate_local_config` call removal breaks health-check and auto-boot** — Severity: **M** — `wizard.py:1048–1055` imports and calls `compose.generate_local_config()` which writes `.local-config` mapping agent→clone paths. This is read by `health_check.py` and `boot_remote_agents`. If wizard stops writing it, and compose skill doesn't write it, agents in sibling clones won't discover each other. **Mitigation**: `compose.py deploy-all` (line 1022) already calls `generate_local_config`. If the compose skill runs `deploy-all`, `.local-config` is regenerated. Ensure the compose skill always runs `deploy-all`, not per-role `deploy`.

- **Risk 3: `cmd_setup_yes` post-setup summary prints boot instructions for uncomposed agents** — Severity: **M** — `wizard.py:2201` calls `post_setup_summary(spec)` which prints per-agent boot commands (`claude --resume`). After decoupling, agents have no CLAUDE.md yet — booting would fail or produce undefined behavior. **Mitigation**: `cmd_setup_yes` must print a different summary: "Scaffolding complete. Run compose to generate agent instructions, then boot." Or CI chains to compose and only prints summary after compose succeeds.

- **Risk 4: `add_role.py` dry-run messages become misleading** — Severity: **L** — Lines 210–215 print `[dry-run] Would deploy {role} CLAUDE.md + SOUL.md` and `Would generate boot scripts`. After removing compose calls, these messages are false. **Mitigation**: Update to "Would register clone directory (composition handled by /squidsquad-compose skill)".

- **Risk 5: `agent-compose` config field becomes dead but harmless** — Severity: **L** — `config.py:66` maps `"agent-compose"` to `("Agent Compose", "Enabled")`. Existing configs with `agent-compose: yes` will parse fine but the field has no consumer. No migration needed, but the field should be removed from config.py's FIELD_MAP or marked deprecated to prevent future confusion.

## Edge Cases

- **SOUL.md never written because compose skill not run**: After `scaffold_install()`, `.squidsquad/<agent>/` directories exist with `working-state.md`, `iterations/`, `planning/` but no `CLAUDE.md` or `SOUL.md`. If a user boots an agent before running compose, the agent has no instructions. Currently impossible because scaffold composes inline. After decoupling, this is a real failure mode. The setup skill runbook must enforce the order: scaffold → compose → boot.

- **add_role with --boot flag**: `add_role.py:291–305` boots the agent after composition. After removing compose calls, the clone has no CLAUDE.md. The `--boot` flag either (a) must be removed from add_role.py, or (b) add_role.py must refuse `--boot` without `--compose` (but there's no compose flag), or (c) the add-role skill must run compose before boot. **Recommendation: remove --boot from add_role.py** — booting is the add-role skill's responsibility after compose succeeds.

- **Re-run wizard with `overwrite_existing=True`**: Currently re-running scaffold re-composes CLAUDE.md (via deploy_role). After decoupling, re-running scaffold is a no-op for composition — only refreshes config.md and directory structure. This is actually the desired behavior (separation of concerns), but the WIZARD.md runbook at line 636 says "CLAUDE.md is refreshed" on re-install. The runbook must be updated.

- **Scaffold without compose (offline/no gh auth)**: Currently `scaffold_install` can fail at `deploy_role` if compose can't read templates. After decoupling, scaffold can succeed without gh auth since it only writes directories + config.md. The compose step fails later with a clearer error. This is a UX improvement — the failure is localized.

- **Partial clone failure in scaffold_install**: `scaffold_install:1008–1040` creates sibling clones. If a clone fails, the agent directory exists but has no CLAUDE.md (currently deploy_role happens before clone step). After decoupling, the compose skill needs to handle agents whose clones failed — the agent directory exists but the clone is missing. The compose skill should verify `.squidsquad/<agent>/` exists before composing for that agent.

- **Upgrade on pre-install-spec installations**: SKILL.md:340 says "If the file does not exist (pre-install-spec installations), derive the agent list from the Dev Agents field." After decoupling, the compose skill (called from upgrade) must handle both cases. `compose.py deploy-all` already does this via `_collect_all_roles()` which reads config.md. No change needed.

## Integration Risks

- **PM post-merge recompose sub-skill**: `references/sub-skills/roles/pm/post-merge-recompose.md:25` runs `python references/scripts/compose.py deploy-all` as inline bash. Changing to `/squidsquad-compose` means the PM agent invokes a slash command from within its cycle. This works but PM must know the slash command exists. The sub-skill text is the natural place to document this.

- **Upgrade slash command is dangerously stale**: `.claude/commands/squidsquad-upgrade.md` (lines 19–31) describes spawning parallel subagents to regenerate templates — a flow that predates compose.py entirely. If any agent reads this file directly (instead of SKILL.md), it executes the wrong flow. **This must be fixed atomically with the compose skill introduction** — the upgrade flow switch from parallel-subagent to compose-skill is a separate correctness concern from the wizard/add_role decoupling, but the atomic delivery constraint means they ship together.

- **WIZARD.md runbook references compose.py directly**: `references/wizard/WIZARD.md:587–591` instructs the installer agent to call `compose.py deploy <role>` for preview. Lines 704–705 say "Do not compose CLAUDE.md by hand — always go through compose.py deploy or wizard.py scaffold." After decoupling, the preview path must change: either the wizard previews config.md only (no CLAUDE.md preview), or the compose skill supports a `--dry-run` / preview mode. Simpler: drop the CLAUDE.md preview from the wizard — the user sees config.md only, and the CLAUDE.md is generated by compose later.

- **CI integration (GitHub Actions, etc.)**: Any existing CI scripts that call `wizard.py setup-yes` currently get a fully composed install. After decoupling, they get scaffold-only. CI scripts must be updated to add a second `compose.py deploy-all` invocation. This is a breaking change for any downstream CI pipelines.

- **Config field removal**: Removing `agent-compose` from config.py's FIELD_MAP (line 66) means `config.py get agent-compose` returns empty string instead of whatever value was in config.md. This is harmless for new installs. For existing installs with `agent-compose: yes`, the field becomes invisible but the config.md line remains (it's under `## Flags` section). The next config.md rewrite (upgrade, re-scaffold) would drop it. No functional impact — the field had no runtime effect.

## Upgrade & Migration

- **New config values**: none required
- **New files**: `.claude/commands/squidsquad-compose.md` — compose skill slash command definition (currently does not exist)
- **Template changes**:
  - `SKILL.md:298–306` — "mechanical helpers" list removes `compose.py deploy <role>`; adds `/squidsquad-compose` reference
  - `SKILL.md:342–352` — upgrade Step 3 changes from inline `compose.py deploy-all` to `/squidsquad-compose` invocation
  - `.claude/commands/squidsquad-upgrade.md` — entire file rewritten (stale parallel-subagent flow → compose-skill-based flow)
  - `references/wizard/WIZARD.md:587–591,704–705` — CLAUDE.md preview removed; "always go through compose.py" changed
  - `references/sub-skills/roles/pm/post-merge-recompose.md:25` — inline bash changed to skill invocation
  - `references/scripts/config.py:66` — `agent-compose` field optionally deprecated/removed
- **Upgrade steps**:
  1. Existing installs get new `squidsquad-compose.md` slash command on `git pull`
  2. PM post-merge recompose picks up new sub-skill text at next recompose
  3. The stale `squidsquad-upgrade.md` must be fixed atomically — old flow would spawn parallel subagents that conflict with compose.py
  4. No schema version bump required — config.md schema unchanged
  5. `.install-spec.json` remains source of truth for agent configuration
- **Graceful degradation**: If user hasn't upgraded and runs old `squidsquad-upgrade.md` (parallel subagent flow), compose.py's deterministic output would still be correct but the parallel approach wastes API calls. The old wizard.py (with embedded compose calls) still works — no breakage until new code is pulled.

## Open Questions

- **Q1**: Where does SOUL.md seeding actually move? — **Why**: This is the hard blocker. `wizard.py:956–987` currently seeds SOUL.md with project context after `deploy_role` writes it. If wizard can't call deploy_role, SOUL.md won't exist. Options: (A) wizard writes minimal SOUL.md then seeds (but this duplicates compose.py's `_assemble_soul()` logic — "wizard owns composition" in disguise), (B) compose.py's `deploy_role()` handles seeding by reading `.install-spec.json` and `.repo-scan.json` (cleaner, but contradicts Decision 3), (C) three-step: scaffold → compose → seed (fragile). **Recommendation: Option B** — SOUL.md content is composition's concern; wizard owns directory structure and config.md.

- **Q2**: Should `cmd_setup_yes` still print the post-setup summary with boot instructions? — **Why**: The summary assumes agents are composed. After decoupling, it's misleading. Options: (a) `cmd_setup_yes` prints a minimal "Scaffolding complete" message, (b) `cmd_setup_yes` chains to compose internally (defeats decoupling), (c) CI documentation says "run compose after setup-yes." **Recommendation: Option (a)** with a clear "Next: run compose" message.

- **Q3**: Should `add_role.py --boot` be removed or deferred? — **Why**: Without compose, `--boot` would start an agent with no CLAUDE.md. The flag currently calls compose internally to generate templates before booting. After decoupling, either remove the flag or have it error with "run /squidsquad-compose first." **Recommendation: Remove --boot** — the add-role skill orchestrates clone→compose→boot.

- **Q4**: Does the compose skill need a `--validate` flag for #5868, or is validation always-on? — **Why**: Decision 1 says "Always validate on every compose." If validation is always-on and slow, CI and interactive use suffer. If validation is opt-in, agents might skip it. **Recommendation: Always validate file existence and basic integrity (fast); make deep content validation (#5868 event contracts) always-on but ensure it completes in <5 seconds for typical installs.**

- **Q5**: Can `boot_role` (compose.py:941–949) be fully removed rather than just having its calls removed? — **Why**: `boot_role` has been a no-op since #4966 but is still imported and called by wizard.py (lines 1058–1067). The function itself is dead code. Removing it from compose.py is a separate cleanup but part of this task. **Recommendation: Remove `boot_role` entirely** — function definition + all call sites + the `boot`/`boot-all` CLI commands in main().

- **Q6**: How does the compose skill report errors to the setup skill? — **Why**: Decision 4 says "conversation-based error reporting between skills." If compose skill prints natural language, the setup skill must parse it to know whether to proceed. This is fragile. **Recommendation: The compose skill should write a structured result file (e.g., `.squidsquad/.compose-result.json`) with per-agent status and errors, AND print a human-readable summary.** The setup skill reads the JSON file for programmatic decisions.

## Recommendation

**Needs rethinking on two decisions.** The architecture is close to coherent but has a fundamental contradiction:

1. **Decision 2 + Decision 3 conflict**: Wizard cannot both "keep SOUL.md seeding" AND "lose compose.py calls" — the seeding code depends on compose.py's output. Resolution: **Move SOUL.md seeding into compose.py's `deploy_role()`.** It already reads config.md and writes SOUL.md. Adding project context seeding there is a natural extension. Wizard's role becomes: create directories, write config.md, write `.install-spec.json`, create `.repo-scan.json`. Composition's role becomes: write CLAUDE.md, write SOUL.md, seed SOUL.md from install-spec and repo-scan. This is a cleaner boundary.

2. **The compose skill slash command file doesn't exist yet** — it's the entire orchestration target. Must be created before any caller migration begins. The skill should wrap `compose.py deploy-all` with pre-flight checks (config.md exists, roles directory exists) and post-compose validation (all expected CLAUDE.md files exist and are non-empty).

The remaining four decisions (always validate, conversation-based error reporting, remove agent-compose, CI two-step) are sound with the mitigations noted above. The removal of `agent_compose()` is safe and beneficial — it eliminates the recursive Claude-in-Claude risk that the prior research identified. The CI two-step works because `compose.py deploy-all` reads agent list from config.md which `scaffold_install` writes.

**Test suite impact is significant but manageable**: ~15 tests across 3 test files need updates. The `TestSoulMdSeeding` class is the trickiest — it tests wizard's current SOUL.md patching behavior which would move to compose.py.

## Vault Candidates

- **Type**: decision — "SOUL.md content ownership belongs to composition, not scaffolding" — **Why**: The current coupling between wizard's SOUL.md seeding and compose's SOUL.md writing creates a hard dependency that blocks clean separation. Formalizing that composition owns all instructional content (CLAUDE.md + SOUL.md) while scaffolding owns directory structure and configuration prevents future boundary violations.

- **Type**: learning — "Slash command files can drift from SKILL.md when both describe the same workflow" — **Why**: `squidsquad-upgrade.md` still describes the pre-compose.py parallel-subagent approach while SKILL.md has been updated. Two sources of truth for the same workflow without a sync mechanism is a documented process gap.

- **Type**: pattern — "LLM-enabled paths must degrade gracefully to deterministic equivalents — remove the path entirely if it was never enabled" — **Why**: `agent_compose()` in compose.py was a well-designed graceful-fallback pattern (falls back to deterministic output on any failure), but was never enabled in production. The decision to remove it entirely rather than keep it as dead code demonstrates the principle: dead code with good design is still dead code. Remove it.

- **Type**: learning — "No-op functions should be fully removed, not just emptied — boot_role has been a no-op since #4966 but is still imported and called from wizard.py" — **Why**: `boot_role` in compose.py:941–949 prints "no-op" and returns `[]`. wizard.py:1058–1067 still imports and calls it. This dead code complicates decoupling. Remove the function definition, the CLI commands (`boot`, `boot-all`), and all call sites.

- **Type**: decision — "Scaffolding and composition are distinct lifecycle phases: scaffold creates structure, compose creates content" — **Why**: This task formalizes a distinction that currently doesn't exist. The WIZARD.md runbook currently says "always go through compose.py deploy or wizard.py scaffold" — treating them as interchangeable. Formalizing the separation as an architectural decision prevents future features from blurring the boundary.
```