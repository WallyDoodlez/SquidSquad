## Improvement Scanning (Quiet Cycle Productivity)

During quiet cycles, use your domain expertise to scan the **target project** for improvements. This turns idle time into proactive project improvement. Findings are reported to PM, who files them through the normal tracker pipeline.

### Activation

Check `Improvement Scanning` in `config.md`. If set to `no`, skip scanning entirely.

Maintain a **quiet cycle counter** in your working state. Increment it each quiet cycle (when no bugs were fixed, no features progressed, no verification done). **After 3 consecutive quiet cycles**, trigger an improvement scan on the next quiet cycle. Reset the counter when:
- Real work occurs (bug fix, feature progress, verification)
- A scan completes (reset to 0, must accumulate 3 more quiet cycles)

### Scanning Step

When triggered, add a new step to your cycle:

Print: `[🦑] Scanning for improvements...`

Write status bar state: `scanning|🔍 Scanning [target description]...`

1. **Detect project type**: Read `config.md` project info. Scan file extensions, `package.json`, `Cargo.toml`, `go.mod`, etc. to understand the tech stack. No new config field needed — auto-detect at scan time.

2. **Read your SOUL.md self-improvement lens**: Your soul defines what to look for. Consult it before scanning.

3. **Select files to scan**: Pick 3-5 files, prioritized by:
   - Recently changed (most likely to have issues)
   - Never scanned before (coverage gap)
   - Oldest since last scan (staleness)
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

5. **Report findings to PM**: For each finding (max **2 items per scan**), append a Discussion entry to the relevant feature or bug file, or create a new Discussion-only note:

   ```
   > [YYYY-MM-DD HH:MM] **[role]-lead (improvement-scan)**: Found: [specific finding]. File: [path]. Recommendation: [what to do]. Priority suggestion: Low.
   ```

   Tag all findings with `(improvement-scan)` so PM and human can filter them.

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
