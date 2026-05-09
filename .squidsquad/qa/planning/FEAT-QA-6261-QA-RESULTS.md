# FEAT-QA-6261 QA Results — Fixed Team Architecture

**Task**: #6261 — Fixed team architecture (PM+QA+DM+Workers always present, tracker-protocol into L1)
**Branch**: squidsquad/task/6261
**Executed**: 2026-05-09
**Test suite**: 1250 static + 17 integration = all PASS
**Overall verdict**: FAIL — 7 test cases fail; back to dev

---

## Summary

| Category | Count |
|---|---|
| Total TCs | 41 |
| PASS | 34 |
| FAIL | 7 |
| CQs | 3 (all PASS) |

**Failing TCs**: TC-13, TC-18, TC-21, TC-29, TC-30, TC-32, TC-40 (see detail below)

---

## TC Results

### TC-1: tracker-protocol content present in L1 base (references/roles/instructions.md)
- **Result**: PASS
- **Evidence**: `grep -i "{{include.*tracker-protocol}}" references/roles/instructions.md` → Exit 1 (no matches). `grep -c "check-gh|create-issue|list-issues|list-tasks|tracker.py transition" references/roles/instructions.md` → 8 matches. File contains `## Tracker Protocol — GitHub Issues` at line 21 with full inline content.

### TC-2: tracker-protocol include removed from all four role instructions.md files
- **Result**: PASS
- **Evidence**: `grep -r "{{include.*common/tracker-protocol}}" references/roles/` → Exit 1 (no matches).

### TC-3: tracker-protocol sub-skill file deleted
- **Result**: PASS
- **Evidence**: `test ! -f references/sub-skills/common/tracker-protocol.md && echo "PASS"` → `PASS`.

### TC-4: tracker-protocol removed from all includes.yml manifests
- **Result**: PASS
- **Evidence**: `grep -r "common/tracker-protocol" references/roles/` → Exit 1 (no matches).

### TC-5: PM instructions.md has no "if QA absent" or "if DM absent" language
- **Result**: PASS
- **Evidence**: `grep -i "QA absent|DM absent|fall back|combined PM/QA|if DM is absent|if QA is absent" references/roles/pm/instructions.md` → Exit 1 (no matches).

### TC-6: No qa_present or dm_present fields in cycle-input.json output
- **Result**: PASS
- **Evidence**: `grep -i "qa_present|dm_present|squidsquad/qa.*exist|squidsquad/dm.*exist" references/scripts/cycle_pre.py` → Exit 1 (no matches). Ran `python references/scripts/cycle_pre.py pm` → Exit 0. `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); print('qa_present' in d or 'dm_present' in d)"` → `False`.

### TC-7: cycle_pre.py and cycle_post.py have no role-presence detection
- **Result**: PASS
- **Evidence**: `grep -i "isdir.*squidsquad/qa|isdir.*squidsquad/dm|qa.*not.*installed|dm.*not.*installed" references/scripts/cycle_pre.py references/scripts/cycle_post.py` → Exit 1 (no matches).

### TC-8: delivery-fallback.md file deleted
- **Result**: PASS
- **Evidence**: `test ! -f references/sub-skills/roles/pm/delivery-fallback.md && echo "PASS"` → `PASS`.

### TC-9: PM includes.yml has no delivery-fallback entry
- **Result**: PASS
- **Evidence**: `grep "delivery-fallback" references/roles/pm/includes.yml` → Exit 1 (no matches).

### TC-10: tracker.py allows in-progress → pending-ship for dm-lead
- **Result**: PASS
- **Evidence**: LEGAL_TRANSITIONS has `"status:in-progress": {..., "status:pending-ship", ...}` (line 125). ROLE_AUTHORITY has `("status:in-progress", "status:pending-ship"): {"dm"}` (line 182) with comment `# #6261: DM skips QA`.

### TC-11: tracker.py rejects in-progress → pending-ship for non-DM roles
- **Result**: PASS
- **Evidence**: Via code inspection — ROLE_AUTHORITY at line 182 has `{"dm"}` as sole authorized set for `("status:in-progress", "status:pending-ship")`. `skill-lead` and `qa-lead` prefixes do not match `"dm"`. Transition will be rejected with unauthorized error for non-DM roles.

### TC-12: DM task-pickup sub-skill routes completion to pending-ship, not pending-test
- **Result**: PASS
- **Evidence**: `grep -i "pending-test" references/sub-skills/roles/dm/delivery-packaging.md` → Exit 1 (no matches). `grep -i "pending-ship" references/sub-skills/roles/dm/delivery-packaging.md` → 4 matches showing delivery-packaging routes to pending-ship and transitions via `tracker.py transition [NUMBER] pending-ship shipped`.

### TC-13: DM isDraft gate removed from delivery-packaging.md
- **Result**: FAIL
- **Evidence**: `grep -i "isDraft|is_draft|draft.*status|draft.*gate" references/sub-skills/roles/dm/delivery-packaging.md` → Exit 0 with 3 matches. Lines 43-46 still contain:
  ```
  gh pr list --search "squidsquad/" --state open --json number,headRefName,isDraft --limit 20
  Find the PR matching this issue number. If found:
  - If `isDraft` is true: **STOP** — this PR has not been verified by QA...
  - If `isDraft` is false: request merge via harness before shipping
  ```
  The isDraft gate is still fully present and active. It was NOT removed as part of #6261.

### TC-14: DM merge conflict handling — transition back to in-progress
- **Result**: PASS
- **Evidence**: `grep "tracker.py transition.*pending-ship.*in-progress|transition.*pending-ship.*in-progress" references/sub-skills/roles/dm/delivery-packaging.md` → returns match: `python references/scripts/tracker.py transition [NUMBER] pending-ship in-progress --role dm-lead`. Merge conflict handler present at lines 51-54 of delivery-packaging.md.

### TC-15: config.py no longer synthesizes QA from PM/QA combined identity
- **Result**: PASS
- **Evidence**: `grep -n "PM/QA|PM.QA combined|synthesize.*QA" references/scripts/config.py` → Exit 1 (no matches). `_parse_agents_v1` (lines 340-395) has been rewritten: PM always present (line 364-365), dev roles enumerated (lines 377-387), QA+DM always present as fixed team (#6261) (lines 389-393). No `if "PM/QA" in agents_text` synthesis block.

### TC-16: compose.py deploy-all still works and produces valid CLAUDE.md for all roles
- **Result**: PASS
- **Evidence**: `python references/scripts/compose.py deploy-all` → Exit 0. `ls -la .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/dm/CLAUDE.md` → all exist with sizes 106642, 59073, 53575 bytes respectively. "Validation passed with 10 warning(s)." (warnings are pre-existing bidirectional dependency warnings, not errors).

### TC-17: Composed PM CLAUDE.md contains tracker-protocol content from L1
- **Result**: PASS
- **Evidence**: `grep -i "timestamp|check-gh|status transition" .squidsquad/pm/CLAUDE.md` → multiple matches including "### Timestamps", "python references/scripts/tracker.py check-gh", "Note: Design label changes are NOT status transitions". `grep "{{include" .squidsquad/pm/CLAUDE.md` → Exit 1 (no matches).

### TC-18: Composed PM CLAUDE.md contains no fallback language
- **Result**: FAIL
- **Evidence**: `grep -i "QA absent|DM absent|fall back|combined PM/QA|delivery-fallback|if DM is absent|if QA is absent" .squidsquad/pm/CLAUDE.md` → Exit 0 with 4 matches. The matches are `fall back` in the context of script failure handling ("fall back to spawning a Claude subagent", "fall back to manually checking scan-history.md"). These are NOT role-absence fallback language — they describe fallback procedures when external scripts fail. However, the grep command from the test plan returns matches, so this TC fails on the letter of the verification command.
- **Note**: The `fall back` matches are all about tool/script fallback, not "if QA is absent, PM falls back to QA duties". The substantive requirement (no role-absence fallback) is met. The grep command is over-broad.

### TC-19: PM retains pending-test transition authority (coordination backstop)
- **Result**: PASS
- **Evidence**: ROLE_AUTHORITY line 185-186: `("status:pending-test", "status:in-progress"): {"qa", "pm"}` and `("status:pending-test", "status:pending-ship"): {"qa", "pm"}`. PM is in authorized set for both pending-test transitions.

### TC-20: QA still owns pending-test → pending-ship transitions
- **Result**: PASS
- **Evidence**: ROLE_AUTHORITY line 186: `("status:pending-test", "status:pending-ship"): {"qa", "pm"}` — `qa` is authorized. `grep -i "pending-ship" references/sub-skills/roles/qa/verification.md` → multiple matches including `python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role qa-lead`.

### TC-21: tracker.py ROLE_AUTHORITY comment no longer references "combined PM/QA identity"
- **Result**: FAIL
- **Evidence**: `grep -i "combined PM/QA|PM.QA combined|without a dedicated QA|deployments without" references/scripts/tracker.py` → Exit 0 with match: `pending-test -> pending-ship (PM/QA combined identity)` at line 23 of the module docstring. The ROLE_AUTHORITY table comment correctly says "QA/PM owns verification. PM and QA are both authorized." (line 184), but the top-level module docstring at line 23 still describes PM's authority as "PM/QA combined identity" — the old framing that #6261 was supposed to remove. Also, DM's `in-progress → pending-ship` is NOT listed in the module docstring (line 29 only says `DM: pending-ship → shipped`).

### TC-22: status-line.md "DM if present" language updated to "DM"
- **Result**: PASS
- **Evidence**: `grep -i "DM if present|dm.*if.*present|if.*dm.*present" references/sub-skills/roles/pm/status-line.md` → Exit 1 (no matches). `grep -i "DM" references/sub-skills/roles/pm/status-line.md` → match showing `PM + QA + DM + workers` unconditionally.

### TC-23: All existing tracker transitions (non-DM-skips-QA) still work
- **Result**: PASS
- **Evidence**: Via code inspection of LEGAL_TRANSITIONS and ROLE_AUTHORITY:
  - `approved → in-progress` by `skill-lead`: legal (line 122), authorized via `_assignee` (line 178) ✓
  - `in-progress → pending-test` by `skill-lead`: legal (line 124), authorized via `_assignee` (line 179) ✓
  - `pending-test → pending-ship` by `qa-lead`: legal (line 135), authorized via `{"qa", "pm"}` (line 186) ✓
  - `pending-ship → shipped` by `dm-lead`: legal (line 137), authorized via `{"dm"}` (line 195) ✓
  No regressions detected in existing transitions.

### TC-24: Post-upgrade compose produces no error for any role
- **Result**: PASS
- **Evidence**: `python references/scripts/compose.py deploy-all 2>&1 | grep -i "error|not found|missing"` → no matches for tracker-protocol or delivery-fallback. Exit 0. "Validation passed with 10 warning(s)." Compose detected no missing sub-skill files.

### TC-25: installer-files.txt updated — deleted files removed
- **Result**: PASS
- **Evidence**: `grep "tracker-protocol" references/installer-files.txt` → Exit 1. `grep "delivery-fallback" references/installer-files.txt` → Exit 1. Both deleted files are absent from installer manifest.

### TC-26: manifest.md tracker-protocol references removed
- **Result**: PASS
- **Evidence**: `grep -c "tracker-protocol" references/sub-skills/manifest.md` → `0`. No stale references.

### TC-27: tracker.py LEGAL_TRANSITIONS includes pending-ship from in-progress
- **Result**: PASS
- **Evidence**: `grep -A5 '"status:in-progress"' references/scripts/tracker.py | grep "pending-ship"` → matches `"status:pending-ship",  # #6261: DM skips QA — goes directly to pending-ship` at line 125.

### TC-28: tracker.py ROLE_AUTHORITY — DM authorized for pending-ship → in-progress
- **Result**: PASS
- **Evidence**: ROLE_AUTHORITY line 198: `("status:pending-ship", "status:in-progress"): {"pm", "qa", "dm"}`. `"dm"` is in the authorized set for merge conflict rollback.

### TC-29: dm/issue-triage.md uses two-step flow (open → in-progress → pending-ship)
- **Result**: FAIL
- **Evidence**: `grep "pending-test" references/sub-skills/roles/dm/issue-triage.md` → Exit 0 with match at line 20:
  ```
  python references/scripts/tracker.py transition [NUMBER] open pending-test --role dm-lead
  python references/scripts/tracker.py comment [NUMBER] --role dm --message "Fixed in commit [hash]. [Brief explanation]. Status → Pending Test."
  ```
  `grep "pending-ship" references/sub-skills/roles/dm/issue-triage.md` → Exit 1 (no matches). The issue-triage.md still routes DM bugs to `pending-test` (not `pending-ship`). The expected two-step flow (`open → in-progress → pending-ship`) is NOT implemented — DM's issue triage goes `open → pending-test`.

### TC-30: DM-specific task-pickup overrides common task-pickup
- **Result**: FAIL
- **Evidence**: `test -f references/sub-skills/roles/dm/task-pickup.md` → file does not exist. Only `references/sub-skills/common/task-pickup.md` exists. The common task-pickup routes completed work to `pending-test` (line 25: `tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead`). DM uses this common task-pickup and therefore routes approved tasks to `pending-test`, not `pending-ship`. No DM-specific override exists.

### TC-31: L4 project files cleaned of fallback language
- **Result**: PASS (with note)
- **Evidence**: `grep -i "QA fallback|DM absent|DM is optional|fallback" .squidsquad/project/pm-instructions.md .squidsquad/project/dm-instructions.md` → one match in dm-instructions.md: `### Model & Fallback`. The full context is:
  ```
  ### Model & Fallback
  - **Use `model: "sonnet"` for subagents** — Opus unnecessary for directed subtasks.
  - **DM is always present.** Fixed team architecture — PM + QA + DM + workers.
  ```
  This is model selection language, not role-absence fallback. No DM-absent or QA-fallback role language present.

### TC-32: PM SOUL.md DM-absent reboot fallback removed
- **Result**: FAIL
- **Evidence**: `grep -i "DM absent|fallback reboot" .squidsquad/pm/SOUL.md` → Exit 0 with match at line 147:
  ```
  - If DM absent: execute directly — PM is the fallback reboot authority
  ```
  This is in the `### Process Governance` section under `**Agent lifecycle governance**`. The old "DM is optional" fallback reboot authority language remains in the composed SOUL.md. This contradicts the fixed-team architecture of #6261.

### TC-33: boot_remote.py handles new config.md format
- **Result**: PASS
- **Evidence**: `grep -n "PM/QA|PM.QA" references/scripts/boot_remote.py` → Exit 1 (no matches). boot_remote.py has no combined PM/QA parsing logic.

### TC-34: cycle_post.py PM fallback CHANGELOG/version-bump branch removed entirely
- **Result**: PASS
- **Evidence**: `grep -n "dm_dir|_dir_exists.*dm|not.*dm.*exists" references/scripts/cycle_post.py` → Exit 1 (no matches). `grep -n "CHANGELOG|version.bump|_do_version_bump" references/scripts/cycle_post.py` → `_do_version_bump` function exists at line 415 with comment at line 437: `# DM always handles CHANGELOG entries (#6261). No PM fallback.` No PM fallback delivery code in the function.

### TC-35: delivery-packaging.md has explicit merge-fail handler
- **Result**: PASS
- **Evidence**: `grep -i "conflict|merge.*fail|in-progress" references/sub-skills/roles/dm/delivery-packaging.md` → matches at lines 51-54:
  ```python
  python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "PR merge failed — merge conflict. Dev agent: resolve conflicts and re-push. Status → In Progress."
  python references/scripts/tracker.py transition [NUMBER] pending-ship in-progress --role dm-lead
  ```
  Explicit merge conflict handler with tracker.py transition command present.

### TC-36: test_compose.py updated for tracker-protocol removal
- **Result**: PASS
- **Evidence**: `grep -c "tracker.protocol" tests/test_compose.py` → `0`. No stale tracker-protocol references.

### TC-37: add_role.py DM directory existence check removed
- **Result**: PASS
- **Evidence**: `grep -n "dm.*exists|squidsquad.*dm.*isdir|if.*dm" references/scripts/add_role.py` → Exit 1 (no matches).

### TC-38: wizard.py writes separate PM and QA entries
- **Result**: PASS
- **Evidence**: `grep "PM/QA" references/scripts/wizard.py` → Exit 1 (no matches). wizard.py `_render_agent()` function (line 708) writes each agent as a separate entry using its ID key (`- **pm**: alias`, `- **qa**: alias`). No combined PM/QA entry is written. The new v2 schema enforces separate agent entries.

### TC-39: config.py sync_agents() writes separate PM/QA entries
- **Result**: PASS
- **Evidence**: `grep "PM/QA" references/scripts/config.py` → Exit 1 (no matches). `_parse_agents_v1` now explicitly appends pm, then dev roles, then qa and dm as fixed team members (lines 364-393).

### TC-40: Event contracts stable after L1 promotion
- **Result**: PASS
- **Evidence**: Event contracts are stored in `.squidsquad/config.md` (not in CLAUDE.md). `grep -n "status-transition" .squidsquad/config.md` shows all 4 roles emit `status-transition`:
  - dm: `- **emits**: request-merge, status-transition, tracker-comment` (line 135)
  - pm: `- **emits**: phase-change, status-transition, tracker-comment` (line 139)
  - qa: `- **emits**: agent-health, request-merge, status-transition, tracker-comment, verification-failed, verification-passed` (line 143)
  - skill: `- **emits**: pr-create, status-transition, tracker-comment` (line 147)
  All agents still emit `status-transition` after tracker-protocol L1 promotion. No event contract regression detected.
- **Note**: TC-40 spec says to check `grep -A3 "emits" .squidsquad/pm/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/dm/CLAUDE.md` — these files don't contain an "emits" section (contracts are in config.md). The substantive requirement (all agents emit status-transition) is met.

### TC-41: At least one variant role composed output contains tracker-protocol
- **Result**: PASS
- **Evidence**: `grep -c "check-gh|create-issue|tracker.py transition" .squidsquad/skill/CLAUDE.md` → `21` (21 matches, well above the required 3). Skill CLAUDE.md (73816 bytes) contains full tracker-protocol content inherited from L1.

---

## Comprehension Questions

### CQ-1: What roles are always present on a SquidSquad team?
- **Result**: PASS
- **Files checked**: `references/roles/pm/instructions.md`, `references/roles/qa/instructions.md`, `references/roles/dm/instructions.md`
- **Findings**: All three instructions files define their role as part of the SquidSquad autonomous dev team without any conditional language. PM: "You are the PM on the SquidSquad autonomous dev team... QA handles verification independently. DM handles delivery." QA: "You independently verify work from ALL dev and designer agents... You hand verified work to DM for delivery." DM: "You are the Delivery Manager on the SquidSquad autonomous dev team." No "if QA is installed", "if DM is present" conditional language in any file. The `config.py` code (lines 389-393) enforces QA and DM as always-present: `# Fixed team: QA + DM always present (#6261)`.
- **Answer**: PM, QA, and DM are always present on a SquidSquad team, along with at least one technical worker (skill/dev). No conditional "if present" language. Absence of any core role would be an error, not a supported configuration.

### CQ-2: As a DM agent, after completing a docs task, what status do you transition to?
- **Result**: PASS
- **Files checked**: `references/sub-skills/roles/dm/delivery-packaging.md`, `references/scripts/tracker.py`
- **Findings**: delivery-packaging.md Step 2 (Scan for Pending Ship items) shows DM picks up items at `status:pending-ship`. DM's delivery step (line 67-70) transitions to shipped: `tracker.py transition [NUMBER] pending-ship shipped --role dm-lead`. tracker.py ROLE_AUTHORITY confirms `("status:in-progress", "status:pending-ship"): {"dm"}` — DM directly skips QA. The merge conflict handler (lines 51-54) shows DM rolls back to `in-progress` on failure.
- **Answer**: `pending-ship`. DM transitions completed delivery work directly to `pending-ship` via the `in-progress → pending-ship` transition (authorized for `dm-lead` only). DM does NOT route through `pending-test`. QA is not involved in DM's delivery flow.
- **Caveat**: issue-triage.md (bug fixes) still routes to `pending-test` — this is a bug found in TC-29.

### CQ-3: Where do you find the tracker protocol instructions?
- **Result**: PASS
- **Files checked**: `references/roles/instructions.md`, `references/roles/pm/instructions.md`, `references/roles/qa/instructions.md`
- **Findings**: `references/roles/instructions.md` contains `## Tracker Protocol — GitHub Issues` at line 21 with full inline content (timestamps, startup permission check, reading issues, creating issues, status transitions, discussion entries). PM instructions reference it as "see Tracker Protocol above" (line 13 of pm/instructions.md) — confirming it's sourced from L1, not re-defined per-role. No `{{include: common/tracker-protocol}}` line appears in any role file. `grep -r "{{include.*common/tracker-protocol}}" references/roles/` → Exit 1.
- **Answer**: In the L1 base agent definition — `references/roles/instructions.md`. The tracker protocol is inlined directly into the base layer and inherited by all roles automatically. It is not delivered via sub-skill include.

---

## Test Suite Results

```
python tests/run_tests.py
===== 1250 passed in 21.99s =====
+ 17 integration tests: all OK
```

**Full pass** — no regression in automated test suite.

---

## Defect Summary (Back to Dev)

| TC | File | Issue |
|---|---|---|
| TC-13 | `references/sub-skills/roles/dm/delivery-packaging.md` | isDraft gate still present at lines 43-46. Must be removed. |
| TC-18 | `.squidsquad/pm/CLAUDE.md` (composed from source) | "fall back" language from scan_index fallback step matches grep. Source: scan step in PM instructions. Low severity — these are tool fallbacks, not role-absence fallbacks, but the verification grep returns matches. |
| TC-21 | `references/scripts/tracker.py` | Line 23 in module docstring still says "pending-test -> pending-ship (PM/QA combined identity)". Also DM's `in-progress → pending-ship` transition not listed in docstring (line 29 only says `DM: pending-ship → shipped`). |
| TC-29 | `references/sub-skills/roles/dm/issue-triage.md` | Bug triage flow still routes to `pending-test`, not `pending-ship`. Lines 20-22 transition `open → pending-test`. DM bugs should go `open → in-progress → pending-ship` per #6261. |
| TC-30 | Missing: `references/sub-skills/roles/dm/task-pickup.md` | No DM-specific task-pickup override exists. Common task-pickup routes to `pending-test`. DM needs a role-specific override that routes approved tasks to `pending-ship`. |
| TC-32 | `.squidsquad/pm/SOUL.md` (composed from source) | Line 147: "If DM absent: execute directly — PM is the fallback reboot authority". This contradicts fixed-team architecture. Source is in pm SOUL.md source file. |
| TC-40 | Note | TC-40 PASSES on substantive check (all agents emit status-transition in config.md). Marked PASS — see note in TC-40 result. |

**Note on TC-18**: The "fall back" matches are tool-failure fallbacks, not role-absence fallbacks. The test plan verification grep is over-broad. However per zero-gap gate policy, this is a FAIL until the verification command passes or the grep is revised.

**Note on TC-40**: Revised to PASS — event contracts are stored in config.md not CLAUDE.md, and all agents emit status-transition.

**Revised FAIL count**: TC-13, TC-18 (marginal), TC-21, TC-29, TC-30, TC-32 = 6 FAILs. Any TC failure = back to dev.
