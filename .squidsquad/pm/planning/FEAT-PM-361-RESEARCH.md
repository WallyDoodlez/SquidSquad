# FEAT-PM-361 Research -- Project-Adaptive Role Souls

## Summary

Task #361 introduces two-phase soul adaptation: (A) setup-time seed generation from project intent, and (B) runtime enrichment where PM observes tasks/bugs and evolves role souls over time. The feature is unblocked -- #328 (intent-driven wizard with role manifest registry) has shipped. All five roles (pm, dev, qa, dm, designer) already have `### Project Context` and `### Project-Specific Responsibilities` placeholder sections in their reference SOUL.md templates, and `wizard.py scaffold` already writes `domain_context` into these placeholders at install time. This feature extends that foundation from a static one-shot fill to a living, LLM-generated adaptation section that grows with the project.

The primary risks are: (1) adaptation drift where PM infers something wrong and it silently pollutes all future agent behavior, (2) unbounded growth of adaptation sections without consolidation, and (3) coordination complexity when one signal should update multiple roles differently.

## Impact Analysis

- **Files touched**:
  - `references/roles/*/SOUL.md` -- add `## Project Adaptation` section placeholder
  - `references/scripts/wizard.py` -- extend scaffold to invoke Claude for soul seed generation
  - `references/wizard/WIZARD.md` -- add Step 9 review of adaptation addenda
  - `.squidsquad/vault/areas/role-adaptations.md` -- new file, PM's append-only changelog
  - `.squidsquad/config.md` -- add `Project Intent Description` field
  - `.squidsquad/vault/BRIEFING.md` -- include project intent at session start
  - PM CLAUDE.md template -- add "soul shepherd" sub-step to Ralph Loop
  - `references/scripts/compose.py` -- may need awareness of `## Project Adaptation` to preserve it on recompose

- **Behavior changes**:
  - Setup wizard gains an LLM generation step (Claude generates adaptation text per role)
  - PM's Ralph Loop gains a new sub-step each cycle: evaluate latest task/bug for character signals
  - Role SOUL.md files become partially machine-maintained (adaptation section)
  - `compose.py deploy` must preserve the `## Project Adaptation` section on template refresh

- **Dependencies**:
  - #328 (shipped) -- provides wizard Step 9 review screen and role manifest registry
  - compose.py's `deploy_role` function already skips existing SOUL.md -- this is compatible

## Side Effects

- **Risk 1**: Recompose clobbers adaptations -- `compose.py deploy` currently preserves existing SOUL.md files (never overwrites). But if a user runs `/squidsquad-upgrade` and the regenerate path replaces SOUL.md, adaptations would be lost. -- Severity: M -- Mitigation: compose.py must explicitly preserve `## Project Adaptation` sections during any regeneration, even if the rest of the soul is refreshed from the template.

- **Risk 2**: PM inference quality -- PM is an LLM with a finite context window. Early in a project's life (first 5-10 tasks), signals are sparse and PM may make premature inferences. -- Severity: M -- Mitigation: Require a confidence level on each adaptation entry and human-visible changelog in `role-adaptations.md`.

- **Risk 3**: Soul bloat slowing agent boot -- SOUL.md is read at every session start. If adaptation sections grow unbounded, they consume context tokens and slow boot. -- Severity: L -- Mitigation: Length cap with periodic consolidation (see Q8 below).

## Edge Cases

- **Empty project intent**: User skips or gives minimal intent during setup. Adaptation section should be left blank with a note: "No project intent provided -- PM will populate this as the project develops."
- **Contradictory signals**: Task #50 says "we never do frontend work" but task #75 adds a React component. PM must not silently overwrite; must note the contradiction.
- **Single-role installs**: If only PM and DM are installed, PM still shepherds both souls.
- **Pre-existing customized SOUL.md**: Existing installs may have hand-edited SOUL.md files. The adaptation section must be additive and clearly demarcated so hand edits in other sections are preserved.

## Integration Risks

- **compose.py interaction**: When compose.py recomposes CLAUDE.md (e.g., after a branch merge that updates templates), it currently leaves SOUL.md alone. This is correct behavior for this feature. However, if a future feature adds SOUL.md recomposition, it must preserve the `## Project Adaptation` section.
- **Vault remember interaction**: PM already does end-of-cycle vault reflection. The soul shepherd step is a new, separate sub-step that writes to `role-adaptations.md` and then re-renders live SOUL.md. These must not conflict with vault-remember's write budget.
- **Multi-clone setups**: Each agent runs in its own clone. When PM updates a role's SOUL.md in its clone, the other agent picks it up on `git pull --rebase` at their next cycle start. There is a lag of one cycle interval.

## Upgrade & Migration

- **New config values**: `Project Intent Description` field in config.md (default: empty string)
- **New files**: `vault/areas/role-adaptations.md` (created by PM on first signal, or by upgrade script)
- **Template changes**: All five reference SOUL.md templates gain a `## Project Adaptation` placeholder below the existing `### Project Context` and `### Project-Specific Responsibilities` sections
- **Upgrade steps**: `/squidsquad-upgrade` must:
  1. Add `Project Intent Description` to config.md if missing (default empty)
  2. Create `vault/areas/role-adaptations.md` if missing (empty template)
  3. Append `## Project Adaptation` section to each live SOUL.md if not already present (never overwrite existing content)
  4. For installs with already-customized SOUL.md: append the section at the end, clearly demarcated
- **Graceful degradation**: If a user does not upgrade, PM simply never runs the soul shepherd step (it checks for the existence of `role-adaptations.md` and the `## Project Adaptation` section). No breakage.

## Capability Gaps

- `capability_check.py skill` exits with code 2 (role manifest not found for `skill` -- `skill` is a dev agent alias, not a reference role name). This is expected behavior; the script looks for `references/roles/skill/manifest.yaml` which does not exist because `skill` maps to the `dev` role. No capability gap for this feature -- it requires no sub-skills, only PM's existing Claude reasoning.

---

## Open Questions -- Research Findings

### Q1: Frequency -- How often does PM's runtime enrichment update each role's soul?

**Recommendation: Signal-driven, not periodic.**

PM should evaluate every new task and bug for character signals as part of its normal Ralph Loop (a lightweight check, not a deep analysis). However, PM should only write an adaptation update when a genuine signal is detected. Expected frequency: roughly 1 update per 10-20 tasks in an active project, tapering to near-zero as the project character stabilizes.

Rationale:
- Periodic updates (every N tasks) create artificial writes -- most tasks are "normal work" that teach nothing new about the project.
- Per-task evaluation is cheap (one internal reasoning step), while per-task writing would create noise.
- The soul shepherd step should be a lightweight filter: "Does this task reveal something new about the project character?" If no, move on. If yes, draft the adaptation update.

### Q2: Conflict resolution -- How are contradictions resolved?

**Recommendation: Append with supersession markers, never silent overwrite.**

When PM detects a signal that contradicts an earlier adaptation:
1. PM appends a new entry to `role-adaptations.md` with an explicit `Supersedes:` reference to the earlier entry.
2. PM re-renders the live SOUL.md `## Project Adaptation` section by replaying all non-superseded entries.
3. The contradiction is noted in the Discussion entry on the triggering issue.

Rationale:
- Silent overwrite loses history and makes rollback impossible.
- Append-only with supersession markers gives full auditability via git history and the changelog file.
- Re-rendering from the changelog means the live SOUL.md always reflects the current state, not accumulated silt.

### Q3: Trigger rules -- What makes PM decide "this reveals something about the project"?

**Recommendation: A checklist of signal categories.**

PM applies this internal checklist to each new task/bug:
1. **Deliverable type shift**: Does this task introduce a new kind of deliverable (e.g., first API endpoint, first mobile screen, first data pipeline)? If yes, this changes what "shipping" means for dev/dm.
2. **Tech stack evolution**: Does this task introduce a new language, framework, or tool not previously used? If yes, this changes dev's implementation context and QA's verification approach.
3. **Domain vocabulary**: Does the human use domain-specific terms (e.g., "actuarial tables", "campaign brief", "sprint retrospective") that reveal the project's domain? If yes, all roles benefit from knowing the domain lens.
4. **Quality/process preference**: Does the human express a quality standard, process preference, or constraint (e.g., "we need 100% test coverage", "no external dependencies", "must work offline")? If yes, this constrains dev and QA behavior.
5. **User persona shift**: Does this task reveal a new user type or audience (e.g., "our API consumers are enterprise clients")? If yes, DM's communication style and dev's error handling approach may need to adapt.

If none of these apply, the task is "normal work" and no adaptation update is triggered.

### Q4: Human oversight on runtime updates -- Approve every update, or PM updates silently?

**Recommendation: PM updates silently, human can review and override.**

Arguments for silent updates:
- The human already approved the tasks that generated the signals. The adaptation is a downstream inference, not a new decision.
- Requiring approval for every adaptation would create friction and slow the feedback loop (human might not respond for hours/days).
- The `role-adaptations.md` file is fully auditable -- human can read it anytime and revert via git.

Safeguards:
- PM mentions significant adaptation updates in its cycle check-in: "Updated dev soul: this project now includes data pipeline work."
- Human can edit `role-adaptations.md` directly as an override path (per the acceptance criteria).
- Human can set a config flag `Adaptation Approval: yes` if they want to opt into mandatory approval (future, out of scope for v1).

### Q5: Rollback mechanism -- How is a bad inference corrected?

**Recommendation: Human edits `role-adaptations.md` directly, PM re-renders.**

Rollback flow:
1. Human notices a bad adaptation (either by reading SOUL.md, seeing odd agent behavior, or reviewing `role-adaptations.md`).
2. Human edits `role-adaptations.md`: marks the bad entry with `Status: reverted` and optionally adds a corrected entry.
3. On PM's next cycle, PM detects the edit (file mtime changed), re-renders the affected role's `## Project Adaptation` section from the non-reverted entries.
4. PM commits and pushes. The role picks up the corrected SOUL.md on its next pull.

This is simple, uses existing git primitives, and does not require new tooling. An automated rollback UI is explicitly out of scope per the issue.

### Q6: Cross-role consistency -- How are multi-role signals coordinated?

**Recommendation: PM writes all role adaptations atomically in a single commit.**

When a signal affects multiple roles (e.g., "we are now a data pipeline project" affects dev, QA, and DM):
1. PM drafts adaptation entries for each affected role.
2. PM appends all entries to `role-adaptations.md` in a single block with a shared `Signal:` reference.
3. PM re-renders all affected roles' `## Project Adaptation` sections.
4. PM commits all changes in a single commit: `chore: soul adaptation -- [signal description]`.

This ensures atomicity -- no agent sees a partial update. All agents pull the complete set of changes together.

### Q7: Startup re-loading -- When PM updates role-adaptations.md, does it re-render live SOUL.md immediately?

**Recommendation: Yes, PM re-renders immediately after writing to role-adaptations.md.**

Flow:
1. PM detects signal, appends to `role-adaptations.md`.
2. PM re-renders each affected role's `## Project Adaptation` section in the live `.squidsquad/<role>/SOUL.md`.
3. PM commits and pushes.
4. Other agents pick up the new SOUL.md on their next `git pull --rebase` (Step 1 of their Ralph Loop).

There is no "lazy re-render" or "wait for next cycle" -- PM does the full update cycle in one step. The affected agent reads the updated SOUL.md on its next session start or context reset (when it re-reads SOUL.md from disk).

Note: Agents read SOUL.md at session start, not every cycle. So the update takes effect on the agent's next fresh session (context reset, self-restart, or manual restart). This is acceptable because soul changes are strategic, not urgent.

### Q8: Length cap -- How long can an adaptation grow before consolidation?

**Recommendation: 30-line soft cap with consolidation trigger.**

Rules:
- The `## Project Adaptation` section in a live SOUL.md should not exceed ~30 lines (roughly 500-800 tokens).
- PM tracks section length on each write. When the section exceeds 30 lines, PM triggers consolidation:
  1. Re-read all non-reverted entries in `role-adaptations.md` for this role.
  2. Generate a consolidated summary (Claude call) that captures the essential character in fewer lines.
  3. Replace the `## Project Adaptation` section with the consolidated version.
  4. Mark all pre-consolidation entries in `role-adaptations.md` as `Status: consolidated` with a reference to the consolidated version.
- After consolidation, the section should be 15-20 lines.

This prevents unbounded growth while preserving the full history in `role-adaptations.md`.

---

## Additional Research

### Q9: Integration with #328 -- Setup flow and soul generation

#328 has shipped (status: shipped, closed). The wizard flow now has:
- Step 1b: Adaptive context questions (captures `domain_context`)
- Step 2: Intent classification (captures preset)
- Step 6: Review screen with [E]dit option
- Step 7: Scaffold (writes files to disk)

**Current state**: `wizard.py scaffold` already fills the `### Project Context` placeholder in SOUL.md with `domain_context` from the install spec. It also fills `### Project-Specific Responsibilities` from repo scan results.

**Gap for #361**: The current fill is mechanical (string replacement). Task #361 needs Claude to generate a richer, role-specific adaptation. This cannot happen in `wizard.py` (Python, deterministic, no LLM access). It must happen in the wizard agent (Claude session running WIZARD.md).

**Proposed integration point**: Between Step 6 (review screen) and Step 7 (commit/write):
- New **Step 6b**: For each installing role, the wizard agent generates a `## Project Adaptation` section using the collected project intent, domain context, and the role's base soul template.
- The wizard agent uses its own Claude reasoning (no external API call needed -- it IS Claude).
- Results are shown in the Step 6 review screen (or as a separate review sub-step with [E]dit option).
- Confirmed adaptations are passed to `wizard.py scaffold` as part of the install spec, which writes them into the live SOUL.md files.

This requires:
- `wizard.py scaffold` to accept an `adaptations` dict in the spec (keyed by role, containing the generated text).
- WIZARD.md to document the generation prompt and review flow.

### Q10: Storage format -- Example `## Project Adaptation` sections

Below are example adaptations for a hypothetical **Python web API project** (FastAPI backend, PostgreSQL, deployed to AWS, team of 3 developers, serving enterprise customers).

**PM adaptation example:**
```markdown
## Project Adaptation

This is a production Python web API serving enterprise customers. Planning must account for:

- **Shipping means**: API endpoints are live and documented, integration tests pass against staging, OpenAPI spec is updated, and migration scripts run cleanly on the staging database.
- **Primary deliverables**: API endpoints, database migrations, background job definitions, integration test suites, OpenAPI documentation.
- **Domain vocabulary**: "tenants" (multi-tenant SaaS), "migrations" (Alembic), "workers" (Celery background jobs), "contracts" (API versioning promises to enterprise clients).
- **Priority lens**: Breaking API changes are always high severity (enterprise clients depend on stability). Performance regressions in hot paths are medium. Internal tooling improvements are low unless they unblock a blocked feature.
```

**Dev (skill) adaptation example:**
```markdown
## Project Adaptation

This is a FastAPI + PostgreSQL project deployed to AWS ECS. Implementation context:

- **Tech stack**: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery + Redis, pytest, mypy strict mode.
- **Code patterns**: Repository pattern for data access, Pydantic v2 models for request/response validation, dependency injection via FastAPI Depends. Async handlers for I/O-bound routes.
- **Testing expectations**: Every endpoint needs an integration test hitting a test database. Unit tests for business logic. No mocking the database in integration tests -- use a real test PostgreSQL instance.
- **Constraints**: All API changes must be backwards-compatible (enterprise clients). New fields are always optional. Deprecation requires a 2-version grace period.
```

**QA adaptation example:**
```markdown
## Project Adaptation

This is an enterprise API project. Verification context:

- **What "verified" means here**: Endpoint returns correct status codes and response shapes. Database state is consistent after operations. Concurrent requests do not cause data races. Error responses follow the project's error envelope format.
- **Critical test areas**: Authentication/authorization (multi-tenant isolation), database migrations (up AND down), API versioning (old clients still work), background job idempotency.
- **Regression hotspots**: Tenant data isolation, rate limiting, pagination edge cases (empty results, last page).
```

**DM adaptation example:**
```markdown
## Project Adaptation

This project serves enterprise API consumers. Delivery context:

- **Audience**: Backend developers at enterprise clients integrating our API. Technical, impatient, need exact endpoint documentation.
- **Shipping means**: CHANGELOG entries reference API endpoint changes with before/after request/response examples. README updates focus on getting-started and migration guides. OpenAPI spec is the primary reference -- docs point to it.
- **Tone**: Professional, precise, no marketing language. Enterprise clients want accuracy, not enthusiasm.
- **Version communication**: Semantic versioning is a contract. Breaking changes get dedicated migration guides with code examples.
```

**Designer adaptation example:**
```markdown
## Project Adaptation

This project is a backend API with no user-facing frontend. Design context:

- **Primary design work**: API documentation layout, error message formatting, developer portal UX (if applicable), CLI tool interfaces.
- **No traditional UI work**: This project has no web frontend, mobile app, or visual interface to design. Design specs focus on information architecture, documentation structure, and developer experience.
- **Constraints**: All design output must be implementable as static documentation or CLI formatting -- no JavaScript-heavy interactive components.
```

### Q11: Capability gap analysis

`capability_check.py skill` exits with code 2 (role manifest not found for `skill`). This is because `skill` is a project-specific dev agent name that maps to the `dev` reference role. The capability check script expects reference role names, not agent aliases. No capability gap exists for this feature -- it requires only PM's native Claude reasoning ability, no external sub-skills or tools.

### Q12: Upgrade path for existing installs

**Scenario A -- Existing install, no customized SOUL.md**:
The `/squidsquad-upgrade` flow (regenerate templates) already preserves existing SOUL.md via `compose.py`. Upgrade adds:
1. `## Project Adaptation` placeholder appended to each role's SOUL.md (if not present).
2. `role-adaptations.md` created in vault/areas/ (empty template).
3. `Project Intent Description` field added to config.md (empty -- human can fill it, or PM will infer from existing tasks).
4. PM's Ralph Loop automatically starts the soul shepherd sub-step. Since there is no initial intent, adaptations accumulate gradually from task signals.

**Scenario B -- Existing install, hand-customized SOUL.md**:
The upgrade script detects existing `## Project Adaptation` content (or any custom content at the end of SOUL.md) and does NOT overwrite it. It only appends the `## Project Adaptation` section if it does not already exist. If the user has written custom content in the location where `## Project Adaptation` would go, the upgrade appends at the very end of the file with a clear section header. Hand edits in other sections (Professional Identity, Quality Bar, etc.) are never touched.

**Scenario C -- Fresh install after #361 ships**:
Full flow: wizard generates adaptation seed at setup time (Step 6b), writes it into SOUL.md at install. PM starts enriching from cycle 1.

## Open Questions

- **Q-A**: Should the wizard prompt for seed generation be standardized in a template file (e.g., `references/prompts/soul-seed.md`), or inline in WIZARD.md? -- **Why**: Keeping it in a template file makes it testable and versionable independently. Inline is simpler but harder to test.
- **Q-B**: Should `role-adaptations.md` be in `vault/areas/` (as specified in the issue) or in `.squidsquad/pm/` (closer to PM's domain)? -- **Why**: vault/areas/ makes it visible to all agents and browsable in Obsidian. PM's directory keeps it within PM's ownership boundary.

## Recommendation

**Feasible with caveats.** The core mechanism is straightforward -- PM already evaluates every task, and the SOUL.md infrastructure exists. The main caveats are:

1. **Setup-time generation requires careful wizard integration** -- Claude must generate role-specific adaptations, and the human must review each one. This adds time to setup but the review is essential.
2. **Runtime enrichment needs a tight feedback loop** -- PM must mention significant updates in its check-in so the human stays aware, even though approval is not required.
3. **Consolidation logic adds complexity** -- The 30-line cap with consolidation re-generation is the most complex part and should be carefully tested.
4. **compose.py must be audited** -- Any code path that could overwrite SOUL.md must be checked to ensure it preserves the `## Project Adaptation` section.
