## Improvement Scanning (Quiet Cycle Productivity)

During quiet cycles, use your domain expertise to scan the **target project** for improvements. This turns idle time into proactive project improvement. Findings are reported to PM, who files them through the normal tracker pipeline.

### Activation

Check `Improvement Scanning` in `config.md`. If set to `no`, skip scanning entirely.

**Bug gate**: Before triggering a scan, check for open bugs assigned to your role:
```bash
gh issue list --label "type:bug,role:[ROLE]" --state open --json number --limit 1
```
If any bugs exist, skip the scan — fix bugs instead. Bugs always take priority over improvement scanning.

Maintain a **quiet cycle counter** in your working state. Increment it each quiet cycle (when no bugs were fixed, no features progressed, no verification done). **After 3 consecutive quiet cycles**, trigger an improvement scan on the next quiet cycle (subject to the bug gate above). Reset the counter when:
- Real work occurs (bug fix, feature progress, verification)
- A scan completes (reset to 0, must accumulate 3 more quiet cycles)

### Scanning Step

When triggered, add a new step to your cycle:

Print: `[🦑 HH:MM:SS] Scanning for improvements...`

Write status bar state: `scanning|🔍 Scanning [target description]...`

1. **Detect project type**: Read `config.md` project info. Scan file extensions, `package.json`, `Cargo.toml`, `go.mod`, etc. to understand the tech stack. No new config field needed — auto-detect at scan time.

2. **Read your SOUL.md self-improvement lens**: Your soul defines what to look for. Consult it before scanning.

3. **Select files to scan**: Pick 3-5 source files from the target project, prioritized by:
   - Recently changed (most likely to have issues)
   - Never scanned before (coverage gap)
   - Oldest since last scan (staleness)

   **Exclude from scanning**: `.squidsquad/`, `node_modules/`, `vendor/`, `.git/`, build output directories (`dist/`, `build/`, `out/`), generated files, and binary files. Only scan source files belonging to the target project.

   Check `.squidsquad/[your-role]/scan-history.md` to avoid re-scanning recently reviewed files.

4. **Scan with your domain lens**:

   **Dev agent** — code quality:
   - Dead code, unused imports, unreachable branches
   - Missing error handling, unchecked edge cases
   - Code duplication, candidates for extraction
   - Outdated patterns, deprecated API usage
   - Performance bottlenecks, unnecessary allocations
   - Security concerns (hardcoded secrets, injection risks)

   **QA agent** — test coverage:
   - Source files without corresponding test files
   - Public functions/APIs without test cases
   - Missing edge case tests (null, empty, boundary values)
   - Flaky test indicators (timing dependencies, order-dependent)
   - Missing integration or E2E test scenarios

   **Designer agent** — design consistency:
   - Hardcoded colors/spacing vs design tokens
   - Missing component states (hover, disabled, error, loading, empty)
   - Accessibility gaps (contrast, labels, keyboard navigation)
   - Inconsistent patterns across similar components
   - UX friction (confusing flows, missing feedback)

   **DM agent** — documentation:
   - Outdated README sections that don't match current behavior
   - Missing API documentation for public endpoints
   - Changelog entries that could be clearer
   - Missing getting-started guides or setup instructions
   - Public-facing features without user documentation

   **PM agent** — process:
   - Stale Pending features that need attention
   - Backlog items that could be consolidated
   - Priority imbalances (too many High, neglected Low items)
   - Workflow bottlenecks visible from tracker patterns

5. **Report findings to PM**: For each finding (max **2 items per scan**), classify it and file a GitHub Issue via `gh issue create`:

   **Classification:**
   - **Bug** (`type:bug`): something broken, wrong, inconsistent, stale, or not working as specified
   - **Feature** (`type:feature`): something new that doesn't exist yet, enhancement, optimization

   File each finding as a GitHub Issue with labels: the appropriate `type:bug` or `type:feature`, `role:[target-role]`, `priority:low`, and `improvement-scan`. Include in the Issue body:

   ```
   **Found by**: [role]-lead (improvement-scan)
   **File**: [path]
   **Finding**: [specific finding]
   **Recommendation**: [what to do]
   ```

   Tag all findings with the `improvement-scan` label so PM and human can filter them.

6. **Update scan history**: Record the scanned files and any filed items in `.squidsquad/[your-role]/scan-history.md`:

   ```markdown
   ## Scan — YYYY-MM-DD HH:MM

   - **Files scanned**: [list of 3-5 files]
   - **Findings**: [list of findings reported, or "none"]
   - **Items rejected by human**: [list of previously rejected items — never refile these]
   ```

### Rules

- **PM is the single coordination point** — agents don't file directly to trackers. Report to PM via Discussion.
- **Default Low priority** — all scan items are Low priority. Human bumps if valuable.
- **Max 2 items per scan** — prevents noise. Quality over quantity.
- **Never refile rejected items** — track rejected/dismissed items in scan history. If human says "not worth it," don't suggest it again.
- **Scanning must not extend cycle time excessively** — if a scan takes too long, reduce file count for next cycle.
- **PM does NOT auto-approve** scan items — human decides whether to act on them.
