# FEAT-PM-475 Research — Token Efficiency Audit

## Summary

SquidSquad's four active agent roles consume a combined 27,922 words (~36,299 estimated tokens) in their composed CLAUDE.md files. The PM role is by far the heaviest at 11,056 words (~14,373 tokens), driven by three massive sub-skills: task-intake (2,088 words), vault-protocol (1,712 words), and tracker-protocol (1,033 words). The tracker-protocol sub-skill alone is duplicated verbatim across all 5 role templates (pm, qa, skill/dev, dm, designer), contributing ~5,165 words of redundant content across the system. The boot-remote-agents sub-skill is also included in every role despite having a PM-only gate that makes it a no-op for non-PM roles.

The largest single efficiency win would be compressing or extracting the tracker-protocol and vault-protocol sub-skills, since these are the most duplicated and verbose sections. The Label Taxonomy section within tracker-protocol (~40 lines, ~300 words) is pure reference data that agents rarely need mid-cycle — it could be moved to an external reference file. Similarly, the vault-protocol's detailed vault-check, vault-search, and entity model sections are reference material rather than operational instructions.

Reduction is feasible but requires careful validation. The prohibitions, zero-gap gate, and approval gates are safety-critical and must not be trimmed. Template changes propagate automatically via `compose.py deploy-all`, so existing installs would pick up changes on the next recompose. The main risk is that overly terse instructions cause agents to deviate from expected behavior, which can only be caught through comprehension testing.

## Token Baseline

| Role  | Lines | Words  | Est. Tokens (w*1.3) | Top 3 Sections by Size                                    |
|-------|-------|--------|----------------------|-----------------------------------------------------------|
| pm    | 1,561 | 11,056 | 14,373               | task-intake (2,088w), vault-protocol (1,712w), tracker-protocol (1,033w) |
| qa    | 792   | 4,854  | 6,310                | verification (1,296w), tracker-protocol (1,033w), vault-protocol-slim (263w) |
| skill | 1,152 | 7,633  | 9,923                | vault-protocol (1,712w), tracker-protocol (1,033w), improvement-scan (684w) |
| dm    | 731   | 4,379  | 5,693                | tracker-protocol (1,033w), delivery-packaging (340w), vault-protocol-slim (263w) |
| **Total** | **4,236** | **27,922** | **36,299** | |

## Sub-Skill Analysis

### Common Sub-Skills (shared across roles)

| Sub-Skill | Lines | Words | Est. Tokens | Roles Using It |
|-----------|-------|-------|-------------|----------------|
| tracker-protocol | 186 | 1,033 | 1,343 | pm, qa, skill/dev, dm, designer (5) |
| vault-protocol | 200 | 1,712 | 2,226 | pm, skill/dev (2) |
| vault-protocol-slim | 44 | 263 | 342 | qa, dm, designer (3) |
| improvement-scan | 86 | 684 | 889 | pm, skill/dev (2) |
| improvement-scan-slim | 12 | 76 | 99 | qa, dm, designer (3) |
| vault-remember | 80 | 445 | 579 | pm, skill/dev (2) |
| vault-optimize | 31 | 239 | 311 | pm, skill/dev (2) |
| boot-remote-agents | 26 | 160 | 208 | pm, qa, skill/dev, dm, designer (5) |
| self-restart | 32 | 242 | 315 | pm, qa, skill/dev, dm, designer (5) |
| context-pressure | 25 | 193 | 251 | pm, qa, skill/dev, dm, designer (5) |
| pull-latest | 10 | ~60 | 78 | pm, qa, skill/dev, dm, designer (5) |
| git-commit (common) | 93 | 393 | 511 | skill/dev (1, others override) |

### Role-Specific Sub-Skills (largest)

| Sub-Skill | Lines | Words | Est. Tokens | Role |
|-----------|-------|-------|-------------|------|
| pm-specific/task-intake | 309 | 2,088 | 2,714 | pm |
| qa-specific/verification | 199 | 1,296 | 1,685 | qa |
| pm-specific/testing-and-verification | 84 | 684 | 889 | pm |
| dev-specific/implement-tasks | 70 | 582 | 757 | skill/dev |
| pm-specific/delivery-fallback | 51 | 486 | 632 | pm |
| pm-specific/checkin | 28 | 411 | 534 | pm |
| dm-specific/delivery-packaging | 46 | 340 | 442 | dm |
| dm-specific/version-bumps | 40 | 267 | 347 | dm |
| pm-specific/task-approval | 23 | 243 | 316 | pm |

## Top 10 Token-Heavy Sections

1. **task-intake** (pm) — 2,714 est. tokens — HIGH reduction potential. Contains full 5-phase lifecycle, artifact resume logic, 3 subagent prompt templates, and "Open in Editor" flow. Subagent prompts and RESEARCH/CONTEXT/TEST-PLAN markdown templates are verbose.
2. **vault-protocol** (pm, skill) — 2,226 est. tokens per inclusion (4,452 total) — MEDIUM reduction potential. Entity model table, vault-search modes, vault-check Level 1+2 sections are reference-heavy. Could extract to a vault-reference.md file agents `cat` on demand.
3. **verification** (qa) — 1,685 est. tokens — MEDIUM reduction potential. Branch checkout instructions and PR Flow conditional logic are verbose. Could condense the PR Flow sections.
4. **tracker-protocol** — 1,343 est. tokens per inclusion (6,715 total across 5 roles) — HIGH reduction potential. Label Taxonomy (~300 words) is pure reference data. Legal flows table is duplicated. Design Field instructions repeat `gh issue edit` examples.
5. **testing-and-verification** (pm) — 889 est. tokens — MEDIUM reduction potential. Steps 3-6 with QA fallback logic. Some overlap with qa-specific/verification.
6. **improvement-scan** (pm, skill) — 889 est. tokens per inclusion (1,778 total) — MEDIUM reduction potential. Scan rules and file selection could be more concise.
7. **delivery-fallback** (pm) — 632 est. tokens — LOW reduction potential. Only included in PM. Version bump sequence is already minimal.
8. **implement-tasks** (skill) — 757 est. tokens — LOW reduction potential. Task pickup, QA-rejected rework, and branch workflow are essential operational instructions.
9. **vault-remember** (pm, skill) — 579 est. tokens per inclusion (1,158 total) — MEDIUM reduction potential. Gate sequence is verbose. Could be summarized with a reference to vault-protocol for details.
10. **checkin** (pm) — 534 est. tokens — LOW reduction potential. Issue Discussion Flow and Task Request flow are behavior-critical.

## Redundancy Analysis

### Verbatim Duplication

- **tracker-protocol**: 1,033 words duplicated verbatim in all 5 composed templates = **4,132 words of redundancy** (only 1 copy is needed if extracted to a shared reference). This is the single largest redundancy in the system.
- **boot-remote-agents**: 160 words included in all 5 roles, but has a `PM-only gate` making it a no-op for 4 of 5 roles = **640 words wasted**. Should only be composed into PM's template.
- **self-restart**: 242 words in all 5 roles. Identical content. Justified — each role needs restart capability.
- **context-pressure**: 193 words in all 5 roles. Identical content. Justified — each role needs pressure monitoring.
- **pull-latest**: ~60 words in all 5 roles. Small and justified.

### Near-Duplication

- **vault-protocol vs vault-protocol-slim**: The slim variant (263 words) is a condensed version of vault-protocol (1,712 words). Good design — QA/DM/designer get the slim read-only version. No further action needed.
- **improvement-scan vs improvement-scan-slim**: Similar pattern. The full version (684 words) is in pm+dev, the slim (76 words) in qa+dm+designer. Good design.
- **Role-specific overrides**: 7 sub-skills (discussion-protocol, file-conventions, git-commit, issue-filing, iteration-log, prohibitions, status-line) have both common and role-specific versions. Each role uses its own override, not the common one. The common versions serve as defaults for new roles. No redundancy issue.

### Structural Redundancy

- **Label Taxonomy** in tracker-protocol lists all labels (~40 lines) — this is reference data agents rarely consult. Could be extracted to a file agents `cat` on demand.
- **Legal flows and owning roles** table — reference data, not operational instructions. Could be in tracker.py's help output instead.
- **Vault entity model table** — 9 rows of entity/location/purpose. Reference data.

## Script Output Analysis

### tracker.py (827 lines)
- Returns JSON for create operations (number + url). Compact output.
- `list-tasks` and `list-issues` return `gh issue list` output filtered by labels. Output is proportional to open issues — typically compact.
- `transition` returns success/failure messages. Compact.
- **Finding**: No excess output. Script is well-designed as a thin wrapper.

### health_check.py (426 lines)
- Two modes: pretty table (human) and `--json` (structured). Both are proportional to agent count (typically 2-4 agents).
- **Finding**: Output is minimal. No concern.

### config.py (467 lines)
- `get <field>` returns a single value. `dump` returns full JSON. `agents` returns agent list JSON.
- **Finding**: Agents use targeted `get` calls. No excess output.

### compose.py (529 lines)
- Only runs at deploy time, not during agent cycles. Output is deployment confirmation.
- **Finding**: Not relevant to runtime token efficiency.

### cycle.py (250 lines)
- Utility for timestamps, step markers, status bar writes, iteration log creation/cleanup.
- **Finding**: Minimal output. Well-scoped.

### git_ops.py (427 lines)
- Handles pull, commit-push, branch operations. Output is git command results.
- **Finding**: Output proportional to git changes. No concern.

### boot_remote.py (608 lines)
- Returns JSON with per-agent action/success. Only runs in PM cycle.
- **Finding**: Output is compact. No concern.

### Other scripts
- vault_remember.py (387 lines), vault_optimize.py (644 lines), vault_check.py (316 lines): Only produce output when vault operations occur. Minimal otherwise.
- scan_index.py (773 lines): Returns file suggestions for improvement scanning. Compact output.
- triage.py (176 lines): Returns JSON array of QA-rejected items. Compact.

**Overall script finding**: Scripts are well-designed with minimal output. The token concern is in the CLAUDE.md template instructions that describe how to use these scripts, not in the script output itself.

## Planning Artifact Templates

The CLAUDE.md instructions contain embedded markdown templates for:

1. **RESEARCH.md template** (~25 lines in task-intake): Summary, Impact Analysis, Side Effects, Edge Cases, Integration Risks, Upgrade & Migration, Capability Gaps, Open Questions, Recommendation. This is appropriate — it guides subagent output structure.
2. **CONTEXT.md template** (~15 lines): Scope, Locked Decisions, Dev Discretion, Side Effect Mitigations, Upgrade Path, Out of Scope. Concise and appropriate.
3. **TEST-PLAN.md template** (~20 lines): Test Cases with TC-N format, Smoke Tests, Regression Risks. Appropriate.
4. **Iteration log template** (~10 lines per role): Varies by role. Concise.
5. **Working state template** (~12 lines): Standard across roles. Concise.

**Finding**: The templates themselves are not excessive. The verbosity in task-intake comes from the process instructions around the templates (artifact resume logic, Phase 2A/2B subagent prompts, AskUserQuestion examples, open-in-editor flow), not the templates themselves.

## Side Effects

- **Risk 1**: Trimming tracker-protocol Label Taxonomy could cause agents to construct incorrect labels — Severity: **H** — Mitigation: Keep the label names in tracker.py's help output or error messages so agents can self-correct. The script already enforces correct labels, so agents don't need to memorize them.
- **Risk 2**: Removing boot-remote-agents from non-PM roles could break if a future role needs boot capability — Severity: **L** — Mitigation: The PM-only gate already prevents execution. Removing saves 160 words per non-PM role. Easy to re-add via includes.yml.
- **Risk 3**: Condensing vault-protocol could cause agents to skip vault-check after writes — Severity: **M** — Mitigation: Keep the "vault-check Level 1 runs after every write" rule prominent. Move reference details (entity model, search modes) to a separate file.
- **Risk 4**: Terse instructions may cause agent behavioral drift (doing something wrong because the instruction was too brief) — Severity: **M** — Mitigation: Comprehension testing (spawn fresh agent, quiz on instructions) after any template change.
- **Risk 5**: Trimming prohibitions section could weaken safety guardrails — Severity: **H** — Mitigation: Never trim prohibitions. These are explicitly safety-critical.

## Edge Cases

- **Overly terse instructions**: If an instruction is reduced below the threshold where an LLM can reliably follow it, the agent may hallucinate or improvise. Example: replacing "Use the tracker script for all queries — it encodes correct label formats" with just "Use tracker.py" may cause agents to bypass the script and construct `gh` commands directly. Testing via comprehension quiz is the mitigation.
- **New role onboarding**: If tracker-protocol is extracted to a separate file, new roles would need a `cat` step in their startup. If compose.py doesn't inject the reference, the agent would start without label knowledge.
- **Vault protocol complexity**: The vault-protocol is already split into full (200 lines) and slim (44 lines). Further trimming the full version risks agents not understanding vault-check requirements.
- **Context window pressure**: Ironically, if we trim too much, agents may need to `cat` reference files each cycle, which adds to context usage per-cycle rather than the one-time CLAUDE.md load.

## Upgrade & Migration

- **New config values**: None expected. Token efficiency is a template-only change.
- **Template changes**: All changes would be in `references/sub-skills/` markdown files. compose.py regenerates the CLAUDE.md files from these sources.
- **Upgrade steps**: `compose.py deploy-all` regenerates all role CLAUDE.md files. Existing installs pick up changes on next recompose. No manual migration needed.
- **Graceful degradation**: If an existing install doesn't recompose, they keep the verbose templates. No breakage — just no efficiency gain.

## Capability Gaps

- **capability_check.py skill**: Exit 2 — role manifest not found at `references/roles/skill/manifest.yaml`. The skill role uses the `dev` role template (`references/roles/dev/`). Running `capability_check.py dev` returns exit 0 (no capabilities required). No capability gaps for active roles.
- **No includes.yml for skill**: The `skill` role maps to the `dev` role in `references/roles/dev/includes.yml`. This is by design — skill is an instance of the dev role template.

## Open Questions

- **Q1**: Should tracker-protocol's Label Taxonomy be extracted to a reference file that agents `cat` on demand? — **Why**: Saves ~300 words per role (1,500 total across 5 roles) but adds a file read per cycle if agents need label info. Agents typically don't need to look up labels — tracker.py handles label construction.
- **Q2**: Should boot-remote-agents be removed from non-PM includes.yml? — **Why**: Saves 640 words total. The PM-only gate already prevents execution, but removing it is cleaner. Risk: future roles that need boot capability would need to re-add it.
- **Q3**: Should vault-protocol be split into vault-protocol-core (operational rules only) and vault-protocol-reference (entity model, search modes, check levels)? — **Why**: Could save ~800 words per vault-protocol inclusion. Risk: agents may not search the vault effectively without inline search examples.
- **Q4**: What is the acceptable minimum instruction density for reliable agent behavior? — **Why**: There's no established threshold. Too terse = behavioral drift. Need comprehension testing methodology to validate reductions.
- **Q5**: Should subagent prompt templates in task-intake be shortened? — **Why**: Each prompt template is ~5-10 lines. They're instructions for spawned subagents, not the host agent. Trimming them risks subagent output quality.

## Recommendation

**Feasible with caveats.** There are clear, low-risk wins:

1. **Remove boot-remote-agents from non-PM roles** — saves 640 words, zero risk (PM-only gate already prevents execution).
2. **Extract Label Taxonomy from tracker-protocol to a reference file** — saves ~1,500 words across 5 roles. Low risk since tracker.py enforces labels programmatically.
3. **Extract vault entity model + search modes to a reference file** — saves ~400 words per vault-protocol inclusion (~800 total). Medium risk.
4. **Condense vault-check Level 2 section** — only PM and dev have it, and Level 2 is rarely invoked. Could be a one-liner pointing to a reference.

Total estimated savings from low-risk changes: **~3,000 words (~3,900 tokens)**, roughly **10-11% of total**.

Higher-risk changes (condensing tracker-protocol further, trimming task-intake process, condensing vault-remember gates) could save an additional ~2,000-3,000 words but require comprehension testing to validate. A phased approach is recommended: implement low-risk changes first, measure agent behavior, then proceed to medium-risk changes.
