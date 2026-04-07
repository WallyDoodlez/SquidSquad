# FEAT-251 Test Plan — Self-Diagnostic Bug Reporting

**Feature**: #251 — Self-diagnostic bug reporting
**Script under test**: `references/scripts/diagnostics.py`
**Test file**: `references/scripts/test_diagnostics.py` (Python unittest, stdlib only)
**Python**: 3.8+, stdlib only

---

## Test Infrastructure

### Conventions
- All tests use a temporary directory for diagnostic log output (cleaned up in `tearDown`)
- Unit tests mock filesystem and subprocess calls via `unittest.mock.patch`
- Integration tests use real file I/O in temp directories
- Exit codes: 0 = success, 1 = validation error, 2 = I/O error

### Test Runner
```bash
cd references/scripts && python -m unittest test_diagnostics.py -v
```

---

## A. Unit Tests — diagnostics.py

### A1. Log Entry Creation (JSON Lines Format)

**TC-001: log command produces valid JSON Lines entry**
- Precondition: Empty diagnostic log file in temp dir
- Steps: Call `diagnostics.py log warning skill phantom-fix "git diff empty after claiming fix for #142"`
- Expected: File contains exactly one line. Line parses as valid JSON with fields: `timestamp`, `severity`, `agent`, `category`, `message`. Exit 0.

**TC-002: required fields present in every log entry**
- Precondition: Empty diagnostic log
- Steps: Call `log` with severity=`error`, agent=`pm`, category=`tracker`, message=`transition rejected`
- Expected: JSON object contains all required keys: `timestamp` (ISO 8601), `severity` (`error`), `agent` (`pm`), `category` (`tracker`), `message` (`transition rejected`). No key is null or empty string.

**TC-003: timestamp is ISO 8601 format**
- Precondition: Empty diagnostic log
- Steps: Call `log info skill context-pressure "exiting at 83%"`
- Expected: `timestamp` field matches pattern `YYYY-MM-DDTHH:MM:SS` (or with timezone offset). Parseable by `datetime.fromisoformat()`.

**TC-004: severity must be info, warning, or error**
- Steps: Call `log critical skill tracker "bad severity"`
- Expected: Exit 1, stderr indicates invalid severity. No line appended to log.

**TC-005: multiple log calls append sequentially**
- Precondition: Empty diagnostic log
- Steps: Call `log` three times with different messages
- Expected: File contains exactly 3 lines. Each line is valid JSON. Order matches call order.

**TC-006: optional context field included when provided**
- Steps: Call `log_diagnostic("warning", "skill", "phantom-fix", "empty diff", context={"issue": 142})`
- Expected: JSON entry includes `context` key with value `{"issue": 142}`.

**TC-007: log creates diagnostics directory if missing**
- Precondition: Diagnostics directory does not exist
- Steps: Call `log info skill tracker "first entry"`
- Expected: Directory created, log file created, entry written. Exit 0.

### A2. Log Rotation

**TC-008: log file under 1MB is not rotated**
- Precondition: Diagnostic log exists at 500KB
- Steps: Call `log info skill tracker "small append"`
- Expected: Entry appended to existing file. No `.1.txt` backup created.

**TC-009: log file at 1MB triggers rotation**
- Precondition: Diagnostic log exists at exactly 1MB
- Steps: Call `log info skill tracker "triggers rotation"`
- Expected: Old file renamed to `diagnostic-log.1.txt`. New `diagnostic-log.txt` created containing only the new entry. Exit 0.

**TC-010: rotation overwrites existing backup**
- Precondition: Both `diagnostic-log.txt` (1MB) and `diagnostic-log.1.txt` (old backup) exist
- Steps: Call `log info skill tracker "second rotation"`
- Expected: `diagnostic-log.1.txt` replaced with previous `diagnostic-log.txt` contents. New `diagnostic-log.txt` contains only the new entry. Only 1 backup file exists (no `.2.txt`).

**TC-011: max disk usage is 2MB (1MB active + 1MB backup)**
- Precondition: `diagnostic-log.txt` at 1MB, `diagnostic-log.1.txt` at 1MB
- Steps: Call `log` to trigger rotation
- Expected: Total size of `diagnostic-log.txt` + `diagnostic-log.1.txt` does not exceed ~2MB.

### A3. Sanitization

**TC-012: file paths stripped from config snapshot**
- Steps: Call sanitization function on string containing `C:\Users\john\project\src\main.py`
- Expected: Path replaced with `[PATH]` or `[REDACTED]`.

**TC-013: Unix paths stripped from config snapshot**
- Steps: Call sanitization function on string containing `/home/john/project/src/main.py`
- Expected: Path replaced with `[PATH]` or `[REDACTED]`.

**TC-014: API tokens stripped**
- Steps: Call sanitization function on string containing `ghp_ABC123def456ghi789jklmnop` (GitHub PAT format)
- Expected: Token replaced with `[TOKEN]` or `[REDACTED]`.

**TC-015: generic bearer tokens stripped**
- Steps: Call sanitization function on string containing `Bearer eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOi`
- Expected: Token value replaced with `[TOKEN]` or `[REDACTED]`.

**TC-016: email addresses stripped**
- Steps: Call sanitization function on string containing `user@example.com`
- Expected: Email replaced with `[EMAIL]` or `[REDACTED]`.

**TC-017: safe fields pass through unchanged**
- Steps: Call sanitization function on string containing only SquidSquad version `0.12.0`, OS `linux`, shell `bash`
- Expected: String returned unchanged — no redaction applied to safe metadata.

**TC-018: multiple sensitive items in one string all stripped**
- Steps: Call sanitization function on `"path /home/user/repo token ghp_abc123 email dev@co.io"`
- Expected: All three sensitive items redacted. Safe words (`path`, `token`, `email` as labels) preserved.

### A4. Public vs Private Repo Detection

**TC-019: public repo detected via gh api**
- Precondition: Mock `gh api repos/{owner}/{repo}` returning `{"private": false}`
- Steps: Call repo visibility detection function
- Expected: Returns `"public"`. Diagnostics default to ON.

**TC-020: private repo detected via gh api**
- Precondition: Mock `gh api repos/{owner}/{repo}` returning `{"private": true}`
- Steps: Call repo visibility detection function
- Expected: Returns `"private"`. Diagnostics default to OFF.

**TC-021: gh api failure falls back gracefully**
- Precondition: Mock `gh api` returning exit code 1 (network error or no auth)
- Steps: Call repo visibility detection function
- Expected: Returns `"unknown"`. Diagnostics default to OFF (safe default). No crash.

---

## B. Integration Tests

### B1. Bug Report Command

**TC-022: /squidsquad-bug generates correct report structure**
- Precondition: Config.md populated with version, OS, agents, interval, PR flow, tracker type. Diagnostic log has 5 entries.
- Steps: Simulate `/squidsquad-bug` with description "Labels not applied on issue creation"
- Expected: Generated report body contains all sections: Description (sanitized), Environment (version, OS, shell, agents, tracker, interval, PR flow), Recent diagnostics (up to 20 entries), Steps to reproduce. No project-specific paths or repo names in output.

**TC-023: gh issue create -R upstream succeeds for public repo**
- Precondition: `gh` authenticated with access to upstream repo. Upstream reporting enabled in config.
- Steps: Call the bug report filing function targeting `WallyDoodlez/SquidSquad`
- Expected: `gh issue create -R WallyDoodlez/SquidSquad` executes. Returns issue URL. Issue has `bug` label.
- Teardown: Close and delete the test issue.

**TC-024: browser fallback URL generated when gh auth fails**
- Precondition: Mock `gh issue create -R` returning exit code 1 (403 forbidden)
- Steps: Call the bug report filing function
- Expected: Returns a URL matching `https://github.com/WallyDoodlez/SquidSquad/issues/new?title=...&body=...&labels=bug`. URL-encoded title and body are present. No error raised.

### B2. Detection Hooks

**TC-025: tracker.py error triggers diagnostic log entry**
- Precondition: Empty diagnostic log. Set up a condition where `tracker.py transition` will fail (illegal transition).
- Steps: Call `python references/scripts/tracker.py transition 1 pending shipped` (illegal)
- Expected: Diagnostic log contains one entry with severity=`error`, category=`tracker`, message mentioning the rejected transition.

**TC-026: compose.py error triggers diagnostic log entry**
- Precondition: Empty diagnostic log. Template file references a missing include: `{{include: nonexistent.md}}`
- Steps: Run `compose.py` against the broken template
- Expected: Diagnostic log contains one entry with severity=`error`, category=`compose`, message mentioning unresolved include.

### B3. Normal Operation Logging

**TC-027: diagnostic log entries appended during normal operation**
- Precondition: Empty diagnostic log
- Steps: Trigger multiple normal-path events that generate diagnostic entries (e.g., context pressure info log, vault check info log). Read log after.
- Expected: Log contains entries in chronological order. Each entry is valid JSON Lines. No duplicate entries for a single event.

---

## C. Side Effect Regression

**TC-028: existing tracker.py operations unchanged when diagnostics.py present**
- Precondition: `diagnostics.py` exists in `references/scripts/`
- Steps: Run the full existing tracker.py test suite (`test_scripts.py` tracker section)
- Expected: All existing tracker.py tests pass with zero changes. No new failures introduced.

**TC-029: existing tracker.py operations unchanged when diagnostics.py missing**
- Precondition: Rename `diagnostics.py` to `diagnostics.py.bak` (simulate missing file)
- Steps: Run tracker.py operations: `create-bug`, `transition`, `list-bugs`, `comment`
- Expected: All operations succeed. Stderr may contain a one-line warning about missing diagnostics. No crash, no exit code change.
- Teardown: Restore `diagnostics.py`.

**TC-030: .gitignore covers diagnostics directory**
- Steps: Read `.gitignore` and check for `.squidsquad/diagnostics/` entry. Run `git status` after creating a file in `.squidsquad/diagnostics/`.
- Expected: `.gitignore` contains the entry. `git status` does not show any files under `.squidsquad/diagnostics/` as untracked.

**TC-031: no performance degradation on normal cycles**
- Precondition: Diagnostic hooks active in tracker.py, compose.py, git_ops.py
- Steps: Time 10 consecutive successful `tracker.py list-bugs skill` calls with diagnostics present vs absent (use `time` or `timeit`)
- Expected: Average call duration increase is less than 50ms per call. Diagnostic logging does not introduce perceptible latency.

---

## D. Smoke Tests (Manual)

**TC-032: run /squidsquad-bug end-to-end**
- Steps: In a live Claude session, type `/squidsquad-bug`. Provide description "Test bug report". Review the preview. Cancel before filing.
- Verify: Preview shows all expected sections. No project-specific data leaks. Cancel works cleanly.

**TC-033: diagnostic log accumulates across cycles**
- Steps: Run 3 Ralph Loop cycles. After each, check `.squidsquad/diagnostics/diagnostic-log.txt`.
- Verify: Log grows monotonically. Entries from all 3 cycles present. JSON Lines format intact.

**TC-034: diagnostic log rotation works at scale**
- Steps: Write ~1.1MB of test entries to diagnostic log. Trigger one more log call.
- Verify: `diagnostic-log.1.txt` exists with old content. `diagnostic-log.txt` is small (just the new entry). No data loss in backup.

**TC-035: diagnostics.py clear command truncates log**
- Steps: Populate diagnostic log with entries. Run `diagnostics.py clear`.
- Verify: Log file is empty or deleted. No backup files affected.

**TC-036: tail command shows last N entries**
- Steps: Populate log with 25 entries. Run `diagnostics.py tail 10`.
- Verify: Output shows exactly 10 entries, formatted for human readability (not raw JSON). Most recent entries shown.

**TC-037: summary command shows counts by severity and category**
- Steps: Populate log with mixed entries (3 info, 2 warning, 1 error across tracker, compose, phantom-fix). Run `diagnostics.py summary`.
- Verify: Output shows correct counts grouped by severity and by category.
