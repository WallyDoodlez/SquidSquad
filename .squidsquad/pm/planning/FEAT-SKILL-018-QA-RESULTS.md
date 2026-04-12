# FEAT-SKILL-018 QA Results — Vault Phase 4: vault-optimize

**Date**: 2026-04-11
**Tester**: QA subagent
**Vault state**: 7 notes (below 20-note threshold)

---

## Happy Path

### TC-1: prune-scan identifies stale+orphan notes
- **Result**: CANNOT TEST (vault below threshold)
- **Notes**: Vault has only 7 notes. The `prune` command runs successfully on small vaults (exits 0, outputs "Pruned: 0 notes") but there are no stale/orphan candidates to verify detection logic. Command name mismatch: test plan says `prune-scan`, script uses `prune`.

### TC-2: prune-scan identifies superseded notes
- **Result**: FAIL
- **Notes**: The script has NO superseded note detection logic. The `prune` function only checks for stale+orphan notes. There is no keyword overlap analysis or supersession detection anywhere in the code. The test plan expects `reason: superseded` in output — this feature is entirely missing.

### TC-3: consolidate-scan detects merge candidates
- **Result**: FAIL
- **Notes**: The `consolidate-scan` command does not exist. The script mentions "consolidate candidates" in the docstring but has zero implementation of consolidation logic. There is no `consolidate-scan` CLI command, no consolidation function, and no merge candidate detection.

### TC-4: reindex fixes broken wikilinks and syncs frontmatter
- **Result**: PARTIAL PASS
- **Notes**: The `reindex` command works and updates `links` frontmatter from body wikilinks. On the current vault, 4 notes had links updated successfully. However: (1) broken wikilinks are not flagged in a report — they are silently ignored, (2) there is no `fixes_applied` or `issues_found` count in JSON output — it just prints text lines, (3) no JSON report format at all — output is plain text lines like `rel: links -> [list]`.

### TC-5: decay-apply applies confidence decay
- **Result**: CANNOT TEST (no eligible notes)
- **Notes**: Command name mismatch: test plan says `decay-apply`, script uses `decay`. The code logic is present for high->medium decay after 60 days. No eligible notes in current vault. The decay function does NOT append changelog entries — it only updates `confidence` and `updated` fields. Test plan expects changelog entry "Confidence decayed by vault-optimize" — this is missing from the implementation.

### TC-6: decay-apply respects evergreen tag exemption
- **Result**: FAIL
- **Notes**: The script has NO evergreen tag exemption logic. There is no check for the `evergreen` tag anywhere in the code. The decay function processes all notes with confidence and updated fields regardless of tags.

### TC-7: relevance-report produces ranked output
- **Result**: PARTIAL PASS
- **Notes**: Command name mismatch: test plan says `relevance-report`, script uses `relevance`. The command runs successfully and outputs valid JSON with scores for all 7 vault notes. Each entry includes score, links, recency, and confidence. The `.relevance-index.json` file is written and is valid JSON. However: (1) output is NOT ranked/sorted descending — it's sorted alphabetically by key, (2) score breakdown field names differ from spec (script uses `links`/`recency`/`confidence` vs spec's `inbound_links`/`outbound_links`/`recency_bonus`/`confidence_bonus`), (3) no outbound_links metric — only inbound.

### TC-8: full-sweep runs all commands in correct order
- **Result**: PARTIAL PASS
- **Notes**: Command name mismatch: test plan says `full-sweep`, script uses `run`. When vault has <20 notes, the `run` command correctly reports "Vault too small" and skips. The code shows execution order: prune -> decay -> reindex -> relevance. This differs from the spec which requires: relevance-report -> prune-scan -> consolidate-scan -> decay-apply -> reindex (reindex last). In the implementation, reindex runs BEFORE relevance (3rd, not 5th), and consolidate is missing entirely.

### TC-9: auto-archive moves stale+orphan notes to archives/
- **Result**: FAIL
- **Notes**: The prune function uses `shutil.move()` instead of `git mv`. This means git history is NOT preserved on archive moves — the file appears as a new file in archives/ with no connection to the original. The test plan explicitly requires `git mv` for history preservation. Additionally, there is no frontmatter update (no `status: archived`, no `archived-date`), no changelog entry appended, and no inbound wikilink update/annotation.

### TC-10: pending questions queue created for non-auto items
- **Result**: PARTIAL PASS
- **Notes**: The `add-question` command works. It writes JSON entries to `.squidsquad/vault/.pending-questions`. However, the script itself never auto-generates pending questions during prune or consolidate scans — the `add-question` is purely a manual CLI tool. Entries are JSON objects (not plain language prose). There is no "Skip for now" option in the entry format.

### TC-11: PM check-in reports pending question count
- **Result**: PASS
- **Notes**: The `pending-count` command correctly returns the number of entries. The PM CLAUDE.md includes instructions to mention pending vault questions in check-in. The vault-optimize sub-skill documents the `pending-count` command and PM check-in integration.

### TC-12: Status bar icon with escalating urgency
- **Result**: FAIL
- **Notes**: The `statusline.sh` file has NO reference to `.pending-questions` anywhere. There is no code to read the pending questions file, no emoji rendering logic, and no escalating fire emoji logic. The status bar completely lacks the vault pending questions indicator.

---

## Edge Cases

### TC-13: Circular wikilinks — both notes stale
- **Result**: FAIL
- **Notes**: No circular reference detection logic exists in the script. The prune function checks each note independently — there is no grouping, no circular dependency analysis, and no `circular_group` output field.

### TC-14: Frontmatter parse failure — graceful handling
- **Result**: FAIL
- **Notes**: The `_parse_frontmatter()` function uses a simple line-by-line parser. If frontmatter is malformed, it silently returns an empty dict or partial results. There is no error reporting, no `unparseable` section in output, and notes with bad frontmatter are silently skipped rather than flagged.

### TC-15: Empty archives/ directory — first archive operation
- **Result**: CANNOT TEST
- **Notes**: Cannot test archive operations because vault is too small and prune uses `shutil.move` not `git mv`. The code does not create `archives/` directory if missing — `shutil.move` would fail if the directory doesn't exist.

### TC-16: Grace period — today's notes never optimized
- **Result**: PARTIAL PASS
- **Notes**: Grace period logic exists but uses filesystem mtime (`path.stat().st_mtime`) instead of the `created` frontmatter field. The test plan specifies checking the `created` date. Using mtime means the grace period could be defeated by file system operations that update mtime (copy, touch, etc.).

### TC-17: Vault below threshold (< 20 notes)
- **Result**: PASS
- **Notes**: Running `python references/scripts/vault_optimize.py run` with 7 notes correctly outputs "Vault too small (7 notes, minimum 20) - skipping" and exits with code 0. No modifications made. Confirmed via individual subcommands: `prune`, `decay`, `reindex`, `relevance` all run without the threshold check (only `run` enforces it). This is a discrepancy — individual commands bypass the threshold.

### TC-18: Zero optimization candidates
- **Result**: CANNOT TEST (vault below threshold for `run`)
- **Notes**: Individual commands (`prune`, `decay`) do run on any vault size and correctly report 0 candidates. But the `run` command blocks at the threshold check, so the full zero-candidates path cannot be tested.

### TC-19: Lock file prevents concurrent optimization
- **Result**: FAIL
- **Notes**: The `run` command checks vault size BEFORE checking the lock file. Since the vault has <20 notes, the lock file check is never reached. Additionally, the lock file TTL is only 30 seconds (very short — spec doesn't mention a specific TTL but implies 10 minutes for staleness). Individual commands (`prune`, `decay`, `reindex`, `relevance`) do NOT check the lock file at all — only `run` does.

### TC-20: Lock file cleanup on completion
- **Result**: PARTIAL PASS
- **Notes**: The `run` function uses try/finally to release the lock, which is correct. Verified: after running `run`, no lock file remains. However, individual commands never create or manage the lock file.

### TC-21: Lock file cleanup on script crash/error
- **Result**: PASS
- **Notes**: The try/finally pattern in `run_optimize()` ensures the lock is released even on exceptions. This is a correct implementation pattern.

### TC-22: Decay clock reset prevents cascading decay
- **Result**: PASS (code review)
- **Notes**: The decay function sets `updated` to today's date after decaying. On a subsequent run, the note's updated date is today, which is within the 60-day window, so it won't be decayed again. Correct by design.

### TC-23: Area note exemption from pruning
- **Result**: PASS
- **Notes**: The prune function only processes notes with `rel.startswith("galaxy/")`. Area notes, project notes, BRIEFING.md, and all non-galaxy content are automatically excluded.

### TC-24: Plain language prompts — no vault internals exposed
- **Result**: CANNOT TEST
- **Notes**: The script never auto-generates pending questions. The `add-question` command accepts arbitrary text — it's up to the caller (agent) to write plain language. The format spec in the sub-skill instructions say to use plain language, but the script itself does not enforce this.

### TC-25: Skip for now option on all prompts
- **Result**: FAIL
- **Notes**: The pending question JSON format contains only `timestamp`, `agent`, `note`, and `question` fields. There is no `skip` option, no `actions` array, and no structure for presenting choices to the human.

---

## Side Effect Regression Tests

### TC-26: vault-check still works unchanged after optimize install
- **Result**: PASS
- **Notes**: `python references/scripts/vault_check.py validate` runs successfully. All commands work: validate, check-frontmatter, check-wikilinks, check-structure, list-orphans, dedup-check. Output: "OK: Vault structure valid, OK: All galaxy note frontmatter valid, OK: All wikilinks resolve, ORPHAN: galaxy/pattern-windows-utf8-subprocess.md, Vault validation passed".

### TC-27: vault-remember still works unchanged after optimize install
- **Result**: PASS
- **Notes**: `vault_remember.py note-count` returns 7 (correct). `vault_remember.py --help` shows all expected commands. `vault_check.py dedup-check` works. No import errors or behavior changes observed.

### TC-28: vault-create and vault-update not affected
- **Result**: PASS (by inspection)
- **Notes**: vault_optimize.py is a standalone script with no shared imports from vault_check.py or vault_remember.py. Lock file only exists during optimize runs. No interference path exists.

### TC-29: git history preserved on archive moves
- **Result**: FAIL
- **Notes**: The prune function uses `shutil.move()` instead of `git mv`. Git history will NOT be preserved on archive moves. The file will appear as deleted + new file rather than a rename.

### TC-30: Wikilink rewrites after archive do not break other notes
- **Result**: FAIL
- **Notes**: The prune function does not update inbound wikilinks after archiving a note. When a note is moved to archives/, all `[[note-name]]` references in other active notes become broken. There is no wikilink rewrite or annotation logic.

### TC-31: Config file not corrupted by optimize additions
- **Result**: PASS
- **Notes**: The `## Vault Optimize` section exists in config.md with Enabled: yes, Threshold: 20. `python references/scripts/config.py get vault-remember` still returns `yes`. Existing config sections are intact.

---

## Upgrade Verification Tests

### TC-32: Fresh install — vault_optimize.py available
- **Result**: FAIL
- **Notes**: Script is present and `--help` works (exit 0). However, the help text shows commands `run`, `prune`, `decay`, `reindex`, `relevance`, `pending-count`, `add-question`. The test plan expects `prune-scan`, `consolidate-scan`, `reindex`, `decay-apply`, `relevance-report`, `full-sweep`. Of the 6 expected commands, only `reindex` matches exactly. `consolidate-scan` is entirely missing.

### TC-33: Existing install without upgrade — graceful degradation
- **Result**: PASS (by inspection)
- **Notes**: The sub-skill instructions in CLAUDE.md tell agents to run `python references/scripts/vault_optimize.py run`. If the script is absent, Python will exit with a file-not-found error. The sub-skill does not explicitly instruct agents to check for script existence first. However, this is a sub-skill documentation concern, not a script bug.

### TC-34: Manifest and role files updated
- **Result**: PASS
- **Notes**: `vault-optimize` is listed in `references/sub-skills/manifest.md` as entry 8c. The vault-optimize sub-skill content is composed into all agent CLAUDE.md files (pm, skill, dm, dev, qa, designer templates all contain the vault-optimize step).

### TC-35: Config section added with defaults
- **Result**: PARTIAL PASS
- **Notes**: `## Vault Optimize` section exists in config.md with Enabled: yes and Threshold: 20. However, `python references/scripts/config.py get vault-optimize` returns an error ("Field 'vault-optimize' not found"). The config.py script does not recognize the vault-optimize field. Only the script's internal `_is_config_enabled()` function can read it via regex.

### TC-36: Relevance index file location
- **Result**: PASS
- **Notes**: After running `python references/scripts/vault_optimize.py relevance`, the file `.squidsquad/vault/.relevance-index.json` exists and is valid JSON. Contains scored entries for all 7 active vault notes.

---

## Smoke Tests

| Check | Result |
|-------|--------|
| `prune-scan` exits 0 on vault < 20 notes | PASS (command is `prune`, not `prune-scan`, but exits 0) |
| `reindex` exits 0 on healthy vault | PASS |
| `decay-apply` exits 0 with no eligible notes | PASS (command is `decay`, not `decay-apply`) |
| `relevance-report` produces valid JSON | PASS (command is `relevance`, not `relevance-report`) |
| `.relevance-index.json` written after relevance | PASS |
| Lock file created/removed during sub-command | FAIL — individual commands do NOT use lock file, only `run` does |
| `vault_check.py validate` still passes | PASS |
| `vault_remember.py note-count` returns correct count | PASS |
| Status bar renders pending questions icon | FAIL — not implemented in statusline.sh |
| Status bar shows no icon when no pending questions | FAIL — not implemented in statusline.sh |

---

## Summary Table

| TC | Title | Result |
|----|-------|--------|
| TC-1 | prune-scan identifies stale+orphan notes | CANNOT TEST |
| TC-2 | prune-scan identifies superseded notes | **FAIL** |
| TC-3 | consolidate-scan detects merge candidates | **FAIL** |
| TC-4 | reindex fixes broken wikilinks and syncs frontmatter | PARTIAL PASS |
| TC-5 | decay-apply applies confidence decay | CANNOT TEST |
| TC-6 | decay-apply respects evergreen tag exemption | **FAIL** |
| TC-7 | relevance-report produces ranked output | PARTIAL PASS |
| TC-8 | full-sweep runs all commands in correct order | PARTIAL PASS |
| TC-9 | auto-archive moves via git mv | **FAIL** |
| TC-10 | pending questions queue | PARTIAL PASS |
| TC-11 | PM check-in reports pending count | PASS |
| TC-12 | Status bar icon with escalating urgency | **FAIL** |
| TC-13 | Circular wikilinks detection | **FAIL** |
| TC-14 | Frontmatter parse failure handling | **FAIL** |
| TC-15 | Empty archives/ first archive | CANNOT TEST |
| TC-16 | Grace period for today's notes | PARTIAL PASS |
| TC-17 | Vault below threshold | PASS |
| TC-18 | Zero optimization candidates | CANNOT TEST |
| TC-19 | Lock file prevents concurrent runs | **FAIL** |
| TC-20 | Lock file cleanup on completion | PARTIAL PASS |
| TC-21 | Lock file cleanup on crash | PASS |
| TC-22 | Decay clock reset | PASS |
| TC-23 | Area note exemption | PASS |
| TC-24 | Plain language prompts | CANNOT TEST |
| TC-25 | Skip for now option | **FAIL** |
| TC-26 | vault-check regression | PASS |
| TC-27 | vault-remember regression | PASS |
| TC-28 | vault-create/update unaffected | PASS |
| TC-29 | git history on archive | **FAIL** |
| TC-30 | Wikilink rewrites after archive | **FAIL** |
| TC-31 | Config not corrupted | PASS |
| TC-32 | Help shows all sub-commands | **FAIL** |
| TC-33 | Graceful degradation without script | PASS |
| TC-34 | Manifest and role files updated | PASS |
| TC-35 | Config section with defaults | PARTIAL PASS |
| TC-36 | Relevance index file location | PASS |

---

## Overall Verdict: FAIL

**Passed**: 12 | **Partial Pass**: 6 | **Failed**: 12 | **Cannot Test**: 6

### Critical Gaps

1. **Missing `consolidate-scan` command**: Entirely unimplemented. No consolidation/merge detection logic.
2. **Missing superseded note detection**: No keyword overlap analysis in prune.
3. **`shutil.move` instead of `git mv`**: Archive operations break git history.
4. **No status bar integration**: `statusline.sh` has zero pending-questions code.
5. **No evergreen tag exemption**: Decay applies to all notes regardless of tags.
6. **Command name mismatches**: Script uses `prune`/`decay`/`relevance`/`run` vs spec's `prune-scan`/`decay-apply`/`relevance-report`/`full-sweep`.
7. **No circular reference detection**: Stale notes with mutual links not grouped.
8. **No frontmatter error reporting**: Malformed notes silently skipped.
9. **No wikilink rewrite on archive**: Broken links left behind after pruning.
10. **Individual commands bypass lock file and threshold**: Only `run` enforces these guards.
11. **config.py does not recognize vault-optimize field**: Only the script's internal regex reads it.
12. **No "Skip for now" option in pending question format**.
13. **No changelog entry on decay**: Spec requires appending "Confidence decayed by vault-optimize".
