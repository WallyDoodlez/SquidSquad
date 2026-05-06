I now have a thorough understanding. Let me compile the research:

```markdown
# FEAT-PM-5888 Research — /squidsquad-compose skill wrapping compose.py

## Summary
This research identified all call sites of `compose.py`, mapped the skill vs. sub-skill architecture, and analyzed what a `/squidsquad-compose` skill wrapper should look like. Currently `compose.py` is called from four places: setup (wizard.py import), upgrade (SKILL.md inline shell command), post-merge recompose (PM sub-skill inline shell command), and add-role (add_role.py subprocess). The proposed `/squidsquad-compose` skill would be a **Claude Code slash command** (`.claude/commands/squidsquad-compose.md` + SKILL.md section) that wraps `compose.py` as a first-class orchestration target, analog to `/squidsquad-setup` and `/squidsquad-upgrade`. This provides a single entry point for future #5868 validation hooks. The primary risk is migration: the `.claude/commands/squidsquad-upgrade.md` slash command file is already stale (it still references the pre-compose.py parallel-subagent flow), so the upgrade path needs attention.

## Vault Context
- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill (pending, high, role:skill) — compose-time config" directly drives this work. The skill wrapper is prerequisite infrastructure for #5868.
- **Related decisions**: [[decision-sub-skill-architecture]] — composition is build-time concatenation from references/sub-skills/. The skill wrapper is NOT a sub-skill; it's a Claude Code slash command that orchestrates compose.py. [[decision-local-config-priority]] — `generate_local_config()` in compose.py writes `.local-config` which takes priority over global clones; the skill wrapper must preserve this behavior.
- **Related patterns**: [[learning-atomic-migration-strategy]] — the entire migration (SKILL.md update + slash command creation + caller migration + test updates) must ship atomically to avoid agents getting mismatched instructions.
- **Human preferences**: "Terse, direct communication preferred" from [[human-profile]] — the skill wrapper's output should be concise. "Prefers direct/mechanical checks over indirect state files" — the compose validation should verify actual file output, not just exit codes.
- **Related learnings**: [[learning-atomic-migration-strategy]] — atomic delivery of infrastructure changes prevents coordination breakage across running agents.

## Impact Analysis
- **Files touched**:
  - **NEW**: `.claude/commands/squidsquad-compose.md` — slash command definition
  - **MODIFY**: `SKILL.md` — add `/squidsquad-compose` section (after `/squidsquad-interval` at line ~481)
  - **MODIFY**: `SKILL.md` — upgrade instructions (lines 329-394) change Step 3 from inline `compose.py deploy-all` to `trigger /squidsquad-compose`
  - **MODIFY**: `SKILL.md` — setup instructions (line 305) reference `/squidsquad-compose` instead of raw compose.py
  - **MODIFY**: `.claude/commands/squidsquad-upgrade.md` — Step 3 must switch from parallel subagent flow (stale) to `/squidsquad-compose` invocation
  - **MODIFY**: `references/sub-skills/roles/pm/post-merge-recompose.md` (line 25) — replace inline `python references/scripts/compose.py deploy-all` with `/squidsquad-compose deploy-all` invocation
  - **NO CHANGE**: `references/scripts/compose.py` — it remains the mechanical engine; the skill is a wrapper
  - **NO CHANGE**: `references/scripts/wizard.py` — it imports compose.py directly for scaffold (Python API, not CLI). Wizard could optionally route through the skill but this is unnecessary — wizard already owns its orchestration
  - **NO CHANGE**: `references/scripts/add_role.py` — it calls compose.py as a subprocess; could optionally route through skill but not required
  - **POTENTIAL**: `tests/test_compose.py` — no mechanical changes needed, but may need new tests for the skill wrapper itself if it has logic beyond dispatch
- **Behavior changes**:
  1. Setup: wizard.py continues to import compose.py directly (Python API) — no behavioral change
  2. Upgrade: agent no longer runs `python references/scripts/compose.py deploy-all` inline; instead triggers `/squidsquad-compose` which runs the same command but can add pre/post validation (#5868)
  3. Post-merge recompose: PM agent triggers `/squidsquad-compose` instead of inline bash
  4. `squidsquad-upgrade.md` slash command: currently has stale parallel-subagent flow; must be updated to match SKILL.md and use `/squidsquad-compose`
- **Dependencies**:
  - compose.py (unchanged engine)
  - `references/scripts/wizard.py` scaffold function (must stay import-compatible)
  - PM sub-skill `post-merge-recompose.md` (LLM instruction update)
  - SKILL.md upgrade instructions (LLM instruction update)

## Side Effects
- **Risk 1**: `.claude/commands/squidsquad-upgrade.md` is stale — Severity: **M** — The file (lines 19-31) still describes the old "Fan Out Agents in Parallel" approach where each role gets its own agent to regenerate templates. This hasn't been updated since compose.py took over template regeneration. If an agent reads that slash command file instead of SKILL.md's upgrade section, it will spawn parallel agents that conflict with compose.py's deterministic single-process approach. — Mitigation: Fix squidsquad-upgrade.md in the same atomic change.
- **Risk 2**: Skill wrapper delegation ambiguity — Severity: **L** — wizard.py and add_role.py call compose.py via Python import/subprocess. They should NOT be forced through the Claude Code slash command (which requires an LLM). The task is about LLM-driven flows (setup runbook, upgrade runbook, PM post-merge) using the skill. — Mitigation: Clearly document that `/squidsquad-compose` is for LLM-orchestrated flows; Python scripts continue to import compose.py directly.
- **Risk 3**: compose.py outputs are silent on success (no validation output) — Severity: **L** — Currently `deploy-all` prints per-role line counts but doesn't validate content integrity. #5868 will add validation, but until then, the wrapper should verify that all expected CLAUDE.md files were actually written (not zero-byte). — Mitigation: Make the skill wrapper do a post-compose existence check for every expected agent file.

## Edge Cases
- **Stale upgrade slash command**: `.claude/commands/squidsquad-upgrade.md` (lines 19-31) describes parallel subagent template regeneration. An agent consulting the slash command file directly would execute the wrong flow. This must be fixed atomically with the compose skill introduction.
- **Skill invoked when compose.py is missing**: If `references/scripts/compose.py` doesn't exist (corrupted install), the skill wrapper must detect this and report it clearly rather than failing with an opaque Python traceback.
- **Agent-driven compose enabled**: `compose.py agent_compose()` (line 550-637) can invoke Claude via subprocess to polish output. If `/squidsquad-compose` is itself running inside Claude, and the compose engine also calls Claude, there could be a recursive agent invocation. The `agent-compose` config flag controls this; the skill wrapper should respect it.
- **Partial deploy failure**: `deploy-all` wraps each role in try/except (line 1010-1018), collecting failures. The skill wrapper should propagate the failure list to the user rather than silently succeeding if some roles failed.
- **Running agents during recompose**: Upgrades write CLAUDE.md to the primary repo; agents in sibling clones pull on their next cycle. The skill wrapper should mention this (as the current SKILL.md does at line 390) but it's not a race condition — just a timing note.

## Integration Risks
- **Integration with #5868 event contracts**: The compose skill wrapper needs extension points for validation hooks. Currently compose.py has deterministic output verification (`test_compose.py` with ~75 test cases) but no runtime content validation. The skill wrapper should reserve a "validation" step between compose and report that #5868 can populate.
- **PM sub-skill post-merge-recompose**: This sub-skill instructs PM to run compose.py directly (line 25). Changing it to reference the slash command means PM must understand `/squidsquad-compose` as a trigger. The sub-skill markdown already describes bash commands; changing to a skill invocation is natural but different.
- **wizard.py direct import**: wizard.py imports `compose.deploy_role` at line 883 — this is a Python API call, not a CLI invocation. The skill wrapper is for LLM-driven flows and does NOT replace this import. No regression risk.

## Upgrade & Migration
- **New config values**: none
- **New files**: `.claude/commands/squidsquad-compose.md` (slash command definition)
- **Template changes**: 
  - `.claude/commands/squidsquad-upgrade.md` — must be rewritten (stale parallel-subagent flow → `/squidsquad-compose` based flow)
  - `SKILL.md` — new `/squidsquad-compose` section; existing upgrade section's Step 3 changed to reference it
  - `references/sub-skills/roles/pm/post-merge-recompose.md` — inline bash changed to skill invocation
- **Upgrade steps**:
  1. Users with existing installs get the new slash command on `git pull`
  2. Post-merge recompose (PM step 6e) picks up the new sub-skill text automatically on next recompose
  3. The stale `squidsquad-upgrade.md` slash command must be fixed atomically — if user runs `/squidsquad-upgrade` before the fix deploys, they get the old parallel-subagent behavior which may conflict
  4. No new schema versions, no config changes, no data migration
- **Graceful degradation**: If a user hasn't upgraded and runs old `squidsquad-upgrade.md` (parallel subagent flow), compose.py's deterministic output will still be correct but the parallel approach wastes API calls and risks coordination issues. The old flow DOES produce correct output — it's just inefficient.

## Open Questions
- **Q1**: Should `/squidsquad-compose` support a `--validate` flag for #5868 or should validation be implicit? — **Why**: If validation is implicit, every compose invocation runs validation which could be slow. If explicit, agents must remember to add `--validate` when #5868 lands.
- **Q2**: Should `wizard.py` and `add_role.py` also route through the skill wrapper, or stay as direct imports? — **Why**: Routing through the skill would create a circular dependency (skill → compose.py → skill). Direct imports are the right call but need to be documented as intentional.
- **Q3**: How does `/squidsquad-compose` report errors to the calling context when triggered from within a slash command? — **Why**: If the compose wrapper is called from within `/squidsquad-upgrade`, the upgrade flow needs to know whether compose succeeded to decide whether to proceed with config patching and commit.

## Recommendation
**Straightforward** — The compose skill wrapper is primarily a documentation/organization change with minimal mechanical risk. The key deliverables are:
1. `.claude/commands/squidsquad-compose.md` — slash command that runs `compose.py deploy-all` with pre-flight checks and post-compose validation
2. SKILL.md section documenting the `/squidsquad-compose` command
3. Update call sites to reference the skill instead of raw compose.py

The real complexity is fixing the stale `squidsquad-upgrade.md` slash command (which still has the parallel-subagent flow) and ensuring all four call sites are updated consistently. The atomic migration constraint from [[learning-atomic-migration-strategy]] mandates shipping compose.py → skill wrapper migration + squidsquad-upgrade.md fix in a single change.

## Vault Candidates
- **Type**: learning — "Slash command files can drift from SKILL.md when both describe the same workflow" — **Why**: `squidsquad-upgrade.md` still describes the pre-compose.py parallel-subagent approach while SKILL.md has been updated. This is a process gap — two sources of truth for the same workflow without a sync mechanism. Document to prevent recurrence.
- **Type**: decision — "Skill wrappers (Claude Code slash commands) vs. sub-skills (composed agent instructions) are distinct layers" — **Why**: This task forces a distinction that isn't currently documented in the vault: slash commands are user/agent-facing triggers; sub-skills are composed into agent instructions; Python scripts are mechanical helpers. The three-tier architecture (slash commands → compose.py → sub-skills) should be formalized to prevent future confusion about where to put new functionality.
- **Type**: pattern — "compose.py serves dual role: Python API (wizard import) and CLI (skill/agent invocation)" — **Why**: compose.py is used both as a mechanical library (wizard.py, add_role.py) and as a CLI tool driven by LLM agents (upgrade, post-merge recompose). This dual-use pattern should be preserved — the skill wrapper adds an LLM-friendly interface without breaking the Python API. Future scripts that touch composition should follow this pattern.
```