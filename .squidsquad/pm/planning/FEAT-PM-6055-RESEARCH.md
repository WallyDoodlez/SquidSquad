Now I have a comprehensive understanding of the codebase. Let me compile the findings.

```markdown
# FEAT-PM-6055 Research — Enforce Role Separation PM/QA/DM

## Summary

This research maps every L2 instruction path where one role absorbs another's duties and assesses the impact of removing those fallbacks. Two primary fallback chains were identified: **PM→QA** (verification fallback) and **PM→DM** (delivery fallback). Both are triggered by directory-existence checks in the PM agent's cycle instructions. Removing silent fallback introduces a hard requirement for explicit human opt-in when roles are absent — surfacing the gap rather than silently absorbing work. The primary risk is breaking solo/minimal team compositions that currently rely on these fallbacks to function end-to-end.

Recommendation: Replace silent directory-existence-gated fallbacks with explicit configuration flags (`qa_absent_opt_in`, `dm_absent_opt_in`) in `config.md`. When a required role is absent and no opt-in flag is set, the PM cycle should surface a warning and block verification/delivery steps rather than silently absorbing them. Solo compositions (PM only) require the human to explicitly acknowledge "I understand PM self-verifies and self-delivers — no independent QA or DM check."

## Vault Context

- **BRIEFING.md priorities**: #6055 Enforce role separation PM/QA/DM directly matches this task. #5620 L3 PM stuck-rebase recovery is tangentially relevant (PM boundary enforcement for git ops). #5855 Vault as static decision log constrains how findings are preserved.
- **Related decisions**: [[decision-deterministic-testing]] — Human-directed requirement that verification must be deterministic, not subjective. PM self-verifying directly violates "independent check" principle behind this decision. [[decision-self-healing-sentinel]] — Systems should detect gaps and file bugs. Role absence should trigger gap detection, not silent work absorption. [[decision-sub-skill-architecture]] — PM sub-skills include `delivery-fallback` and `testing-and-verification`; these are the files to modify.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — Presence checks should be deterministic (script-verified), not agent-judgment-based.
- **Human preferences**: "Systems should self-heal: detect stuck states → unstick immediately → file root-cause bug → agent fixes gap." Role absence should trigger self-healing (warn → human opt-in → proceed), not silent absorption. "PM should not intervene in code or branch management" — and by extension should not self-verify or self-deliver without explicit opt-in.
- **Related learnings**: [[learning-atomic-migration-strategy]] — Template changes across multiple roles must ship atomically to avoid coordination breakage. This task touches PM, QA, DM, and cycle scripts simultaneously.

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/roles/pm/testing-and-verification.md` (lines 1-5, 99, 104) — PM→QA fallback gating logic and zero-gap gate enforcement
  - `references/sub-skills/roles/pm/delivery-fallback.md` (lines 1-7, 51) — PM→DM fallback gating logic and version bump sequence
  - `references/roles/pm/instructions.md` (line 5, 105) — PM role description mentions QA fallback; Step 6c references DM fallback
  - `references/roles/qa/instructions.md` (line 19) — QA's responsibility statement references PM delivery fallback
  - `references/roles/pm/manifest.yaml` (line 5) — "Routes to every other role and falls through to DM when nothing else is present"
  - `references/roles/pm/SOUL.md` (line 11) — "almost half a QA agent" wording blurs role boundary
  - `references/roles/pm/prohibitions.md` (lines 1-8) — Add prohibition against self-verification and self-delivery
  - `references/roles/dm/prohibitions.md` — No changes needed (DM prohibitions are clean)
  - `references/roles/qa/prohibitions.md` — No changes needed (QA prohibitions are clean)
  - `references/scripts/cycle_pre.py` (lines 603-604, 767-768) — `qa_present`/`dm_present` signals fed to PM
  - `references/scripts/cycle_post.py` (lines 437-453) — PM fallback CHANGELOG writing when DM absent
  - `.squidsquad/config.md` — New config values for opt-in flags
  - `references/scripts/config.py` (lines 392-404) — QA/DM presence detection logic may need opt-in flag awareness
  - `references/sub-skills/roles/pm/pipeline-sentinel.md` (line 2) — "This step runs every cycle regardless of QA presence" — should it?
  - `references/sub-skills/roles/pm/improvement-scan.md` — PM improvement scan; may need role-gap awareness

- **Behavior changes**:
  1. PM cycle: When QA directory absent, **STOP at verification step** with warning instead of silently running Steps 3-6
  2. PM cycle: When DM directory absent, **STOP at delivery step** with warning instead of silently running Step 6d
  3. Both stops surface explicit opt-in requirement to human
  4. PM manifest description updated to remove "falls through to DM"
  5. PM SOUL "almost half a QA agent" revised to "holds QA accountable, does not replace QA"
  6. Zero-gap gate enforcement: PM must not be the one verifying its own planned work
  7. cycle_post.py CHANGELOG fallback gated on opt-in flag, not just directory absence

- **Dependencies**:
  - `compose.py` — `_collect_all_roles()` (line 1112-1120) and `deploy_role()` (line 811-873) must be audited: does deployment break if roles reference sub-skills for absent roles?
  - `boot_remote.py` (lines 128-132) — QA/DM presence detection for remote boot may need opt-in awareness
  - `config.py` — `parse_agent_entries()` (lines 340-406) presence detection feeds into multiple scripts
  - `cycle_pre.py` — `_build_pm_input()` sends presence signals; must still compute presence but not gate on it (PM instructions gate instead)

## Side Effects

- **Risk 1**: Solo teams (PM only, no dev/QA/DM) **completely break** — no verification or delivery can happen without human opt-in. Severity: **H**. Mitigation: First-time startup with solo composition should detect this and prompt the human with a clear explanation: "You're running in solo mode. PM will plan, verify, and deliver its own work. This means no independent QA check and no dedicated delivery manager. Type 'I understand' to continue." Record opt-in in config.md. This must be a one-time step, not per-cycle.
- **Risk 2**: Minimal teams (PM+dev, no QA/DM) lose QA verification. PM verification fallback was the only quality gate. Severity: **H**. Mitigation: Same opt-in flow as solo, but surface that dev work will ship without QA verification. Consider whether dev should be allowed to mark its own work `Pending Ship` when QA is absent (currently dev marks `Pending Test` and waits).
- **Risk 3**: Standard teams (PM+dev+QA, no DM) lose delivery. PM delivery fallback was the only path to `Shipped`. Severity: **M**. Mitigation: Opt-in prompt at startup. DM-less teams may be intentionally lightweight — this is the least problematic fallback removal because QA still provides independent verification, and delivery is mechanical docs/CHANGELOG work.
- **Risk 4**: QA agent crashes (directory exists but agent dead). Current check at `testing-and-verification.md` line 3 checks both directory existence AND `current-state` file exists. If `current-state` exists but is stale (QA crashed), PM skips verification, but QA isn't actually working. Severity: **M**. Mitigation: The health check in `pipeline-sentinel.md` detects stalled agents. PM should cross-reference `qa_present` with health data before deciding to skip verification. If QA directory exists but health is `stalled`/`stopped`, treat as absent and surface the warning.

## Edge Cases

- **QA deployed but not running (draft/stale)**: PM checks `.squidsquad/qa/` directory AND `current-state` file. If directory exists but `current-state` is stale (>2x interval), PM should NOT skip verification — QA is effectively absent. Currently line 3 of `testing-and-verification.md` only checks file existence, not freshness. Enhancement: check `current-state` mtime or cross-reference with `health_check.py` output already in `cycle-input.json`.
- **DM deployed but not running**: Same pattern as QA. PM skips delivery but DM isn't delivering. Coordinate with health check data.
- **Branch workflow enabled, no QA, PM falls back**: PM must handle PR merge during verification (Step 6, item 4). Without QA, PM would merge PRs — which PM SOUL says "Never close or merge PRs directly." This creates a direct contradiction between fallback behavior and PM boundaries.
- **Human adds QA/DM mid-session**: New opt-in flags should auto-clear when the role directory appears (or vice versa). If human installs QA after previously opting into QA-less mode, the opt-in should reset so QA verification is used.
- **Multiple PM cycles in absence**: Once the human opts into "no QA" or "no DM" mode, PM should NOT re-prompt every cycle. The opt-in persists until the role is installed.
- **`delivery:skip` tasks when DM absent**: PM delivery fallback checks `delivery:skip` before performing delivery work. If delivery is blocked entirely (no DM, no opt-in), `delivery:skip` items should still transition to `Shipped` — they require zero delivery work. This is an exception to the block rule.

## Integration Risks

- **Compose pipeline**: `compose.py deploy pm` must still succeed when `delivery-fallback.md` and `testing-and-verification.md` are modified. These are `{{include}}` directives in PM's `CLAUDE.md` — modifying their content does not affect the composition mechanism itself.
- **Cycle scripts**: `cycle_pre.py` sends `qa_present` and `dm_present` to PM. If PM now needs to check opt-in flags, it also needs the flag values in `cycle-input.json`. Add `qa_absent_opt_in` and `dm_absent_opt_in` fields to `_build_pm_input()`.
- **QA instruction dependency**: QA's `instructions.md` line 19 says "If DM absent, PM's delivery fallback handles it." This is QA assuming PM→DM fallback exists. If we remove silent fallback, QA needs updated language: "If DM absent, PM will surface the gap to the human. Work remains at Pending Ship until DM is available or human opts into PM delivery."
- **Tracker status flow**: Without DM, `Pending Ship` items have no path to `Shipped` unless human opts in. Blocked items at `Pending Ship` accumulate. The pipeline sentinel (`pipeline-sentinel.md`) already detects stalled `Pending Ship` items (line 37) — this would catch the accumulation.
- **Event bus**: If role absence events need to be emitted (e.g., "QA absent — verification gap"), verify the event schema supports this. The event bus (Harness Phase 2+3, #5622, #5868) has infrastructure for status events.
- **#5932 external code review loop**: This task depends on #6055 — the external review loop's role in the pipeline may intersect with QA verification boundaries.

## Upgrade & Migration

- **New config values**:
  - `qa_absent_opt_in`: `no` (default) — Human must set to `yes` to allow PM verification fallback
  - `dm_absent_opt_in`: `no` (default) — Human must set to `yes` to allow PM delivery fallback
  - Both should live under a new `## Role Separation` section in `config.md`

- **New files**: None — all changes are modifications to existing templates and scripts.

- **Template changes**:
  - `testing-and-verification.md`: Replace silent directory check with opt-in check + warning
  - `delivery-fallback.md`: Replace silent directory check with opt-in check + warning
  - `pm/instructions.md`: Update role description header
  - `pm/SOUL.md`: Revise "almost half a QA agent" wording
  - `pm/prohibitions.md`: Add "Never verify your own planned work unless human has explicitly opted into QA-less mode"
  - `qa/instructions.md`: Update DM fallback reference

- **Upgrade steps**: Running installs upgrading to this change will have existing PM agents with old instructions until recompose. The upgrade process must:
  1. Detect if QA/DM are absent
  2. If absent, prompt human for opt-in and set config flags before first PM cycle
  3. Run `compose.py deploy pm` (and `qa`/`dm` if present) to deploy updated instructions
  4. This should be part of `/squidsquad-upgrade` or the recompose flow

- **Graceful degradation**: If user doesn't upgrade, old PM agents continue with silent fallback behavior. This is backward-compatible — the change is opt-in enforcement. Existing teams with absent QA/DM will keep working until they recompose with new templates.

## Open Questions

- **Q1**: Should the opt-in be per-role or a single "solo mode" flag? — **Why**: Per-role granularity allows standard teams (no DM) to work without DM while still having QA. A single flag is simpler but less flexible. Standard composition (PM+dev+QA, no DM) is a valid lightweight team shape.
- **Q2**: When QA is absent and human opts into PM verification, does PM also take over PR merge responsibility (currently QA's job)? — **Why**: PM's SOUL explicitly prohibits merging PRs (line 78-79). PM fallback would need to merge PRs during verification (Step 6, PR Flow gate). This creates a hard contradiction with PM boundaries that needs resolution.
- **Q3**: Should `Pending Ship` items accumulate indefinitely when DM absent and no opt-in? — **Why**: Work completes verification but never ships. This could be correct (human must approve delivery) or could create a backlog problem. The pipeline sentinel would detect and nudge, but should there be a timeout after which the system escalates more aggressively?
- **Q4**: Does the zero-gap gate lose meaning when PM both plans and verifies? — **Why**: The zero-gap gate was designed for independent QA enforcement. If PM verifies its own plans, every gap that PM missed during planning is also missed during verification. The gate becomes ceremonial. Should the opt-in warning explicitly state "zero-gap gate is weaker without independent QA"?
- **Q5**: Should `pipeline-sentinel.md` step header "This step runs every cycle regardless of QA presence" remain true? — **Why**: If QA is absent and PM is blocked from verification, the pipeline sentinel is PM's only remaining oversight tool. It should still run.

## Recommendation

**Feasible with caveats.** The fallback paths are well-isolated (two sub-skills, one script function). The primary implementation risk is breaking solo/minimal teams. Mitigation requires:

1. A clear human opt-in flow at startup (not buried in docs)
2. Granular per-role opt-in flags (not a single "solo" toggle)
3. Addressing the PR merge contradiction for PM→QA fallback (Q2)
4. Updating QA's instructions to not assume PM→DM fallback exists
5. Health-check integration so stalled-but-present agents don't cause false skip

The PM SOUL "almost half a QA agent" identity creates cultural permission for boundary-blurring. That line should be revised to "PM holds QA accountable for verification quality — but does not replace QA" to reinforce separation.

## Vault Candidates

- **Type**: decision — Role absence surfacing over silent absorption: when a pipeline gate lacks its designated enforcer, stop and warn rather than silently reassigning work — **Why**: This is an architectural principle that applies beyond PM/QA/DM. Any role-based pipeline with separation of concerns should surface gaps. Relevant to future role types (designer, security auditor, etc.).
- **Type**: pattern — Opt-in flags for degraded team compositions: `config.md` flags that a human sets once to acknowledge risk, checked each cycle by agents — **Why**: This pattern is reusable for any future team shape where a role is intentionally absent. Prevents per-cycle prompting while maintaining an explicit audit trail.
- **Type**: learning — Directory-existence is a weak presence signal for agent liveness: `.squidsquad/<role>/` directory existing doesn't mean the agent is running. Health check data is more reliable — **Why**: This bug exists in current PM instructions (line 3 of `testing-and-verification.md` checks directory + `current-state` file existence, not freshness). Should be a general guidance: always cross-reference with health data for liveness decisions.
- **Type**: learning — Boundary statements in agent SOULs create real behavioral guardrails: PM's SOUL says "Never close or merge PRs directly" but PM→QA fallback requires merging PRs during verification. When boundaries contradict fallback behaviors, agents face impossible instructions — **Why**: This is a general lesson about instruction design: prohibitions and fallback responsibilities must be consistent, or agents will pick one and violate the other unpredictably.
```