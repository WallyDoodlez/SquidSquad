# FEAT-251 Context — Self-Diagnostic Bug Reporting

## Scope

Add `/squidsquad-bug` slash command for user bug reporting to upstream SquidSquad repo, and automated local anomaly detection that logs diagnostics for debugging.

**Delivers:**
1. `/squidsquad-bug` slash command in SKILL.md — collects issue description, version, OS, config snapshot, recent diagnostics; files to upstream repo via `gh issue create -R WallyDoodlez/SquidSquad` with browser URL fallback
2. `references/scripts/diagnostics.py` — anomaly detection hooks and diagnostic log management
3. `.squidsquad/diagnostics/` directory (gitignored) — local diagnostic log
4. Detection hooks in existing error paths (tracker.py, compose.py, git_ops.py)
5. Config additions for diagnostic settings

## Locked Decisions (human decided)

- **JSON Lines log format**: One JSON object per line with structured fields (timestamp, severity, source, message). Programmatic parsing, clean attachment to bug reports. Why: structured data enables future tooling without sacrificing readability.

- **Diagnostic visibility by repo type**: Public repos default to diagnostics ON (opt-out). Private repos default to OFF (opt-in). Why: public installs benefit the community with diagnostic data; private repos need explicit consent.

- **Include diagnostics in bug reports with redaction preview**: Auto-attach last 20 diagnostic entries to the bug report. User sees full editable preview before filing and can redact anything sensitive. Why: maximum debugging value with user control.

- **Editable preview before upstream filing**: Show complete report content via AskUserQuestion. User can edit/redact, then confirm. Report goes to public GitHub repo — user must have informed control. Why: public data requires informed consent.

## Dev Discretion (dev agent can choose)

- Exact anomaly detection hook points in tracker.py, compose.py, git_ops.py
- Diagnostic log rotation strategy (1MB cap recommended by research)
- JSON Lines field schema (required: timestamp, severity, source, message; optional: context)
- How to detect public vs private repo (gh api or git remote inspection)
- Browser URL fallback format when gh auth fails for upstream
- Sanitization rules for config snapshot (strip paths, tokens, emails)

## Side Effect Mitigations (required)

- **Privacy**: No code, secrets, project names, or file paths in upstream reports. Config snapshot sanitized. User previews everything before filing.
- **Auth fallback**: If user can't `gh issue create -R` upstream, generate a pre-filled URL that opens in browser. Never fail silently.
- **Log growth**: Diagnostic log capped at 1MB with rotation. Gitignored — never committed.
- **No performance impact**: Detection hooks piggyback on existing error paths, not a separate monitoring process.

## Upgrade Path (required)

- **New files**: `references/scripts/diagnostics.py`, `.squidsquad/diagnostics/.gitkeep`
- **Modified files**: SKILL.md (add /squidsquad-bug command spec), .gitignore (add diagnostics/), config.md (add Diagnostics section), tracker.py/compose.py/git_ops.py (add detection hooks)
- **Graceful degradation**: Without diagnostics.py, detection hooks silently skip. Without /squidsquad-bug, users report manually via CONTRIBUTING.md.

## Out of Scope

- `/squidsquad-diagnostics` viewer command (future follow-up)
- Automated upstream filing without user confirmation
- Telemetry or usage analytics
- Diagnostic data aggregation across multiple installs
