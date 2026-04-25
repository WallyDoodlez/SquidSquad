# FEAT-PM-2487 Context — Wire Cycle Runner Into Templates

## Scope

Replace the manual Ralph Loop mechanical steps with the cycle-runner 3-phase flow (cycle_pre → creative work → cycle_post) across all agent templates. The goal is to move non-deterministic, unreliable mechanical operations into deterministic scripts.

## Locked Decisions (human decided)

- **Composition-time substitution for [ROLE]**: compose.py substitutes [ROLE] in the cycle-runner sub-skill during deploy, same as it does for {{ROLE}} in boot scripts. Single sub-skill source, role-correct output.
- **No feature flag — cycle-runner is always on**: Remove the `Cycle Runner: yes/no` config flag. The 3-phase flow is the only flow. Existing sub-skills (pull-latest, git-commit, iteration-log) stay in the codebase as convenient tools agents can reference, but they are not part of the cycle flow.
- **Creative phase boundary**: Cycle-runner handles transport only (pull, commit, push, log, triage). All role-specific work (PM pipeline sentinel, QA verification, skill implementation, DM delivery) stays as creative work between pre and post scripts.
- **Permissive schema with warnings**: cycle_post processes whatever fields are present, warns on missing optional fields. No strict per-role validation.
- **Recompose at idle, reboot all**: Wait for all agents to go idle, recompose templates, reboot all agents. Clean cut.

## Dev Discretion (dev agent can choose)

- How to implement the composition-time [ROLE] substitution in compose.py
- Remove the Cycle Runner config flag and feature flag gate from the sub-skill
- Ordering of cycle-runner sub-skill relative to other includes
- How to structure the "skip when Cycle Runner enabled" markers if any are needed

## Side Effect Mitigations (required)

- **[ROLE] placeholder**: Must not appear as literal text in any deployed CLAUDE.md. Verify after composition.
- **No fallback needed**: Cycle-runner is always on. Remove the feature flag gate from the sub-skill text.
- **Suppressed cycles**: PM planning suppression must work correctly — cycle_pre already sets `suppressed: true` in cycle-input.json. Agent writes minimal cycle-output.json and runs cycle_post.
- **Branch switching**: cycle_pre handles branch checkout for QA/skill. cycle_post normalizes back to main. Agent instructions must not duplicate this.

## Upgrade Path (required)

- **Template changes**: All role CLAUDE.md files gain the cycle-runner sub-skill section
- **Upgrade steps**: compose.py deploy-all recomposes all templates. Agents need reboot to pick up new instructions.
- **Graceful degradation**: If user doesn't upgrade, nothing changes (old templates still have manual steps). Upgraded templates always use cycle-runner.

## Out of Scope

- Moving role-specific logic into cycle_pre/post scripts (that's a future optimization)
- Changing cycle_post.py schema validation (currently permissive, staying permissive)
- Removing the existing manual sub-skills from the codebase (they stay as reference)
