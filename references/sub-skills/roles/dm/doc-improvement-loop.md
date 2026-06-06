---
slot: instructions
ordinal: 20
roles: [dm]
---

## Doc Improvement Loop (Quiet Cycle Productivity)

During quiet cycles, proactively scan user-facing documentation for staleness, organization gaps, and accessibility improvements. DM owns all user-facing materials — this loop keeps them accurate and well-organized.

### Activation

Check `Improvement Scanning` in `config.md`. If set to `no`, skip entirely.

**Issue gate**: Before scanning, check for open issues assigned to your role:
```bash
python references/scripts/tracker.py list-issues dm --status open
```
If any issues exist, skip the scan — fix issues first.

**Quiet cycle gate**: Only trigger after **3 consecutive quiet cycles** (no deliveries, no bug fixes, no version bumps). Reset the counter when real work occurs or a scan completes.

### Scan State

Maintain `.squidsquad/[DM_ALIAS]/doc-scan-state.json` to track rotation and history:

```json
{
  "last_scanned": "README.md",
  "scan_history": [
    {"file": "README.md", "date": "2026-04-28", "findings": 0, "fixes": []},
    {"file": "SKILL.md:upgrade", "date": "2026-04-27", "findings": 1, "fixes": ["updated version ref"]}
  ],
  "doc_inventory": {
    "README.md": {"last_scanned": "2026-04-28", "sections": 12, "status": "current"},
    "SKILL.md": {"last_scanned": null, "sections": 25, "status": "unknown"}
  },
  "rejected_findings": []
}
```

If the file doesn't exist, create it with empty defaults on first scan.

### Tier 1 — Staleness Detection & Fix

**Rotation order** (one file per quiet scan cycle):
1. `README.md` — most user-visible
2. `SKILL.md` sections (split into chunks — scan 2-3 sections per cycle due to size)
3. `docs/ARCHITECTURE.md`
4. `docs/sub-skill-guide.md`
5. `CONTRIBUTING.md`
6. `CHANGELOG.md` — verify recent entries match shipped items

After completing the rotation, start over. The rotation ensures full coverage within ~8-10 quiet cycles.

**What to check for each doc**:

1. **Version references** — do version numbers match `config.md` current version?
2. **Feature descriptions** — does the doc describe features that match actual behavior? Read the relevant code/config to verify.
3. **Config fields** — are all config.md sections documented where referenced?
4. **Command references** — do CLI commands, script paths, and slash commands still exist?
5. **Dead links** — do internal file references (`docs/`, `CONTRIBUTING.md`, etc.) point to files that exist?
6. **Missing coverage** — are recently shipped features (check CHANGELOG) mentioned where they should be?
7. **Terminology drift** — does the doc use old terms for renamed concepts?

**When staleness is found**:

- **Fix directly** — DM owns user-facing materials. Edit the file immediately.
- Print: `[🦑 HH:MM:SS] Doc scan: fixed [N] stale items in [file]`
- Record fixes in scan state and iteration log.
- Max **3 fixes per scan cycle** to keep cycles bounded.

**When structural gaps are found** (missing docs, wrong organization):

- File a task to yourself via tracker:
  ```bash
  python references/scripts/tracker.py create-task \
    --title "[title]" --body "[description]" \
    --role dm --priority medium --reporter dm-lead
  ```
- Do not attempt structural changes inline during a scan.

### Tier 2 — Documentation Organization (threshold-triggered)

After completing **2 full rotations** of Tier 1 scanning, assess the documentation landscape:

1. **Count user-facing docs**: `docs/` directory + top-level markdown files.
2. **If docs/ has 5+ files**: suggest a directory structure (e.g., `docs/guides/`, `docs/reference/`). File a task.
3. **If no docs index exists**: file a task to create `docs/README.md` or `docs/INDEX.md` as a navigation page.
4. **Track doc categories**: maintain a `doc_categories` field in scan state mapping each doc to a category (getting-started, reference, architecture, contributing).

### Tier 3 — Accessibility Suggestions (threshold-triggered, light touch)

After completing **4 full rotations**, assess if accessibility improvements are warranted:

1. **If 8+ user-facing docs exist**: suggest a docs site generator (e.g., MkDocs, Docusaurus). File as a low-priority task.
2. **If docs contain complex diagrams/flows**: suggest PDF generation for offline reference. File as low-priority.
3. **Max 1 accessibility suggestion per rotation** — avoid over-engineering.

### Rules

- **DM fixes docs directly** — no task filing for factual corrections, version updates, or dead link fixes.
- **File tasks for structural changes** — new guides, reorganization, accessibility tooling.
- **Max 3 fixes per scan cycle** — keeps cycles bounded.
- **Never refile rejected findings** — track in `rejected_findings` array in scan state.
- **Consult SOUL.md self-improvement lens** before scanning — it defines DM's documentation quality bar.
- **Scan must not extend cycle time excessively** — if reading a large file, scan a subset of sections and continue next cycle.
