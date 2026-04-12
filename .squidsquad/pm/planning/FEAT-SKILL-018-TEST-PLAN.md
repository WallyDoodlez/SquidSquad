# FEAT-SKILL-018 Test Plan — Vault Phase 4: vault-optimize

## Test Cases

---

### Happy Path

### TC-1: prune-scan identifies stale+orphan notes
- **Precondition**: Vault with 20+ notes. At least one galaxy note has `status: active`, `updated` older than 60 days, and zero inbound wikilinks.
- **Steps**: Run `python references/scripts/vault_optimize.py prune-scan`
- **Expected**: JSON output includes the stale+orphan note with reason `stale+orphan`. Notes updated within 60 days or with inbound links are NOT listed.
- **Verification**: `python references/scripts/vault_optimize.py prune-scan | python -m json.tool` — confirm candidate list contains the expected note and reason field.

### TC-2: prune-scan identifies superseded notes
- **Precondition**: Two galaxy notes with same type prefix and >60% keyword overlap in titles/tags. The older one (by `created` date) is the candidate.
- **Steps**: Run `python references/scripts/vault_optimize.py prune-scan`
- **Expected**: JSON output includes the older note as a superseded candidate. The newer note is NOT listed.
- **Verification**: Parse JSON output; confirm `reason` is `superseded` and the candidate's `created` date is older than the surviving note.

### TC-3: consolidate-scan detects merge candidates
- **Precondition**: Two galaxy notes of the same type, both under 50 lines, sharing 3+ tags.
- **Steps**: Run `python references/scripts/vault_optimize.py consolidate-scan`
- **Expected**: JSON output groups the two notes as a merge candidate pair.
- **Verification**: Parse JSON; confirm the group contains both note paths and the shared tag count is >= 3.

### TC-4: reindex fixes broken wikilinks and syncs frontmatter
- **Precondition**: Note A body contains `[[note-b]]` but note-b.md was renamed to note-b-v2.md. Note A frontmatter `links` field is stale (missing note-b-v2).
- **Steps**: Run `python references/scripts/vault_optimize.py reindex`
- **Expected**: Broken link flagged in report. `links` frontmatter across all notes updated to match their body wikilinks. Report includes count of fixes applied and issues requiring agent review.
- **Verification**: Read note A frontmatter — `links` field matches body wikilinks. Report JSON contains `fixes_applied` and `issues_found` counts.

### TC-5: decay-apply applies confidence decay
- **Precondition**: Galaxy note with `confidence: high`, `updated` older than 60 days, no `evergreen` tag.
- **Steps**: Run `python references/scripts/vault_optimize.py decay-apply`
- **Expected**: Note's `confidence` changed from `high` to `medium`. `updated` field set to today. Changelog entry appended: "Confidence decayed by vault-optimize".
- **Verification**: Read the note's frontmatter — `confidence: medium`, `updated: <today>`. Changelog section contains decay entry.

### TC-6: decay-apply respects evergreen tag exemption
- **Precondition**: Galaxy note with `confidence: high`, `updated` older than 60 days, tag `evergreen` present.
- **Steps**: Run `python references/scripts/vault_optimize.py decay-apply`
- **Expected**: Note is NOT decayed. Confidence remains `high`. No changelog entry added.
- **Verification**: Read the note — `confidence: high`, `updated` unchanged.

### TC-7: relevance-report produces ranked output
- **Precondition**: Vault with 20+ notes, varying inbound/outbound link counts and ages.
- **Steps**: Run `python references/scripts/vault_optimize.py relevance-report`
- **Expected**: JSON ranked list of all notes by relevance score. Each entry includes note path, score, and score breakdown (inbound_links, outbound_links, recency_bonus, confidence_bonus). Relevance index written to `.squidsquad/vault/.relevance-index.json`.
- **Verification**: `cat .squidsquad/vault/.relevance-index.json | python -m json.tool` — confirm file exists, is valid JSON, contains all vault notes, and scores are ordered descending.

### TC-8: full-sweep runs all commands in correct order
- **Precondition**: Vault with 20+ notes including candidates for prune, consolidate, decay, and reindex.
- **Steps**: Run `python references/scripts/vault_optimize.py full-sweep`
- **Expected**: Combined JSON report with sections for each sub-command. Execution order is: relevance-report, prune-scan, consolidate-scan, decay-apply, reindex (reindex always last).
- **Verification**: Parse combined JSON — all 5 sections present. Check timestamps or ordering in output to confirm reindex ran last.

### TC-9: auto-archive moves stale+orphan notes to archives/
- **Precondition**: prune-scan has identified a stale+orphan note at `galaxy/old-note.md`.
- **Steps**: Agent (or script with `--auto-archive` flag) executes the archive for the stale+orphan candidate.
- **Expected**: File moved via `git mv` from `galaxy/old-note.md` to `archives/old-note.md`. Frontmatter updated: `status: archived`, `archived-date: <today>`. Changelog entry appended with reason. Inbound wikilinks across vault updated or annotated.
- **Verification**: `git log --follow archives/old-note.md` shows history preserved. Frontmatter has `status: archived`. No broken `[[old-note]]` links remain in active notes.

### TC-10: pending questions queue created for non-auto items
- **Precondition**: prune-scan identifies a superseded note (not stale+orphan — requires judgment).
- **Steps**: Agent writes finding to pending questions queue.
- **Expected**: `.squidsquad/vault/.pending-questions` file exists and contains an entry describing the superseded note in plain language (no vault internals like "galaxy", "frontmatter", "PARAG").
- **Verification**: Read `.squidsquad/vault/.pending-questions` — entry uses project-domain language, describes the note by topic, includes a "Skip for now" option.

### TC-11: PM check-in reports pending question count
- **Precondition**: `.squidsquad/vault/.pending-questions` contains 2 entries.
- **Steps**: PM runs its check-in step (Step 2 of Ralph Loop).
- **Expected**: Check-in message mentions pending vault questions with count: "2 vault questions pending".
- **Verification**: Observe PM check-in output — count matches file contents. Tone is calm (1-2 items).

### TC-12: Status bar icon with escalating urgency
- **Precondition**: `.squidsquad/vault/.pending-questions` contains varying numbers of entries.
- **Steps**: Check status bar rendering for counts 0, 1, 2, 3, 4, 5, 6.
- **Expected**:
  - 0: no icon
  - 1: `📝1`
  - 2: `📝2`
  - 3: `📝3🔥`
  - 4: `📝4🔥🔥`
  - 5: `📝5🔥🔥🔥🔥`
  - 6+: `📝6🔥🔥🔥🔥🔥🔥🔥🔥` (capped at 8 fires)
- **Verification**: Set pending-questions to each count level, read status bar output, compare against expected icon string. Formula: 2^(count-3) fires when count >= 3.

---

### Edge Cases

### TC-13: Circular wikilinks — both notes stale
- **Precondition**: Note A links to B, B links to A. Both have `updated` older than 60 days, both orphaned from rest of vault.
- **Steps**: Run `python references/scripts/vault_optimize.py prune-scan`
- **Expected**: Both notes presented as a group decision (not individual candidates). Output indicates circular reference detected.
- **Verification**: JSON output contains a `circular_group` or equivalent grouping with both note paths.

### TC-14: Frontmatter parse failure — graceful handling
- **Precondition**: A vault note with malformed frontmatter (e.g., multi-line values, colons in values).
- **Steps**: Run `python references/scripts/vault_optimize.py reindex`
- **Expected**: Note is flagged in the report as unparseable. NOT silently skipped. Other notes processed normally.
- **Verification**: Report JSON contains an `unparseable` or `errors` section listing the problematic note path and parse error.

### TC-15: Empty archives/ directory — first archive operation
- **Precondition**: `archives/` contains only `.gitkeep`. No previously archived notes.
- **Steps**: Archive a stale+orphan note.
- **Expected**: Note moved to `archives/` successfully. `.gitkeep` not disturbed. Directory handling does not error.
- **Verification**: `ls .squidsquad/vault/archives/` shows both `.gitkeep` and the archived note.

### TC-16: Grace period — today's notes never optimized
- **Precondition**: A note with `created: <today>` and zero inbound wikilinks (technically orphan).
- **Steps**: Run `python references/scripts/vault_optimize.py prune-scan`
- **Expected**: Today's note is NOT included in any prune candidate list despite being orphaned.
- **Verification**: Parse prune-scan JSON — no entry with today's date in `created` field.

### TC-17: Vault below threshold (< 20 notes)
- **Precondition**: Vault with 7 notes (current state).
- **Steps**: Run `python references/scripts/vault_optimize.py full-sweep`
- **Expected**: Script prints "Vault too small for optimization (7 notes, minimum 20)" and exits with code 0. No modifications made.
- **Verification**: Exit code is 0. No files modified (check `git status`).

### TC-18: Zero optimization candidates
- **Precondition**: Vault with 25 notes, all recently updated, all with inbound links, all healthy.
- **Steps**: Run `python references/scripts/vault_optimize.py full-sweep`
- **Expected**: Report indicates "Vault healthy — no optimization needed" for prune, consolidate, and decay sections. Reindex may still sync links. Relevance report still generated.
- **Verification**: JSON output has empty candidate lists for prune/consolidate/decay. Exit code 0.

### TC-19: Lock file prevents concurrent optimization
- **Precondition**: `.squidsquad/vault/.optimize-lock` already exists (another agent running).
- **Steps**: Run `python references/scripts/vault_optimize.py full-sweep`
- **Expected**: Script detects lock file, prints warning about concurrent optimization in progress, and exits without making changes. Non-zero exit code.
- **Verification**: No vault files modified. Lock file still present. Error message references the lock file.

### TC-20: Lock file cleanup on completion
- **Precondition**: No lock file exists.
- **Steps**: Run `python references/scripts/vault_optimize.py full-sweep` to completion.
- **Expected**: Lock file created at start, removed on completion. Not present after script finishes.
- **Verification**: After script exits, `ls .squidsquad/vault/.optimize-lock` returns "not found".

### TC-21: Lock file cleanup on script crash/error
- **Precondition**: Force a script error mid-execution (e.g., corrupt a note file that the script reads).
- **Steps**: Run `python references/scripts/vault_optimize.py full-sweep`
- **Expected**: Lock file is cleaned up even on error (try/finally or equivalent). Script exits with non-zero code.
- **Verification**: Lock file does not persist after a failed run.

### TC-22: Decay clock reset prevents cascading decay
- **Precondition**: Note decayed from `high` to `medium` in this optimize run.
- **Steps**: Run `python references/scripts/vault_optimize.py decay-apply` again immediately.
- **Expected**: Note is NOT decayed again (its `updated` was set to today during the first decay, so it is no longer past the 60-day threshold).
- **Verification**: Note still shows `confidence: medium` (not `low`). No additional changelog entry.

### TC-23: Area note exemption from pruning
- **Precondition**: An area note (`areas/human-profile.md`) with `updated` older than 60 days and zero inbound wikilinks.
- **Steps**: Run `python references/scripts/vault_optimize.py prune-scan`
- **Expected**: Area note is NOT included in prune candidates. Area notes and BRIEFING.md are exempt.
- **Verification**: Parse prune-scan JSON — no entry with path containing `areas/` or `BRIEFING.md`.

### TC-24: Plain language prompts — no vault internals exposed
- **Precondition**: Pending questions generated from prune-scan or consolidate-scan.
- **Steps**: Read `.squidsquad/vault/.pending-questions` entries.
- **Expected**: No references to "galaxy", "frontmatter", "wikilinks", "PARAG", "areas/", "galaxy/", "confidence field", or other vault internals. Notes described by topic and content.
- **Verification**: `grep -iE "galaxy|frontmatter|wikilink|PARAG|confidence field" .squidsquad/vault/.pending-questions` returns no matches.

### TC-25: Skip for now option on all prompts
- **Precondition**: Pending questions exist in the queue.
- **Steps**: Review each pending question entry.
- **Expected**: Every entry includes a "Skip for now" or equivalent deferral option.
- **Verification**: Each entry in `.pending-questions` contains a skip/defer option in its structure.

---

### Side Effect Regression Tests

### TC-26: vault-check still works unchanged after optimize install
- **Precondition**: Existing vault with notes. vault_optimize.py installed alongside vault_check.py.
- **Steps**: Run `python references/scripts/vault_check.py validate`
- **Expected**: All existing vault-check commands (validate, check-structure, check-frontmatter, check-wikilinks, list-orphans, dedup-check) produce identical output to pre-optimize behavior.
- **Verification**: Compare vault-check output before and after vault_optimize.py is added. No regressions.

### TC-27: vault-remember still works unchanged after optimize install
- **Precondition**: Existing vault. vault_optimize.py installed alongside vault_remember.py.
- **Steps**: Run `python references/scripts/vault_remember.py effective-confidence galaxy/some-note.md`, `decay-scan`, `note-count`, `is-quiet`, `write-budget`
- **Expected**: All vault-remember commands produce identical output. No import errors, no behavior changes.
- **Verification**: Compare vault-remember output before and after. No regressions.

### TC-28: vault-create and vault-update not affected
- **Precondition**: Working vault with optimize installed.
- **Steps**: Create a new galaxy note via vault-create. Update an existing note via vault-update.
- **Expected**: vault-check Level 1 runs automatically after each. No interference from optimize lock file (lock only exists during optimize runs). Notes created and updated normally.
- **Verification**: New note exists with correct frontmatter. Updated note has new changelog entry. No lock file present.

### TC-29: git history preserved on archive moves
- **Precondition**: A note `galaxy/decision-example.md` with several commits of history.
- **Steps**: Archive the note via vault-optimize.
- **Expected**: `git log --follow archives/decision-example.md` shows full history including pre-move commits. `git mv` was used (not manual copy+delete).
- **Verification**: `git log --follow --oneline archives/decision-example.md` — commit count matches or exceeds the pre-archive history count.

### TC-30: Wikilink rewrites after archive do not break other notes
- **Precondition**: Note C links to Note D via `[[note-d]]`. Note D is archived.
- **Steps**: Archive Note D. Run reindex.
- **Expected**: Note C's `[[note-d]]` is updated (annotated as archived or removed). No broken wikilinks remain in active notes.
- **Verification**: `grep -r '\[\[note-d\]\]' .squidsquad/vault/galaxy/ .squidsquad/vault/areas/ .squidsquad/vault/projects/` returns no results in active directories (or only annotated references).

### TC-31: Config file not corrupted by optimize additions
- **Precondition**: Existing `.squidsquad/config.md` with all current sections.
- **Steps**: Add the `## Vault Optimize` section to config.
- **Expected**: All existing config sections remain intact and parseable. `python references/scripts/config.py get vault-remember` still returns correct value.
- **Verification**: Run `python references/scripts/config.py get vault-remember` and other existing config reads — all return expected values.

---

### Upgrade Verification Tests

### TC-32: Fresh install — vault_optimize.py available
- **Precondition**: Clean clone of the repo after #18 is merged.
- **Steps**: Run `python references/scripts/vault_optimize.py --help` (or equivalent).
- **Expected**: Script is present, executable, and prints usage/help information.
- **Verification**: Exit code 0, help text includes all sub-commands (prune-scan, consolidate-scan, reindex, decay-apply, relevance-report, full-sweep).

### TC-33: Existing install without upgrade — graceful degradation
- **Precondition**: An existing install that does NOT have vault_optimize.py (pre-#18 code).
- **Steps**: Agent reads vault-optimize.md sub-skill which references `vault_optimize.py`.
- **Expected**: Agent checks for script existence before invoking. Falls back to vault-check Level 2 if script is absent. No crash, no unhandled error.
- **Verification**: Agent prints a message like "vault_optimize.py not found — falling back to vault-check Level 2" and continues normally.

### TC-34: Manifest and role files updated
- **Precondition**: Post-merge state of the repo.
- **Steps**: Check `references/sub-skills/manifest.md` for vault-optimize entry. Check role entry files for `{{include: common/vault-optimize}}`.
- **Expected**: vault-optimize listed in manifest. Role files include the sub-skill.
- **Verification**: `grep "vault-optimize" references/sub-skills/manifest.md` returns a match. `grep "vault-optimize" references/sub-skills/roles/dev-agent.md references/sub-skills/roles/pm-agent.md` returns matches.

### TC-35: Config section added with defaults
- **Precondition**: Post-merge config.md.
- **Steps**: Read `## Vault Optimize` section from `.squidsquad/config.md`.
- **Expected**: Section exists with: Enabled (yes), Auto-Prune Orphan+Stale (yes), minimum vault size (20), and other tuning knobs.
- **Verification**: `python references/scripts/config.py get vault-optimize` returns `yes` (or equivalent enabled check).

### TC-36: Relevance index file location
- **Precondition**: Run relevance-report at least once.
- **Steps**: Check for `.squidsquad/vault/.relevance-index.json`.
- **Expected**: File exists, is valid JSON, contains scored entries for all active vault notes.
- **Verification**: `python -m json.tool .squidsquad/vault/.relevance-index.json` exits 0.

---

## Smoke Tests

- [ ] `python references/scripts/vault_optimize.py prune-scan` exits 0 on a vault with < 20 notes (prints threshold message)
- [ ] `python references/scripts/vault_optimize.py reindex` exits 0 on a healthy vault (no fixes needed)
- [ ] `python references/scripts/vault_optimize.py decay-apply` exits 0 with no eligible notes
- [ ] `python references/scripts/vault_optimize.py relevance-report` produces valid JSON output
- [ ] `.squidsquad/vault/.relevance-index.json` is written after relevance-report
- [ ] Lock file created at start and removed at end of any sub-command
- [ ] `python references/scripts/vault_check.py validate` still passes after vault_optimize.py is installed
- [ ] `python references/scripts/vault_remember.py note-count` still returns correct count
- [ ] Status bar renders `📝N` icon when `.pending-questions` has entries
- [ ] Status bar shows no vault icon when `.pending-questions` is empty or absent

## Regression Risks

- **vault-check import breakage**: If vault_optimize.py shares utility functions with vault_check.py (e.g., `_get_all_notes()`, `_parse_frontmatter()`), changes to shared code could break vault-check. Watch for import errors or changed return formats.
- **vault-remember decay-scan divergence**: vault_optimize.py decay-apply must use the same decay logic as vault_remember.py effective-confidence. If the formulas diverge, notes may show different confidence values depending on which script is queried.
- **git mv on Windows**: `git mv` behavior may differ on Windows (path separators, case sensitivity). Test archive moves on Windows explicitly.
- **Lock file stale after crash**: If the script crashes without cleanup, the lock file persists and blocks all future optimize runs. Must have try/finally cleanup AND a staleness check (e.g., lock file older than 10 minutes = stale, safe to override).
- **Concurrent vault-remember + vault-optimize**: vault-remember creates notes every cycle. If vault-optimize runs simultaneously and archives a note that vault-remember just created (within the grace period window), the grace period check must use `created` date, not filesystem mtime.
- **Reindex wikilink rewrite scope**: Reindex rewrites `links` frontmatter across ALL notes. A bug in the rewrite logic could corrupt frontmatter vault-wide. Reindex should write a dry-run report first, then apply.
- **Pending questions file format**: If the file format is not well-defined, different agents may write incompatible entries. The dev agent should document the format clearly.
- **Status bar performance**: Reading and parsing `.pending-questions` on every status bar refresh must be fast. A large queue (unlikely but possible) should not slow the status bar.
- **Config.py compatibility**: Adding a new `## Vault Optimize` section must not break existing config parsing. Test that all existing `config.py get` calls still work.
