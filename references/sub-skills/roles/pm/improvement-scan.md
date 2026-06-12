---
slot: instructions
ordinal: 20
roles: [pm]
---

## Improvement Scanning (Quiet Cycle Productivity) — PM Override

During quiet cycles, scan for **process and workflow improvements**. PM never scans application source code — PM's domain is the squad's operating system: templates, sub-skills, vault, config, and handoff gates. This turns idle time into proactive process improvement and creative proposals.

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

Print: `[🦑 HH:MM:SS] Scanning for process improvements...`

Write status bar state: `scanning|🔍 Scanning process/workflow...`

1. **Read context sources**: Before scanning, read:
   - Your SOUL.md `### Improvement Scan` section for criteria and approval tiers
   - `.squidsquad/vault/BRIEFING.md` for active priorities and constraints
   - Relevant vault decisions and patterns (`grep -rl "type: decision\|type: pattern" .squidsquad/vault/galaxy/ --include="*.md" | head -10`)
   - Cross-reference vault content with current template instructions for contradictions or drift

2. **Select files to scan**: Use the scan index for query-driven targeting:
   ```bash
   python references/scripts/scan_index.py suggest-targets [ROLE] --count 5
   ```
   If `scan_index.py` is not available or fails, fall back to manually checking `.squidsquad/[your-role]/scan-history.md` and picking files based on recency, coverage gaps, and staleness.

   **PM scan targets** (in priority order):
   - `references/sub-skills/` — sub-skill definitions (shared and role-specific)
   - `references/roles/*/CLAUDE.md` — role templates
   - `.squidsquad/*/CLAUDE.md` — composed output (detect compose drift)
   - `.squidsquad/vault/galaxy/` — vault decisions, patterns, learnings
   - `.squidsquad/vault/areas/` — human-profile, code-conventions
   - `.squidsquad/config.md` — configuration consistency

   **Exclude from scanning**: Application source code, `node_modules/`, `vendor/`, `.git/`, build output, generated files, binary files. PM scans process files only.

3. **Scan with your domain lens**: Read your SOUL.md `### Improvement Scan` section for criteria, approval tiers, and noise filter. Apply to selected files looking for:
   - **Gaps**: missing handoff gates, unclear transitions, undocumented procedures
   - **Contradictions**: template instructions conflicting with vault decisions or each other
   - **Staleness**: references to removed features, old patterns, or defunct paths in templates
   - **Inconsistencies**: roles receiving different instructions for the same shared behavior
   - **Creative proposals**: novel improvements based on vault learnings — ideas the human wouldn't think to ask for

4. **Handle findings by approval tier** (max **2 items per scan**):

   **Tier 1 — Small mechanical fixes** (typo, stale ref, broken link):
   PM auto-fixes inline in the same cycle. No task needed. Note in iteration summary: `Auto-fixed: [description]`.

   **Tier 2 — Larger gap fixes** (workflow changes, cross-role impact):

   → run sub-skill: `tracker-protocol` — use the **Improvement-scan finding** one-liner shape (Observation / Location / Suggested-fix body, with `**Found by**: [ROLE]-lead (improvement-scan)` prefix). Choose `create-task` for workflow changes / `create-issue` for defects. Set `--role [target-role]`, `--severity low` (issue) or `--priority low` (task), `--reporter [ROLE]-lead`. Tag with `improvement-scan` label. These require human discussion before approval.

   **Tier 3 — Creative/experimental proposals**:

   → run sub-skill: `tracker-protocol` — always `create-task` shape with body:
   ```
   **Found by**: [ROLE]-lead (improvement-scan, creative proposal)
   **Context**: [what vault learnings or observations prompted this]
   **Proposal**: [what to do and why]
   **Expected benefit**: [what improves]
   ```
   Set `--role [target-role]`, `--priority low`, `--reporter [ROLE]-lead`. Tag with `improvement-scan` label. Always discuss with human. Never auto-approve.

5. **Update scan history**: Record the scan in both the DB and markdown (dual-write):
   ```bash
   python references/scripts/scan_index.py record-scan --role [ROLE] --files "[comma-separated files]" --findings '[JSON array of findings]'
   ```
   If `scan_index.py` is not available, skip the DB write — the markdown write below is sufficient.

   Also append to `.squidsquad/[your-role]/scan-history.md`:

   ```markdown
   ## Scan — YYYY-MM-DD HH:MM

   - **Files scanned**: [list of 3-5 files]
   - **Findings**: [list of findings reported, or "none"]
   - **Auto-fixed**: [list of tier-1 fixes applied inline, or "none"]
   - **Items rejected by human**: [list of previously rejected items — never refile these]
   ```

### Rules

- **PM scans process, not code** — never scan application source files
- **Default Low priority** — all scan items are Low priority. Human bumps if valuable.
- **Max 2 items per scan** — prevents noise. Quality over quantity. Tier-1 auto-fixes do not count toward this limit.
- **Never refile rejected items** — track rejected/dismissed items in scan history. If human says "not worth it," don't suggest it again.
- **Scanning must not extend cycle time excessively** — if a scan takes too long, reduce file count for next cycle.
- **Creative proposals always need human approval** — scan proposes, human decides.
- **Vault consultation is mandatory** — cross-reference vault context before and during scanning to catch contradictions and leverage learnings.
