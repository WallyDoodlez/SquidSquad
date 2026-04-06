# FEAT-149 Research — Extract SOUL.md as Runtime-Injectable Files

**Feature**: Agent personality separate from template — souls as editable runtime files
**Date**: 2026-04-05
**Researcher**: PM research agent

---

## 1. Codebase Impact

### 1a. compose.py Changes

**File**: `references/scripts/compose.py`

Currently, `_resolve_includes()` (line 25) treats `{{include: souls/dev}}` identically to any other include — it reads the file from `references/sub-skills/souls/dev.md` and inlines it with `<!-- sub-skill: dev -->` markers. The `deploy_role()` function (line 137) calls `compose_role()` which triggers this resolution, meaning the full soul text is baked into the generated CLAUDE.md.

**Required changes (Approach A — runtime injection)**:
- `_resolve_includes()` must detect soul includes specifically (path starts with `souls/`) and replace them with a runtime read instruction instead of inlining the content.
- The replacement text would be something like:

```markdown
## Soul

Read your personality and behavioral guidelines from `.squidsquad/[ROLE]/SOUL.md` at the start of each cycle. This file defines your professional identity, quality bar, decision-making style, communication style, boundaries, collaboration posture, and self-improvement lens. Internalize it — it colors everything you do.

If `.squidsquad/[ROLE]/SOUL.md` does not exist, operate with professional defaults and note the missing file in your iteration log.
```

- Alternatively, a new directive like `{{runtime: souls/dev}}` could signal compose.py to emit a read instruction instead of inlining.

### 1b. Role Entry File Changes

**Files affected**:
- `references/sub-skills/roles/dev-agent.md` — line 1: `{{include: souls/dev}}`
- `references/sub-skills/roles/pm-agent.md` — line 1: `{{include: souls/pm}}`
- `references/sub-skills/roles/pm-lean.md` — line 1 (assumed same pattern)
- `references/sub-skills/roles/qa-agent.md` — line 1 (assumed same pattern)
- `references/sub-skills/roles/dm-agent.md` — line 1 (assumed same pattern)
- `references/sub-skills/roles/designer.md` — line 1 (assumed same pattern)

Each entry file's first line is the soul include. This would change to either:
- A new directive: `{{runtime: souls/dev}}` (compose.py emits a read instruction)
- Or the soul include is removed entirely and a "Read SOUL.md" instruction is added to the Ralph Loop preamble (e.g., in the "On Startup" section or as Step 0)

### 1c. New Files Created

Per-role SOUL.md files deployed to:
- `.squidsquad/skill/SOUL.md` (or whatever dev roles exist)
- `.squidsquad/pm/SOUL.md`
- `.squidsquad/dm/SOUL.md` (if DM present)
- `.squidsquad/qa/SOUL.md` (if QA present)
- `.squidsquad/designer/SOUL.md` (if designer present)

Source content comes from `references/sub-skills/souls/*.md` — these files remain as templates/defaults.

### 1d. Impact on Setup Flow

The setup flow (squidsquad-setup skill or equivalent) must:
1. Copy `references/sub-skills/souls/<role>.md` to `.squidsquad/<role>/SOUL.md` for each configured role during initial setup.
2. Dev agents use `souls/dev.md` as the default; PM uses `souls/pm.md`; etc.
3. Optionally prompt the human: "Want to customize agent personality? Edit `.squidsquad/<role>/SOUL.md`."

### 1e. Impact on Upgrade Flow

For existing installations:
1. Detect that `.squidsquad/<role>/SOUL.md` does not exist.
2. Extract the soul section from the existing CLAUDE.md (it's wrapped in `<!-- sub-skill: dev -->` / `<!-- /sub-skill: dev -->` markers — or `pm`, `qa`, `dm`, `designer` respectively).
3. Write it to `.squidsquad/<role>/SOUL.md`.
4. Redeploy CLAUDE.md without the inlined soul (run `compose.py deploy <role>`).

The `<!-- sub-skill: dev -->` markers in existing CLAUDE.md (visible in `.squidsquad/skill/CLAUDE.md` lines 6-60) make extraction straightforward — grep for the markers and extract the content between them.

### 1f. Impact on Boot Scripts

**Files**: `references/templates/start-role.sh`, `references/templates/start-role.ps1`

Boot scripts currently just launch Claude with `--append-system-prompt "SQUIDSQUAD_ROLE={{ROLE}}"`. The auto-boot mechanism in `CLAUDE.md` (repo root) reads `.squidsquad/<role>/CLAUDE.md` which currently contains the inlined soul.

With Approach A, **boot scripts do NOT need changes**. The CLAUDE.md auto-boot still works — it's just that the generated CLAUDE.md now contains a "Read SOUL.md" instruction instead of the inlined soul content. The agent reads SOUL.md dynamically during its cycle.

---

## 2. Runtime vs Compile-time Injection

### Approach A: Boot-time / Cycle-start Injection (Recommended)

**How it works**: compose.py stops inlining soul content. The generated CLAUDE.md contains an instruction: "Read `.squidsquad/<role>/SOUL.md` at cycle start and internalize it." The soul file lives as a standalone file the human can edit.

**Pros**:
- Edits take effect next cycle without any tooling — just save the file
- Different projects get different personalities by editing SOUL.md per project
- Setup flow can include personality customization as an interactive step
- Matches the BRIEFING.md pattern (runtime-injectable context file)
- Enables future: personality A/B testing, per-project tuning, human-in-the-loop soul editing
- Lower barrier: non-technical humans can edit personality without understanding compose.py

**Cons**:
- Agent must spend tokens reading SOUL.md every cycle (~700 tokens per read for a typical 55-line soul file)
- If SOUL.md is corrupted or deleted, agent behavior degrades until fixed
- Soul content is no longer visible in CLAUDE.md — debugging requires checking two files
- Slight risk of agent ignoring or deprioritizing the read instruction (though BRIEFING.md works fine with this pattern)

**Token cost estimate**: Each soul file is 54-60 lines, 540-660 words. At ~1.3 tokens/word, that's roughly **700-860 tokens per read**. Read once per cycle — negligible compared to the full CLAUDE.md which is 500+ lines and tens of thousands of tokens.

### Approach B: File-based with Redeploy

**How it works**: SOUL.md exists as a separate editable file, but compose.py reads it during `deploy` and inlines it into CLAUDE.md. Editing SOUL.md requires running `compose.py deploy <role>` afterward.

**Pros**:
- Zero runtime cost — soul is baked in at deploy time like today
- No risk of missing SOUL.md at runtime
- CLAUDE.md is self-contained — one file to debug

**Cons**:
- Does NOT achieve the primary goal: "edit and it works next cycle"
- Requires running compose.py after every edit — same friction as today
- Setup flow personality customization still requires a redeploy step
- Doesn't match the BRIEFING.md pattern the human wants to follow

### Recommendation: Approach A

The human explicitly wants runtime injection. The token cost is trivial (~800 tokens per cycle). The BRIEFING.md pattern already proves this works in the codebase. The only real risk is a missing/corrupted SOUL.md, which is mitigated by a graceful fallback (see Section 3).

---

## 3. Side Effects

### 3a. Missing SOUL.md

**Risk**: Agent boots or starts a cycle without SOUL.md present.

**Mitigation**: The "Read SOUL.md" instruction in CLAUDE.md should include a fallback:
> "If SOUL.md does not exist, operate with professional defaults appropriate to your role. Note the missing file in your iteration log and continue. Do not halt."

This is consistent with how agents handle missing BRIEFING.md (vault may not be initialized yet). The agent still functions — it just lacks personality customization.

### 3b. Invalid SOUL.md Content

**Risk**: Human writes invalid markdown, contradictory instructions, or content that confuses the agent.

**Mitigation**: SOUL.md is freeform markdown — there's no schema to validate against. The existing override clause in every soul file ("Human instructions always override these defaults") already handles this. If the human writes something weird, the agent follows it. This is by design — the human owns the personality.

No additional validation is needed. The worst case is an agent with odd communication style, which the human can fix by editing SOUL.md again (takes effect next cycle).

### 3c. Transition Period

**Risk**: Old CLAUDE.md has inline soul + new CLAUDE.md doesn't. During upgrade, there's a window where the agent may have neither (old CLAUDE.md without read instruction, new SOUL.md not yet created) or both (new CLAUDE.md with read instruction, but also old inline soul still present).

**Mitigation**: The upgrade flow must be atomic:
1. Create `.squidsquad/<role>/SOUL.md` from existing inline content
2. Redeploy CLAUDE.md (which now has the read instruction instead of inline soul)
3. These should happen in the same commit

The `compose.py deploy-all` command already exists and can handle step 2 for all roles.

### 3d. Context Window Cost

Each soul file is approximately **800 tokens**. Read once per cycle at step 0 (or on startup). Given that CLAUDE.md itself is 10,000-15,000 tokens and the agent's full context budget is 200K+, this is negligible — well under 1% of context.

The `improvement-scan.md` sub-skill already instructs agents to "Read your SOUL.md self-improvement lens" (line 29), so there's already a precedent for soul access during a cycle. Currently this references the inline content; with extraction, it would reference the file.

---

## 4. Edge Cases

### 4a. Fresh Install Race Condition

**Scenario**: `compose.py deploy <role>` runs before `compose.py` copies soul files to `.squidsquad/<role>/SOUL.md`.

**Mitigation**: The deploy command should be updated to also create SOUL.md if it doesn't exist. Alternatively, the setup flow creates SOUL.md before deploying CLAUDE.md. Either way, the order is: create SOUL.md first, then deploy CLAUDE.md.

The fallback instruction ("if SOUL.md doesn't exist, use defaults") covers any timing gap.

### 4b. Simultaneous SOUL.md Edits

**Scenario**: Two humans (or a human and a process) edit SOUL.md at the same time.

**Analysis**: SOUL.md is a local file per clone. Each agent instance has its own `.squidsquad/<role>/SOUL.md`. Git handles cross-clone synchronization via pull/push. Same-clone simultaneous edits are a standard filesystem concern — last write wins. This is identical to how `config.md`, `BRIEFING.md`, and `working-state.md` already work. No special handling needed.

### 4c. Accidental SOUL.md Deletion

**Scenario**: Human or git operation deletes SOUL.md.

**Mitigation**: The fallback instruction covers this (agent operates with defaults). To recover, the human can either:
- Re-run `compose.py deploy <role>` (which recreates SOUL.md from the template)
- Copy from `references/sub-skills/souls/<role>.md` manually
- Git restore from history

SOUL.md should be tracked in git (committed), so `git checkout` recovers it.

### 4d. Custom Soul for Unlisted Role

**Scenario**: A role has a custom SOUL.md but no default template in `references/sub-skills/souls/`.

**Analysis**: This is a feature, not a bug. The human creates a custom personality for a special-purpose agent. As long as SOUL.md exists in `.squidsquad/<role>/`, the agent reads it. The `references/sub-skills/souls/<role>.md` template is only needed for initial setup/reset.

---

## 5. Integration Risks

### 5a. compose.py Deploy

**Interaction**: compose.py still generates CLAUDE.md, but the soul section is replaced with a read instruction. The `souls/*.md` files in `references/sub-skills/` remain as source templates (used during setup to populate `.squidsquad/<role>/SOUL.md`).

**Risk**: Low. The change to compose.py is surgical — modify how `souls/` includes are handled. All other includes (`common/`, `pm-specific/`, etc.) work unchanged.

**Specific change**: In `_resolve_includes()` (compose.py line 31-48), when `include_path` starts with `souls/`, emit a read instruction instead of inlining. The sub-skill markers (`<!-- sub-skill: dev -->`) would no longer wrap the soul content in the generated CLAUDE.md.

### 5b. Vault Interaction

SOUL.md is NOT a vault note. It lives in `.squidsquad/<role>/SOUL.md`, not `.squidsquad/vault/`. It is agent configuration, not knowledge. The vault protocol's orphan detection (which scans `.squidsquad/vault/`) won't touch it. No vault changes needed.

However, the soul files reference vault notes via wikilinks (e.g., `[[code-conventions]]`, `[[human-profile]]`, `[[design-system]]`). These references still work because the agent resolves wikilinks at read time against the vault. Moving the soul out of CLAUDE.md doesn't change wikilink resolution.

### 5c. Sub-skill Dev Guide (#189)

If #189 introduces a new sub-skill development workflow, it needs to know that `souls/` sub-skills are special — they're runtime-injected, not compile-time inlined. The dev guide should document:
- `souls/*.md` in `references/sub-skills/` are templates, not directly included
- The actual soul content lives at `.squidsquad/<role>/SOUL.md`
- compose.py emits a read instruction for soul includes

**Risk**: Medium. If #189 ships before #149, the dev guide will document the current (inline) behavior. If #149 ships first, #189 needs to document the new (runtime) behavior. Coordinate ordering.

### 5d. Ralph Loop Modularization (#195)

If #195 modularizes the Ralph Loop into discrete sub-skill files, the "Read SOUL.md" instruction needs a clear home. Options:
- As part of the "On Startup" section (read once at session start)
- As Step 0 of the Ralph Loop (read every cycle)
- As a preamble in the role entry file (before the Ralph Loop)

**Risk**: Low. The read instruction is a single paragraph — it fits anywhere. If #195 creates a `common/soul-read.md` sub-skill, that's clean. If not, it goes in the role entry file preamble.

### 5e. Improvement Scan

`references/sub-skills/common/improvement-scan.md` line 29 says: "Read your SOUL.md self-improvement lens." Currently this is a reference to the inline soul section. With extraction, this instruction naturally becomes "read the file at `.squidsquad/<role>/SOUL.md`" — the instruction text doesn't even need to change since it already says "Read your SOUL.md."

---

## 6. Upgrade & Migration

### 6a. Creating SOUL.md for Existing Installs

**Strategy**: Add a migration step to the upgrade flow:

1. For each role directory in `.squidsquad/`:
   a. Check if `SOUL.md` already exists. If yes, skip (human may have customized it).
   b. Check if `CLAUDE.md` contains `<!-- sub-skill: dev -->` (or `pm`, `qa`, `dm`, `designer`) markers.
   c. If markers found: extract content between markers, write to `SOUL.md`.
   d. If markers not found: copy from `references/sub-skills/souls/<role>.md`.
2. Run `compose.py deploy-all` to regenerate all CLAUDE.md files without inline souls.
3. Commit both the new SOUL.md files and the updated CLAUDE.md files.

### 6b. Existing Inline Soul in CLAUDE.md

After migration, the old inline soul in CLAUDE.md is replaced by the read instruction. The `<!-- sub-skill: dev -->` markers disappear. The CLAUDE.md `<!-- GENERATED -->` header already warns not to edit — the regeneration removes the inline soul cleanly.

### 6c. Graceful Degradation (No Upgrade)

If a user doesn't upgrade:
- Their CLAUDE.md still has the inline soul. Everything works as before.
- No SOUL.md file exists. No impact — the old template doesn't reference it.
- When they eventually upgrade, the migration creates SOUL.md from the inline content.

This is fully backward-compatible. No breaking changes for users who don't upgrade.

---

## 7. Open Questions

### Q1: Where in the cycle should the agent read SOUL.md?

**Options**:
- **(a) On startup only** (once per session): Lower token cost, but edits only take effect on next session restart.
- **(b) At the start of each cycle** (Step 0): Edits take effect next cycle. ~800 extra tokens per cycle. Matches BRIEFING.md read pattern.
- **(c) On startup + when file mtime changes**: Best of both worlds but adds complexity (checking mtime each cycle).

**Recommendation**: Option (b). The human explicitly wants "changes take effect next cycle." 800 tokens is negligible. This matches how BRIEFING.md works.

**WHY this needs human input**: This determines the edit-to-effect latency and has a (small) token cost trade-off.

### Q2: Should compose.py deploy also create/update SOUL.md?

**Options**:
- **(a) Yes**: `compose.py deploy skill` creates both `.squidsquad/skill/CLAUDE.md` and `.squidsquad/skill/SOUL.md` (from template, only if SOUL.md doesn't exist).
- **(b) No**: SOUL.md is only created during setup. `compose.py deploy` only regenerates CLAUDE.md.

**Recommendation**: Option (a) with a "don't overwrite if exists" guard. This ensures SOUL.md is always present after any deploy, while preserving human customizations.

**WHY this needs human input**: Affects whether `compose.py deploy` is a single command that handles everything or whether SOUL.md creation is a separate step.

### Q3: Should SOUL.md be git-tracked?

**Options**:
- **(a) Yes, committed**: SOUL.md is part of the repo. Changes are versioned. Shared across clones via git pull.
- **(b) No, gitignored**: SOUL.md is local-only. Each clone/agent has its own personality. Not shared.

**Recommendation**: Option (a). SOUL.md is project config (like `config.md`, `BRIEFING.md`). It should be shared across the team's clones so all agents of the same role have consistent personality. Human customizations are versioned.

**WHY this needs human input**: If the human wants per-clone personality divergence (different personality for the same role on different machines), option (b) is needed. This seems unlikely but worth confirming.

### Q4: Should the read instruction be a new compose.py directive?

**Options**:
- **(a) New directive**: `{{runtime: souls/dev}}` — compose.py emits a read instruction instead of inlining.
- **(b) Hardcoded in compose.py**: `_resolve_includes()` detects `souls/` prefix and special-cases it.
- **(c) Replace in entry file**: Remove `{{include: souls/dev}}` from entry files, add the read instruction as plain markdown text.

**Recommendation**: Option (a). A new `{{runtime:}}` directive is clean, extensible (future sub-skills could also be runtime-injected), and self-documenting. The entry file reads `{{runtime: souls/dev}}` which clearly signals "this is loaded at runtime, not inlined."

**WHY this needs human input**: This is an architectural choice about compose.py's directive system. Option (c) is simpler but less extensible.

### Q5: What role name mapping does SOUL.md use?

Currently, all dev agents (skill, backend, frontend, etc.) share `souls/dev.md`. PM uses `souls/pm.md`. The mapping is implicit in the entry file (`dev-agent.md` includes `souls/dev`).

With runtime injection, the CLAUDE.md read instruction says "read `.squidsquad/<role>/SOUL.md`". But the source template for all dev agents is `souls/dev.md`. So during setup:
- `.squidsquad/skill/SOUL.md` gets a copy of `souls/dev.md`
- `.squidsquad/backend/SOUL.md` also gets a copy of `souls/dev.md`

This is actually a **feature** — the human can then customize each dev agent's personality independently even though they started from the same template.

**WHY this needs human input**: Confirm this per-role copy behavior is desired vs. a shared symlink/reference.

---

## 8. Recommendation

**Implement Approach A (runtime injection)** with the following specifics:

1. **New `{{runtime:}}` directive** in compose.py that emits a read instruction instead of inlining content.
2. **Read at cycle start** (each cycle, not just on startup) — matches BRIEFING.md pattern.
3. **SOUL.md created during deploy** (`compose.py deploy` creates it if missing, never overwrites existing).
4. **Git-tracked** — SOUL.md is committed like config.md.
5. **Graceful fallback** — agent operates with defaults if SOUL.md is missing.
6. **Migration** — upgrade flow extracts inline soul from existing CLAUDE.md using sub-skill markers.

**Implementation order**:
1. Add `{{runtime:}}` directive to compose.py
2. Update role entry files: `{{include: souls/dev}}` becomes `{{runtime: souls/dev}}`
3. Update `deploy_role()` to also create SOUL.md from template (if not exists)
4. Add migration logic to upgrade flow
5. Update manifest.md to document the new pattern
6. Update improvement-scan.md if needed (current wording already works)
7. Test: deploy, verify SOUL.md created, verify CLAUDE.md has read instruction, verify agent reads it

**Estimated scope**: Medium. Touches compose.py, 6 role entry files, manifest.md, setup/upgrade flow. No changes to boot scripts, vault protocol, or tracker.
