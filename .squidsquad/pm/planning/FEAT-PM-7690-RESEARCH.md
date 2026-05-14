Now I have a thorough understanding of the codebase. Let me compile the research document.

```markdown
# FEAT-PM-7690 Research — Update squidsquad-setup flow for event-driven architecture (#7630)

## Summary

This research analyzes what the current squidsquad-setup flow does, identifies every file and step that references cycles/loops/intervals, determines what new setup steps are needed for event-driven mode, and maps the upgrade/migration path for existing installs.

The setup flow lives primarily in **`references/wizard/WIZARD.md`** (the install runbook) backed by **`references/scripts/wizard.py`** (mechanical helpers). There is no `references/skills/squidsquad-setup/` directory — the setup skill is a Claude Code command at **`.claude/commands/squidsquad-setup.md`** which delegates directly to WIZARD.md. The architecture decisions for #7630 are fully documented in **`.squidsquad/pm/planning/FEAT-PM-7630-CONTEXT.md`** (locked decisions) and **`.squidsquad/pm/planning/FEAT-PM-7630-RESEARCH.md`** (gap review). The gating constraint is that the Monitor tool (Claude Code v2.1.98+) has not been validated — the entire wake model lock depends on it.

**Recommendation**: Feasible with caveats. The setup flow changes are straightforward (add one question branch, new config fields, tweak review screen). The real risk is that the setup flow must not be the first component changed — Phase 1.5 infrastructure (event bus disk persistence, clone discovery fix, per-role queues, thread safety) and Monitor tool validation must complete before setup can offer event-driven mode. Until then, setup should continue producing cycle-based configs with event-driven gated behind a `--experimental-event-driven` flag or similar opt-in.

## Vault Context

- **BRIEFING.md priorities**: #7630 is the active top priority — "Event-driven agent architecture — harness owns cycle, agents react to events (pending, high, role:skill) — supersedes #6056, #5775, #5613"
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 split mechanical/creative into cycle_pre/cycle_post; #7630 completes the transfer by absorbing all mechanical operations into harness. [[decision-self-healing-sentinel]] — two-tier self-healing (unstick + file root-cause bug) must be preserved in event-driven model. [[decision-improvement-loop-philosophy]] — improvement scan's role as proactive discovery (layer 3) must survive the architectural transition; trigger changes from quiet-cycle counter to `scan-due` event.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — directly applicable: all cycle orchestration prose becomes harness code. [[learning-atomic-migration-strategy]] — all templates, scripts, harness changes must be one atomic deploy. [[pattern-windows-utf8-subprocess]] — Windows subprocess encoding applies to new harness continuous monitors.
- **Human preferences**: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" (human-profile.md line 34). Context pressure threshold: 70%. "Systems should self-heal: detect stuck states → unstick immediately" (human-profile.md line 42).
- **Related learnings**: [[learning-atomic-migration-strategy]] — 30+ files (4 base includes.yml, 20 variant includes.yml, 4+ instructions.md, 6+ sub-skills) must change atomically in one compose deploy-all.

## Impact Analysis

### Files touched

**Setup flow — direct changes:**
- `references/wizard/WIZARD.md` — Step 5 (lines 373-395) must branch: if event-driven, skip interval question, ask `scan-idle-timeout` and `wake-mechanism` instead. Step 6 review screen (lines 546-600) must show event-driven status. Step 7.3 scaffold (line 629) must write new config fields.
- `references/scripts/wizard.py` — `build_config_md()` (lines 585-720): `## Loop` section writes `Interval Minutes` and `Context Threshold`. For event-driven mode, must write `## Event Driven` section with `Enabled`, `Scan Idle Timeout`, `Wake Mechanism` fields instead (or conditionally). `generate_default_spec()` (lines 2073-2166): `loop` key is hardcoded — needs conditional branching. `validate_interval()` (lines 339-381): may be skipped entirely in event-driven mode.
- `.claude/commands/squidsquad-setup.md` (line 1): references "Setup Instructions in SKILL.md" — will pick up WIZARD.md changes automatically.

**Config layer — new field support:**
- `references/scripts/config.py` — `FIELD_MAP` (lines 38-95): must add `event-driven` → `("Event Driven", "Enabled")`, `scan-idle-timeout` → `("Event Driven", "Scan Idle Timeout")`, `wake-mechanism` → `("Event Driven", "Wake Mechanism")`. `get_field()`/`set_field()` work generically — no code changes needed beyond FIELD_MAP entries.
- `references/scripts/wizard.py` `build_config_md()` (lines 693-701): current `## Loop` section must become conditional — write `## Event Driven` when event-driven mode is selected, `## Loop` otherwise.

**Boot prompt — thin_launcher.py:**
- `references/scripts/thin_launcher.py` (line 86): `"Boot. Begin your first Ralph Loop cycle now."` must change to event-driven orientation: `"Boot. Monitor the event bus and process events as they arrive."` or similar. Must be conditional on config flag.
- Must read new config field `event-driven` (via config.py) to decide which prompt to emit.

**Harness startup — mode awareness:**
- `references/scripts/harness.py` `lifespan()` (lines 406-500): currently auto-starts all agents unconditionally via `boot_remote.boot_agent()`. When `event-driven: yes`, must activate continuous monitors (git pull, context pressure, triage, branch enforcement, scan-due idle timer) and event bus persistence. This is primarily a #7630 concern, not setup, but setup must write the flag that harness reads.

**Compose template engine:**
- `references/scripts/compose.py` `_substitute_placeholders()` (lines 460-497): substitutes `[INTERVAL]` placeholder. In event-driven mode, this placeholder is meaningless (no interval). Must be conditional or removed from event-driven templates. This is a #7630 template concern but affects setup because setup calls compose.
- `references/scripts/compose.py` `deploy_role()` (line 807-869): event contract derivation calls `derive_and_write_event_contracts()` which calls `event_catalog.py`. New event types from #7630 must be added to event_catalog.py before setup can work end-to-end.

**Templates — sub-skills stripped during compose:**
- `references/sub-skills/common/cycle-runner.md` (93 lines) — **removed** from includes when event-driven
- `references/sub-skills/common/context-pressure.md` (19 lines) — **removed** (absorbed by harness)
- `references/sub-skills/common/self-restart.md` (21 lines) — **removed** (absorbed by harness)
- `references/sub-skills/common/interval-sync.md` (13 lines) — **removed** (no interval to sync)
- `references/sub-skills/common/iteration-log.md` (21 lines) — **removed** (replaced by per-event log)
- `references/sub-skills/common/pull-latest.md` (7 lines) — **removed** (harness owns git pull)
- `references/sub-skills/common/event-reactions.md` (32 lines) — **rewritten** for event handler guidance
- `references/sub-skills/common/agent-lifecycle.md` (46 lines) — **rewritten** for persistent session + Monitor tool
- `references/sub-skills/common/improvement-scan.md` (103 lines) — trigger mechanism changed (harness emits `scan-due`)
- `references/sub-skills/common/status-line.md` (10 lines) — event-based display, not cycle-based
- All 24 includes.yml files (4 base + 20 variant) — remove cycle-related includes, add `event-driven-workflow.md`
- New file: `references/sub-skills/common/event-driven-workflow.md` — agent event handler guidance

**Event catalog:**
- `references/scripts/event_catalog.py` — 10+ new event types: `work-available`, `work-started`, `work-completed`, `stop-requested`, `agent-stopping`, `agent-stopped`, `scan-due`, `scan-completed`, `event-timeout`, `event-reemitted`, `work-failed` (all currently in RECOGNIZED tier per #7630 RESEARCH.md lines 27-28)

**SKILL.md documentation:**
- `SKILL.md` — The Ralph Loop section (lines 162-261) documents cycle-based operation. Must be updated or supplemented with event-driven architecture description. The role table (lines 54-59) lists "Loop" column — needs "Wake" column for event-driven.

### Behavior changes

1. **Setup Step 5 (Loop interval) becomes conditional**: Currently always asks "How often should each agent run its cycle?" After #7630, must branch: detect event-driven capability → ask `scan-idle-timeout` + `wake-mechanism` instead, or skip entirely and use defaults. The `loop` key in the install spec becomes optional; `event_driven` key is added.

2. **Config.md gains new section**: `## Event Driven` with `Enabled: yes/no`, `Scan Idle Timeout: 10`, `Wake Mechanism: monitor`. The `## Loop` section is retained for backward compatibility but unused when `event-driven: yes`.

3. **Review screen (Step 6) shows event-driven status**: Pipeline display adds event-driven indicator. Summary shows `Event-Driven: yes | Scan Idle: 10m | Wake: monitor` instead of `Loop: 10 minutes`.

4. **Boot prompt changes**: thin_launcher.py must read `event-driven` flag and emit either the legacy "Begin your first Ralph Loop cycle now" or the new "Monitor the event bus..." prompt.

5. **Compose.py deploy-all behavior**: When `event-driven: yes`, compose must include `event-driven-workflow.md` sub-skill and exclude `cycle-runner.md`, `context-pressure.md`, `self-restart.md`, `interval-sync.md`. This requires compose.py to read the config flag (currently it doesn't — it substitutes placeholders mechanically).

### Dependencies

- **#7630 Phase 1.5 infrastructure** — event bus disk persistence, clone discovery fix, per-role in-flight queues, harness thread safety — must be implemented before setup can offer event-driven mode, or setup must gracefully handle the case where infrastructure isn't ready.
- **Monitor tool validation** — Claude Code v2.1.98+ required. Current install is v2.1.86. Until validated, `wake-mechanism: monitor` cannot be the default.
- **compose.py** — must be able to conditionally include/exclude sub-skills based on `event-driven` config flag. Currently has no such capability — includes are driven by static `includes.yml` manifests.
- **harness.py** — must read `event-driven` flag on startup and activate continuous monitors. Currently has no awareness of this flag.

## Side Effects

- **Risk 1: Setup offers event-driven mode before infrastructure is ready** — Severity: H. If WIZARD.md is updated to offer event-driven mode before #7630 Phase 1.5 and Phase 2 are complete, users could configure a mode that doesn't work. Mitigation: gate the event-driven question behind a check — either a config flag (`--experimental-event-driven`) or a version check on harness.py. The WIZARD.md should default to cycle-based until #7630 ships.
- **Risk 2: Config schema version bump needed** — Severity: M. Adding `## Event Driven` section means Architecture Version should go from 2 to 3. The upgrade flow (SKILL.md lines 347-412) has a v1→v2 migration but no v2→v3 path. Mitigation: add v2→v3 patch step in upgrade instructions, or make the new section optional with graceful fallback (all consumers default to cycle mode when absent).
- **Risk 3: compose.py conditional includes require manifest changes** — Severity: M. Currently `includes.yml` files are static YAML lists. To conditionally include `event-driven-workflow.md` vs `cycle-runner.md`, either: (a) add conditional logic to compose.py, (b) create separate event-driven includes.yml variants, or (c) use a different compose entry point. Mitigation: compose.py can check config flag at compose time and swap include lists — this is the least-invasive approach but requires compose.py changes that aren't in scope of #7690.

## Edge Cases

- **Mixed-mode team (some roles event-driven, some cycle-based)**: Per CONTEXT.md line 183, cross-role event-driven detection needed — if PM is event-driven and dev is cycle-based, events are missed. Mitigation: setup must enforce team-wide consistency — `event-driven` is a team-level flag, not per-role. The WIZARD.md must not offer per-role event-driven toggles.
- **Existing install with custom SOUL.md referencing cycles**: Setup's "regenerate templates only" re-run path (WIZARD.md Step 0b option 2) must not overwrite SOUL.md (already protected by compose.py line 843-867). But if the user switches to event-driven, their SOUL.md may contain cycle-based personality traits that don't match the new workflow. Mitigation: warn on mode switch; offer SOUL.md review.
- **Config.md has both `## Loop` and `## Event Driven` sections**: Must define precedence — `event-driven: yes` means `## Loop` is ignored. Mitigation: config.py readers check `event-driven` first; harness.py warns if both sections present with conflicting semantics.
- **User sets `event-driven: yes` but hasn't upgraded Claude Code**: Agent boots, Monitor tool isn't available, agent sits idle forever. Mitigation: harness.py checks Claude Code version on startup when `event-driven: yes`; warns if < v2.1.98. thin_launcher.py can also validate Monitor tool availability before emitting the event-driven boot prompt.

## Integration Risks

- **Compose integration**: Setup calls `compose.py deploy-all` via wizard scaffold (WIZARD.md Step 7.3). If event-driven config flag causes compose to generate different templates, the scaffold step must pass the flag through. Currently `wizard.py scaffold_install()` (line 917) calls compose.py but doesn't thread a mode flag. Mitigation: compose.py reads `event-driven` from the freshly-written config.md — since scaffold writes config.md before composing (it's the first thing scaffold does), the flag is available by the time compose runs.
- **Upgrade flow conflict**: The existing upgrade flow (SKILL.md lines 347-412) regenerates templates via compose.py deploy-all, then patches config schema v1→v2. If event-driven adds v3 schema, the upgrade must also handle v2→v3 patching. The upgrade must NOT automatically enable event-driven mode — it must preserve the existing mode.
- **Status bar**: statusline.sh uses cycle-based display (iteration number, cycle timer, quiet cycle count). Setup doesn't directly touch statusline.sh, but the review screen may want to show what the status bar will look like under event-driven mode. Low risk — out of scope for setup.
- **Tracker protocol**: cycle_post.py currently handles status transitions and tracker comments. Under event-driven, harness owns these. Setup doesn't touch tracker.py directly, but the event closure API (`POST /events/{id}/complete`) must exist before setup can claim event-driven mode is functional. Medium risk — setup should validate the closure endpoint exists before offering event-driven mode.

## Upgrade & Migration

- **New config values**:
  - `event-driven` → `("Event Driven", "Enabled")` — default: `no`
  - `scan-idle-timeout` → `("Event Driven", "Scan Idle Timeout")` — default: `10` (minutes)
  - `wake-mechanism` → `("Event Driven", "Wake Mechanism")` — default: `monitor`
  - These must be added to `config.py` `FIELD_MAP` (after line 95) and to `wizard.py` `build_config_md()` (after line 701).

- **New files**:
  - `references/sub-skills/common/event-driven-workflow.md` — agent event handler guidance (created by #7630, consumed by setup via compose)
  - Possibly `references/scripts/event_store.py` — disk-persistent event storage (created by #7630 Phase 1.5)
  - No new setup-only files.

- **Template changes**:
  - 4 base `includes.yml` files remove 3-4 cycle includes each (`cycle-runner`, `context-pressure`, `self-restart`, optionally `interval-sync`)
  - 20 variant `includes.yml` files inherit changes via `base_role` + `additional_includes` pattern — may need no direct edits if base role manifests are updated
  - 1 new sub-skill `event-driven-workflow.md` added to all role manifests
  - All changes atomic via one `compose.py deploy-all` invocation
  - `[INTERVAL]` placeholder in templates becomes conditional — only substituted in cycle mode

- **Upgrade steps** (for existing installs when #7630 ships):
  1. Human upgrades Claude Code to v2.1.98+ (prerequisite)
  2. Run `/squidsquad-upgrade` (or manual upgrade flow)
  3. Upgrade detects v2→v3 schema gap, patches config.md: adds `## Event Driven` section with defaults (`Enabled: no`)
  4. Regenerate templates via `compose.py deploy-all` (templates still cycle-based because flag is `no`)
  5. User manually sets `event-driven: yes` when ready
  6. Run `compose.py deploy-all` again to regenerate with event-driven templates
  7. Restart harness — harness reads flag, activates continuous monitors
  8. Rollback: set `event-driven: no`, `compose.py deploy-all`, restart harness

- **Graceful degradation**: When `event-driven: no` (default), existing cycle model runs unchanged. Both models cannot run simultaneously for the same role — harness startup must warn if mixed-mode detected. Rollback is a config flip + recompose. No data loss — iteration logs and vault content are preserved.

## Open Questions

- **Q1: Should setup default to event-driven or cycle-based when #7630 ships?** — **Why**: If the Monitor tool is validated and infrastructure is solid, new installs should default to event-driven. But if there are edge cases (e.g., Monitor tool doesn't work on all platforms, or certain role combinations are untested), cycle-based should remain the safe default. The BRIEFING.md says #7630 is the "next major architectural shift" — suggesting it should become the default once shipped.
- **Q2: Should setup offer `wake-mechanism` as a user-facing choice?** — **Why**: CONTEXT.md lists `wake-mechanism: monitor` with a future `spawn` fallback. But PHASE2-PREP says Option A (stateless spawn) is the fallback if Monitor doesn't work. If Monitor is the only viable mechanism at launch, exposing this choice is misleading. Mitigation: hide `wake-mechanism` behind an advanced/experimental flag until both mechanisms exist.
- **Q3: Should the `## Loop` section be retained or renamed in config.md?** — **Why**: The FIELD_MAP keys `interval` and `context-threshold` are referenced by `config.py get interval` throughout the codebase. Renaming the section to `## Event Driven` would break all existing consumers. Mitigation: keep `## Loop` for backward compatibility; add `## Event Driven` as a new section. When `event-driven: yes`, `## Loop` values are ignored. When `event-driven: no`, `## Event Driven` values are ignored.

## Recommendation

**Feasible with caveats.** The setup flow changes are well-scoped and mechanical: one question branch in WIZARD.md Step 5, three new FIELD_MAP entries in config.py, conditional section in wizard.py build_config_md(), and a conditional boot prompt in thin_launcher.py. The real constraint is sequencing — setup must not offer event-driven mode before #7630 Phase 1.5 infrastructure and Phase 2 wake mechanism are implemented and validated.

Recommended implementation order:
1. Add `event-driven`, `scan-idle-timeout`, `wake-mechanism` to `config.py` FIELD_MAP (safe — fields are read-only until consumers use them)
2. Add `## Event Driven` section to `wizard.py` `build_config_md()` as an optional section (not in default spec yet)
3. Update `wizard.py` `generate_default_spec()` to include `event_driven` key (defaulting to disabled)
4. Add conditional branch in WIZARD.md Step 5 — gated behind `event-driven` flag in the in-memory spec
5. Update thin_launcher.py boot prompt to check `event-driven` flag
6. Wire harness.py to read `event-driven` flag and activate continuous monitors (belongs to #7630, not #7690)
7. After #7630 ships, flip the default in `generate_default_spec()` from cycle to event-driven

## Vault Candidates

- **Type**: decision — Setup flow must enforce team-wide `event-driven` flag, not per-role toggles — **Why**: CONTEXT.md identifies mixed-mode teams as an edge case (line 183). The setup flow is the enforcement point — if it allows per-role toggles, the system breaks. This is a design constraint worth vaulting.
- **Type**: pattern — Config schema versioning with graceful degradation: `## Event Driven` section coexists with `## Loop` section, precedence by flag — **Why**: This pattern (add new section, gate on flag, keep old section for backward compat) avoids breaking existing config.py consumers. Reusable for future schema changes.
- **Type**: learning — compose.py conditional includes require runtime config awareness, which compose.py currently lacks — **Why**: The includes.yml manifests are static. Event-driven mode requires composing different sub-skills for the same role based on a runtime flag. This is a new capability that compose.py must gain, and the design choice (manifest variants vs. conditional logic vs. separate entry points) will shape future template evolution.
- **Type**: learning — Monitor tool validation is the critical path blocker for the entire #7630 architecture, and setup must not expose features that depend on unvalidated infrastructure — **Why**: FEAT-PM-5613 already concluded "Monitor cannot completely replace /loop." #7630's locked decision #1 ignored this finding. Setup is the user-facing surface — if it offers event-driven mode before Monitor is validated, users will hit broken behavior. The lesson: UI/setup changes must lag behind infrastructure validation, not lead it.
- **Type**: decision — `scan-idle-timeout` default of 10 minutes with issue gate (skip scan if role has open bugs) — **Why**: This is one of the locked decisions (#5 in CONTEXT.md) and directly affects the setup question flow. The issue gate means PM improvement scans are demand-driven, not time-driven — this nuance should be explained in the setup wizard's question text.
```