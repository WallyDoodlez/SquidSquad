# FEAT-PM-475 Test Plan — Token Efficiency Audit

## Overview

This test plan covers three changes to agent instruction templates:

1. **Change A**: Remove `boot-remote-agents` sub-skill from non-PM role includes (QA, Skill/Dev, DM, Designer)
2. **Change B**: Extract Label Taxonomy from `tracker-protocol` to a reference file (`references/docs/label-taxonomy.md`)
3. **Change C**: Compress `vault-protocol` inline (condense entity model table, search modes, vault-check Level 2)

All changes propagate via `compose.py deploy-all`. No behavioral changes to agents — only instruction density changes. Safety-critical sections (prohibitions, zero-gap gate, approval gates) are explicitly untouched.

---

## Section 1: Happy Path Test Cases

### TC-1: boot-remote-agents removed from QA includes.yml

- **Precondition**: Clean repo on main branch. Current `references/roles/qa/includes.yml` contains `common/boot-remote-agents`.
- **Steps**:
  1. Open `references/roles/qa/includes.yml`
  2. Verify the line `- common/boot-remote-agents` has been removed
  3. Run `python references/scripts/compose.py deploy-all`
  4. Read the composed `.squidsquad/qa/CLAUDE.md`
- **Expected**: The composed QA CLAUDE.md does NOT contain the "Boot Remote Agents" step section. No `<!-- sub-skill: boot-remote-agents -->` markers present.
- **Verification**:
  ```bash
  grep -c "boot-remote-agents" references/roles/qa/includes.yml  # expect 0
  python references/scripts/compose.py deploy-all
  grep -c "Boot Remote Agents" .squidsquad/qa/CLAUDE.md  # expect 0
  grep -c "boot-remote-agents" .squidsquad/qa/CLAUDE.md  # expect 0
  ```

### TC-2: boot-remote-agents removed from Dev/Skill includes.yml

- **Precondition**: Same as TC-1, for `references/roles/dev/includes.yml`.
- **Steps**:
  1. Verify `- common/boot-remote-agents` removed from `references/roles/dev/includes.yml`
  2. Run `python references/scripts/compose.py deploy-all`
  3. Read the composed `.squidsquad/skill/CLAUDE.md` (dev variant)
- **Expected**: Composed skill CLAUDE.md has no boot-remote-agents section.
- **Verification**:
  ```bash
  grep -c "boot-remote-agents" references/roles/dev/includes.yml  # expect 0
  python references/scripts/compose.py deploy-all
  grep -c "Boot Remote Agents" .squidsquad/skill/CLAUDE.md  # expect 0
  ```

### TC-3: boot-remote-agents removed from DM includes.yml

- **Precondition**: Same as TC-1, for `references/roles/dm/includes.yml`.
- **Steps**:
  1. Verify `- common/boot-remote-agents` removed from `references/roles/dm/includes.yml`
  2. Run `python references/scripts/compose.py deploy-all`
  3. Read the composed `.squidsquad/dm/CLAUDE.md` (if DM is active)
- **Expected**: Composed DM CLAUDE.md has no boot-remote-agents section.
- **Verification**:
  ```bash
  grep -c "boot-remote-agents" references/roles/dm/includes.yml  # expect 0
  ```

### TC-4: boot-remote-agents removed from Designer includes.yml

- **Precondition**: Same as TC-1, for `references/roles/designer/includes.yml`.
- **Steps**:
  1. Verify `- common/boot-remote-agents` removed from `references/roles/designer/includes.yml`
  2. Run `python references/scripts/compose.py deploy-all`
- **Expected**: Composed designer CLAUDE.md has no boot-remote-agents section.
- **Verification**:
  ```bash
  grep -c "boot-remote-agents" references/roles/designer/includes.yml  # expect 0
  ```

### TC-5: boot-remote-agents RETAINED in PM includes.yml

- **Precondition**: `references/roles/pm/includes.yml` still contains `- common/boot-remote-agents`.
- **Steps**:
  1. Verify the line exists in PM's includes.yml
  2. Run `python references/scripts/compose.py deploy-all`
  3. Read composed `.squidsquad/pm/CLAUDE.md`
- **Expected**: PM's composed CLAUDE.md still contains the full "Boot Remote Agents" step, including the PM-only gate, boot_remote.py command, and output interpretation instructions.
- **Verification**:
  ```bash
  grep -c "boot-remote-agents" references/roles/pm/includes.yml  # expect 1
  grep -c "Boot Remote Agents" .squidsquad/pm/CLAUDE.md  # expect >= 1
  grep "boot_remote.py" .squidsquad/pm/CLAUDE.md  # should find the command
  ```

### TC-6: Label Taxonomy extracted to reference file

- **Precondition**: `references/docs/label-taxonomy.md` does not yet exist (or wherever dev places it).
- **Steps**:
  1. Verify `references/docs/label-taxonomy.md` (or equivalent) exists and contains the full Label Taxonomy (Type, Priority, Status, Role, Design, Severity, Special labels)
  2. Verify `references/sub-skills/common/tracker-protocol.md` no longer contains the inline Label Taxonomy section
  3. Run `python references/scripts/compose.py deploy-all`
  4. Check all 5 composed CLAUDE.md files
- **Expected**:
  - The reference file contains ALL label definitions verbatim from the original taxonomy
  - tracker-protocol.md either omits the taxonomy entirely or contains a brief pointer (e.g., "See `references/docs/label-taxonomy.md` for the full label list")
  - All composed CLAUDE.md files reflect the trimmed tracker-protocol
- **Verification**:
  ```bash
  # Reference file exists and has all label categories
  grep -c "priority:high" references/docs/label-taxonomy.md  # expect 1
  grep -c "status:in-progress" references/docs/label-taxonomy.md  # expect 1
  grep -c "severity:high" references/docs/label-taxonomy.md  # expect 1
  grep -c "role:skill" references/docs/label-taxonomy.md  # expect 1
  grep -c "design:needed" references/docs/label-taxonomy.md  # expect 1
  grep -c "improvement-scan" references/docs/label-taxonomy.md  # expect 1

  # tracker-protocol.md no longer has full taxonomy inline
  grep -c "priority:high" references/sub-skills/common/tracker-protocol.md  # expect 0 (or 1 if pointer kept)
  grep -c "status:pending-ship" references/sub-skills/common/tracker-protocol.md  # expect 0

  # Composed templates also lack the inline taxonomy
  grep -c "priority:low — nice-to-have" .squidsquad/pm/CLAUDE.md  # expect 0
  grep -c "priority:low — nice-to-have" .squidsquad/qa/CLAUDE.md  # expect 0
  ```

### TC-7: Vault-protocol entity model condensed

- **Precondition**: `references/sub-skills/common/vault-protocol.md` currently has a 9-row Entity Model table.
- **Steps**:
  1. Read the modified `vault-protocol.md`
  2. Check that the entity model is condensed (terse summary or pointer to reference)
  3. Run `python references/scripts/compose.py deploy-all`
  4. Check PM and skill/dev composed CLAUDE.md files
- **Expected**: The entity model section is significantly shorter (summary or pointer). Full vault-protocol roles (PM, dev/skill) show the condensed version. vault-protocol-slim (QA, DM, designer) is unchanged.
- **Verification**:
  ```bash
  # vault-protocol.md is shorter
  wc -l references/sub-skills/common/vault-protocol.md  # expect < 180 (was 200)
  wc -w references/sub-skills/common/vault-protocol.md  # expect < 1500 (was 1712)

  # vault-protocol-slim is untouched
  wc -l references/sub-skills/common/vault-protocol-slim.md  # expect 44 (unchanged)
  ```

### TC-8: Vault-protocol search modes condensed

- **Precondition**: vault-protocol.md currently has 4 search modes with full bash examples (~30 lines).
- **Steps**:
  1. Read modified vault-protocol.md
  2. Verify search modes are condensed but still present (all 4 modes: by tag, by type, by keyword, by wikilink traversal)
- **Expected**: All 4 search mode names are still mentioned. Bash examples may be reduced to 1-2 lines each or collapsed. The section is shorter but functionally equivalent.
- **Verification**:
  ```bash
  grep -c "By tag" references/sub-skills/common/vault-protocol.md  # expect 1
  grep -c "By type" references/sub-skills/common/vault-protocol.md  # expect 1
  grep -c "By keyword" references/sub-skills/common/vault-protocol.md  # expect 1
  grep -c "wikilink traversal" references/sub-skills/common/vault-protocol.md  # expect 1
  ```

### TC-9: Vault-check Level 2 condensed

- **Precondition**: vault-protocol.md currently has a detailed Level 2 section (~20 lines) with orphan check bash snippet.
- **Steps**:
  1. Read modified vault-protocol.md
  2. Verify Level 2 is condensed to a terse summary or pointer
- **Expected**: Level 2 is mentioned (agents must know it exists and what it does), but detailed steps and bash snippets are moved to a reference file or significantly shortened.
- **Verification**:
  ```bash
  grep -c "Level 2" references/sub-skills/common/vault-protocol.md  # expect >= 1
  # The orphan check bash snippet should be gone or shortened
  grep -c "for f in .squidsquad/vault/galaxy" references/sub-skills/common/vault-protocol.md  # expect 0
  ```

### TC-10: compose.py deploy-all succeeds without errors

- **Precondition**: All three changes applied.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`
  2. Check exit code
  3. Verify all composed CLAUDE.md files are written
- **Expected**: Exit code 0. No ERROR lines in output. All role CLAUDE.md files updated.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all 2>&1
  echo "Exit code: $?"  # expect 0
  ls -la .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/skill/CLAUDE.md
  ```

---

## Section 2: Comprehension Tests (Per Changed Sub-Skill)

These tests spawn a fresh agent and quiz it on key behaviors to verify the trimmed instructions are still comprehensible. Each test case describes the quiz questions, the expected correct answers, and how to score.

### TC-11: Comprehension — tracker-protocol (Label Taxonomy removed)

- **Precondition**: A fresh agent session using a composed CLAUDE.md where the Label Taxonomy has been extracted.
- **Method**: Spawn a fresh agent with the role's CLAUDE.md. Ask it the following questions. Record its answers.
- **Quiz Questions**:
  1. "You need to file a bug you found during testing. What command do you run, and what labels get applied?"
     - **Expected**: Agent uses `python references/scripts/tracker.py create-issue` with `--severity` flag. Agent does NOT try to construct `gh issue create` with manual labels. Agent knows the script handles label construction.
  2. "What labels does an issue get when you file it via tracker.py?"
     - **Expected**: Agent says the script automatically adds `ISSUE:` prefix, correct labels, and `squidsquad` tag. Agent may or may not remember exact label names — this is acceptable since tracker.py enforces them. Agent should NOT list incorrect label names.
  3. "What status values can a task go through?"
     - **Expected**: Agent mentions the progression: Pending -> Planning -> Planned -> Approved -> In Progress -> Pending Test -> Pending Ship -> Shipped. Agent may consult the reference file or state it relies on tracker.py for transitions.
  4. "Can you transition an issue from pending-test directly to shipped?"
     - **Expected**: Agent says NO — this is an illegal transition. tracker.py would reject it. Must go through pending-ship first.
- **Pass criteria**: Questions 1, 3, and 4 must be answered correctly. Question 2 is a soft check — agent may defer to tracker.py, which is acceptable.
- **Fail action**: If the agent constructs raw `gh` commands instead of using tracker.py, or states incorrect transition flows, the trimming went too far.

### TC-12: Comprehension — tracker-protocol (Status Transitions preserved)

- **Precondition**: Fresh agent with trimmed tracker-protocol.
- **Quiz Questions**:
  1. "You are the QA agent. An issue is in pending-test. What transitions can you perform?"
     - **Expected**: Agent can transition `pending-test -> in-progress` (reject) or `pending-test -> pending-ship` (verify). Agent knows it is authorized as QA for these transitions.
  2. "You are a dev agent (skill-lead). Can you transition an issue from pending-test to pending-ship?"
     - **Expected**: Agent says NO — only PM or QA can do that. Dev agents are unauthorized for that transition.
  3. "How do you add a discussion comment to issue #42?"
     - **Expected**: Agent uses `python references/scripts/tracker.py comment 42 --role [role]-lead --message "[message]"`. Does NOT use raw `gh issue comment`.
- **Pass criteria**: All 3 must be correct. The legal flows and role authority sections are the most critical part of tracker-protocol — they MUST survive trimming.

### TC-13: Comprehension — vault-protocol (entity model condensed)

- **Precondition**: Fresh agent (PM or skill/dev role) with condensed vault-protocol.
- **Quiz Questions**:
  1. "You want to record a decision the human made about using REST over GraphQL. Where do you put it and what do you name the file?"
     - **Expected**: Agent says `galaxy/decision-use-rest-over-graphql.md` (or similar kebab-case with `decision-` prefix). Agent knows galaxy/ is for atomic knowledge notes.
  2. "After creating a vault note, what must you do?"
     - **Expected**: Agent says run vault-check Level 1. It runs automatically after every vault-create or vault-update. Agent mentions checking the written note and 2-hop neighborhood.
  3. "What are the valid galaxy note type prefixes?"
     - **Expected**: Agent lists `decision-`, `pattern-`, `learning-`, `style-`. Agent may mention that new prefixes can be introduced if documented.
  4. "Where does the human's communication style preference go?"
     - **Expected**: Agent says `areas/human-profile.md`. Agent knows areas/ is for ongoing concerns.
- **Pass criteria**: All 4 must be correct. If the agent cannot map entity types to folders, the entity model was trimmed too aggressively.

### TC-14: Comprehension — vault-protocol (search modes condensed)

- **Precondition**: Fresh agent (PM or skill/dev role) with condensed vault-protocol.
- **Quiz Questions**:
  1. "How do you find all vault notes tagged with 'architecture'?"
     - **Expected**: Agent uses `grep -rl "tags:.*\barchitecture\b" .squidsquad/vault/ --include="*.md"` or describes searching by tag. Agent knows the vault-search interface.
  2. "How do you find all notes that link TO a specific note called 'decision-rest-api'?"
     - **Expected**: Agent uses `grep -rl '\[\[decision-rest-api\]\]' .squidsquad/vault/ --include="*.md"`. Agent understands inbound wikilink traversal.
  3. "What is the maximum number of search results you should return?"
     - **Expected**: Agent says 10, sorted by most recently updated.
- **Pass criteria**: Questions 1 and 2 must be correct. Question 3 is a soft check. If the agent cannot describe any search mode, the condensation was too aggressive.

### TC-15: Comprehension — vault-protocol (vault-check Level 2 condensed)

- **Precondition**: Fresh agent with condensed vault-protocol.
- **Quiz Questions**:
  1. "What is the difference between vault-check Level 1 and Level 2?"
     - **Expected**: Agent says Level 1 is automatic after every write (single note + 2-hop), Level 2 is on-demand (full vault sweep). Agent mentions orphan detection, staleness detection, broken link census as Level 2 features.
  2. "When does vault-check Level 1 run?"
     - **Expected**: Agent says after every vault-create and vault-update. Automatic, not manual.
  3. "What frontmatter fields are required on every vault note?"
     - **Expected**: Agent lists `type`, `tags`, `created`, `updated`, `owner`, `status`, `confidence`. All 7 required.
- **Pass criteria**: All 3 must be correct. vault-check Level 1 auto-run is a critical rule that must survive condensation.

### TC-16: Comprehension — boot-remote-agents removal (QA agent)

- **Precondition**: Fresh QA agent session with composed CLAUDE.md that no longer includes boot-remote-agents.
- **Quiz Questions**:
  1. "You are the QA agent. Do you boot other agents?"
     - **Expected**: Agent says NO. It has no boot-remote-agents step. It does not reference boot_remote.py.
  2. "What are your Ralph Loop steps?"
     - **Expected**: Agent lists its steps (pull, context pressure, resume state, verification, improvement scan, iteration log, git commit, self-restart, done). Does NOT mention "Boot Remote Agents". No confusion about a missing step.
  3. "Can you spawn new terminal sessions for other agents?"
     - **Expected**: Agent says NO — that is not part of its responsibilities.
- **Pass criteria**: All 3 must be correct. Agent must not hallucinate a boot step or reference boot_remote.py.

### TC-17: Comprehension — boot-remote-agents removal (Dev/Skill agent)

- **Precondition**: Fresh skill agent session with composed CLAUDE.md lacking boot-remote-agents.
- **Quiz Questions**:
  1. "You are the skill agent. A fellow agent seems stalled. What do you do?"
     - **Expected**: Agent says it would comment on the stalled agent's issue or note it in the iteration log. It does NOT try to boot/spawn the agent. It may mention that PM handles agent health checks.
  2. "Do you have access to boot_remote.py?"
     - **Expected**: Agent says NO or indicates it has no instructions for that script. It does NOT reference the script.
- **Pass criteria**: Both must be correct.

---

## Section 3: Behavioral Regression Tests

These verify that agent behavior is identical before and after trimming for scenarios where the trimmed content was previously used.

### TC-18: tracker.py still enforces label format (no agent memorization needed)

- **Precondition**: Label Taxonomy extracted from tracker-protocol.
- **Steps**:
  1. Run `python references/scripts/tracker.py create-issue --title "Test issue" --body "test" --role skill --severity medium --reporter pm-lead`
  2. Check the labels on the created issue
- **Expected**: Issue is created with correct labels (`issue`, `severity:medium`, `role:skill`, `squidsquad`, `status:open`) regardless of whether the agent's CLAUDE.md contains the full taxonomy. tracker.py enforces this programmatically.
- **Verification**:
  ```bash
  python references/scripts/tracker.py create-issue --title "TESTONLY: label check" --body "Delete after test" --role skill --severity low --reporter pm-lead
  # Check output JSON for correct labels
  # Clean up: close the test issue
  ```

### TC-19: tracker.py still rejects illegal transitions

- **Precondition**: An open issue exists.
- **Steps**:
  1. Attempt `python references/scripts/tracker.py transition [NUMBER] open shipped --role pm-lead`
- **Expected**: Script rejects with an illegal transition error. Exit code non-zero.
- **Verification**:
  ```bash
  python references/scripts/tracker.py transition [NUMBER] open shipped --role pm-lead 2>&1
  echo "Exit code: $?"  # expect non-zero
  ```

### TC-20: tracker.py still rejects unauthorized transitions

- **Precondition**: An issue exists with `status:pending-test`.
- **Steps**:
  1. Attempt `python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role skill-lead`
- **Expected**: Script rejects — skill-lead is not authorized for pending-test -> pending-ship (only PM or QA). Exit code non-zero.
- **Verification**:
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role skill-lead 2>&1
  echo "Exit code: $?"  # expect non-zero
  ```

### TC-21: PM boot-remote-agents step still functions

- **Precondition**: PM CLAUDE.md still contains boot-remote-agents.
- **Steps**:
  1. Read composed `.squidsquad/pm/CLAUDE.md`
  2. Verify it contains the full boot-remote-agents step
  3. Verify it contains the PM-only gate, `boot_remote.py --all --json` command, output interpretation, and spawn logging
- **Expected**: PM template is functionally identical to pre-change for boot-remote-agents.
- **Verification**:
  ```bash
  grep "PM-only gate" .squidsquad/pm/CLAUDE.md  # expect match
  grep "boot_remote.py --all --json" .squidsquad/pm/CLAUDE.md  # expect match
  grep "Interpreting output" .squidsquad/pm/CLAUDE.md  # expect match
  ```

### TC-22: vault-protocol-slim NOT modified

- **Precondition**: vault-protocol-slim.md was explicitly out-of-scope per CONTEXT.md.
- **Steps**:
  1. Compare `references/sub-skills/common/vault-protocol-slim.md` with its pre-change content
  2. Check word count
- **Expected**: File is byte-identical to pre-change. 44 lines, 263 words.
- **Verification**:
  ```bash
  wc -l references/sub-skills/common/vault-protocol-slim.md  # expect 44 or 45
  git diff HEAD -- references/sub-skills/common/vault-protocol-slim.md  # expect no diff
  ```

### TC-23: Prohibitions section untouched across all roles

- **Precondition**: Prohibitions are safety-critical and must NEVER be trimmed.
- **Steps**:
  1. For each role's composed CLAUDE.md, verify the prohibitions section exists
  2. Verify key prohibition lines are present
- **Expected**: Every role CLAUDE.md still contains its prohibitions section. Key lines like "Never approve a task without explicit human confirmation" (PM), "Never implement code changes" (QA), etc. are present.
- **Verification**:
  ```bash
  # PM
  grep "What You Must Never Do" .squidsquad/pm/CLAUDE.md  # expect match
  grep "Never approve a task" .squidsquad/pm/CLAUDE.md  # expect match

  # QA (check role-specific prohibitions)
  grep -i "prohibit\|must never" .squidsquad/qa/CLAUDE.md  # expect matches

  # Skill/Dev
  grep -i "prohibit\|must never" .squidsquad/skill/CLAUDE.md  # expect matches
  ```

### TC-24: Zero-gap gate untouched

- **Precondition**: Zero-gap gate is process-critical.
- **Steps**:
  1. Search all composed CLAUDE.md files for "zero-gap" or "Zero-gap"
- **Expected**: The zero-gap gate text is present and unmodified in all roles that had it (PM, QA).
- **Verification**:
  ```bash
  grep -i "zero-gap" .squidsquad/pm/CLAUDE.md  # expect match
  ```

### TC-25: Approval gates untouched

- **Precondition**: Approval gates are process-critical.
- **Steps**:
  1. Search PM CLAUDE.md for task approval gate content
- **Expected**: "Tasks start as Pending — a human must explicitly approve them" text is present. Full status progression is documented.
- **Verification**:
  ```bash
  grep "human must explicitly approve" .squidsquad/pm/CLAUDE.md  # expect match
  ```

### TC-26: vault-create still triggers vault-check Level 1

- **Precondition**: Condensed vault-protocol in PM/dev CLAUDE.md.
- **Steps**:
  1. Search composed vault-protocol section for the Level 1 auto-run rule
- **Expected**: The rule "vault-check Level 1 runs after every write" or equivalent is still present in the composed template. This is a critical operational rule.
- **Verification**:
  ```bash
  grep -i "vault-check.*Level 1.*after every" .squidsquad/pm/CLAUDE.md  # expect match
  grep -i "vault-check.*Level 1.*after every" .squidsquad/skill/CLAUDE.md  # expect match
  ```

### TC-27: vault-update "never delete content" rule preserved

- **Precondition**: Condensed vault-protocol.
- **Steps**:
  1. Search for the "never delete content" / "vault-update never deletes" rule
- **Expected**: The rule is present. This is a safety rule preventing data loss.
- **Verification**:
  ```bash
  grep -i "never delete" references/sub-skills/common/vault-protocol.md  # expect match
  ```

### TC-28: BRIEFING.md section preserved in vault-protocol

- **Precondition**: BRIEFING.md is the agent's startup context. Must not be trimmed.
- **Steps**:
  1. Check vault-protocol.md for the BRIEFING.md section
- **Expected**: BRIEFING.md description (~4 lines) is present and unmodified. Agents must know to read it at session start.
- **Verification**:
  ```bash
  grep "BRIEFING.md" references/sub-skills/common/vault-protocol.md  # expect match
  grep "~50 line summary" references/sub-skills/common/vault-protocol.md  # expect match
  ```

---

## Section 4: Edge Case Test Cases

### TC-29: New role added after taxonomy extraction

- **Precondition**: A hypothetical new role is added with a new `includes.yml` referencing `common/tracker-protocol`.
- **Steps**:
  1. Create a minimal test `includes.yml` with just `common/tracker-protocol`
  2. Run compose on this role
  3. Check that the composed output contains tracker-protocol without inline Label Taxonomy
- **Expected**: The new role gets the trimmed tracker-protocol. No error. The role can function using tracker.py for label construction. If the dev added a pointer to the reference file, the new role's CLAUDE.md mentions where to find the taxonomy.
- **Verification**: Manual review of composed output.

### TC-30: Agent constructs labels manually (regression risk)

- **Precondition**: Label Taxonomy extracted. An agent might try to construct `gh issue create` with manual labels instead of using tracker.py.
- **Steps**:
  1. In the trimmed tracker-protocol, verify the instruction "Use the tracker script for all queries — it encodes correct label formats" is still present
  2. In the "Creating Issues" section, verify the tracker.py commands are still shown
- **Expected**: The instruction to use tracker.py is present. The `create-issue` and `create-task` commands with their flags are documented. Agents should never need to know exact label strings — they pass `--severity`, `--priority`, `--role` flags.
- **Verification**:
  ```bash
  grep "tracker script for all queries" references/sub-skills/common/tracker-protocol.md  # expect match
  grep "create-issue" references/sub-skills/common/tracker-protocol.md  # expect match
  grep "create-task" references/sub-skills/common/tracker-protocol.md  # expect match
  ```

### TC-31: vault-protocol too terse — agent cannot determine folder for note type

- **Precondition**: Entity model condensed to a brief summary.
- **Steps**:
  1. Spawn a fresh PM agent with condensed vault-protocol
  2. Ask: "You learned that the team uses tabs not spaces. Where does this go in the vault?"
- **Expected**: Agent says `areas/code-conventions.md` or creates a galaxy note like `galaxy/style-tabs-over-spaces.md`. Agent must be able to map note types to folders even with condensed entity model. If agent is confused or picks the wrong folder, the condensation is too aggressive.
- **Pass criteria**: Agent picks an appropriate folder. Either areas/ (ongoing concern) or galaxy/ (with a style- prefix) is acceptable.

### TC-32: Reference file missing at runtime

- **Precondition**: Label taxonomy reference file extracted, but hypothetically the file is deleted or missing.
- **Steps**:
  1. Check if tracker-protocol instructs agents to `cat` the reference file, or just omits taxonomy
  2. If agents are told to `cat` — what happens if the file is missing?
- **Expected**: If the tracker-protocol tells agents to `cat references/docs/label-taxonomy.md`, the `cat` command would fail with a file-not-found error. The agent should still function because tracker.py programmatically enforces labels. The agent can file issues and tasks without knowing the exact label strings.
- **Verification**: Confirm tracker.py `create-issue` and `create-task` work regardless of reference file presence:
  ```bash
  python references/scripts/tracker.py create-issue --help  # should show flags
  ```

### TC-33: Concurrent vault writes after vault-protocol compression

- **Precondition**: Condensed vault-protocol. Multiple agents writing to vault simultaneously.
- **Steps**:
  1. Verify the "Concurrent Access" section is still present in vault-protocol.md
  2. Verify the conflict resolution rule ("Keep both versions") is present
- **Expected**: Concurrent access rules are preserved. These are operational rules, not reference data.
- **Verification**:
  ```bash
  grep "Concurrent Access" references/sub-skills/common/vault-protocol.md  # expect match
  grep "Keep both versions" references/sub-skills/common/vault-protocol.md  # expect match
  ```

### TC-34: compose.py handles removed include gracefully

- **Precondition**: boot-remote-agents removed from non-PM includes.yml. The `{{include: common/boot-remote-agents}}` directive exists in the role entry file (e.g., `references/roles/qa/CLAUDE.md`) but is no longer in the manifest.
- **Steps**:
  1. Check if the `{{include: common/boot-remote-agents}}` line in the role's `CLAUDE.md` entry file needs to be removed or if compose.py skips it when the manifest doesn't list it
  2. Run `python references/scripts/compose.py deploy-all`
- **Expected**: compose.py either (a) skips includes not in the manifest, or (b) the entry file's include line has also been removed. Either way, no error and boot-remote-agents content does not appear in the composed output.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all 2>&1 | grep -i "error"  # expect no errors
  ```

### TC-35: Skill role inherits from dev manifest correctly

- **Precondition**: Skill role uses the `dev` role template via `references/roles/dev/includes.yml`. The `skill` role does not have its own `includes.yml`.
- **Steps**:
  1. Verify `references/roles/skill/includes.yml` does NOT exist (or if it does, that it also lacks boot-remote-agents)
  2. Run `python references/scripts/compose.py deploy-all`
  3. Check composed `.squidsquad/skill/CLAUDE.md`
- **Expected**: Skill role inherits the modified dev manifest (without boot-remote-agents). Composed output for skill matches dev template behavior.
- **Verification**:
  ```bash
  ls references/roles/skill/includes.yml 2>/dev/null; echo "exit: $?"  # expect file not found
  grep -c "boot-remote-agents" .squidsquad/skill/CLAUDE.md  # expect 0
  ```

---

## Section 5: Token Count Verification

### TC-36: Per-role token savings match estimates

- **Precondition**: All three changes applied. `compose.py deploy-all` run.
- **Steps**:
  1. Count words in each composed CLAUDE.md (before and after)
  2. Compare with research estimates
- **Expected savings** (from CONTEXT.md and RESEARCH.md):
  - boot-remote-agents removal: ~160 words per non-PM role, ~640 words total across 4 roles
  - Label Taxonomy extraction: ~300 words per role, ~1,500 words total across 5 roles
  - vault-protocol compression: ~500 words per vault-protocol inclusion (PM, dev/skill), ~1,000 words total
  - **Total estimated**: ~3,140 words (~4,082 tokens at 1.3x)
- **Verification**:
  ```bash
  # Before (baseline from research):
  # pm: 11,056 words, qa: 4,854, skill: 7,633, dm: 4,379
  # Total: 27,922 words

  # After:
  wc -w .squidsquad/pm/CLAUDE.md     # expect ~10,200 (saved ~860: 300 taxonomy + 500 vault + 60 other)
  wc -w .squidsquad/qa/CLAUDE.md     # expect ~4,394 (saved ~460: 300 taxonomy + 160 boot)
  wc -w .squidsquad/skill/CLAUDE.md  # expect ~6,673 (saved ~960: 300 taxonomy + 160 boot + 500 vault)

  # Total words across active roles
  # Expected total savings: ~3,000-3,200 words
  ```

### TC-37: Token savings are >= 10% of total baseline

- **Precondition**: Word counts from TC-36 collected.
- **Steps**:
  1. Calculate total words after changes
  2. Calculate percentage reduction
- **Expected**: Total reduction >= 10% (target was ~11% per CONTEXT.md). Minimum acceptable: 8% (accounting for dev discretion in wording).
- **Verification**: Manual calculation from TC-36 word counts.

### TC-38: No role INCREASED in word count

- **Precondition**: All changes are reductions.
- **Steps**:
  1. Compare each role's word count before and after
- **Expected**: Every role's word count decreased or stayed the same. No role increased.
- **Verification**:
  ```bash
  # Compare against baselines from research:
  # pm: 11,056, qa: 4,854, skill: 7,633, dm: 4,379
  for f in .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/skill/CLAUDE.md; do
    echo "$f: $(wc -w < $f) words"
  done
  ```

---

## Section 6: Upgrade Verification Tests

### TC-39: compose.py deploy-all regenerates all CLAUDE.md files

- **Precondition**: Changes applied to sub-skill files and includes.yml. Existing CLAUDE.md files from previous version.
- **Steps**:
  1. Note timestamps of existing CLAUDE.md files
  2. Run `python references/scripts/compose.py deploy-all`
  3. Note new timestamps
- **Expected**: All CLAUDE.md files have updated timestamps. Content reflects the changes.
- **Verification**:
  ```bash
  ls -la .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/skill/CLAUDE.md
  python references/scripts/compose.py deploy-all
  ls -la .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/skill/CLAUDE.md
  # Timestamps should be newer
  ```

### TC-40: Existing install without recompose continues working

- **Precondition**: An install that has NOT run `compose.py deploy-all` after the changes.
- **Steps**:
  1. Verify that the old CLAUDE.md files (verbose version) still function
  2. Agents booted with old templates should behave identically to before
- **Expected**: Graceful degradation. Old templates work fine — they are just less token-efficient. No breakage, no missing instructions. The boot-remote-agents PM-only gate already prevented non-PM execution, so old templates with the step included are harmless.
- **Verification**: This is verified by inspection — the sub-skill file changes are additive removals only. No new required instructions were added that old templates would lack.

### TC-41: No new config values required

- **Precondition**: CONTEXT.md states no new config values.
- **Steps**:
  1. Search all changed files for references to new config.md fields
  2. Check if compose.py needs any new configuration
- **Expected**: No new config fields. `config.md` schema unchanged.
- **Verification**:
  ```bash
  grep -r "config.md" references/sub-skills/common/vault-protocol.md  # check for new config refs
  # Should find only existing references (vault-remember, etc.)
  ```

### TC-42: Reference file is accessible from all agent clone paths

- **Precondition**: Label taxonomy extracted to `references/docs/label-taxonomy.md`. Agents may run in separate clone directories.
- **Steps**:
  1. Verify the reference file is under `references/` (which is shared across clones via git)
  2. Verify it is tracked by git
- **Expected**: The file is git-tracked and will be available in all clones after a `git pull`.
- **Verification**:
  ```bash
  git ls-files references/docs/label-taxonomy.md  # expect the file path (tracked)
  ```

---

## Section 7: Cross-Role Consistency Tests

### TC-43: All roles share identical tracker-protocol (minus taxonomy)

- **Precondition**: All changes applied, deploy-all run.
- **Steps**:
  1. Extract the tracker-protocol section from each composed CLAUDE.md
  2. Compare them
- **Expected**: The tracker-protocol section is identical across all 5 roles (PM, QA, skill, DM, designer). All share the same trimmed version.
- **Verification**:
  ```bash
  # Extract tracker-protocol sections and compare
  grep -A 200 "sub-skill: tracker-protocol" .squidsquad/pm/CLAUDE.md | grep -B 200 "/sub-skill: tracker-protocol" > /tmp/tp-pm.txt
  grep -A 200 "sub-skill: tracker-protocol" .squidsquad/qa/CLAUDE.md | grep -B 200 "/sub-skill: tracker-protocol" > /tmp/tp-qa.txt
  diff /tmp/tp-pm.txt /tmp/tp-qa.txt  # expect no diff
  ```

### TC-44: PM and Dev/Skill share identical vault-protocol (condensed)

- **Precondition**: Condensed vault-protocol applies to PM and dev roles.
- **Steps**:
  1. Extract vault-protocol section from PM and skill composed CLAUDE.md
  2. Compare them
- **Expected**: Identical vault-protocol content in both.
- **Verification**:
  ```bash
  grep -A 300 "sub-skill: vault-protocol" .squidsquad/pm/CLAUDE.md | grep -B 300 "/sub-skill: vault-protocol" > /tmp/vp-pm.txt
  grep -A 300 "sub-skill: vault-protocol" .squidsquad/skill/CLAUDE.md | grep -B 300 "/sub-skill: vault-protocol" > /tmp/vp-skill.txt
  diff /tmp/vp-pm.txt /tmp/vp-skill.txt  # expect no diff
  ```

### TC-45: QA, DM, Designer still use vault-protocol-slim (unchanged)

- **Precondition**: vault-protocol-slim is out-of-scope and should be untouched.
- **Steps**:
  1. Check QA, DM, designer composed CLAUDE.md for vault-protocol section
- **Expected**: They use vault-protocol-slim, which is unchanged (44 lines, read-only variant).
- **Verification**:
  ```bash
  grep "Vault.*Read-Only" .squidsquad/qa/CLAUDE.md  # expect match (slim header)
  grep "Vault.*Read-Only" .squidsquad/dm/CLAUDE.md   # expect match if dm active
  ```

### TC-46: No role references boot_remote.py except PM

- **Precondition**: boot-remote-agents removed from non-PM roles.
- **Steps**:
  1. Search all composed CLAUDE.md files for "boot_remote"
- **Expected**: Only PM's CLAUDE.md contains references to boot_remote.py.
- **Verification**:
  ```bash
  grep -l "boot_remote" .squidsquad/*/CLAUDE.md  # expect only .squidsquad/pm/CLAUDE.md
  ```

---

## Section 8: Smoke Tests

- [ ] `python references/scripts/compose.py deploy-all` exits 0 with no errors
- [ ] All composed CLAUDE.md files are non-empty and well-formed markdown
- [ ] `grep -c "boot-remote-agents" .squidsquad/qa/CLAUDE.md` returns 0
- [ ] `grep -c "boot-remote-agents" .squidsquad/skill/CLAUDE.md` returns 0
- [ ] `grep -c "boot-remote-agents" .squidsquad/pm/CLAUDE.md` returns >= 1
- [ ] `references/docs/label-taxonomy.md` exists and is non-empty (or wherever dev placed it)
- [ ] `wc -w references/sub-skills/common/vault-protocol.md` shows < 1500 words
- [ ] `wc -w references/sub-skills/common/tracker-protocol.md` shows < 800 words (was 1033)
- [ ] `python references/scripts/tracker.py check-gh` still works (exit 0)
- [ ] `python references/scripts/tracker.py create-issue --help` shows expected flags
- [ ] All role includes.yml files parse without YAML errors
- [ ] No `<!-- ERROR: Missing include` markers in any composed CLAUDE.md

---

## Section 9: Regression Risks

- **Risk 1 — Agent constructs raw gh commands for labels**: If tracker-protocol is trimmed too aggressively, agents may bypass tracker.py and construct `gh issue create` with manual labels. The instruction "Use the tracker script for all queries" MUST remain. **Mitigation**: TC-30 and TC-11 verify this.

- **Risk 2 — Agent skips vault-check after writes**: If vault-protocol condensation removes the auto-run rule, agents may silently skip vault-check Level 1. **Mitigation**: TC-26 verifies the rule survives. TC-15 comprehension-tests agent understanding.

- **Risk 3 — Agent cannot map vault entity types to folders**: If entity model table is removed entirely without a summary, agents may put decisions in areas/ or profiles in galaxy/. **Mitigation**: TC-13 and TC-31 comprehension-test this mapping.

- **Risk 4 — Agent hallucinates boot step**: If a non-PM agent has residual knowledge of boot-remote-agents from training data (not template), it might hallucinate the step. **Mitigation**: TC-16 and TC-17 verify agents do not reference boot-remote-agents. Low risk since agents primarily follow their CLAUDE.md instructions.

- **Risk 5 — compose.py skips includes differently than expected**: The manifest-based resolution in compose.py may behave unexpectedly when an entry file has `{{include:}}` but the manifest lacks the path. **Mitigation**: TC-34 verifies compose.py handles this correctly.

- **Risk 6 — Status transition legal flows lost in trimming**: If the "Legal flows and owning roles" section of tracker-protocol is accidentally trimmed, agents lose knowledge of which transitions they can perform. **Mitigation**: TC-12 comprehension-tests this critical section. The section is NOT part of the Label Taxonomy and should be untouched by Change B.

- **Risk 7 — Vault-protocol-slim accidentally modified**: If the dev edits vault-protocol-slim instead of (or in addition to) vault-protocol, QA/DM/designer roles get unexpected changes. **Mitigation**: TC-22 verifies vault-protocol-slim is byte-identical to pre-change.

- **Risk 8 — Reference file not committed to git**: If the new label-taxonomy.md reference file is created but not git-tracked, other agent clones won't receive it. **Mitigation**: TC-42 verifies git tracking.

- **Risk 9 — Token savings below target**: Changes may achieve less than the 10% target if the dev's condensed wording is still verbose. **Mitigation**: TC-36 and TC-37 measure actual savings against estimates.

- **Risk 10 — Wikilink and confidence rules trimmed from vault-protocol**: These operational rules (bare wikilinks only, confidence levels, creation threshold) are mixed in with the reference-heavy sections and could be accidentally removed during condensation. **Mitigation**: TC-27, TC-28, and TC-33 verify key operational rules survive.
