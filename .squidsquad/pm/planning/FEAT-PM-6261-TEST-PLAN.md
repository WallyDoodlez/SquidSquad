# FEAT-PM-6261 Test Plan — Fixed Team Architecture: PM+QA+DM+Workers Always Present, Tracker-Protocol into L1

## Scope

Verify that tracker-protocol content is inlined into the L1 base agent definition and no longer delivered via per-role includes; that all role-absence fallback logic is stripped from templates and scripts; that DM can transition items directly to pending-ship without QA involvement; that DM routes merge conflicts back to dev; that config.py stops synthesizing a combined PM/QA identity; and that compose.py deploy-all still produces valid CLAUDE.md output for all roles after these changes.

---

## Test Cases

### TC-1: tracker-protocol content present in L1 base (references/roles/instructions.md)

- **Precondition**: `references/roles/instructions.md` updated as part of #6261
- **Steps**:
  1. Read `references/roles/instructions.md`
  2. Confirm the file contains the tracker-protocol content (timestamps, status transitions, discussion entries, creating issues, reading issues)
  3. Confirm the tracker-protocol content is inline — not delivered via an `{{include:}}` directive targeting `common/tracker-protocol`
- **Expected**: The file contains tracker-protocol sections covering at minimum: timestamp commands, startup permission check, reading issues, creating issues, status transitions, and discussion entries. No `{{include: common/tracker-protocol}}` line appears in the file
- **Verification**: `grep -i "{{include.*tracker-protocol}}" references/roles/instructions.md` returns no matches. `grep -i "timestamp\|status transition\|tracker" references/roles/instructions.md` returns at least 10 matches (content present)

---

### TC-2: tracker-protocol include removed from all four role instructions.md files

- **Precondition**: `references/roles/pm/instructions.md`, `references/roles/qa/instructions.md`, `references/roles/dm/instructions.md`, `references/roles/dev/instructions.md` updated as part of #6261
- **Steps**:
  1. For each of the four files, search for `{{include: common/tracker-protocol}}`
- **Expected**: None of the four files contain `{{include: common/tracker-protocol}}`. Tracker-protocol is now sourced from L1, not from per-role include directives
- **Verification**: `grep -r "{{include.*common/tracker-protocol}}" references/roles/` returns no matches

---

### TC-3: tracker-protocol sub-skill file deleted

- **Precondition**: #6261 implementation complete
- **Steps**:
  1. Check whether `references/sub-skills/common/tracker-protocol.md` exists
- **Expected**: The file does not exist. Content has been moved to L1 (`references/roles/instructions.md`) and the source file deleted in the same atomic commit
- **Verification**: `test ! -f references/sub-skills/common/tracker-protocol.md && echo "PASS"` prints `PASS`. Alternatively, `ls references/sub-skills/common/tracker-protocol.md` exits with code 1 (file not found)

---

### TC-4: tracker-protocol removed from all includes.yml manifests

- **Precondition**: `references/roles/dev/includes.yml`, `references/roles/pm/includes.yml`, `references/roles/qa/includes.yml`, `references/roles/dm/includes.yml` updated as part of #6261
- **Steps**:
  1. Search all `includes.yml` files under `references/roles/` for references to `common/tracker-protocol`
- **Expected**: Zero matches. All four base-role includes manifests no longer list `common/tracker-protocol`. Variant roles inherit from these base manifests via `base_role:` and therefore also receive no tracker-protocol include
- **Verification**: `grep -r "common/tracker-protocol" references/roles/` returns no matches

---

### TC-5: PM instructions.md has no "if QA absent" or "if DM absent" language

- **Precondition**: `references/roles/pm/instructions.md` updated as part of #6261
- **Steps**:
  1. Read `references/roles/pm/instructions.md`
  2. Search for fallback language: `QA absent`, `DM absent`, `fall back`, `combined PM/QA`, `If DM is absent`, `If QA is absent`
  3. Check Step 6c specifically for the "If DM is absent, PM handles version bumps" clause
- **Expected**: No conditional role-absence language present. Step 6c either refers unconditionally to DM for version bumps or is removed entirely. The PM identity paragraph at the top of the file does not contain "When QA is absent, you fall back to combined PM/QA duties"
- **Verification**: `grep -i "QA absent\|DM absent\|fall back\|combined PM/QA\|if DM is absent\|if QA is absent" references/roles/pm/instructions.md` returns no matches

---

### TC-6: No qa_present or dm_present fields in cycle-input.json output

- **Precondition**: `references/scripts/cycle_pre.py` updated as part of #6261; a working SquidSquad install
- **Steps**:
  1. Read `references/scripts/cycle_pre.py`
  2. Search for role-presence detection logic: `qa_present`, `dm_present`, directory existence checks for `.squidsquad/qa/` or `.squidsquad/dm/`
  3. Run `python references/scripts/cycle_pre.py pm` and read the resulting `cycle-input.json`
- **Expected**: `cycle_pre.py` contains no logic that checks for the presence or absence of QA or DM directories and emits corresponding fields. The output `cycle-input.json` does not contain `qa_present` or `dm_present` keys
- **Verification**: `grep -i "qa_present\|dm_present\|squidsquad/qa.*exist\|squidsquad/dm.*exist" references/scripts/cycle_pre.py` returns no matches. After running cycle_pre, `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); print('qa_present' in d or 'dm_present' in d)"` prints `False`

---

### TC-7: cycle_pre.py and cycle_post.py have no role-presence detection

- **Precondition**: `references/scripts/cycle_pre.py` and `references/scripts/cycle_post.py` updated as part of #6261
- **Steps**:
  1. Search both scripts for any code that checks whether a role directory exists to conditionally enable/disable behavior
- **Expected**: Neither script contains logic of the form `if os.path.isdir('.squidsquad/qa')` or equivalent that gates behavior on the presence of a QA or DM clone directory
- **Verification**: `grep -i "isdir.*squidsquad/qa\|isdir.*squidsquad/dm\|qa.*not.*installed\|dm.*not.*installed" references/scripts/cycle_pre.py references/scripts/cycle_post.py` returns no matches

---

### TC-8: delivery-fallback.md file deleted

- **Precondition**: #6261 implementation complete
- **Steps**:
  1. Check whether `references/sub-skills/roles/pm/delivery-fallback.md` exists
- **Expected**: The file does not exist. No stub, no redirect comment, no empty file. Clean deletion
- **Verification**: `test ! -f references/sub-skills/roles/pm/delivery-fallback.md && echo "PASS"` prints `PASS`

---

### TC-9: PM includes.yml has no delivery-fallback entry

- **Precondition**: `references/roles/pm/includes.yml` updated as part of #6261
- **Steps**:
  1. Read `references/roles/pm/includes.yml`
  2. Search for `delivery-fallback`
- **Expected**: No reference to `roles/pm/delivery-fallback` in PM's includes manifest
- **Verification**: `grep "delivery-fallback" references/roles/pm/includes.yml` returns no matches

---

### TC-10: tracker.py allows in-progress → pending-ship for dm-lead

- **Precondition**: `references/scripts/tracker.py` updated as part of #6261 with the DM direct-ship transition
- **Steps**:
  1. Read the `LEGAL_TRANSITIONS` or `ROLE_AUTHORITY` table in `references/scripts/tracker.py`
  2. Confirm that `("status:in-progress", "status:pending-ship")` is a legal transition for `dm-lead`
  3. Optionally run a dry-run: `python references/scripts/tracker.py transition <dm-issue-number> in-progress pending-ship --role dm-lead --dry-run` (if dry-run is supported)
- **Expected**: The transition `in-progress → pending-ship` is defined as legal in tracker.py with `dm-lead` listed in the authorized roles set. The comment or docstring explaining this transition references DM's direct delivery path (no QA gate required for DM-owned items)
- **Verification**: `grep -A5 "in-progress.*pending-ship\|pending-ship.*in-progress" references/scripts/tracker.py` shows `dm-lead` in the authorized set for this transition

---

### TC-11: tracker.py rejects in-progress → pending-ship for non-DM roles

- **Precondition**: `references/scripts/tracker.py` updated as part of #6261; a test issue at `in-progress` status
- **Steps**:
  1. Attempt to transition a test issue from `in-progress` to `pending-ship` using `--role skill-lead`
  2. Observe the exit code and error message
  3. Attempt the same with `--role qa-lead`
  4. Observe the exit code and error message
- **Expected**: Both attempts fail (non-zero exit code). tracker.py prints an authorization error explaining that `in-progress → pending-ship` is not a permitted transition for the given role. The transition is exclusively authorized for `dm-lead`
- **Verification**: `python references/scripts/tracker.py transition <NUMBER> in-progress pending-ship --role skill-lead` exits non-zero and prints an error containing "unauthorized" or "not authorized" or "illegal". Same for `--role qa-lead`

---

### TC-12: DM task-pickup sub-skill routes completion to pending-ship, not pending-test

- **Precondition**: `references/sub-skills/roles/dm/` sub-skills reviewed post-#6261
- **Steps**:
  1. Read `references/sub-skills/roles/dm/delivery-packaging.md` (or the equivalent DM task-completion instructions)
  2. Find the step where DM transitions a completed task out of `in-progress`
  3. Confirm the target status is `pending-ship`, not `pending-test`
  4. Search for any instruction directing DM to send work to QA for review
- **Expected**: DM transitions completed delivery work to `pending-ship` directly. No step directs DM to transition to `pending-test` or to wait for QA verification. DM's delivery path is: `in-progress → pending-ship → shipped`
- **Verification**: `grep -i "pending-test" references/sub-skills/roles/dm/delivery-packaging.md` returns no matches (or only appears in an explicit note that DM does NOT use this status). `grep -i "pending-ship" references/sub-skills/roles/dm/delivery-packaging.md` returns at least one match showing the target transition

---

### TC-13: DM isDraft gate removed from delivery-packaging.md

- **Precondition**: `references/sub-skills/roles/dm/delivery-packaging.md` updated as part of #6261
- **Steps**:
  1. Read `references/sub-skills/roles/dm/delivery-packaging.md`
  2. Search for `isDraft`, `is_draft`, `draft status`, or any logic that checks a PR's draft state before merging
- **Expected**: No `isDraft` check or draft-gate logic present. DM merges PRs regardless of draft status. The precondition comment from old Step 0b (checking for `isDraft == false`) is removed
- **Verification**: `grep -i "isDraft\|is_draft\|draft.*status\|draft.*gate" references/sub-skills/roles/dm/delivery-packaging.md` returns no matches

---

### TC-14: DM merge conflict handling — transition back to in-progress

- **Precondition**: `references/sub-skills/roles/dm/delivery-packaging.md` updated as part of #6261 with merge conflict handling
- **Steps**:
  1. Read `references/sub-skills/roles/dm/delivery-packaging.md`
  2. Find the PR merge step (the step where DM attempts to merge a PR)
  3. Locate the merge failure / conflict handling branch
  4. Confirm the on-conflict action is: comment on the issue + transition item back to `in-progress`
- **Expected**: DM's delivery sub-skill includes an explicit merge-conflict handler that: (a) comments on the tracker issue describing the conflict, and (b) transitions the item from `pending-ship` back to `in-progress` using `tracker.py transition`. The comment should direct the dev agent to resolve the conflict
- **Verification**: `grep -i "conflict\|merge.*fail\|in-progress" references/sub-skills/roles/dm/delivery-packaging.md` shows a conflict handler branch that references transitioning back to `in-progress`. The transition command shown uses `--role dm-lead`

---

### TC-15: config.py no longer synthesizes QA from PM/QA combined identity

- **Precondition**: `references/scripts/config.py` updated as part of #6261
- **Steps**:
  1. Read the `_parse_agents_v1` function (around line 394) in `references/scripts/config.py`
  2. Check for the block `if "PM/QA" in agents_text` or equivalent that injects a synthetic QA entry
  3. Also check `update_agents_section` and the `config.md` writer for `**PM/QA**: always present` output
- **Expected**: The `if "PM/QA" in agents_text` block is removed. `config.py` does not synthesize a QA entry from a combined PM/QA string. QA is always treated as a first-class, separately listed entry. If a legacy config.md contains `**PM/QA**: always present`, `config.py` either migrates it automatically or errors with a clear message — it does not silently emit a combined identity
- **Verification**: `grep -n "PM/QA\|PM.QA combined\|synthesize.*QA" references/scripts/config.py` returns no matches for synthesis logic. If any `PM/QA` references remain, they must be in migration or error handling code only

---

### TC-16: compose.py deploy-all still works and produces valid CLAUDE.md for all roles

- **Precondition**: #6261 template changes in place; `references/sub-skills/common/tracker-protocol.md` deleted; `delivery-fallback.md` deleted; all includes.yml updated
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`
  2. Observe exit code
  3. Verify the composed CLAUDE.md files exist and are non-empty for pm, qa, dm, and skill (or dev) roles
  4. Confirm no compose error about missing `common/tracker-protocol` or `roles/pm/delivery-fallback` files
- **Expected**: compose.py exits 0. All role CLAUDE.md files are generated without error. No error message referencing a missing sub-skill or include file
- **Verification**: `python references/scripts/compose.py deploy-all && echo "PASS"` prints `PASS`. `ls -la .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/dm/CLAUDE.md` shows all files exist with non-zero size

---

### TC-17: Composed PM CLAUDE.md contains tracker-protocol content from L1

- **Precondition**: TC-16 completed (compose.py deploy-all succeeded)
- **Steps**:
  1. Read `.squidsquad/pm/CLAUDE.md`
  2. Confirm the tracker-protocol content is present: timestamps section, startup permission check, status transitions, discussion entries
  3. Confirm the content is NOT wrapped in a section header indicating it came from an include (i.e., it flows as part of the base agent definition)
- **Expected**: Composed PM CLAUDE.md contains full tracker-protocol content. The content appears inline as part of the base agent layer, not as a separately marked included block. The composed output contains no `{{include:}}` directive artifacts
- **Verification**: `grep -i "timestamp\|startup permission\|check-gh\|status transition" .squidsquad/pm/CLAUDE.md` returns matches. `grep "{{include" .squidsquad/pm/CLAUDE.md` returns no matches

---

### TC-18: Composed PM CLAUDE.md contains no fallback language

- **Precondition**: TC-16 completed
- **Steps**:
  1. Read `.squidsquad/pm/CLAUDE.md`
  2. Search for role-absence fallback language
- **Expected**: Composed PM CLAUDE.md contains no `QA absent`, `DM absent`, `fall back`, `combined PM/QA`, `If DM is absent`, or `delivery-fallback` language
- **Verification**: `grep -i "QA absent\|DM absent\|fall back\|combined PM/QA\|delivery-fallback\|if DM is absent\|if QA is absent" .squidsquad/pm/CLAUDE.md` returns no matches

---

### TC-19: PM retains pending-test transition authority (coordination backstop)

- **Precondition**: `references/scripts/tracker.py` updated as part of #6261
- **Steps**:
  1. Read the `ROLE_AUTHORITY` mapping in `references/scripts/tracker.py`
  2. Find the entry for `("status:pending-test", "status:pending-ship")` and `("status:pending-test", "status:in-progress")`
  3. Confirm `pm-lead` (or `pm`) is in the authorized set for both transitions
- **Expected**: PM retains authority to transition items out of `pending-test` in both directions (`pending-ship` and `in-progress`). The comment framing changes from "combined PM/QA identity" to "coordination backstop" but the actual authority mapping is unchanged
- **Verification**: `grep -A5 "pending-test.*pending-ship\|pending-ship.*pending-test" references/scripts/tracker.py` shows `pm` or `pm-lead` listed alongside `qa` or `qa-lead` as authorized roles

---

### TC-20: QA still owns pending-test → pending-ship transitions

- **Precondition**: `references/scripts/tracker.py` reviewed post-#6261
- **Steps**:
  1. Confirm `qa-lead` (or `qa`) is authorized for `pending-test → pending-ship`
  2. Confirm the QA verification sub-skill still directs QA to run this transition after verification passes
- **Expected**: QA's authority over `pending-test → pending-ship` is unchanged. The tracker.py authority table still includes `qa-lead` for this transition. QA's verification sub-skill still instructs QA to transition verified items to `pending-ship`
- **Verification**: `grep -A5 "pending-test.*pending-ship" references/scripts/tracker.py` includes `qa` or `qa-lead`. `grep -i "pending-ship" references/sub-skills/roles/qa/verification.md` returns at least one match showing QA setting this transition

---

### TC-21: tracker.py ROLE_AUTHORITY comment no longer references "combined PM/QA identity"

- **Precondition**: `references/scripts/tracker.py` updated as part of #6261
- **Steps**:
  1. Read the docstring and the `ROLE_AUTHORITY` comment block in `references/scripts/tracker.py`
  2. Search for "combined PM/QA", "PM/QA combined identity", "deployments without a dedicated QA"
- **Expected**: None of these phrases appear. The comment framing for PM's pending-test authority uses language like "coordination backstop" or "PM is authorized alongside QA for pending-test transitions" — reflecting the fixed-team reality, not a legacy fallback identity
- **Verification**: `grep -i "combined PM/QA\|PM.QA combined\|without a dedicated QA\|deployments without" references/scripts/tracker.py` returns no matches

---

### TC-22: status-line.md "DM if present" language updated to "DM"

- **Precondition**: `references/sub-skills/roles/pm/status-line.md` updated as part of #6261
- **Steps**:
  1. Read `references/sub-skills/roles/pm/status-line.md`
  2. Find the line that references DM in the status bar agents list (previously line 7: "DM if present")
- **Expected**: The language reads "DM" unconditionally, not "DM if present" or "DM (if installed)"
- **Verification**: `grep -i "DM if present\|dm.*if.*present\|if.*dm.*present" references/sub-skills/roles/pm/status-line.md` returns no matches. `grep -i "DM" references/sub-skills/roles/pm/status-line.md` returns at least one match showing unconditional DM reference

---

### TC-23: All existing tracker transitions (non-DM-skips-QA) still work

- **Precondition**: `references/scripts/tracker.py` updated as part of #6261; a test issue exists at various statuses
- **Steps**:
  1. Verify the following transitions still succeed (spot-check 3):
     - `approved → in-progress` by `skill-lead`
     - `in-progress → pending-test` by `skill-lead`
     - `pending-test → pending-ship` by `qa-lead`
     - `pending-ship → shipped` by `dm-lead`
  2. Run each with `tracker.py transition` and observe exit codes
- **Expected**: All four transitions succeed (exit 0). No regression in the existing state machine. The only new transition added is `in-progress → pending-ship` for `dm-lead`
- **Verification**: All four `tracker.py transition` commands exit 0. The issue's label on GitHub reflects the new status after each transition

---

### TC-24: Post-upgrade compose produces no error for any role

- **Precondition**: A fresh `git pull` of the #6261 changes; all old compose artifacts present
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all` immediately after pulling #6261 changes
  2. Check that compose does not error on the deleted files (`tracker-protocol.md`, `delivery-fallback.md`)
- **Expected**: compose.py detects that `common/tracker-protocol` and `roles/pm/delivery-fallback` are no longer referenced in any includes.yml and does not attempt to read them. Exit code 0
- **Verification**: `python references/scripts/compose.py deploy-all 2>&1 | grep -i "error\|not found\|missing"` returns no output (no errors). Exit code is 0

---

## Smoke Tests

- [ ] `grep -r "{{include.*common/tracker-protocol}}" references/roles/` returns no matches
- [ ] `test ! -f references/sub-skills/common/tracker-protocol.md && echo "PASS"` prints `PASS`
- [ ] `test ! -f references/sub-skills/roles/pm/delivery-fallback.md && echo "PASS"` prints `PASS`
- [ ] `grep "delivery-fallback" references/roles/pm/includes.yml` returns no matches
- [ ] `grep -i "QA absent\|DM absent\|fall back\|combined PM/QA" references/roles/pm/instructions.md` returns no matches
- [ ] `grep -i "qa_present\|dm_present" references/scripts/cycle_pre.py` returns no matches
- [ ] `grep -i "qa_present\|dm_present" references/scripts/cycle_post.py` returns no matches
- [ ] `grep -i "PM/QA combined\|combined PM/QA" references/scripts/config.py` returns no matches
- [ ] `grep -i "isDraft\|is_draft" references/sub-skills/roles/dm/delivery-packaging.md` returns no matches
- [ ] `grep -i "pending-test" references/sub-skills/roles/dm/delivery-packaging.md` returns no matches (DM routes to pending-ship, not pending-test)
- [ ] `python references/scripts/compose.py deploy-all` exits 0
- [ ] After compose, `grep -i "fall back\|combined PM/QA\|delivery-fallback" .squidsquad/pm/CLAUDE.md` returns no matches
- [ ] `grep -i "timestamp\|check-gh\|status transition" .squidsquad/pm/CLAUDE.md` returns matches (tracker-protocol content present in composed output)
- [ ] `grep -i "timestamp\|check-gh\|status transition" .squidsquad/qa/CLAUDE.md` returns matches (tracker-protocol in QA too)
- [ ] `grep -i "timestamp\|check-gh\|status transition" .squidsquad/dm/CLAUDE.md` returns matches (tracker-protocol in DM too)

---

## Regression Risks

- **Compose error on deleted files**: If any includes.yml still references `common/tracker-protocol` or `roles/pm/delivery-fallback` after the files are deleted, `compose.py` will fail with a file-not-found error on the next `deploy-all`. The atomic migration approach (delete files and remove all references in the same commit) prevents mixed-state compose runs. Verify with TC-16 and TC-24.
- **Event contracts diverge after L1 promotion**: `compose.py derive_and_write_event_contracts` reads composed CLAUDE.md content to derive tracker event contracts. After tracker-protocol moves from L2 include to L1 inline, the derived contracts may produce slightly different output. Verify the `emits` list for status-transition events is unchanged after compose — specifically that all agents still emit `status-transition` events.
- **Config.md legacy PM/QA format breaks existing installs**: Users with an existing `config.md` containing `**PM/QA**: always present` will fail config.py parsing if the `_parse_agents_v1` synthesis block is removed without a migration step. The upgrade path must call `config.py update-agents-section` (or equivalent) to rewrite the legacy entry to separate PM and QA entries. Verify migration step is documented and runs cleanly.
- **DM draft-gate removal ships unverified code**: The `isDraft` gate was a second-layer check in DM's delivery path. Its removal is safe only because `pending-ship` can exclusively be set by QA/PM (tracker.py authority). If tracker.py's authority table is accidentally broadened (allowing non-QA roles to set `pending-ship`), DM could ship unverified code. TC-11 verifies the authority table remains correctly scoped.
- **PM pending-test authority framing change**: The comment rewrite in tracker.py changes the narrative from "combined PM/QA identity" to "coordination backstop." If agents read the narrative to decide whether to use the authority (rather than the code table), a miscommunication could occur. CQ-1 verifies agents interpret the correct behavior from files alone.
- **Variant roles lose tracker-protocol**: Variant roles (e.g., `dev-skill`, role variants) inherit from the 4 base manifests via `base_role:`. Since tracker-protocol now comes from L1 (not includes), variant roles receive it automatically via the base layer. Verify at least one variant role's composed output contains tracker-protocol content after compose.
- **DM merge conflict handler absent**: Prior to #6261, there was no merge conflict handling in DM's delivery path (only in QA's verification path). If the conflict handler was not added as part of this task, DM will silently fail or stall when a PR can't be merged. TC-14 verifies the handler is present.
- **wizard.py still writes PM/QA combined entry**: If `wizard.py` is not updated to write separate PM and QA entries in new config.md files, new installs will immediately have a legacy-format config that the updated `config.py` cannot parse correctly. This is an integration risk noted in the research — verify `wizard.py` output format.

---

## Comprehension Questions

### CQ-1: What roles are always present on a SquidSquad team?

- **Files**: `references/roles/pm/instructions.md`, `references/roles/qa/instructions.md`, `references/roles/dm/instructions.md`, `SKILL.md`
- **Expected**: PM, QA, and DM are always present, plus at least one technical worker (e.g., skill/dev agent). No role is optional. No conditional language like "if QA is installed" or "if DM is present" appears in the instructions. The team composition is fixed — absence of any core role is an error condition, not a supported configuration

### CQ-2: As a DM agent, after completing a docs task, what status do you transition to?

- **Files**: `references/sub-skills/roles/dm/delivery-packaging.md`, `references/scripts/tracker.py`
- **Expected**: `pending-ship`. DM transitions completed delivery work directly to `pending-ship` without routing through `pending-test`. DM does not send work to QA for review. The `in-progress → pending-ship` transition is explicitly authorized for `dm-lead` in tracker.py. QA is not involved in DM's delivery flow

### CQ-3: Where do you find the tracker protocol instructions?

- **Files**: `references/roles/instructions.md`, `references/roles/pm/instructions.md`, `references/roles/qa/instructions.md`
- **Expected**: In the L1 base agent definition — `references/roles/instructions.md`. The tracker protocol (timestamps, startup permission check, reading issues, creating issues, status transitions, discussion entries) is inlined directly into the base layer. It is not delivered via a separate sub-skill include. All agents receive it automatically as part of the base definition, not through per-role includes manifests
