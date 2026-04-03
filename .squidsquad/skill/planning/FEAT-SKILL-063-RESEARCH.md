# FEAT-SKILL-063 Research — Self-improvement loop: agents suggest improvements during quiet cycles

## Summary

SquidSquad agents currently go fully idle during quiet cycles -- no bugs to triage, no features to implement, no verification work. The agent prints nothing, skips logging and committing, and waits for the next `/loop` invocation. This represents wasted capacity: each quiet cycle consumes a loop invocation (and the human's attention via the status bar) while producing zero value.

FEAT-SKILL-063 proposes that during quiet cycles, agents use their domain expertise to scan the **target project** (not SquidSquad itself) for improvements. Dev finds code quality issues, QA finds missing test coverage, Designer finds design inconsistencies, DM finds documentation gaps, PM finds process inefficiencies. Findings are filed through the normal tracker pipeline as features or bugs, reviewed by the human like any other work item.

This is a capability SquidSquad provides to any repo it manages. The self-improvement loop turns idle agent time into proactive project improvement.

---

## 1. Quiet Cycle Detection

### Current Behavior

Each role template defines a quiet cycle differently, but the pattern is consistent -- "nothing actionable happened this cycle":

- **Dev agent** (`dev-agent.md`, Step 4): "If no bugs were fixed and no features were progressed this cycle, this is a **quiet cycle**."
- **QA agent** (`qa-agent.md`, Step 7): "If no QA issues were found, no bugs were verified, no features were tested, this is a **quiet cycle**."
- **Designer** (`designer.md`, Step 3): "If no design work was done this cycle, this is a **quiet cycle**."
- **DM** (`dm-agent.md`, Step 4): "If no features were delivered this cycle, this is a **quiet cycle**."
- **PM lean** (`pm-lean.md`, Step 4): "If no human input was processed and no features were filed or progressed this cycle, this is a **quiet cycle**."
- **PM full** (`pm-agent.md`, Step 8): "If no QA issues were found, no bugs were verified, no features were shipped, and no human input was processed this cycle, this is a **quiet cycle**."

Quiet cycle detection happens at the end of the loop (Step 4+ for most roles), after triage and implementation steps have already been checked. This is the correct location -- by the time the agent reaches the logging step with nothing done, it has definitively confirmed there is no actionable work.

### Existing Precedent: Designer Quiet Cycle Counter

The designer template already tracks consecutive quiet cycles (`design-session.md`, Step 2): "If no features need design, this is a **quiet cycle** -- increment the quiet cycle counter. After **5 consecutive quiet cycles**, log a suggestion..."

This is the closest existing pattern to what FEAT-SKILL-063 proposes. The designer uses it to suggest stopping the agent; FEAT-SKILL-063 would use it to trigger improvement scans instead.

### Recommended Trigger Strategy

**Configurable threshold with sensible default.** Not every quiet cycle should trigger a scan -- that would be too aggressive and costly. Recommended approach:

- **Config field**: `Improvement Scan > Quiet Cycles Before Scan` (default: 3)
- **Meaning**: After N consecutive quiet cycles, the next quiet cycle triggers an improvement scan
- **Reset**: The counter resets when any real work happens (bug fixed, feature progressed, etc.)
- **Per-scan cooldown**: After a scan completes (whether or not it filed anything), reset the counter to 0. The agent must accumulate N more quiet cycles before scanning again.
- **Config field**: `Improvement Scan > Enabled` (default: yes) -- master toggle

**Why not every quiet cycle?** Token cost. An improvement scan reads target project files, which can be significant. If the agent loops every 30 minutes and has nothing to do, scanning every cycle means 48 scans/day. At 3-cycle threshold, that is 16 scans/day maximum (and realistically fewer, since scans themselves may file work that breaks the quiet streak).

**Why not a longer threshold (e.g., 10)?** At 30-minute intervals, 10 quiet cycles = 5 hours before the first scan. That is too conservative -- the human would see zero proactive value from the feature during a normal work session.

### Avoiding False Quiet Cycles

Risk: An agent has work to do but fails to detect it (e.g., malformed tracker entry, INDEX.md out of sync). It enters a quiet cycle and starts scanning when it should be working.

Mitigation: The improvement scan step occurs AFTER the normal triage/implementation steps. If those steps failed to find work, the scan is a valid fallback. The existing quiet cycle detection is already tested and reliable. No additional safeguards needed beyond what exists today.

---

## 2. Per-Role Scan Strategies

### 2a. Dev Agent -- Code Quality Scan

**What an LLM can find:**
- Dead code (unused functions, unreachable branches, commented-out blocks)
- Missing error handling (uncaught exceptions, missing null checks, bare try/catch)
- Code complexity (deeply nested logic, functions over 50-100 lines, god classes)
- Code duplication (similar logic in multiple places)
- Outdated patterns (deprecated API usage, old syntax when modern alternatives exist)
- Security issues (hardcoded secrets, SQL injection patterns, unsafe deserialization)
- Performance issues (N+1 queries, unnecessary re-renders, synchronous I/O in async context)
- Missing type annotations (in typed languages)
- Inconsistent naming conventions

**What an LLM cannot reliably find:**
- Actual runtime performance bottlenecks (needs profiling data)
- Dependency vulnerability CVEs (needs a security database -- but can flag outdated deps)
- Race conditions (needs dynamic analysis)
- Memory leaks (needs runtime profiling)

**Scan depth:** Targeted, not whole-codebase. An LLM context window cannot hold an entire codebase. Strategy:
1. Read the project's file tree (directory listing)
2. Prioritize: recently-changed files (via `git log --name-only`), largest files (likely most complex), files with no recent tests
3. Read 3-5 files per scan cycle
4. Track which files have been scanned in a scan history file to avoid repetition

**Filing format:** File as bugs (for clear defects like missing error handling, dead code) or features (for improvements like refactoring, better patterns). Use `Reported By: [role]-lead (improvement-scan)` to distinguish from manually-filed items.

### 2b. QA Agent -- Test Coverage Scan

**What an LLM can find:**
- Source files with no corresponding test file
- Public functions/methods with no test coverage (by reading test files and comparing against source)
- Edge cases not tested (null inputs, empty arrays, boundary values, error paths)
- Missing integration tests (components that interact but are only unit-tested in isolation)
- Flaky test indicators (tests that depend on timing, external state, or specific ordering)
- Regression risks (complex functions with no regression test, code with many bug-fix commits)
- Acceptance criteria in feature specs that have no corresponding test assertion

**Scan strategy:**
1. List all source files, list all test files
2. Find source files with no test file counterpart
3. For source files WITH tests, compare exported functions against test coverage
4. Read 2-3 source+test file pairs per scan
5. File findings as features (`FEAT-QA-XXX: Add test coverage for [module]`) or bugs if an existing test is clearly wrong

### 2c. Designer Agent -- Design Consistency Scan

**What an LLM can find (by reading component code):**
- Inconsistent spacing/sizing values (hardcoded px values that should use design tokens)
- Missing component states (hover, focus, disabled, loading, error, empty)
- Accessibility gaps (missing aria labels, insufficient color contrast ratios in CSS, missing keyboard navigation)
- Inconsistent patterns (same UI pattern implemented differently in different components)
- Design system violations (components not using shared tokens/variables)
- Missing responsive breakpoints

**Scan strategy:**
1. Read the design system/tokens file (if exists)
2. Read component files, comparing against design tokens
3. Check for accessibility attributes
4. 2-3 components per scan cycle

**Filing format:** File as features to the dev agent's tracker (`Reported By: designer (improvement-scan)`) since the designer does not implement code. Include specific component paths and what needs to change.

### 2d. DM Agent -- Documentation Scan

**What an LLM can find:**
- README sections that reference outdated features or removed APIs
- Missing API documentation (exported functions with no JSDoc/docstring/README mention)
- Stale references (links to files that no longer exist, version numbers that are wrong)
- Missing CHANGELOG entries (features shipped without changelog updates)
- Inconsistent formatting across documentation files
- Missing getting-started or setup instructions
- Code examples in docs that do not match current API signatures

**Scan strategy:**
1. Read README, CHANGELOG, and any docs/ directory
2. Compare documented APIs against actual exports in source
3. Check internal links for validity
4. 2-3 doc files per scan cycle

### 2e. PM Agent -- Process Scan

**What an LLM can find:**
- Stale tracker items (features/bugs that have been `Open` or `Approved` for many cycles without progress)
- Priority imbalances (High-priority items blocked while Low-priority items are being worked)
- Backlog grooming needs (features that are vaguely specified, missing acceptance criteria)
- Workflow bottlenecks (items stuck in `Pending Test` for many cycles, items bouncing between agents)
- Missing cross-references (related features/bugs that should be linked but are not)

**Scan strategy:**
1. Read all agent INDEX.md files
2. Check timestamps in Discussion sections for staleness
3. Compare priorities against actual work ordering
4. This is the lightest scan -- tracker files are small

---

## 3. Filing Mechanism

### Item Type: Use Existing Bug and Feature Types

No new item type needed. Improvements naturally fall into existing categories:
- **Bug**: Something is objectively wrong (dead code, missing error handling, broken docs link, failing accessibility)
- **Feature**: Something could be better (refactoring, new tests, design improvements, documentation additions)

Adding a third type ("improvement") would require changes to every agent template, INDEX.md schema, config counters, the QA verification flow, and the DM delivery flow. The benefit does not justify the cost.

### Distinguishing Self-Initiated Items

Use `Reported By: [role]-lead (improvement-scan)` in the tracker entry. This is sufficient for humans to filter improvement-scan items visually. The `(improvement-scan)` tag makes them immediately distinguishable from `Reported By: [role]-lead` (self-discovered during normal work) and `Reported By: human`.

Additionally, include a `**Source**: improvement-scan` field in the entry metadata. This allows programmatic filtering if needed later.

### Filing Destination

Each role files to the appropriate tracker based on ownership:
- Dev files code improvements to its own tracker (self-file)
- QA files test coverage gaps to its own tracker (if QA has a features tracker) or to the dev agent's tracker
- Designer files design issues to the dev agent's tracker (designer cannot implement)
- DM files documentation issues -- to its own working scope if doc-only, otherwise to dev agent
- PM files process improvements as features to the skill tracker (PM manages the backlog)

### Human Review Queue

No separate queue needed. Improvements filed as `Pending` status go through the normal approval flow:
1. Agent files improvement as a Pending feature or Open bug
2. PM surfaces it to the human during the next intake cycle
3. Human approves or rejects through normal Discussion mechanism
4. If approved, it enters the normal work pipeline

This is deliberate -- the whole point is that improvements go through the same pipeline as human-filed items. No special treatment, no separate review UI.

### Filing as Pending (Not Approved)

Critical: Agents MUST file improvement-scan items as `Pending` (features) or `Open` (bugs), NOT as `Approved`. The human must approve before any agent acts on the suggestion. This is consistent with the existing rule: "Never implement a feature with status `Pending` -- it has not been approved by a human yet."

For bugs, the existing flow is that `Open` bugs get triaged immediately by the owning agent. This is fine for clear defects (dead code, missing error handling) but problematic for subjective findings (code style, refactoring preferences). Recommendation: improvement-scan bugs should use a new status `Open (scan)` or simply add a tag in the Description: `[improvement-scan — requires human approval before fixing]`. The simpler approach is to file ambiguous findings as features (Pending) rather than bugs (Open), reserving bug filing for unambiguous defects only.

---

## 4. Rate Limiting and Noise Control

### Rate Limits

**Per scan cycle:**
- Maximum 2 items filed per improvement scan (across all findings)
- If the agent finds more than 2 issues, pick the 2 highest-impact ones and note the others in a scan log for next time

**Per day:**
- No explicit daily cap needed. The quiet-cycle threshold (default 3) already limits scan frequency. At 30-minute intervals with continuous quiet, that is ~16 scans/day * 2 items/scan = 32 items/day maximum. In practice, filed items create work that breaks the quiet streak, so actual throughput will be much lower.

**Config fields:**
- `Improvement Scan > Max Items Per Scan` (default: 2)
- `Improvement Scan > Quiet Cycles Before Scan` (default: 3)

### Avoiding Repetitive Suggestions

**Scan history file:** Each role maintains `.squidsquad/[ROLE]/improvement-scan-history.md`:

```markdown
# Improvement Scan History

## Scanned Files
| File | Last Scanned | Findings |
|------|-------------|----------|
| src/api/auth.ts | 2026-04-01 | Filed FEAT-SKILL-064 (missing error handling) |
| src/utils/format.ts | 2026-04-01 | No issues found |

## Filed Items
| Item ID | File | Description | Status |
|---------|------|-------------|--------|
| FEAT-SKILL-064 | src/api/auth.ts | Missing error handling | Pending |
```

**Deduplication rules:**
1. Before filing, check scan history for the same file + similar description
2. Before filing, check existing tracker items for duplicate/overlapping scope
3. If a previously-filed item was rejected by the human, do not refile the same finding
4. Track rejected items in scan history with `rejected` status

### Calibration: Noise vs. Value

**Start conservative, let humans tune up.** Default settings (3 quiet cycles, 2 items max) produce low volume. If the human wants more aggressive scanning, they reduce the quiet cycle threshold or increase the item cap.

**Signal quality over quantity.** Agent instructions should emphasize: only file findings that provide clear, actionable value. "This function could be slightly more readable" is noise. "This API endpoint has no input validation and could accept malformed data" is signal.

**Confidence threshold in instructions:** Include guidance like: "Only file if you are confident the finding represents a real improvement. When in doubt, log it in scan history without filing."

---

## 5. Scan Scope and Depth

### Context Window Constraints

An LLM context window cannot hold an entire codebase. Even a modest project (500 files) would exceed available context. Scans must be targeted.

### Incremental Scanning Strategy

Each scan cycle covers a small slice of the codebase. Over many quiet cycles, the agent progressively covers the entire project.

**File selection priority (highest to lowest):**
1. **Recently changed files** (`git log --since="7 days ago" --name-only`) -- most likely to have fresh issues
2. **Never-scanned files** (not in scan history) -- coverage gaps
3. **Oldest-scanned files** (longest time since last scan in history) -- may have new issues since last scan
4. **Hot paths** (files with most commits historically: `git log --name-only | sort | uniq -c | sort -rn`) -- highest-impact code

**Files per scan:** 3-5 files per scan cycle, depending on file size. The agent should aim to spend no more than ~30% of its context window on improvement scanning (leave room for normal loop operations in case work appears mid-scan).

### Excluded Paths

Agents should skip:
- `.squidsquad/` directory (internal SquidSquad files, not the target project)
- `node_modules/`, `vendor/`, `.git/`, build output directories
- Generated files (`.min.js`, compiled output, lockfiles)
- Binary files

The exclusion list should be configurable in config.md: `Improvement Scan > Exclude Paths` (default: common patterns).

### Scope Configuration

Config field: `Improvement Scan > Scope` with values:
- `full` (default) -- scan entire project incrementally
- `changed` -- only scan files changed in the last N days
- `paths: src/, lib/` -- only scan specified directories

---

## 6. Sub-skill Design

### Architecture: Common Sub-skill + Per-Role Extensions

Create a new common sub-skill `common/improvement-scan.md` that provides:
- Quiet cycle counter tracking
- Scan trigger logic (threshold check)
- Scan history file management
- Rate limiting logic
- File selection algorithm
- Filing protocol (with `improvement-scan` tag)

Each role template then includes this common sub-skill and adds a role-specific scan strategy section:
- Dev: `common/improvement-scan` + code quality checklist
- QA: `common/improvement-scan` + test coverage checklist
- Designer: `common/improvement-scan` + design consistency checklist
- DM: `common/improvement-scan` + documentation checklist
- PM: `common/improvement-scan` + process checklist

### Integration into Ralph Loop

The improvement scan inserts as a new step between the current work steps and the logging step. For the dev agent template:

**Current flow:**
- Step 2: Triage Bugs
- Step 3: Implement Features
- Step 4: Log Iteration (skip on quiet cycles)
- Step 5: Commit and Push (skip on quiet cycles)

**Proposed flow:**
- Step 2: Triage Bugs
- Step 3: Implement Features
- Step 3b: Improvement Scan (only on quiet cycles, after threshold met)
- Step 4: Log Iteration (skip on quiet cycles **unless scan filed items**)
- Step 5: Commit and Push (skip on quiet cycles **unless scan filed items**)

Key behavioral change: if the improvement scan files items, the cycle is no longer "quiet" -- it should log and commit. But the agent should NOT then pick up and implement those items in the same cycle (they are `Pending`, awaiting human approval).

### Interaction with Vault-Remember (FEAT-SKILL-029)

If the vault is available, improvement scan findings could be captured as vault notes:
- `galaxy/pattern-*.md` -- patterns discovered during scans (e.g., "this project uses X pattern for error handling")
- `galaxy/learning-*.md` -- learnings about the codebase (e.g., "auth module is the most complex, needs attention")

However, this is an enhancement, not a requirement. FEAT-SKILL-063 should work independently of FEAT-SKILL-029. If the vault exists, use it; if not, the scan history file is sufficient.

**Recommendation:** Add a conditional check: "If `.squidsquad/vault/` exists, also create a vault note for significant findings using `/vault-remember`." This keeps the two features loosely coupled.

---

## 7. Side Effects and Edge Cases

### 7a. Agent Contradicts Human's Intentional Design Choice

**Risk:** Agent files "improvement" to refactor code that the human intentionally wrote a certain way (e.g., verbose code for readability, specific architecture for extensibility reasons).

**Mitigation:**
- Human rejects the suggestion through normal approval flow -- it is filed as `Pending`, not `Approved`
- Rejected items are recorded in scan history with `rejected` status
- Agent checks scan history before filing to avoid refiling rejected patterns
- If vault-remember is available, the rejection could be captured as a vault decision note ("Human prefers verbose style in auth module")

### 7b. Duplicate of Existing Tracker Item

**Risk:** Agent files an improvement that overlaps with an already-filed feature or known bug.

**Mitigation:**
- Before filing, agent reads the relevant INDEX.md and checks for similar items
- Include in scan instructions: "Search existing tracker for related items before filing. If a similar item exists, skip or add a Discussion comment to the existing item instead of filing a new one."
- This is a best-effort check -- LLMs may miss subtle duplicates. The PM will catch obvious duplicates during intake.

### 7c. False Positive (Wrong Suggestion)

**Risk:** Agent suggests "fixing" something that is not actually broken (e.g., flagging intentional dead code that is a feature flag, or flagging a "missing test" for an untestable utility).

**Mitigation:**
- Human rejects through normal flow
- Low cost: a rejected Pending item costs one human review action
- Over time, scan history accumulates rejections that help the agent learn what NOT to file (though cross-context learning requires vault-remember)

### 7d. Self-Feeding Loop (Agents Keep Filing Work for Themselves)

**Risk:** Agent files improvement, it gets approved, agent implements it, files more improvements from the implementation, repeat forever. Quiet cycles become rare because the agent generates its own work.

**Mitigation:**
- Items filed as `Pending` require human approval -- the human controls the gate
- Rate limiting (2 items/scan, 3-cycle threshold) naturally bounds throughput
- The human can set `Improvement Scan > Enabled: no` to disable entirely
- PM can deprioritize improvement-scan items below human-filed items

### 7e. Token Cost During Idle Time

**Risk:** Improvement scans consume tokens during otherwise idle time. For API-based deployments, this has a direct cost.

**Analysis:** A scan that reads 3-5 project files and files 0-2 items consumes roughly 10-30k tokens per scan. At the default rate (one scan per 3 quiet cycles at 30-minute intervals), that is ~5-10 scans per idle workday, or 50-300k tokens/day. This is modest compared to active development cycles (which consume 50-200k tokens each).

**Mitigation:** The `Enabled: no` config toggle lets cost-conscious users disable entirely. The quiet cycle threshold lets them reduce frequency.

### 7f. Concurrent Scan Conflicts

**Risk:** Multiple agents scan and file improvements simultaneously, creating duplicate entries or counter conflicts in config.md.

**Mitigation:** Existing SquidSquad concurrency model applies -- agents pull before each cycle, use atomic writes, and counters are incremented per-file. The risk of counter collision exists today for cross-filed bugs and is acceptably low. No additional mitigation needed.

---

## 8. Upgrade and Migration

### New Files

- `references/sub-skills/common/improvement-scan.md` -- shared sub-skill
- Per-role scan strategy additions in each role template (inline or as include sections)
- Config additions (new section in `config.md`)

### Config Changes

Add to `config.md`:
```markdown
## Improvement Scan

- **Enabled**: yes
- **Quiet Cycles Before Scan**: 3
- **Max Items Per Scan**: 2
- **Exclude Paths**: node_modules/, vendor/, .git/, dist/, build/, .squidsquad/
- **Scope**: full
```

### Template Changes

Each role template gets:
1. A new step (Step 3b or equivalent) for improvement scanning
2. Modified quiet cycle detection: quiet cycles now have two modes -- "true quiet" (below threshold) and "scan cycle" (threshold reached)
3. Include directive for `common/improvement-scan`

### Existing Install Migration

The upgrade script (`squidsquad-upgrade`) needs to:
1. Add the `## Improvement Scan` section to `config.md` if not present
2. Regenerate agent templates from updated sub-skills (this already happens during upgrade)
3. No data migration needed -- scan history files are created on first scan

### Rollback

Setting `Improvement Scan > Enabled: no` disables the feature completely. No scan history files are created, no items filed. The feature is fully opt-out.

---

## 9. Implementation Plan

### Recommended Phasing

**Phase 1: Infrastructure** (smallest shippable unit)
- Add config section
- Create `common/improvement-scan.md` sub-skill with: quiet cycle counter, threshold check, scan history management, rate limiting, filing protocol
- Integrate into dev agent template only (narrowest blast radius)
- Dev agent scans for 2-3 code quality categories (dead code, missing error handling)

**Phase 2: All Roles**
- Extend to QA, Designer, DM, PM templates
- Each role gets its domain-specific scan checklist
- All roles share the common sub-skill

**Phase 3: Vault Integration**
- If FEAT-SKILL-029 is shipped, add conditional vault-remember integration
- Scan findings captured as vault notes
- Rejected items captured as vault decisions

### Estimated Complexity

- **Phase 1**: Medium -- one new sub-skill file, one template modification, config addition
- **Phase 2**: Medium -- five template modifications using the same pattern
- **Phase 3**: Low -- conditional check + vault-remember call

---

## 10. Open Questions for CONTEXT Phase

1. Should improvement-scan items have a lower default priority than human-filed items? (Recommendation: yes, default to `Low` priority)
2. Should the PM aggregate scan findings into a periodic "improvement report" for the human? (Recommendation: no, use normal tracker flow)
3. Should there be a global scan budget (total items across all agents per day)? (Recommendation: no, per-agent rate limiting is sufficient)
4. Should scan findings be visible in the status bar? (e.g., "scanned 5 files, filed 1 item") (Recommendation: yes, as a status bar phase `scanning|...`)
5. For the target project context: how does the agent know what kind of project it is? (Recommendation: read `config.md` project metadata + infer from file extensions and structure)
