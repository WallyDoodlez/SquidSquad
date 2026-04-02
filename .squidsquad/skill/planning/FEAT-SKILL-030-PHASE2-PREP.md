# FEAT-SKILL-030 Phase 2 Prep -- Discussion Options

## Suggested Question Order

| Order | Question | Rationale |
|-------|----------|-----------|
| 1 | **Q2** (build-time vs runtime composition) | Foundational architecture decision. Every other question depends on whether agents see composed files or raw sub-skills. |
| 2 | **Q5** (concatenation vs separate file reads) | Closely coupled to Q2. Once composition timing is decided, this pins down the output format. |
| 3 | **Q1** (directory location for sub-skill sources) | Now that we know how composition works, we can place the source files. Low controversy, high dependency for later work. |
| 4 | **Q3** (fate of agent-instructions.md) | Depends on Q1/Q2/Q5 answers. If build-time concatenation wins, agent-instructions.md can become generated output. |
| 5 | **Q7** (schema version bump) | Depends on Q1-Q3 to know what config.md changes are needed. Determines migration complexity. |
| 6 | **Q6** (--print vs Agent tool for hardened execution) | Phase B design question. Independent of file structure but depends on understanding the composition model. |
| 7 | **Q8** (atomicity testing) | Testing strategy depends on all prior decisions being settled. Best discussed once the design is locked. |
| 8 | **Q4** (minimum viable Phase C) | Most scope-sensitive and potentially controversial. Best discussed last when A and B are well-defined, so we can realistically assess what ships atomically. |

---

### Q2: Build-time vs runtime template composition
**Category**: Architecture
**Why it matters**: This determines whether agents see pre-composed single files (as today) or must read multiple sub-skill files at boot. It affects context pressure, failure modes, boot reliability, and the entire composition pipeline design.

**Option A**: Build-time composition (setup/upgrade generates monolithic templates from sub-skill sources)
- Pros: Agents read exactly one file (no change to boot path); no ordering bugs at runtime; missing sub-skill file is caught at generation time, not at agent boot; template output can be diffed against current monoliths to verify equivalence
- Cons: Any sub-skill change requires full template regeneration via upgrade; slightly more complex upgrade logic; sub-skill boundaries invisible to running agents

**Option B**: Runtime composition (CLAUDE.md instructs agents to Read N sub-skill files in sequence)
- Pros: No generation step needed; sub-skill changes take effect immediately on next agent boot; clearer sub-skill boundaries visible in agent context
- Cons: Agents must Read 5-8 files at boot (context pressure); file ordering bugs possible; any missing file breaks agent boot; harder to verify correctness; boot path fundamentally changes

**Option C**: Hybrid -- build-time for common sub-skills, runtime Read for role-specific overrides
- Pros: Balances stability (common parts pre-composed) with flexibility (role parts loaded dynamically); limits runtime file reads to 1-2 extra files
- Cons: Two composition mechanisms to maintain; harder to reason about what the agent actually sees; debugging requires understanding both paths

**Recommended**: A -- Build-time composition preserves the proven single-file boot path, catches errors early, and enables diff-verified migration. The research already recommends this.

---

### Q5: Concatenation into templates vs separate file reads at runtime
**Category**: Architecture
**Why it matters**: Even if build-time composition wins (Q2), we still need to decide whether the composed output is one file per role or multiple files. This affects template size, update granularity, and agent context consumption.

**Option A**: Full concatenation -- one composed template file per role (current behavior preserved)
- Pros: Agents read exactly one file; no change to bootstrapper CLAUDE.md; template is self-contained and portable; easiest to diff against current monoliths
- Cons: Any sub-skill change requires regenerating entire template; larger files (but no larger than today); sub-skill boundaries lost in output

**Option B**: Separate files -- agents Read each sub-skill file independently at boot
- Pros: Granular updates (change one sub-skill, only that file changes); smaller individual files; clear sub-skill boundaries in agent context
- Cons: 5-8 Read calls at boot; context pressure; ordering dependencies; any missing file breaks boot; CLAUDE.md bootstrapper must list all files in correct order; harder to test

**Option C**: Concatenation with section markers -- one file but with `<!-- sub-skill: [name] -->` delimiters
- Pros: Single file read (simple boot); sub-skill boundaries visible for debugging/maintenance; upgrade can diff individual sections; enables future tooling to extract/replace sections
- Cons: Markers add minor noise; composition logic slightly more complex; agents might reference marker comments (unlikely but possible)

**Recommended**: C -- Full concatenation with section markers gives the reliability of a single file while preserving sub-skill traceability. The markers cost nothing at runtime and are valuable for maintenance and debugging.

---

### Q1: Where should sub-skill source files live?
**Category**: Scope / file structure
**Why it matters**: Directory placement affects upgrade flow file discovery, whether sub-skills feel like "reference material" or "first-class entities," and whether a second migration is needed later.

**Option A**: `references/sub-skills/` (nested under existing references directory)
- Pros: Consistent with existing pattern (agent-instructions.md lives in references/); upgrade flow already knows about references/; no new top-level directory clutter; clear that these are source material for generation
- Cons: Deep nesting (references/sub-skills/common/tracker-protocol.md is 4 levels); "references" implies read-only material, but sub-skills are actively composed; may feel wrong if sub-skills evolve into something more than references

**Option B**: Top-level `sub-skills/` directory
- Pros: First-class visibility; short paths; clear separation from other reference material; signals that sub-skills are a core architectural concept
- Cons: New top-level directory in the repo; breaks the pattern of all SquidSquad source material living under references/; may confuse users who expect sub-skills to be a Claude Code platform feature

**Option C**: `.squidsquad/sub-skills/` (under the generated directory)
- Pros: Co-located with the rest of the SquidSquad install; clear ownership; self-contained install directory
- Cons: Mixes source files (sub-skill definitions from SKILL.md) with generated files (templates, config); .squidsquad/ is per-install, but sub-skill sources are per-skill-version; upgrade must overwrite these files, which feels wrong for a "generated" directory

**Recommended**: A -- `references/sub-skills/` is the natural home. These files are reference material that gets composed into templates, exactly like `agent-instructions.md` today. The deeper nesting is a minor cost.

---

### Q3: What happens to `references/agent-instructions.md`?
**Category**: Migration / compatibility
**Why it matters**: This file is currently the source of truth for template generation. Changing its role affects the entire template pipeline and any tooling or documentation that references it.

**Option A**: Keep as generated artifact -- composed from sub-skills for human readability and backward compatibility
- Pros: Humans can still read one file to see what agents get; backward-compatible with any tooling referencing this file; serves as a "compiled" view of the sub-skill architecture; easy diff target for verifying sub-skill composition
- Cons: Two sources of truth risk (someone edits agent-instructions.md instead of sub-skills); must be regenerated on every sub-skill change; file becomes "do not edit" which may confuse contributors

**Option B**: Delete and replace entirely with sub-skill sources
- Pros: Single source of truth (sub-skill files only); no risk of editing the wrong file; cleaner repo structure; forces everyone to understand the sub-skill model
- Cons: Loses the "one file to read" convenience for humans; breaks any existing references to agent-instructions.md; harder for newcomers to understand what agents actually see

**Option C**: Keep as the primary source, extract sub-skills as read-only views
- Pros: Minimal disruption to current workflow; agent-instructions.md remains the single source of truth; sub-skill files are just sliced views for potential future use
- Cons: Defeats the purpose of sub-skill architecture; no real decomposition benefit; sub-skill "views" would drift from the source; does not enable independent sub-skill evolution

**Recommended**: A -- Keep agent-instructions.md as a generated artifact with a clear "DO NOT EDIT -- generated from sub-skills" header. This preserves human readability and backward compatibility while making sub-skill files the true source.

---

### Q7: Does sub-skill architecture warrant a new schema version (Schema 4)?
**Category**: Migration / versioning
**Why it matters**: Schema versions track structural changes that require migration. If we bump, we need a migration path. If we don't, we need another way to detect pre-sub-skill installs.

**Option A**: Bump to Schema 4 -- sub-skill architecture is a structural change
- Pros: Clean version boundary; upgrade flow can detect "Schema 3 -> 4" and run the sub-skill migration; consistent with existing pattern (Schema 1->2->3 each had structural changes); config.md gets a new `Architecture: sub-skill` field
- Cons: Schema versions previously tracked tracker format changes, not template generation changes; may set a precedent for bumping schema on every internal refactor; requires writing a full migration path

**Option B**: No schema bump -- sub-skill architecture is an internal refactor, not a format change
- Pros: Simpler; no migration path needed for schema; tracker format is unchanged; agents don't care how templates are generated
- Cons: No clean way to detect "this install predates sub-skill architecture"; upgrade flow must use heuristics (check for references/sub-skills/ directory); version detection is ad-hoc

**Option C**: Add a separate `Architecture Version` field to config.md without bumping the schema version
- Pros: Separates tracker schema version from template architecture version; each can evolve independently; upgrade flow checks `Architecture Version` for sub-skill migration; no confusion about what "schema" means
- Cons: More fields in config.md; two version numbers to track; slightly more complex upgrade logic; new concept to document

**Recommended**: C -- A separate `Architecture Version` field cleanly separates concerns. Schema versions should track data format changes (tracker structure). Architecture versions track template generation changes. This avoids conflating two different kinds of versioning.

---

### Q6: How does `--print` mode interact with the Agent tool subagent pattern?
**Category**: Architecture / compatibility
**Why it matters**: Phase B proposes using `--print` for deterministic phase execution, but the current system uses the Agent tool for subagents. Mixing models adds complexity; a wholesale switch may break things.

**Option A**: Replace Agent tool with `--print` for Research and Test Plan phases
- Pros: Fresh context per phase (no context pressure bleed); deterministic output; parallelizable; no conversational drift; explicit file-based state passing
- Cons: Need to verify `--print` has full tool access (Read, Write, Grep, Bash); orchestrator must handle output capture and error detection; loses in-process communication (Agent tool can return results directly); more moving parts (CLI invocations vs function calls)

**Option B**: Keep Agent tool, do not adopt `--print` for Phase B
- Pros: Proven pattern that works today; simpler orchestration (no CLI spawning); in-process result passing; no tool-access uncertainty
- Cons: Context pressure from subagents sharing parent context; conversational drift risk; harder to parallelize; subagent failures can corrupt parent context; no fresh context per phase

**Option C**: Coexist -- use `--print` for new phases (Discussion Prep), keep Agent tool for existing phases (Research, Test Plan)
- Pros: Incremental adoption; lower risk than wholesale switch; can evaluate `--print` on a low-stakes phase first; existing behavior preserved for proven phases
- Cons: Two execution models to maintain and document; inconsistent behavior between phases; cognitive overhead for maintainers; "temporary" coexistence often becomes permanent

**Recommended**: A -- Replace with `--print` for Research and Test Plan. The research correctly identifies that fresh context per phase is a significant advantage. However, gate this on verifying `--print` tool access first. If `--print` lacks tool access, fall back to Option B.

---

### Q8: How to test the atomicity of the migration?
**Category**: Testing
**Why it matters**: The biggest risk is a partial migration leaving agents broken. Without tests, the highest-risk scenario ships blind.

**Option A**: Manual test matrix -- document test scenarios, run them by hand before shipping
- Pros: No test infrastructure needed; covers the exact scenarios that matter (fresh install, upgrade, mid-cycle); human judgment catches subtle issues; fast to set up
- Cons: Not repeatable; easy to skip or shortcut; does not catch regressions on future changes; labor-intensive; human error in test execution

**Option B**: Scripted test harness -- shell scripts that simulate fresh install, upgrade, and mid-cycle scenarios
- Pros: Repeatable; catches regressions; can run in CI; documents expected behavior; fast to re-run after changes
- Cons: Significant upfront effort to build; must simulate agent behavior (read template, check format); may not catch all edge cases; test scripts themselves can have bugs; maintaining test infra is ongoing cost

**Option C**: Diff-verified composition tests -- automated checks that composed templates match expected output byte-for-byte
- Pros: Directly validates the core risk (template divergence); simple to implement (diff two files); catches any composition bug; can be a pre-commit check; no need to simulate full agent behavior
- Cons: Only tests template output, not the full upgrade flow; does not test mid-cycle safety; does not test fresh install path; "expected output" files must be maintained

**Recommended**: C with elements of A -- Diff-verified composition tests cover the primary risk (template correctness) with minimal effort. Supplement with a manual test checklist for fresh install, upgrade, and mid-cycle scenarios. Full scripted harness (Option B) is overkill for the current scale.

---

### Q4: What is the minimum viable Phase C (interaction layer)?
**Category**: Scope
**Why it matters**: Phase C's scope determines whether Phases A+B+C can realistically ship atomically. If Phase C is too ambitious, it blocks the entire atomic ship.

**Option A**: File-based discussion -- write DISCUSSION-PREP.md, human edits CONTEXT.md with decisions, PM reads it on next cycle
- Pros: Zero new infrastructure; works today with existing file conventions; atomic ship is trivially achievable; human uses their normal editor; all decisions are in git; perfectly compatible with the existing planning artifact pattern
- Cons: Poor UX (human must know which file to edit and what format to use); no notification when discussion is ready; no structured decision capture; easy to forget or miss

**Option B**: GitHub Issues as discussion surface -- PM creates an Issue with structured questions, human comments with decisions, PM reads comments on next cycle
- Pros: Familiar interface; notifications built in; threaded discussion; already partially implemented (GitHub Issues ingestion exists); mobile-friendly; visible to collaborators
- Cons: Requires GitHub; adds API dependency; comment parsing is fragile; decision extraction from freeform comments is error-prone; more code to write and maintain

**Option C**: Full web UI (FEAT-SKILL-020 scope)
- Pros: Best UX; structured decision capture; real-time interaction; purpose-built for the workflow
- Cons: Massive scope increase; cannot ship atomically with A+B; requires frontend development, hosting, authentication; months of additional work; blocks the entire feature

**Recommended**: A -- File-based discussion is the only option that keeps Phase C minimal enough to ship atomically with A and B. It uses existing conventions and requires no new infrastructure. GitHub Issues (Option B) is a good follow-up feature but should not gate this ship.
