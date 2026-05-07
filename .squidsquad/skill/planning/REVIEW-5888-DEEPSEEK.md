Now let me produce the final research document.

---

# 5888 Research — PR #5894 /squidsquad-compose Skill Code Review

## Summary

PR #5894 introduces `/squidsquad-compose` as a Claude Code slash command that wraps `compose.py` for LLM-orchestrated flows (upgrade, post-merge recompose). The code review reveals a **well-structured slash command** that correctly delegates to `compose.py deploy` and `deploy-all`, but uncovers several gaps: a **distribution dead-end** where the slash command file won't reach installed projects, **incomplete dead-code cleanup** around the removed `boot_role` function in `compose.py`, and a **sync drift** between `SKILL.md` and `.claude/commands/squidsquad-upgrade.md` regarding which composition path to invoke.

**Recommendation**: Feasible with caveats. The slash command content is correct but the distribution mechanism is broken for downstream projects. The stale import in `wizard.py` line 1059 and `TEMPLATES_DIR` residue at `compose.py` line 938 must be cleaned. `SKILL.md` upgrade instructions (line 347) still call `compose.py deploy-all` directly while the upgrade slash command (line 9) invokes `/squidsquad-compose` — these must be reconciled.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" (pending) — `/squidsquad-compose` is prerequisite infrastructure for validation hooks. #5557 "Composed CLAUDE.md edit prohibition + compose.py guard" — the compose skill must be the sole writer of composed CLAUDE.md files.
- **Related decisions**: [[decision-sub-skill-architecture]] — Composition is build-time concatenation; the slash command is an orchestrator wrapping compose.py, not a replacement. [[decision-local-config-priority]] — `generate_local_config()` in compose.py writes `.local-config`; the skill wrapper must preserve this behavior.
- **Related patterns**: [[learning-atomic-migration-strategy]] — SKILL.md updates, slash command creation, and call-site updates must ship atomically.
- **Human preferences**: "Never ship with failed TCs" — the test suite has zero coverage for the compose slash command; tests should be added. "Prefers direct/mechanical checks over indirect state files" — the slash command's post-compose validation (file existence + non-empty check) aligns well.
- **Related learnings**: [[learning-atomic-migration-strategy]] — stale `squidsquad-upgrade.md` with parallel-subagent flow must be fixed in the same atomic change to prevent agents executing conflicting flows.

## Impact Analysis

- **Files touched**:
  - `.claude/commands/squidsquad-compose.md` (NEW) — slash command definition, lines 1–38
  - `.claude/commands/squidsquad-upgrade.md` (MODIFIED) — line 9 now invokes `/squidsquad-compose`
  - `references/commands/squidsquad-compose.md` (NEW) — reference copy, lines 1–38, identical content
  - `references/commands/squidsquad-upgrade.md` (MODIFIED) — line 9 invokes `/squidsquad-compose`
  - `references/installer-files.txt` (MODIFIED) — line 12 adds `references/commands/squidsquad-compose.md`
  - `references/sub-skills/roles/pm/post-merge-recompose.md` (MODIFIED) — line 25 uses `/squidsquad-compose`
  - `references/scripts/compose.py` — `boot_role` removed, `TEMPLATES_DIR` residue at line 938
  - `references/scripts/wizard.py` — stale `from compose import boot_role` at line 1059
  - `tests/test_compose.py` — empty `# boot_role` section at line 448, `TestStartRolePs1Template` tests dead references
  - `SKILL.md` — NOT updated: line 347 still uses direct `compose.py deploy-all`

- **Behavior changes**:
  1. LLM-orchestrated upgrade now routes through `/squidsquad-compose` (slash command) instead of direct `compose.py`
  2. PM post-merge recompose now triggers `/squidsquad-compose` instead of inline bash
  3. Wizard.py boot script generation (lines 1057–1067) has been a silent no-op since `boot_role` was removed from compose.py
  4. `boot_role`/`boot_all` fully removed from compose.py (correct)

- **Dependencies**:
  - `compose.py` (unchanged engine — importable Python API + CLI remain)
  - `wizard.py` scaffold — continues to import `deploy_role` directly (line 883), correct per DeepSeek audit recommendation
  - `add_role.py` — continues to call compose.py as subprocess, correct
  - Claude Code slash command system: `.claude/commands/` directory must contain the compose file

## Side Effects

- **Risk 1: Distribution dead-end — slash command unreachable in installed projects** — Severity: **H** — `installer-files.txt` distributes `references/commands/squidsquad-compose.md` (line 12), which lands at `references/commands/` in target projects. Claude Code reads slash commands from `.claude/commands/`, not `references/commands/`. No mechanism copies the file from `references/commands/` to `.claude/commands/`. The `/squidsquad-compose` slash command works in the SquidSquad dev repo (where `.claude/commands/squidsquad-compose.md` is tracked in git) but will silently fail in installed projects — Claude won't recognize it. **Same issue affects `squidsquad-upgrade.md`** (also present in `.claude/commands/` but distributed to `references/commands/`). Mitigation: Either (a) add `.claude/commands/squidsquad-compose.md` and `.claude/commands/squidsquad-upgrade.md` to `installer-files.txt`, or (b) have `wizard.py scaffold_install` copy from `references/commands/` to `.claude/commands/`, or (c) add a copy step to the CLI's `index.js` seed-commit logic (currently only writes `squidsquad-setup.md`).

- **Risk 2: SKILL.md vs slash command sync drift** — Severity: **M** — `SKILL.md` line 347 instructs agents to run `python references/scripts/compose.py deploy-all` directly during upgrade. But `.claude/commands/squidsquad-upgrade.md` line 9 instructs agents to invoke `/squidsquad-compose`. An agent reading SKILL.md does one thing; an agent reading the slash command file does another. Both produce correct output (same underlying compose.py call) but the divergence means the skill wrapper is bypassed for SKILL.md-driven upgrades. Mitigation: Update SKILL.md line 347 to invoke `/squidsquad-compose` instead of the direct Python call.

- **Risk 3: Stale `from compose import boot_role` in wizard.py** — Severity: **L** — `wizard.py` line 1059 imports `boot_role` from compose, which doesn't exist (removed in this PR). The `try/except ImportError` at line 1060 silently catches it, so it's harmless — but it's dead code that implies boot script generation still happens when it's been a no-op since #4966. Mitigation: Remove lines 1057–1067 entirely (the entire "Step 5. Generate boot scripts" block). The corresponding test at `test_wizard.py:863-873` (`test_boot_scripts_not_generated`) already verifies no boot scripts are written.

- **Risk 4: No test coverage for the compose slash command** — Severity: **M** — A grep for `squidsquad-compose` across the `tests/` directory returns zero matches. The slash command has no test coverage for its pre-flight checks, compose invocation, post-compose validation, or error handling. The `test_installer_wiring.py` tests verify `installer-files.txt` consistency but don't validate the slash command file content. Mitigation: Add tests that verify the slash command file content (correct compose.py invocations, proper steps) and verify it exists at the expected path.

## Edge Cases

- **Compose invoked when `compose.py` is missing**: The slash command's Step 1 pre-flight check handles this — verifies `references/scripts/compose.py` exists before proceeding. Correct.

- **Agent-driven compose recursive invocation**: `compose.py agent_compose()` (line 550) can spawn a Claude subprocess for output polishing. If `/squidsquad-compose` runs inside Claude and `agent-compose` config is enabled, this creates a recursive agent-in-agent call. The slash command's Notes section (line 37) correctly states that Python scripts continue to import compose.py directly — but doesn't address the recursive risk. The `agent_compose()` function already has a 120s timeout and graceful fallback (returns deterministic output on failure), so the risk is bounded. Mitigation: The slash command should mention that `agent-compose` should typically be `no` when running inside a Claude session.

- **Partial deploy failure during `deploy-all`**: `compose.py` line 1010–1018 wraps individual role deploys in try/except, collecting failures. The slash command correctly propagates these as validation failures (Step 3). Correct.

- **SOUL.md upgrade**: `compose.py upgrade-soul <role>` (line 1006–1013) is a CLI command for re-rendering the L1 base SOUL layer while preserving role content. This is NOT covered by the slash command. If a future upgrade needs to update SOUL.md base layers, there's no LLM-orchestrated path. Mitigation: Either add `/squidsquad-compose upgrade-soul <role>` to the slash command, or document that `upgrade-soul` is a mechanical-only operation called by `deploy_role` internally.

- **Running agents during recompose**: The slash command correctly notes (line 38) that sibling-clone agents pick up updated CLAUDE.md on their next `git pull`. No race condition.

## Integration Risks

- **PM post-merge recompose flow**: `references/sub-skills/roles/pm/post-merge-recompose.md` line 25 correctly invokes `/squidsquad-compose`. If the slash command isn't distributed (Risk 1), PM will attempt to invoke a non-existent slash command and fail. This creates a hard dependency on fixing the distribution gap.

- **Upgrade flow divided across two sources**: The upgrade flow exists in three places: SKILL.md (line 329), `.claude/commands/squidsquad-upgrade.md`, and `references/commands/squidsquad-upgrade.md`. Only the slash command versions invoke `/squidsquad-compose`. SKILL.md still uses direct `compose.py`. This triplication makes future changes error-prone — all three must stay in sync.

- **`installer-files.txt` path correctness**: `references/commands/squidsquad-compose.md` is the only new entry (line 12). The `test_installer_wiring.py:test_every_listed_file_exists_on_disk` (line 248) test will verify it exists. But the distribution gap means the file at that path won't function as a slash command in target projects.

## Upgrade & Migration

- **New config values**: none required
- **New files**: `.claude/commands/squidsquad-compose.md` (slash command, 38 lines), `references/commands/squidsquad-compose.md` (reference copy, identical content)
- **Template changes**: `.claude/commands/squidsquad-upgrade.md` — line 9 now invokes `/squidsquad-compose` instead of stale parallel-subagent flow. `references/sub-skills/roles/pm/post-merge-recompose.md` — line 25 now invokes `/squidsquad-compose` instead of inline bash.
- **Upgrade steps**: (1) New slash command arrives via `git pull` into dev repo's `.claude/commands/`. (2) Agent runs `/squidsquad-upgrade` which invokes `/squidsquad-compose`. (3) For downstream projects, the slash command must be distributed — currently broken (see Risk 1). (4) No schema bump, no data migration.
- **Graceful degradation**: If `/squidsquad-compose` is unavailable (old install or distribution gap), the SKILL.md upgrade path still works via direct `compose.py deploy-all`. The slash command path degrades to a "command not found" error, which is confusing but not data-corrupting.

## Open Questions

- **Q1**: How should `.claude/commands/squidsquad-compose.md` reach installed projects? — **Why**: Currently it's only distributed to `references/commands/`, which Claude Code doesn't read. Options: (a) add `.claude/commands/squidsquad-compose.md` to `installer-files.txt`, (b) have wizard.py copy from `references/commands/` to `.claude/commands/` during scaffold, (c) have the CLI copy it during `npx squidsquad` (alongside the hardcoded `squidsquad-setup.md`). Each option has different upgrade implications.

- **Q2**: Should SKILL.md upgrade instructions be updated to use `/squidsquad-compose`? — **Why**: SKILL.md line 347 still uses `python references/scripts/compose.py deploy-all`. If the slash command is the single LLM-orchestrated entry point, SKILL.md should invoke it. But if SKILL.md is the fallback for when slash commands aren't available, the direct call is correct. This needs clarification.

- **Q3**: Should the stale `from compose import boot_role` block (wizard.py lines 1057–1067) be removed in this PR or separately? — **Why**: It's dead code since #4966. Removing it is trivial but touches wizard.py outside the stated scope. Leaving it is harmless (silent no-op) but misleading.

- **Q4**: Should `compose.py upgrade-soul <role>` be added to the slash command? — **Why**: The slash command covers `deploy` and `deploy-all` but not `upgrade-soul`. If SOUL.md base-layer upgrades are ever needed via LLM orchestration, this gap would need filling. Currently `upgrade-soul` is a mechanical-only operation.

## Recommendation

**Feasible with caveats.** The slash command content is correct and well-structured — it properly delegates to `compose.py`, performs pre-flight checks, validates outputs, and preserves SOUL.md/vault. The primary delivery-blocker is the distribution gap (Risk 1): the slash command file won't reach target projects' `.claude/commands/` directory, making it invisible to Claude Code. Secondary issues include the SKILL.md/slash-command sync drift (Risk 2) and incomplete dead-code cleanup around `boot_role` removal (Risk 3). All are straightforward to fix but must ship atomically per [[learning-atomic-migration-strategy]].

## Vault Candidates

- **Type**: decision — "Slash command files must be distributed to `.claude/commands/`, not `references/commands/` — `references/commands/` is for agent-readable prose, not Claude Code registration" — **Why**: The current distribution mechanism puts files in a path Claude Code doesn't read. This is a fundamental architectural constraint that future slash commands must respect. Prevents recurrence of this gap for future commands like `/squidsquad-interval`, `/squidsquad-diagnostics`, etc.

- **Type**: learning — "Three-source sync problem: SKILL.md, `.claude/commands/squidsquad-upgrade.md`, and `references/commands/squidsquad-upgrade.md` must agree on the upgrade flow" — **Why**: The upgrade flow is described in three places with inconsistent composition invocation paths (direct compose.py vs `/squidsquad-compose`). The #5888 research already identified this drift risk. This PR partially fixes the slash command versions but leaves SKILL.md behind. A vault entry would flag this as a persistent process gap requiring a sync mechanism.

- **Type**: learning — "Dead `boot_role` import in wizard.py survived #4966 as a silent no-op for multiple cycles" — **Why**: `wizard.py` line 1059 imports a function that doesn't exist, caught by `except ImportError: pass`. The test suite (test_wizard.py:863-873) verifies boot scripts aren't written but doesn't verify the import isn't attempted. This is a pattern: silent no-ops masked by broad exception handling escape detection. Any future "remove deprecated function" work should also remove all importers and verify removal at the import level.

- **Type**: decision — "compose.py serves three distinct interfaces: Python API (wizard import), CLI (add_role subprocess), and Claude Code slash command (LLM orchestration)" — **Why**: Already identified in original #5888 research and confirmed by DeepSeek audit. Each interface serves a different caller with different constraints (setup/no-LLM, CI/deterministic, interactive/LLM-orchestrated). Formalizing prevents future proposals from collapsing these distinct interfaces.

- **Type**: pattern — "`TEMPLATES_DIR` at compose.py:938 is unused dead code — when removing a feature (boot_role), also remove its module-level constants" — **Why**: `TEMPLATES_DIR = REPO_ROOT / "references" / "templates"` was used by the removed `boot_role` function. The templates directory now contains only `forgejo-compose.yaml` (unrelated). `TestStartRolePs1Template` in test_compose.py references this constant and checks for template files that no longer exist (tests safely skip). This is a pattern of incomplete feature removal — the function was removed but its support infrastructure and test references were left behind.