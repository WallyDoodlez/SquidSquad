# FEAT-251 Research — Self-Diagnostic Bug Reporting

**Feature**: #251 — Self-diagnostic bug reporting: SquidSquad detects and logs its own bugs, users can report from within.

**Date**: 2026-04-05

---

## Summary

SquidSquad is going public. Two capabilities are needed: (1) a `/squidsquad-bug` slash command that lets users report bugs to the upstream SquidSquad repo from within any session, and (2) automated self-diagnostics that detect anomalies during operation and log them locally for debugging.

Currently, bug reporting requires the user to manually navigate to GitHub Issues on `WallyDoodlez/SquidSquad` and fill in environment details by hand (per CONTRIBUTING.md). There is no in-session reporting and no anomaly detection.

**Recommendation**: Implement both capabilities. The slash command generates a pre-filled GitHub issue URL (browser fallback) when the user lacks write access to the upstream repo, and uses `gh issue create -R` when they do. Self-diagnostics are append-only local logs in `.squidsquad/diagnostics/`, gitignored, with severity levels and size rotation. Detection hooks are added to existing scripts (tracker.py, compose.py, git_ops.py) rather than a new monolithic diagnostics script.

---

## 1. Codebase Impact

### New Files

| File | Purpose |
|------|---------|
| `.squidsquad/diagnostics/diagnostic-log.txt` | Append-only local anomaly log (gitignored) |
| `references/scripts/diagnostics.py` | Logging API + anomaly detection utilities |

### Modified Files

| File | Change |
|------|--------|
| `SKILL.md` | New `/squidsquad-bug` slash command section (follows `/squidsquad-status` and `/squidsquad-interval` pattern) |
| `.squidsquad/config.md` | New config fields: `Upstream Repo`, `Upstream Reporting` (opt-in) |
| `.gitignore` | Add `.squidsquad/diagnostics/` |
| `references/scripts/tracker.py` | Add diagnostic logging on failures (label not applied, transition rejected) |
| `references/scripts/compose.py` | Add diagnostic logging on template rendering failures |
| `references/scripts/git_ops.py` | Add diagnostic logging on phantom fix detection |
| Boot script templates (`start-role.sh`, `start-role.ps1`) | Add diagnostic logging on restart loop detection (connects to #250) |

### New Config Fields

```markdown
## Upstream Reporting

- **Upstream Repo**: WallyDoodlez/SquidSquad
- **Enabled**: no
```

`Enabled: no` by default — users opt in explicitly. The upstream repo URL is pre-populated at setup but editable (forks may want to report to their own fork).

---

## 2. User Bug Reporting (`/squidsquad-bug`)

### Slash Command Pattern

Follows the existing pattern established by `/squidsquad-status` (SKILL.md line 953) and `/squidsquad-interval` (line 991). The command is defined as a section in SKILL.md with trigger phrases, instructions, and output format.

### How It Works

1. **User invokes** `/squidsquad-bug` (or "report a squidsquad bug", "file a bug on squidsquad").
2. **PM collects context**:
   - Asks user for a description of the issue (required).
   - Auto-collects: SquidSquad version (from config.md), OS, shell, agent roles configured, iteration interval, PR flow setting.
   - Does NOT auto-collect: project name, project code, file contents, secrets, env vars, git remote URLs.
3. **Sanitization pass**: Strip any project-specific paths, repo names, or identifiers from the description. Replace with `[PROJECT]` placeholder.
4. **File upstream**:
   - **Primary**: `gh issue create -R WallyDoodlez/SquidSquad --title "BUG: [title]" --body "[body]" --label "bug"`
   - **Fallback**: If `gh` fails (no auth for upstream, or upstream unreachable), generate a pre-filled URL: `https://github.com/WallyDoodlez/SquidSquad/issues/new?title=...&body=...&labels=bug`
5. **Confirm to user**: Print the issue URL or the pre-filled link.

### Information Collected

| Field | Source | Privacy |
|-------|--------|---------|
| Description | User-provided | Sanitized — user controls content |
| SquidSquad version | `config.md` | Safe — public version number |
| OS / shell | System detection | Safe — generic environment info |
| Agent roles | `config.md` Dev Agents field | Safe — role names only (e.g. "skill, be") |
| Iteration interval | `config.md` | Safe |
| PR flow enabled | `config.md` | Safe |
| Tracker type | `config.md` | Safe |
| Context pressure threshold | `config.md` | Safe |
| Recent diagnostic log entries | `diagnostics/diagnostic-log.txt` (last 10 lines) | Safe — contains only SquidSquad internal errors, no project data |

### Information Excluded

- Project name, repo URL, git remotes
- File contents, code snippets, diffs
- Environment variables, secrets, API keys
- GitHub Issue titles/bodies from the user's project
- Vault contents (human preferences, project context)
- Working state contents
- Iteration log contents

### Issue Body Template

```markdown
## Bug Report (filed via /squidsquad-bug)

**Description**: [user description, sanitized]

**Environment**:
- SquidSquad version: [version]
- OS: [os]
- Shell: [shell]
- Agents: [role list]
- Tracker: [tracker type]
- Interval: [N]m
- PR Flow: [yes/no]

**Recent diagnostics** (last 10 entries):
```
[diagnostic log tail, if any]
```

**Steps to reproduce**: [user-provided, or "see description"]
```

### gh Auth for Upstream

The user's `gh` CLI is authenticated against their own repo, not necessarily against `WallyDoodlez/SquidSquad`. Two scenarios:

1. **User has push/issues access to upstream** (maintainer, collaborator, or public repo with issues enabled): `gh issue create -R WallyDoodlez/SquidSquad` works directly.
2. **User does NOT have access**: `gh issue create -R` will fail with a 403 or similar. The command falls back to generating a browser URL.

**GitHub public repos allow anyone to file issues** (unless issues are disabled). Since `WallyDoodlez/SquidSquad` is public with issues enabled (per CONTRIBUTING.md), any authenticated `gh` user can file issues there. The only failure case is if `gh` is not authenticated at all, which is already caught by the startup permission check.

**Recommendation**: Try `gh issue create -R` first. If it fails, fall back to the browser URL. Do not require a separate auth step.

---

## 3. Automated Self-Diagnostics

### Anomaly Detection Hooks

Each anomaly type maps to an existing script or agent behavior. Detection is added as lightweight logging calls within those scripts, not as a separate monitoring process.

| Anomaly | Detection Point | Severity | Description |
|---------|----------------|----------|-------------|
| **Phantom fix** | `git_ops.py has-changes` returning `false` after agent claims fix | warning | Agent said it fixed something but `git diff` is empty. Already detected in Step 2/3 of Ralph Loop — add diagnostic log call. |
| **Tracker transition rejected** | `tracker.py transition` exit code != 0 | error | Illegal status transition attempted. tracker.py already prints an error — add diagnostic log. |
| **Tracker label failure** | `tracker.py create-bug/create-feature` exit code != 0 | error | Label not applied, issue creation failed. |
| **Compose template error** | `compose.py` template rendering | error | `{{include:}}` directive unresolved, template file missing. |
| **Boot restart loop** | Boot script restart counter (from #250) | warning | Agent restarted N times in rapid succession. If restart count exceeds threshold (e.g. 5 in 10 minutes), log as error. |
| **Vault check failure** | vault-check Level 1 warnings | info | Missing frontmatter, unresolved wikilinks. Already printed — also log to diagnostics. |
| **Context pressure exit** | Step 1b context check | info | Agent exiting due to context pressure. Track frequency — if >3 exits in 1 hour, escalate to warning. |
| **gh unreachable** | Any `gh` command timeout/failure | warning | GitHub API temporarily unreachable. |
| **Test failure** | `run_tests.py` exit code != 0 | warning | Tests failed during bug fix or feature implementation. |

### Log Format

```
[YYYY-MM-DD HH:MM:SS] [SEVERITY] [AGENT] [CATEGORY] message
```

Examples:
```
[2026-04-05 14:23:01] [WARNING] [skill] [phantom-fix] git diff empty after claiming fix for #142
[2026-04-05 14:23:45] [ERROR] [skill] [tracker] transition rejected: #142 open -> shipped (illegal)
[2026-04-05 14:24:10] [INFO] [skill] [context-pressure] exiting at 83% — 2nd exit this hour
[2026-04-05 14:30:00] [WARNING] [pm] [restart-loop] agent restarted 4 times in last 10 minutes
[2026-04-05 14:31:00] [ERROR] [skill] [compose] unresolved include: {{include: missing-file.md}}
```

### Log Location and Management

- **Path**: `.squidsquad/diagnostics/diagnostic-log.txt`
- **Gitignored**: Yes — diagnostics are local-only, never committed. They may contain timing info or error details specific to the user's environment.
- **Append-only**: Scripts always append, never truncate or rewrite.
- **Rotation**: `diagnostics.py` checks file size before each append. If > 1 MB, rotate: rename current file to `diagnostic-log.1.txt` (overwriting any existing `.1`), start fresh. Keep only 1 rotated file (2 MB max total).
- **Concurrency**: Multiple agents may append simultaneously. Each write is a single `open(path, 'a')` call with the full line — atomic on most filesystems for lines under 4 KB.

### diagnostics.py API

```python
"""SquidSquad self-diagnostics — append-only anomaly logging.

Usage:
    python references/scripts/diagnostics.py log <severity> <agent> <category> <message>
    python references/scripts/diagnostics.py tail [N]          # show last N entries (default 10)
    python references/scripts/diagnostics.py summary           # count by severity and category
    python references/scripts/diagnostics.py clear             # truncate log (manual cleanup)
"""

# Severity levels: info, warning, error
# Categories: phantom-fix, tracker, compose, restart-loop, vault-check,
#             context-pressure, gh-unreachable, test-failure
```

Scripts call it via subprocess:
```bash
python references/scripts/diagnostics.py log warning skill phantom-fix "git diff empty after claiming fix for #142"
```

Or import it directly (for scripts already in Python):
```python
from diagnostics import log_diagnostic
log_diagnostic("error", "skill", "tracker", "transition rejected: #142 open -> shipped")
```

### Integration with Existing Scripts

**tracker.py**: Add `log_diagnostic()` call in the error paths of `transition()`, `create_bug()`, `create_feature()`. These paths already print to stderr — the diagnostic log is an additional structured record.

**compose.py**: Add `log_diagnostic()` call when an `{{include:}}` directive fails to resolve or a template file is missing.

**git_ops.py**: Add `log_diagnostic()` call in `has_changes()` when it returns `false` (callers can use this to correlate phantom fixes). Also log pull/rebase failures.

**Boot scripts**: After #250 lands, the restart counter is already tracked. Add a diagnostic log call when the counter increments.

---

## 4. Side Effects

| Side Effect | Impact | Mitigation |
|-------------|--------|------------|
| **Privacy risk from auto-filing upstream** | User's project context could leak in bug description | Sanitization pass strips project-specific info. User reviews description before filing. Upstream reporting is opt-in (`Enabled: no` default). |
| **gh auth for upstream** | User may not have `gh` configured, or may have restricted scopes | Fall back to browser URL. The startup `check-gh` already verifies local repo access — upstream filing is best-effort. |
| **Log file growth** | `diagnostic-log.txt` grows unbounded if anomalies are frequent | 1 MB rotation with 1 backup file. Max 2 MB on disk. |
| **Performance of anomaly detection** | Extra subprocess call or function call per detection point | Negligible — logging is a single file append. Detection piggybacks on existing error paths, not new monitoring. |
| **Multiple agents writing to same log** | Potential interleaving or corruption | Single-line atomic appends. Each entry is self-contained. Worst case: two lines interleave in the middle — each is still parseable because the format is fixed-width prefix. |
| **diagnostics.py as new dependency** | All scripts gain a new import | Optional import — if `diagnostics.py` is missing, scripts degrade gracefully (skip logging). This prevents a diagnostics bug from breaking core functionality. |

---

## 5. Edge Cases

### User has no gh auth for upstream repo
- `gh issue create -R WallyDoodlez/SquidSquad` fails.
- Fallback: generate a `https://github.com/WallyDoodlez/SquidSquad/issues/new?...` URL with pre-filled title, body, and labels.
- Print the URL and instruct the user to open it in a browser.

### Upstream repo is unreachable
- Same fallback as above. The URL is generated locally — it works even if GitHub is temporarily down (the user opens it later when GitHub is back).

### Diagnostic log fills up
- Rotation at 1 MB. Only 1 backup kept. Max 2 MB disk usage.
- `diagnostics.py clear` available for manual cleanup.
- If filesystem is full, the append fails silently — diagnostics must never crash the agent.

### Sensitive info accidentally included in bug report
- Sanitization pass replaces known-sensitive patterns (file paths containing the project directory, git remote URLs, env var values).
- User sees the full issue body before it is filed and can cancel.
- The `/squidsquad-bug` command should show a preview: "This is what will be filed: [preview]. Proceed? (y/n)"

### diagnostics.py is missing or broken
- All callers use a try/except or check exit code. If diagnostics fails, the calling script continues normally.
- This prevents a meta-bug where the diagnostic system itself breaks SquidSquad.

### User invokes /squidsquad-bug from a non-PM agent
- The command should work from any Claude session in the repo (like `/squidsquad-status`). It reads config.md directly.

---

## 6. Upgrade and Migration

### New Config Fields

Add to `config.md` template and existing config:

```markdown
## Upstream Reporting

- **Upstream Repo**: WallyDoodlez/SquidSquad
- **Enabled**: no
```

For existing installs, `/squidsquad-upgrade` adds the section if missing (with defaults).

### New Directory

```
.squidsquad/diagnostics/          (created on first diagnostic log write)
```

### .gitignore Additions

```
.squidsquad/diagnostics/
```

### SKILL.md Addition

New section: `## /squidsquad-bug — Report a SquidSquad Bug` — placed after the `/squidsquad-interval` section (follows the existing slash command pattern at SKILL.md lines 953-1008).

### compose.py / config.py

`config.py` needs a new `get upstream-repo` and `get upstream-reporting` accessor. `compose.py` needs no changes for the slash command (it is defined in SKILL.md, not in templates).

---

## 7. Open Questions

1. **Should the diagnostic log be structured (JSON lines) or plain text?** JSON lines would be easier to parse programmatically (for the `summary` command and for attaching to bug reports). Plain text is easier for humans to read with `tail -f`. Recommendation: JSON lines internally, with `tail` and `summary` commands formatting for human consumption.

2. **Should `/squidsquad-bug` require user confirmation before filing?** Yes — always show a preview. The user must see exactly what will be sent to the public upstream repo. No auto-filing.

3. **Should diagnostic entries be included in upstream bug reports by default?** Yes, the last 10 entries — they contain only SquidSquad-internal error messages (categories like "tracker", "compose", "phantom-fix"), no project code. The user can redact before confirming.

4. **Should there be a `/squidsquad-diagnostics` command to view the local log?** Useful but not part of this feature. Can be a fast follow-up. For now, users can `cat .squidsquad/diagnostics/diagnostic-log.txt`.

5. **Should anomaly detection be opt-out?** Diagnostics are local-only and have zero performance impact. Recommendation: always-on for local logging, opt-in for upstream reporting.

---

## 8. Recommendation

### Implementation Approach

**Phase 1 — diagnostics.py + detection hooks** (lower risk, immediate value):
1. Create `references/scripts/diagnostics.py` with `log`, `tail`, `summary`, `clear` commands.
2. Add `log_diagnostic()` calls to `tracker.py`, `compose.py`, `git_ops.py` error paths.
3. Add `.squidsquad/diagnostics/` to `.gitignore`.
4. Add `Upstream Reporting` section to config template.

**Phase 2 — /squidsquad-bug slash command**:
1. Add the slash command section to SKILL.md (follows existing `/squidsquad-status` pattern).
2. Implement context collection (version, OS, roles, diagnostic tail).
3. Implement sanitization pass.
4. Implement `gh issue create -R` with browser URL fallback.
5. Add user confirmation step (preview before filing).

**Phase 3 — boot script integration** (after #250 ships):
1. Add restart loop diagnostic logging to boot scripts.
2. Add context pressure frequency tracking.

### Estimated Scope

| Component | Files Changed | New LOC | Complexity |
|-----------|--------------|---------|------------|
| `diagnostics.py` | 1 new | ~150 | Low — file I/O, rotation, formatting |
| Script hooks (tracker, compose, git_ops) | 3 modified | ~30 total | Low — add try/except + log call in existing error paths |
| `.gitignore` + config template | 2 modified | ~5 | Trivial |
| `/squidsquad-bug` in SKILL.md | 1 modified | ~80 lines of markdown | Medium — slash command spec with sanitization rules |
| `config.py` accessors | 1 modified | ~10 | Trivial |
| Boot script hooks (Phase 3) | 2 modified | ~10 | Low — depends on #250 |

Total: ~285 new LOC across 5 files + ~80 lines of SKILL.md specification.

### Key Design Principles

1. **Diagnostics must never break the agent**. Every diagnostic call is wrapped in error handling. If `diagnostics.py` fails, the calling script continues normally.
2. **Local by default, upstream opt-in**. Diagnostic logs are local and gitignored. Upstream reporting requires explicit user opt-in AND per-report confirmation.
3. **No project data leaves the machine**. Bug reports contain only SquidSquad metadata (version, roles, config settings) and diagnostic entries. Project code, names, and secrets are never included.
4. **Piggyback on existing error paths**. No new monitoring processes or polling. Detection hooks are added where errors already occur.
5. **Follow established patterns**. The slash command follows `/squidsquad-status` and `/squidsquad-interval`. The script follows `tracker.py` and `cycle.py` conventions (subprocess list form, no `shell=True`, CLI + importable API).
