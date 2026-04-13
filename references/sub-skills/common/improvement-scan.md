## Improvement Scanning (Quiet Cycle Productivity)

During quiet cycles, use your domain expertise to scan the **target project** for improvements. This turns idle time into proactive project improvement. Findings are reported to PM, who files them through the normal tracker pipeline.

### Activation

Check `Improvement Scanning` in `config.md`. If set to `no`, skip scanning entirely.

**Issue gate**: Before triggering a scan, check for open issues assigned to your role:
```bash
python references/scripts/tracker.py list-issues [ROLE] --status open
```
If any issues exist, skip the scan — fix issues instead. Issues always take priority over improvement scanning.

Maintain a **quiet cycle counter** in your working state. Increment it each quiet cycle (when no issues were fixed, no tasks progressed, no verification done). **After 3 consecutive quiet cycles**, trigger an improvement scan on the next quiet cycle (subject to the issue gate above). Reset the counter when:
- Real work occurs (issue fix, task progress, verification)
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

4. **Scan with your domain lens**: Read your SOUL.md `### Improvement Scan` section for:
   - **Scan criteria**: what to look for, in priority order
   - **File patterns**: which file types to target
   - **Noise filter**: what does NOT constitute a finding

   Apply these criteria to the selected files. If your SOUL.md lacks an Improvement Scan section, fall back to general code quality checks (dead code, error handling, security).

5. **Report findings to PM**: For each finding (max **2 items per scan**), classify it and file via `python references/scripts/tracker.py create-issue` or `create-task`:

   **Classification:**
   - **Issue** (`type:issue`): something broken, wrong, inconsistent, stale, or not working as specified
   - **Task** (`type:task`): something new that doesn't exist yet, enhancement, optimization

   File each finding as a GitHub Issue with labels: the appropriate `type:issue` or `type:task`, `role:[target-role]`, `priority:low`, and `improvement-scan`. Include in the Issue body:

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
