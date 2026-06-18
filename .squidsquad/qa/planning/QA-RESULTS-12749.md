# QA-RESULTS-12749 — DM-ARCH layered DM refactor

**Verdict: PASS (all 8 ACs) → pending-ship.** 2026-06-18 00:55. Append-only.
**Branch**: `squidsquad/dm-arch` @ `c85e1da5a` (PR #12689, MERGEABLE/CLEAN).
**Verification instance**: main-landing state (config `dm/skill` + L4 release policy + statusline live-sync) applied to
working tree per skill's durable §main-landing spec; `compose.py deploy-all` (EXIT=0); composed `.squidsquad/dm/CLAUDE.md`
inspected directly. Branch working tree reverted to stripped state after testing.

## AC walk

- **AC1 — PASS.** Composed DM L2 spine = 8 bare-H3 anchors at lines 486–545: `detect-ready / pre-flight / package /
  confirm-landing / generate-report / contribute-knowledge / publish / handle-failure`. `grep step:cycle/version-bump`
  on composed DM → exit 1 (clean). All three `Shipped Since Last Bump` occurrences are confined to the L4
  `### Release policy` / `### Version Bumps` sections (lines 663–682) — none in the L2 spine band.

- **AC2 — PASS.** L4 batch-10 policy composes into the DM (line 667). No-L4 compose (L4 file moved aside, redeploy):
  ship-on-ready default present (1), `Shipped Since Last Bump`/`batch of 10`/`### Release policy` → 0,
  `step:cycle/version-bump` → 0. Default-when-silent = ship-on-ready confirmed.

- **AC3 — PASS.** Composed DM `step:cycle/package` (line 500) = "merge-to-main + compose" (merge feature branch +
  `compose.py deploy`); `step:cycle/publish` (line 534) = ship-comment + CHANGELOG. Required wiring `dm`→`dm/skill`
  L3 domain (`config.md` `**dm**: dm/skill`, bullet parser extended for `<class>/<domain>`). Identity preserved:
  `config.py alias dm` → `dm` (c12-F1 fix verified — no tracker corruption).

- **AC4 — PASS.** `verification.md:121` increment removed (replaced with explicit "Do NOT touch any release counter");
  `verifier/responsibility.md` disclaims release state; `statusline.sh` PM ship-counter block removed.
  Counter/alias test set (feat_1328 + config_functions + config_aliases_registry + cycle_post + cycle_pre + feat_9772 +
  git_ops): **539 passed**. `test_qa_owns_ship_counter` correctly inverted — asserts the increment command is ABSENT
  (no false-green). Two statusline-sync tests failed on the branch (live `.squidsquad/statusline.sh` is main-landing,
  stripped) → **pass after applying the documented live-copy sync** (2 passed). Counter machinery (config field,
  cycle_post reset) correctly retained as L4-DM-owned.

- **AC5 — PASS.** Named docs all L4-qualified: AGENT-RUNTIME role-table (22) + idle-subloop (1097); ARCHITECTURE
  DM-row (215) + Feature-Lifecycle diagram + deep-dive (217); COMPOSE-ARCH op-grammar-consumer note; README indexes
  DM-ARCH (151). Grep-clean: `verifier increments` → 0, `PM coordinates bump` → 0. Surviving "version bump" refs are
  correct DM attributions, the now-L4-gated version-bumps sub-skill, or other role variants (dm/fullstack) — none assert
  a universal-DM bump duty.

- **AC6 — PASS.** `compose.py deploy-all` green (4 roles, EXIT=0). Fresh DM comprehension agent (file-only context,
  `tests/comprehension/12749_spec.json`) answered 4/4: **CQ1 "when do you bump?" → "only because THIS project's L4
  policy says batch-of-10 → minor bump; a generic DM never bumps — ships on ready"** (NOT a universal rule); CQ2 DM owns
  + increments at publish, verifier doesn't; CQ3 package = merge-to-main + compose; CQ4 contribute-knowledge = vault
  capture at two granularities (part-level + broad end-to-end). Critical AC6 assertion satisfied.

- **AC7 — PASS.** DS-review covered all 6 changes across 2 rounds (c12 = changes 1–2, 7 findings; c3456 = changes 3–6,
  5 findings; 12 total). Findings corroborated against committed code: c12-F1 `get_alias` strips `/domain` (verified);
  c12-F5 multi-slash domain rejection present in `config.py`; c12-F2/3 delivery-packaging + version-bumps re-wired into
  L3/L4 (not deleted); c3456-F2 `version-bumps.md` L4-conditional qualifier present. F4-decline (no counter on DM
  statusline) is correct — it would contradict AC4.

- **AC8 — PASS.** `git diff --name-status` shows only one added file, `docs/DM-ARCH.md`; all else modifications.
  `references/installer-files.txt` tracks only `references/docs/*` — top-level `docs/*.md` (ARCHITECTURE, AGENT-RUNTIME,
  DM-ARCH) are NOT installer-shipped. So the new DM-ARCH.md needs no manifest entry; installer-files.txt correctly
  unchanged. L3 dm/skill edits in-place; L4 dm.md project-local (not shipped).

## Pre-existing / out-of-scope (NOT #12749 gaps)
- `test_compose_author_comments_11142::test_10360_cleanup_markers_preserved` FAILS — **confirmed pre-existing on clean
  origin/main** (worker/instructions.md missing `#10360-cleanup:` markers; untouched by this branch). Not a regression.

## Non-blocking observations (flagged, not gaps)
1. `README.md:23` ("DM handles delivery: … version bumps, git tags") is accurate for SquidSquad's L4 policy but could
   cross-reference L4 for parity with the other reframed docs — cosmetic, not stale/false.
2. DS-review (AC7) was grouped into 2 rounds rather than literally one-per-change; all 6 changes were covered and
   findings corroborated, so intent is met.
3. Skill's handoff said "no file add/del/rename" — `docs/DM-ARCH.md` IS an add, but the conclusion (installer-files
   unchanged) is correct since top-level docs aren't installer-shipped.

## SHIP CONTINGENCY (carry to DM)
Verdict is **contingent on the main-landing batch landing on main in the SAME window as the #12689 merge**: (1)
`config.md` `**dm**: dm/skill`; (2) L4 `.squidsquad/project/dm.md` release policy; (3) live `.squidsquad/statusline.sh`
synced to `references/statusline.sh`; (4) recomposed `.squidsquad/{dm,pm,qa,skill}/CLAUDE.md`. Skill posted the durable
diff in #12749 discussion. PR is MERGEABLE/CLEAN. Merge deferred to DM. Counter NOT bumped (and this task removes the
verifier increment entirely).
