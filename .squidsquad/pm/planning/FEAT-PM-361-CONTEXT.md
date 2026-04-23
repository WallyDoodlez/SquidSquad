# FEAT-PM-361 Context — Project-Adaptive Role Souls

## Scope

Make role SOUL.md files adapt to the specific project they're deployed on. Two parts: setup-time seeding (Claude generates initial Project Adaptation per role from project intent) and runtime enrichment (PM observes tasks/bugs and updates souls when new project character is learned). All roles get adaptive souls.

## Locked Decisions (human decided)

- **Signal-driven frequency**: PM checks each task/bug against a 5-category checklist (deliverable type, tech stack, domain vocabulary, quality preference, user persona). Updates only when something new is learned. Expected ~1 per 10-20 tasks.
- **Flag human on contradictions**: When new signals contradict earlier adaptations, PM detects the contradiction and asks human to resolve before updating. Non-contradictory new signals are added silently.
- **5-category trigger checklist**: Deterministic trigger rules PM applies to each task. If any category has a new signal not already in the adaptation, it triggers an update.
- **Silent with audit trail**: PM updates adaptations and mentions significant changes in check-in. Human can review/revert via git history. Only contradictions require human approval.
- **Human edits directly for rollback**: Human edits `role-adaptations.md` directly. PM re-renders SOUL.md on next cycle. No special revert command needed.
- **Atomic single commit**: When one task teaches multiple roles different things, PM updates all affected roles in one commit. Consistent state, no partial updates.
- **Immediate re-render**: PM writes adaptations and re-renders SOUL.md in the same cycle. Agents pick up changes on next `git pull`.
- **40-line soft cap**: When Project Adaptation section exceeds 40 lines, PM consolidates — merges related entries, trims redundancy, preserves key insights.
- **Project-specific delivery in SOUL.md**: From #13 discussion — project-specific delivery steps (npm publish, tarball, cargo publish, etc.) belong in SOUL.md as role customization, not config.
- **Comprehension tests required**: Any agent step changes must include comprehension test specs.

## Dev Discretion (dev agent can choose)

- Exact format of `role-adaptations.md` entries (as long as append-only and timestamped)
- How PM renders the adaptation section into live SOUL.md (template injection, string replacement, etc.)
- Internal structure of the 5-category checklist (as long as all 5 categories are covered)
- Consolidation strategy when hitting 40-line cap (as long as no information is lost)

## Side Effect Mitigations (required)

- **Source templates untouched**: `references/roles/<role>/SOUL.md` must never be modified by runtime enrichment. Only live `.squidsquad/<role>/SOUL.md` gets the adaptation section.
- **compose.py compatibility**: compose.py must not overwrite the Project Adaptation section when regenerating templates. It already skips existing SOUL.md files — verify this is maintained.
- **Vault consistency**: `vault/areas/role-adaptations.md` is append-only. PM never deletes entries, only adds or marks as superseded (via human edit).
- **Context budget**: 40-line cap ensures SOUL.md doesn't bloat agent context windows.
- **Atomic commits**: Multi-role updates from a single signal must land in one commit to prevent inconsistent state.

## Upgrade Path (required)

- **Existing installs with customized SOUL.md**: Upgrade adds `## Project Adaptation` section below existing content. Existing customizations preserved.
- **Existing installs with generic SOUL.md**: Upgrade regenerates SOUL.md from template, then prompts for project intent to seed adaptation.
- **Fresh installs**: Setup wizard generates adaptation as part of normal flow.
- **Missing role-adaptations.md**: PM creates it on first signal detection. Not an error.
- **Graceful degradation**: If no adaptation section exists, roles work with generic souls. No breakage.

## Out of Scope

- Cross-project learning (shared adaptations across installs)
- Automatic adaptation rollback (human edits directly)
- Visual diff of adaptation changes
- Role-to-role adaptation propagation (dev learns from designer's signals)
- Non-PM roles writing adaptations (PM exclusive in v1)
