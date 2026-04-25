# FEAT-PM-2487 Research — Wire Cycle Runner sub-skill into all agent templates

## Summary
Researched the existing “cycle runner” transport layer and how agent templates are currently composed from sub-skills. The cycle runner already exists as a sub-skill doc (`references/sub-skills/common/cycle-runner.md`) plus mechanical scripts (`references/scripts/cycle_pre.py`, `cycle_post.py`, and shared `cycle.py`) with test coverage. However, it is **not actually composed into any role template** today (none of the role entry templates include it), and the vault decision note indicates it was “proposed” and “not yet implemented” even though the scripts now exist—so the missing piece is composition + clear interaction rules with existing Ralph Loop steps.

Recommendation: **conditionally include** the cycle-runner sub-skill in *all* role templates via the composition manifest (or directly in each role entry file), but keep it **feature-flagged** (default off) as the sub-skill already specifies. Do **not** remove existing Ralph Loop steps; instead, cycle-runner should act as an optional “transport wrapper” that (a) replaces the mechanical parts of Step 1 + Step 5 and (b) coexists with role-specific creative steps (triage/implement/verify/deliver/etc.). Primary risks are (1) confusing dual instructions if the flag is on but the template still describes manual steps, and (2) schema drift: `cycle_post.py` only validates a minimal subset of `cycle-output.json`, so role-specific needs must be treated as optional extras and/or documented.

## Vault Context
- **BRIEFING.md priorities**: none directly about cycle-runner; relevant constraints include “Never ship with failed test cases” and Windows-safe atomic writes (`.squidsquad/vault/BRIEFING.md:26-37`).
- **Related decisions**: [[decision-cycle-runner-architecture]] — constrains this task to a “mechanical shell / agent creative core split” with `cycle_pre.py` writing `cycle-input.json` and `cycle_post.py` consuming `cycle-output.json` (`.squidsquad/vault/galaxy/decision-cycle-runner-architecture.md:20-25`).
- **Related patterns**: Sub-skill build-time composition via `references/sub-skills/manifest.md` include order and `{{include: ...}}` directives (`references/sub-skills/manifest.md:1-14`).
- **Human preferences**: Windows 11 + prefers direct/mechanical checks over indirect state files (`.squidsquad/vault/areas/human-profile.md:29-34`), which aligns with cycle runner moving mechanics into deterministic scripts.
- **Related learnings**: [[learning-commit-code-state-exclusion]] is referenced by the decision as motivation (branch switching bugs) (`decision-cycle-runner-architecture.md:26-31`).

## Impact Analysis
- **Files touched**:
  - `references/sub-skills/manifest.md` — currently lists `common/cycle-runner` in inventory and dev composition order, but it is not actually included in role templates (inventory: `manifest.md:163-191`; dev order mention: `manifest.md:16-44`).
  - Role entry templates (to add `{{include: common/cycle-runner}}`):
    - `references/roles/dev/CLAUDE.md` (currently no include; see includes around `dev/CLAUDE.md:70-95`)
    - `references/roles/pm/CLAUDE.md` (no include; see includes around `pm/CLAUDE.md:77-133`)
    - `references/roles/qa/CLAUDE.md` (no include; see includes around `qa/CLAUDE.md:79-112`)
    - `references/roles/dm/CLAUDE.md` (no include; see includes around `dm/CLAUDE.md:78-114`)
    - `references/roles/designer/CLAUDE.md` (no include; see includes around `designer/CLAUDE.md:78-120`)
  - (Docs already exist, likely no changes required but may need alignment wording):
    - `references/sub-skills/common/cycle-runner.md` (feature flag + schema guidance; `cycle-runner.md:4-65`)
  - (Scripts exist; only touched if schema/behavior changes are needed):
    - `references/scripts/cycle_pre.py`
    - `references/scripts/cycle_post.py`
    - `references/scripts/cycle.py`
- **Behavior changes**:
  - When `Cycle Runner: yes` in config, agents will be instructed to run:
    - `python references/scripts/cycle_pre.py [ROLE]` before creative work (`cycle-runner.md:10-21`)
    - write `.squidsquad/[ROLE]/cycle-output.json` and run `python references/scripts/cycle_post.py [ROLE]` after (`cycle-runner.md:35-65`)
  - Mechanical operations shift from “agent does git/tracker/iteration logging manually” to “scripts do it”, especially:
    - git pull handled by `cycle_pre.py` (`cycle_pre.py:97-108`, `main:748-750`)
    - tracker transitions/comments + iteration log + commit/push handled by `cycle_post.py` (`cycle_post.py:364-382`)
- **Dependencies**:
  - `cycle_pre.py` depends on other scripts and external tools:
    - `references/scripts/config.py` via `_config_get()` (`cycle_pre.py:62-68`)
    - `references/scripts/git_ops.py` for pull (`cycle_pre.py:97-107`)
    - `references/scripts/tracker.py`, `triage.py`, `health_check.py` and `gh` CLI (`cycle_pre.py` role builders e.g. PM/QA/DM sections)
  - `cycle_post.py` depends on:
    - `references/scripts/tracker.py` for transitions/comments (`cycle_post.py:108-155`)
    - `references/scripts/cycle.py` for iteration logs (`cycle_post.py:157-180`)
    - `references/scripts/git_ops.py` for commit/push and PR creation (`cycle_post.py:182-246`, `207-214`)
    - `references/scripts/config.py` + repo files for version bump (DM) (`cycle_post.py:248-301`)

## Side Effects
- **Risk 1**: Dual-instruction confusion (manual Ralph Loop vs cycle runner) — Severity: **H** — Mitigation: In `common/cycle-runner.md`, add explicit “When enabled, skip Step 1 pull-latest + Step 5 git-commit + iteration-log instructions; do creative steps only” and ensure the include is placed near the top of “The Ralph Loop” so it’s seen before step-by-step instructions.
- **Risk 2**: Role mismatch for `[ROLE]` placeholder in PM/DM templates — Severity: **M** — Mitigation: `cycle-runner.md` uses `.squidsquad/[ROLE]/...` and `cycle_pre.py [ROLE]` (`cycle-runner.md:10-21, 37-62`). PM/DM templates intentionally do **not** substitute `[ROLE]` (manifest note `manifest.md:145-156`). Therefore, the cycle-runner sub-skill must be included in a way that uses the *actual role name* (pm/qa/dm/designer) or avoids `[ROLE]` placeholders for those roles (e.g., provide role-specific variants or parameterize at composition time).
- **Risk 3**: cycle-output schema drift / under-validation — Severity: **M** — Mitigation: `cycle_post.py` validates only `role`, `cycle_number`, `cycle_type`, and transition structure (`cycle_post.py:31-100`). Document that all other fields are optional and ignored by the script unless implemented; add tests if expanding required fields.

## Edge Cases
- **PM planning suppression**: PM template has “planning phase suppression” logic in Step 1c (`pm/CLAUDE.md:87-96`). `cycle_pre.py` *does* parse `**Phase**:` and sets `suppressed` in working_state (`cycle_pre.py:162-205`) and tests cover PM suppression parsing (`tests/test_cycle_pre.py:95-107`), but there is no end-to-end instruction mapping yet. Handle by: when Cycle Runner is enabled, PM creative phase should check `cycle-input.json.working_state.suppressed` and immediately write `cycle-output.json` with `cycle_type: "suppressed"` and minimal summary, then run `cycle_post.py pm`.
- **QA branch switching**: `cycle_pre.py` will auto-checkout the first pending-test item branch when branch workflow is enabled (`cycle_pre.py:568-587`). QA template currently assumes it stays on main and commits to main. `cycle_post.py` forces QA back to main before committing (`cycle_post.py:231-241`). Ensure instructions clarify that QA may be moved to a feature branch during pre-cycle but post-cycle will normalize.
- **Missing cycle-output.json**: `cycle_post.py` exits 0 with warning and sets status bar idle if output missing (`cycle_post.py:338-345`). This is good for crash tolerance, but agents must be instructed that “no output” means “no post-processing happened” (tracker transitions/commits won’t occur).

## Integration Risks
- **Template composition vs runtime substitution**: The manifest explicitly warns `[ROLE]` is ambiguous and not substituted for PM/DM (`references/sub-skills/manifest.md:145-156`). Since `cycle-runner.md` is written with `[ROLE]` placeholders, naive inclusion into PM/DM/designer templates will produce incorrect paths/commands. This is the biggest integration risk and likely why it “was never composed.”
- **Git workflow interactions**: `cycle_post.py` has special handling for skill branch workflow with split commits (`cycle_post.py:193-230`). If the skill agent’s template still instructs manual `git-commit` sub-skill actions, it may conflict with cycle_post’s expectations.

## Upgrade & Migration
- **New config values**: none required by scripts, but the sub-skill expects a config flag named `Cycle Runner` in `config.md` (`cycle-runner.md:4-6`). Verify whether `references/scripts/config.py` supports that key name/casing before rollout (not checked in this research).
- **New files**: none (scripts and sub-skill already exist).
- **Template changes**:
  - Add `{{include: common/cycle-runner}}` to all role entry templates listed above.
  - Potentially add role-specific cycle-runner variants (e.g., `common/cycle-runner-pm.md`) if `[ROLE]` ambiguity can’t be solved via composition substitution.
- **Upgrade steps**:
  - Recompose templates during upgrade so `.squidsquad/<role>/CLAUDE.md` gains the new section (per composition architecture in `manifest.md:10-13`).
  - If Cycle Runner is enabled, ensure `.squidsquad/<role>/cycle-input.json` and `.squidsquad/<role>/cycle-output.json` are not blocked by permissions and that `gh` CLI is available.
- **Graceful degradation**: If user doesn’t upgrade, nothing changes. If they upgrade but keep `Cycle Runner: no` (default per `cycle-runner.md:4-6`), agents should continue using existing Ralph Loop steps.

## Open Questions
- **Q1**: How should `[ROLE]` be resolved in PM/DM/designer templates for cycle runner commands/paths? — **Why**: If unresolved, the instructions will literally tell PM to run `cycle_pre.py [ROLE]` and read `.squidsquad/[ROLE]/cycle-input.json`, which is unusable and will break adoption.
- **Q2**: Should cycle-runner *replace* `common/pull-latest`, `common/git-commit`, `common/iteration-log`, and status-bar instructions when enabled, or coexist? — **Why**: Coexistence without explicit “skip these steps” will cause duplicated pulls/commits/logs and inconsistent tracker state.
- **Q3**: Do we want `cycle_post.py` to enforce additional required fields per role (PM pipeline sentinel results, QA verification summary, skill test results), or keep schema permissive? — **Why**: Too strict breaks agents; too loose risks losing critical role outputs.
- **Q4**: How to handle role-specific “always-run” steps (e.g., PM pipeline sentinel `references/sub-skills/pm-specific/pipeline-sentinel.md` referenced in manifest `manifest.md:54-55`) under cycle runner? — **Why**: If cycle runner suppresses cycles or changes step ordering, sentinel checks might stop running, regressing safety guarantees.
- **Q5**: What is the rollout plan to avoid breaking agents mid-cycle when templates change? — **Why**: Agents may be in the middle of a manual cycle; switching instructions could cause partial commits or missed tracker transitions.

## Recommendation
Feasible with caveats. The mechanical scripts are real and tested, but composition into templates will break unless the `[ROLE]` placeholder ambiguity is resolved for PM/DM/designer. Implement as a feature-flagged include with **role-correct commands/paths**, and explicitly define which existing sub-skills are skipped when Cycle Runner is enabled (mechanical steps) vs retained (creative/role-specific work).