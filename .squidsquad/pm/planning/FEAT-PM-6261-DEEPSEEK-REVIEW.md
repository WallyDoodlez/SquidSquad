Now I have comprehensively analyzed all the referenced files. Let me compile the review.

---

# REVIEW-6261-TESTPLAN Research — Fixed Team Architecture Test Plan Review

## Summary

This review analyzed `FEAT-PM-6261-TEST-PLAN.md` against `FEAT-PM-6261-RESEARCH.md`, `FEAT-PM-6261-CONTEXT.md`, and the actual codebase (tracker.py, cycle_pre.py, cycle_post.py, config.py, compose.py, all 4 role instructions.md files, all 4 includes.yml files, DM sub-skills, wizard.py, boot_remote.py, add_role.py, installer-files.txt, manifest.md, test_compose.py, test_tracker_authority.py, and L4 project files). The test plan has **36 test cases** covering the major structural changes, but I identified **8 test cases with verification weaknesses or false-positive risks**, **5 acceptance criteria with no test coverage**, **3 regression risks not covered**, and **2 state machine transitions that need testing but aren't.**

**Recommendation**: Feasible with caveats. The test plan's structure is thorough on deletions and content moves, but has gaps around: (a) the DM `open → pending-ship` transition's legality (tracker.py doesn't currently allow it), (b) the merge-conflict handler isn't just missing — what exists now is a "skip" behavior that grep will falsely match, (c) `add_role.py`, `wizard.py`, event contracts, and `config.py sync_agents()` have no test coverage despite being flagged in CONTEXT.md, and (d) TC-1's primary verification grep is trivially satisfied by pre-existing content in the L1 base.

**Primary risks**: DM bug fixes can't route directly to `pending-ship` from `open` without adding a new LEGAL_TRANSITION. The merge-conflict handler must be built, not just verified. The config.md migration path (`sync_agents()`, `_parse_agents_v1`) is underspecified in tests.

---

## Vault Context

- **BRIEFING.md priorities**: #6261 "Fixed team architecture" is listed as planned, high priority, role:skill, awaiting human approval. #6055 ("Enforce role separation — PM/QA/DM mandatory") is shipped — this is a direct follow-on.
- **Related decisions**: [[decision-sub-skill-architecture]] — defines the 5-layer architecture. Tracker-protocol promotion from L2 to L1 respects this layering.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — tracker-protocol content must preserve deterministic script invocations verbatim during the move.
- **Human preferences**: Prefers direct/mechanical checks over indirect state files. Prefers agents to act first on clear requirements. "Never ship with failed TCs."
- **Related learnings**: [[learning-atomic-migration-strategy]] — all changes in one dev cycle to avoid mixed-state agents. This governs the test plan's structure.

---

## Impact Analysis

- **Files touched**: ~18 source files across 5 categories:
  - **4 role instruction templates**: `references/roles/{pm,qa,dm,dev}/instructions.md`
  - **L1 base**: `references/roles/instructions.md`
  - **4 base includes.yml**: `references/roles/{pm,qa,dm,dev}/includes.yml` (plus 20 variant includes.yml that inherit via `base_role:`)
  - **2 sub-skills deleted**: `references/sub-skills/common/tracker-protocol.md`, `references/sub-skills/roles/pm/delivery-fallback.md`
  - **3 DM sub-skills modified**: `delivery-packaging.md`, `issue-triage.md`, `task-pickup.md` (new file)
  - **5 Python scripts**: `tracker.py`, `config.py`, `cycle_pre.py`, `cycle_post.py`, `wizard.py`
  - **4 ancillary files**: `installer-files.txt`, `manifest.md`, `boot_remote.py`, `add_role.py`
  - **3 test files**: `test_compose.py`, `test_tracker_authority.py`, `test_installer_wiring.py`
- **Behavior changes**:
  1. Tracker-protocol content source changes from L2 per-role includes to L1 inline — functionally identical, composition source changes
  2. PM identity shifts from "combined PM/QA" to "coordination backstop" — authority mappings unchanged, narrative only
  3. DM skips QA: `isDraft` gate removed from delivery-packaging Step 0b
  4. DM merge-conflict handler added (new behavior) — transitions back to `in-progress`
  5. DM bug fixes and task pickup route to `pending-ship` not `pending-test`
  6. All role-absence fallback logic stripped from templates, scripts, and config
- **Dependencies**: #6055 (mandatory roles enforcement in compose.py — shipped), compose system for regeneration, no new external dependencies

---

## Side Effects

- **Risk 1: TC-1 false-positive from pre-existing L1 content** — Severity: **H** — **Mitigation**: The L1 base (`references/roles/instructions.md` line 12) already says "All timestamps come from `python references/scripts/cycle.py timestamp-short`." The TC-1 verification grep `timestamp\|status transition\|tracker` matches this pre-existing line, so it can't distinguish between "tracker-protocol content was added" and "only the old timestamp line is there." TC-1 needs to verify unique tracker-protocol markers like `check-gh`, `create-issue`, `list-issues`, or the discussion entries format (`**role**: message`).

- **Risk 2: TC-14 false-positive from existing "skip" behavior** — Severity: **H** — **Mitigation**: The current `delivery-packaging.md` line 50 says "If merge fails (`success: false`), comment on the issue and skip this item." This matches the TC-14 grep pattern `conflict\|merge.*fail\|in-progress` (line 13 has "in-progress" in the working state description), but the current behavior is *skip* — NOT transition back to `in-progress`. The test must verify that a `tracker.py transition ... pending-ship in-progress --role dm-lead` command exists, not just any mention of these tokens. The grep should target the actual transition command.

- **Risk 3: TC-29 blocked by missing LEGAL_TRANSITION** — Severity: **H** — **Mitigation**: DM `issue-triage.md` line 20 currently transitions `open → pending-test`. The test expects it to route to `pending-ship`. But `open → pending-ship` is NOT in `LEGAL_TRANSITIONS` (tracker.py lines 118-119: `"status:open": {"status:pending-test", "status:in-progress"}`). The implementation must either add `pending-ship` to open's legal targets or change DM's flow to `open → in-progress → pending-ship`. The test plan doesn't account for this.

- **Risk 4: Stale composed CLAUDE.md not caught by all TCs** — Severity: **M** — **Mitigation**: TC-16/TC-24 cover compose.py success, but don't verify that variant roles' composed output contains tracker-protocol. The regression risk section mentions this but no TC covers it.

- **Risk 5: config.py `sync_agents()` writes legacy PM/QA format** — Severity: **M** — **Mitigation**: TC-15 only covers `_parse_agents_v1`. The `sync_agents()` function (config.py lines 497-537, specifically line 524: `"- **PM/QA**: always present"`) still writes the legacy combined format. No test covers its update.

---

## Edge Cases

- **DM open→pending-ship legality gap**: DM bug fixes start at `open`. If DM skips QA, they should go to `pending-ship`. But the only legal targets from `open` are `pending-test` and `in-progress`. Either LEGAL_TRANSITIONS must add `pending-ship` to `open`'s targets, or DM must do a two-step `open→in-progress→pending-ship`. The test plan assumes the single-step path exists — it doesn't. Verdict: *Blocker — implementation design decision needed before test plan is complete.*

- **DM task-pickup override file doesn't exist**: TC-30 checks for `references/sub-skills/roles/dm/task-pickup.md` which must be created. The common `task-pickup.md` transitions to `pending-test` (line 23-26), so DM needs an override. But the override must also solve the legality gap above.

- **Variant role composed output verification**: TC-16 verifies base role CLAUDE.md files exist but doesn't check any variant role (e.g., dev-skill, pm-android). The regression risk section mentions this — add a smoke test for at least one variant.

- **cycle_post.py _do_version_bump fallback removal**: TC-34 correctly targets `dm_dir` removal. But the entire lines 437-453 (the `not dm_dir.exists()` branch that writes CHANGELOG) should also be removed or restructured — with DM always present, this code path is dead. The test plan doesn't specify whether to remove just the conditional or the entire fallback CHANGELOG-writing logic.

- **boot_remote.py regex mismatch risk**: TC-33 says "Code no longer depends on `**PM/QA**: always present` format." But boot_remote.py lines 126-136 use legacy regexes (`\*\*PM\*\*:\s*always present`, `\*\*QA\*\*:\s*always present`). If config.md migrates to Q-new17 format (nested agent entries), these regexes won't match and boot_remote falls back to `_parse_dev_agents()` which only reads the Dev Agents line — potentially missing PM, QA, DM roles entirely. The test needs to verify boot_remote works with the NEW config format, not just that it doesn't depend on the old one.

- **L4 project files may not exist in test environment**: TC-31 checks `.squidsquad/project/pm-instructions.md` and `.squidsquad/project/dm-instructions.md`. These are project-local, not in the `references/` tree. They may not exist in a clean checkout (they exist in *this* repo but not necessarily in all installs). The test should handle file-not-found gracefully.

---

## Integration Risks

- **Event contract derivation divergence**: RESEARCH.md flags that `derive_and_write_event_contracts` reads composed CLAUDE.md content and may produce different output when tracker-protocol moves from L2 include to L1 inline. No test case verifies contracts are stable post-change. Add a TC that runs contract derivation and diffs `emits` lists.

- **wizard.py output format**: CONTEXT.md says wizard.py must write separate PM and QA entries. The current wizard.py (line 627-630, `_render_agent()`) uses Q-new17 format which writes per-agent entries. But no test verifies that a fresh `wizard.py` run produces a config.md with separate PM and QA entries (not combined PM/QA). TC-15 only checks config.py parsing.

- **add_role.py DM directory check**: CONTEXT.md line 42 says "add_role.py:63: remove DM directory existence check." The current code (add_role.py line 63: `if (SQUIDSQUAD_DIR / "dm").exists():`) checks for DM's directory. With fixed team, DM is always present. No test case covers this removal.

- **Cross-role transition conflict**: What happens if QA transitions `pending-test → pending-ship` while DM simultaneously picks up the same item? The tracker.py state machine enforces sequential transitions via gh CLI (each transition reads current labels, removes old, adds new — the second transition would fail because the label it's trying to remove is already gone). This is safe by design, but no test verifies the failure mode is graceful (non-zero exit, clear error message, not a silent inconsistency).

- **Config.md migration path underspecified**: The upgrade steps say "Run `config.py update-agents-section`" but this function doesn't exist. There's only `sync_agents()` which uses legacy format. The implementation must create a migration function and the test plan should verify it.

---

## Upgrade & Migration

- **New config values**: None
- **New files**: `references/sub-skills/roles/dm/task-pickup.md` (DM-specific override) — referenced in TC-30 but the TC doesn't verify its CONTENT, only its existence
- **Template changes**: L1 base gains ~140 lines of tracker-protocol. All 4 role instructions lose `{{include: common/tracker-protocol}}`. All 24 includes.yml lose `common/tracker-protocol`. PM's includes.yml loses `roles/pm/delivery-fallback`.
- **Upgrade steps** (from RESEARCH.md):
  1. Stop all agents (harness `INTENT_STOPPED`)
  2. `git pull` the new references
  3. `compose.py deploy-all` — **will HARD ERROR if old composed files reference deleted includes** (acceptable per atomic migration pattern)
  4. `compose.py upgrade-soul <role>` for each role
  5. `config.py update-agents-section` — **function does not exist, must be created**
  6. Start agents via harness
- **Graceful degradation**: None. Old composed CLAUDE.md files will cause compose.py to ERROR on next deploy-all, forcing the upgrade. This is an intentional hard break.

---

## Open Questions

- **Q1**: How should DM bug fixes route to `pending-ship` when `open → pending-ship` is not a legal transition? — **Why**: TC-29 expects `pending-ship` in issue-triage.md, but tracker.py LEGAL_TRANSITIONS doesn't allow this. If unaddressed, DM bugs will fail tracker.py authorization. **Options**: (a) Add `pending-ship` to `open`'s legal targets with dm in ROLE_AUTHORITY, (b) DM does two-step `open → in-progress → pending-ship`, (c) DM's own bugs still go through QA. Decision needed before implementation.

- **Q2**: Should `cycle_post.py` remove the entire fallback CHANGELOG-writing branch (lines 437-453) or just the `not dm_dir.exists()` check? — **Why**: TC-34 only checks for the `dm_dir` check removal. With DM always present, the entire branch is dead code. Removing it entirely is cleaner but the test plan should specify which approach.

- **Q3**: What should `config.py update-agents-section` (referenced in upgrade steps) actually do? — **Why**: This function doesn't exist. The test plan's TC-15 references it as a migration step. Without it, users with legacy config.md (`**PM/QA**: always present`) have no automated migration path.

---

## Recommendation

**Feasible with caveats.** The test plan has the right breadth (36 TCs + 19 smoke tests) and correctly identifies most deletions and content moves. However, 8 TCs need stronger verification commands (TC-1, TC-14, TC-29, TC-33), 3 acceptance criteria from CONTEXT.md have no test coverage (add_role.py DM check, wizard.py output, event contracts), and TC-29 exposes a design gap in tracker.py's LEGAL_TRANSITIONS that must be resolved before the test can pass. I recommend: (1) fix the 8 weak verifications before approval, (2) add TCs for the 3 uncovered acceptance criteria, (3) resolve the `open → pending-ship` legality question (Q1), and (4) create `config.py update-agents-section` before writing its test.

---

## Vault Candidates

- **Type**: learning — "DM draft gate was redundant — tracker authority already enforced the invariant" — **Why**: The isDraft gate removal demonstrates that when the state machine already enforces a constraint, duplicating it in agent instructions creates false negatives. This should inform future feature design: check whether tracker.py already prevents the bad state before adding instruction-level gates.

- **Type**: pattern — "Tests must verify unique content markers, not common tokens" — **Why**: TC-1's grep for `timestamp|status transition|tracker` matches pre-existing L1 content, creating a false-positive risk. Future test plans should verify using unique identifiers (e.g., `check-gh`, `create-issue`) that only appear in the new content. This applies broadly to any verification that greps for content presence.

- **Type**: decision — "tracker-protocol is L1, not a common sub-skill" — **Why**: This is an architectural decision with permanent implications. The tracker protocol is universal (every agent uses it regardless of role), making it a natural L1 concern. Any future protocol-like content that every agent needs should be L1, not a swappable sub-skill.

- **Type**: learning — "LEGAL_TRANSITIONS must be updated before agent sub-skills reference new transitions" — **Why**: TC-29 exposes a classic ordering dependency: the sub-skill wants DM to transition `open → pending-ship`, but tracker.py's LEGAL_TRANSITIONS doesn't allow it. When changing agent workflows, the state machine must be updated first (or simultaneously), and tests must verify both layers agree.

- **Type**: pattern — "atomic migration requires all reference removal before file deletion" — **Why**: The test plan correctly verifies that deleted files are removed from includes.yml, instructions.md, installer-files.txt, and manifest.md before the files themselves are deleted. This atomic approach prevents compose.py errors on deploy-all. Future structural moves should follow this pattern: remove all references → delete file → in a single commit.