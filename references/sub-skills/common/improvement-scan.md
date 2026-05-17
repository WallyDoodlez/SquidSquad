## Improvement Scanning (Quiet Cycle Productivity)

During quiet cycles, use your domain expertise to scan the **target project** for improvements. This turns idle time into proactive project improvement. Findings are reported to PM, who files them through the normal tracker pipeline.

### Activation

Check `Improvement Scanning` in `config.md`. If set to `no`, skip scanning entirely.

**Issue gate**: Before triggering a scan, check for open issues assigned to your role:
```bash
python references/scripts/tracker.py list-issues [ROLE] --status open
```
If any issues exist, skip the scan — fix issues instead. Issues always take priority over improvement scanning.

Trigger an improvement scan on **every quiet cycle** (when no issues were fixed, no tasks progressed, no verification done), subject to the issue gate above.

### Scanning Step

When triggered, add a new step to your cycle:

Print: `[🦑 HH:MM:SS] Scanning for improvements...`

Write status bar state: `scanning|🔍 Scanning [target description]...`

1. **Detect project type**: Read `config.md` project info. Scan file extensions, `package.json`, `Cargo.toml`, `go.mod`, etc. to understand the tech stack. No new config field needed — auto-detect at scan time.

2. **Read your SOUL.md self-improvement lens**: Your soul defines what to look for. Consult it before scanning.

3. **Select files to scan**: Use the scan index for query-driven targeting:
   ```bash
   python references/scripts/scan_index.py suggest-targets [ROLE] --count 5
   ```
   This returns files ranked by a composite score (coverage gaps, git churn, cross-role findings, acceptance rate). If `scan_index.py` is not available or fails, fall back to manually checking `.squidsquad/[your-role]/scan-history.md` and picking files based on recency, coverage gaps, and staleness.

   **Exclude from scanning**: `.squidsquad/`, `node_modules/`, `vendor/`, `.git/`, build output directories (`dist/`, `build/`, `out/`), generated files, and binary files. Only scan source files belonging to the target project.

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

6. **Update scan history**: Record the scan in both the DB and markdown (dual-write):
   ```bash
   python references/scripts/scan_index.py record-scan --role [ROLE] --files "[comma-separated files]" --findings '[JSON array of findings]'
   ```
   If `scan_index.py` is not available, skip the DB write — the markdown write below is sufficient.

   Also append to `.squidsquad/[your-role]/scan-history.md`:

   ```markdown
   ## Scan — YYYY-MM-DD HH:MM

   - **Files scanned**: [list of 3-5 files]
   - **Findings**: [list of findings reported, or "none"]
   - **Items rejected by human**: [list of previously rejected items — never refile these]
   ```

7. **Capture knowledge from navigation** (#5569): As you read files during the scan, you learn things — patterns, gaps, connections between systems. At the end of each scan, log up to **3 knowledge items** (subject to the vault write budget of 2 per cycle):

   - **Vault writes**: learnings, patterns, or decisions discovered during navigation. Use vault-create for new notes, vault-update for existing ones. Apply the same 4-gate logic as vault-remember (write budget → dedup → reusability → fresh context).
   - **Scan criteria adjustments**: if you notice your scan criteria consistently miss a category of issues, note it in scan-history.md under a `- **Criteria note**:` line for future scans.
   - **Connection notes**: observations about how systems relate that aren't obvious from a single file — add as vault galaxy notes (`learning-*` or `pattern-*`).

   Only capture genuinely useful knowledge — not noise. If nothing noteworthy was learned, skip this step.

### Rules

- **File directly to tracker** — agents file scan findings as issues/tasks with the `improvement-scan` label. PM reviews through the normal pipeline.
- **Default Low priority** — all scan items are Low priority. Human bumps if valuable.
- **Max 2 items per scan** — prevents noise. Quality over quantity.
- **Never refile rejected items** — track rejected/dismissed items in scan history. If human says "not worth it," don't suggest it again.
- **Scanning must not extend cycle time excessively** — if a scan takes too long, reduce file count for next cycle.
- **PM does NOT auto-approve** scan items — human decides whether to act on them.
