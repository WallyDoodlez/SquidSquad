# FEAT-PM-2724 Research — Move agent boot detection to cycle_pre.py and create start-squad script

## Summary

This task restructures agent boot logic from two places (PM template step + boot_remote.py config gate) into a single unconditional flow: cycle_pre.py calls boot detection every PM cycle and surfaces results in cycle-input.json, while a new start-squad script handles the human-facing "boot all agents at once" use case. The `Auto Boot Agents` config toggle is removed entirely — boot detection becomes a permanent, unconditional PM responsibility rather than an opt-in feature.

The primary change to understand is that `boot_remote.py` currently has its own config guard (lines 459–467: reads `Auto Boot.*: yes/no` directly from config.md before doing anything). This guard must be removed or bypassed when called from cycle_pre.py, otherwise removing the config section will cause boot_remote.py to silently skip even when called programmatically. The task is feasible with careful sequencing of that change.

The main risks are: (1) the `auto_boot_agents` flag is already read into `cycle-input.json` by `_build_pm_input` in cycle_pre.py — the PM template may be referencing it in its creative phase logic and that reference must be cleaned up or the field removed; (2) the `boot-remote-agents.md` sub-skill is composed into the live PM CLAUDE.md at `.squidsquad/pm/CLAUDE.md` — stripping it from the sub-skill file alone is not enough without recomposing; (3) the watchdog vault decision (#1550) established that lifecycle is centralized in watchdog.py, but there is no watchdog.py in the codebase — the PM template boot step is still the actual liveness mechanism.

---

## Vault Context

- **BRIEFING.md priorities**: v1.0.0 launch readiness — going-public focus is active. Simplifying the boot surface (removing config toggle, adding a clean start-squad entry point) aligns with the launch checklist goal of reducing operational friction.
- **Related decisions**:
  - `decision-pid-primary-liveness` (2026-04-18): PID is the ground truth for liveness, `.health` is informational only. boot_remote.py's `_needs_boot` function already implements this correctly. The move to cycle_pre.py must preserve PID-first semantics.
  - `decision-watchdog-supervisor` (2026-04-19): Documents an intent to centralize lifecycle in watchdog.py, but watchdog.py does not exist in the repo. The PM boot step is currently the actual implementation of that intent. This task moves boot detection into cycle_pre.py, which is a step toward the watchdog pattern without fully implementing it.
- **Related patterns**: start-role.ps1 and start-role.sh already handle singleton enforcement (PID lock), pre-flight checks, branch setup, and heartbeat. start-squad will be a thin orchestration layer on top of these existing scripts.
- **Human preferences**: Agents are manually triggered (MEMORY.md). start-squad does not change that — it gives a single command to start all configured agents simultaneously, but does not automate startup on system boot or create daemons.
- **Related learnings**: MEMORY note "Don't ask before verifying" and "Auto-approve bugs" are not directly relevant here. The "No shipping with open gaps" policy means the config.md section removal and boot_remote.py guard removal must be in sync — if one ships without the other, boot detection silently breaks.

---

## Impact Analysis

- **Files touched**:
  - `references/scripts/config.py` — remove `"auto-boot": ("Auto Boot Agents", "Enabled")` from `FIELD_MAP` (line 53)
  - `references/scripts/boot_remote.py` — remove the config guard block (lines 459–467) in `main()` that reads `Auto Boot.*: yes/no` and exits early; the guard is no longer needed since cycle_pre.py controls when boot runs
  - `references/scripts/cycle_pre.py` — in `_build_pm_input()` (line 442), remove `config["auto_boot_agents"] = _config_get("auto-boot-agents").lower() == "yes"`; add a call to `boot_remote.py --all --json` and capture results into a new `boot_results` field in cycle-input.json
  - `.squidsquad/config.md` — remove `## Auto Boot Agents` section (lines 111–112)
  - `references/sub-skills/common/boot-remote-agents.md` — strip the `Auto Boot Agents` config check (line 8); change the step to read `boot_results` from cycle-input.json rather than running boot_remote.py directly
  - `.squidsquad/pm/CLAUDE.md` — the live PM template; must be recomposed after sub-skill changes via `python references/scripts/compose.py boot pm`
  - `references/agent-instructions.md` — line 436 references the config check; must be updated
  - New: `.squidsquad/start-squad.ps1` — boots all configured agents from config
  - New: `.squidsquad/start-squad.sh` — boots all configured agents from config

- **Behavior changes**:
  - Boot detection runs unconditionally every PM cycle, regardless of any config setting
  - PM no longer runs `boot_remote.py` in its template step — it reads pre-computed `boot_results` from cycle-input.json
  - `boot_remote.py --all` called without a config toggle check means it will attempt to boot any dead agent listed in config.md (subject to `.stop` sentinel and normal needs_boot logic)
  - `Auto Boot Agents: no` in config.md no longer has any effect (the section will be removed)
  - New `start-squad` scripts provide a human-facing "start everything" entry point

- **Dependencies**:
  - `boot_remote.py` is called by the new cycle_pre.py boot logic — it must exist and work correctly before cycle_pre.py changes are deployed
  - `reboot_agent.py` is referenced in the agent-lifecycle sub-skill and is unaffected by this task; PM retains access to it for governance actions
  - compose.py must be run to regenerate `.squidsquad/pm/CLAUDE.md` after the sub-skill is changed

---

## Side Effects

- **Risk 1**: PM template still references `auto_boot_agents` from cycle-input.json in creative phase logic — Severity: M — Mitigation: Search `.squidsquad/pm/CLAUDE.md` for any reference to `auto_boot_agents` before shipping; remove those references. The current CLAUDE.md (as read) does not appear to explicitly act on `auto_boot_agents` in the visible sections, but the field is in cycle-input.json config block and PM may be relying on it implicitly.

- **Risk 2**: boot_remote.py config guard removal causes the script to boot agents on every call, including dry-run and manual invocations that previously respected the `no` setting — Severity: L — Mitigation: This is the desired behavior post-task. The `.stop` sentinel (`.squidsquad/{role}/.stop`) remains the correct opt-out mechanism for users who do not want a specific agent rebooted.

- **Risk 3**: cycle_pre.py calls boot_remote.py which spawns terminal windows during a pre-cycle mechanical phase — timing and sequencing — Severity: M — Mitigation: boot_remote.py spawns via `subprocess.Popen` with `DETACHED_PROCESS`, so it does not block cycle_pre.py. The new `boot_results` in cycle-input.json captures what was spawned and PM can log/act on spawn failures in the creative phase.

- **Risk 4**: `.squidsquad/pm/CLAUDE.md` contains the live boot-remote-agents sub-skill verbatim and is not auto-regenerated — Severity: H — Mitigation: The dev must run `python references/scripts/compose.py boot pm` as an explicit step after updating the sub-skill source. This is a deployment step, not a code change. QA must verify the composed output, not just the sub-skill source file.

- **Risk 5**: start-squad scripts must enumerate roles from config.md in the correct order and handle absent clone paths — Severity: M — Mitigation: start-squad should call `boot_remote.py --all` rather than duplicating role enumeration logic. This delegates to the existing `_get_all_roles()` function which already handles config.md parsing, .stop sentinels, and clone path resolution.

---

## Edge Cases

- **Agent already running**: `_needs_boot` in boot_remote.py returns `skip` if PID is alive. cycle_pre.py calling this during every PM cycle is safe — no double-boot, no crash.
- **`.stop` sentinel present**: boot_remote.py respects `.stop` files even when called unconditionally. Users who want a role permanently stopped can create `.squidsquad/{role}/.stop`.
- **No agents configured**: `_get_all_roles()` returns `[]` if config.md has no Dev Agents. boot_remote.py returns `[{"action": "skip", "message": "no agents configured"}]`. cycle_pre.py should handle this gracefully (empty `boot_results` list).
- **boot_remote.py spawn failure**: Terminal spawn can fail (wt.exe not found on Windows, osascript failure on macOS, no tmux on Linux). These failures are already captured in the result dict (`success: false`). PM's creative phase reads `boot_results` and should log spawn failures to the agent's issue discussion — same behavior as the current template step.
- **PM itself in the roles list**: `_get_all_roles()` explicitly calls `roles.discard("pm")` so PM never tries to boot itself. This is preserved.
- **config.md section missing (post-upgrade)**: If boot_remote.py is called on an install that has already removed the `Auto Boot Agents` section, the current guard block (`re.search(r"Auto Boot.*?:\s*(yes|no)")`) will match `None` and fall through without early exit — so the existing code already degrades gracefully. Removing the guard block is a cleanup, not a fix.
- **start-squad called while agents already running**: Each start-role script enforces the PID singleton check before launching Claude. start-squad calling each role's start script when the role is already running will print "Agent already running" and exit without spawning a duplicate.

---

## Integration Risks

- **compose.py regeneration**: The sub-skill source is in `references/sub-skills/common/boot-remote-agents.md`, but the live PM template is at `.squidsquad/pm/CLAUDE.md`. These are two separate files. Any change to the sub-skill source that is not followed by a recompose will leave the live PM running old instructions. This is the highest-friction integration point in the entire task.
- **agent-instructions.md**: This is a reference template that also contains the old boot-remote-agents step (line 436). It is used by compose.py as source material. If it is not updated in sync with the sub-skill file, future recomposes will re-introduce the old behavior.
- **`auto_boot_agents` field in cycle-input.json**: If the field is removed from `_build_pm_input` but the PM template still expects it, the PM agent will read the JSON, not find the field, and silently treat it as falsy. This could cause the PM to skip boot processing unexpectedly. The field removal and template update must be atomic (same commit or same compose run).
- **Existing installs**: Installs with `Auto Boot Agents: yes` in config.md continue to work after upgrade (the guard removal means the field is ignored, not fatal). Installs with `Auto Boot Agents: no` will see boot detection become active after upgrade — this is a behavioral change that may surprise users who intentionally disabled it.

---

## Upgrade & Migration

- **New config values**: None — a config value is being removed, not added.
- **New files**: `.squidsquad/start-squad.ps1`, `.squidsquad/start-squad.sh` (generated by compose.py or written directly)
- **Template changes**:
  - `references/sub-skills/common/boot-remote-agents.md`: strip the config toggle check; change the step to read `boot_results` from cycle-input.json (or remove the step entirely if boot is now fully cycle_pre territory)
  - `references/agent-instructions.md`: remove or update the Auto Boot Agents config check reference at line 436
  - `.squidsquad/pm/CLAUDE.md`: must be regenerated via compose.py after sub-skill changes
- **Upgrade steps for /squidsquad-upgrade**:
  1. Remove `## Auto Boot Agents` section from `.squidsquad/config.md`
  2. Remove `"auto-boot": ("Auto Boot Agents", "Enabled")` from `FIELD_MAP` in `config.py`
  3. Remove config guard block from `boot_remote.py` `main()` (lines 459–467)
  4. Update `_build_pm_input` in `cycle_pre.py`: remove `auto_boot_agents` field, add boot_remote call and `boot_results` output
  5. Update `references/sub-skills/common/boot-remote-agents.md`
  6. Update `references/agent-instructions.md`
  7. Recompose PM template: `python references/scripts/compose.py boot pm`
  8. Write `.squidsquad/start-squad.ps1` and `.squidsquad/start-squad.sh`
- **Graceful degradation**: If user has not upgraded, `Auto Boot Agents: yes/no` in config.md continues to work as before (the guard is still in boot_remote.py). No functionality breaks on old installs. After upgrade, the section is gone and boot runs unconditionally — the `.stop` sentinel is the new opt-out.

---

## Capability Gaps

- **watchdog.py does not exist**: The `decision-watchdog-supervisor` vault note describes a centralized watchdog supervisor as the intended architecture, but watchdog.py has never been written. This task adds boot detection to cycle_pre.py (PM-controlled), which is the current actual implementation. If watchdog.py is eventually built, the cycle_pre.py boot call should be removed to avoid double-boot races. The dev agent should note this dependency in a code comment.
- **start-squad template generation**: compose.py generates start-role.ps1 and start-role.sh from a role template. There is currently no compose target for start-squad. The dev can either: (a) write start-squad scripts as static files (they call boot_remote.py --all, not role-specific scripts), or (b) add a compose target. Static file is simpler and lower risk given that start-squad has no {{ROLE}} substitution.
- **No boot_results schema documentation**: The task introduces a new `boot_results` field in cycle-input.json. This field's structure (list of result dicts from boot_remote.py) should be documented in the cycle-input schema comment block in cycle_pre.py and in the PM template's cycle-input reading instructions.

---

## Open Questions

- **Q1**: Should `boot-remote-agents.md` be fully removed from the PM template, or converted into a "read boot_results from cycle-input.json" step? — **Why**: If fully removed, the PM has no guidance on what to do when cycle-input.json shows spawn failures. A short "read and act on boot_results" step preserves PM visibility of boot failures without running boot_remote.py at template time.

- **Q2**: Should start-squad call boot_remote.py --all directly, or should it call each role's start-role script in sequence? — **Why**: Calling boot_remote.py --all is simpler and reuses existing logic (clone path resolution, .stop sentinel checks, liveness detection). Calling start-role scripts directly would bypass liveness checks and always attempt to start each role regardless of whether it is already running.

- **Q3**: Does compose.py need a new target (e.g., `python compose.py squad`) to generate start-squad scripts, or are they hand-written static files? — **Why**: If compose.py generates them, future changes to the boot pattern get propagated automatically via upgrade. If hand-written, they are simpler but create a drift risk. Given that start-squad has no role-specific substitution, static files are likely sufficient.

- **Q4**: Should boot_remote.py's config guard be replaced with a `--ignore-config` flag rather than removed entirely? — **Why**: Removing it cleanly is simpler. A flag would be useful if other callers (e.g., manual PM governance reboots) needed to honor a future disable mechanism. Given the `.stop` sentinel covers per-role opt-out, a global disable flag seems unnecessary.

---

## Recommendation

**Feasible with caveats.** The core logic changes are low risk — boot_remote.py already works correctly, cycle_pre.py already calls it at the script level, and the config toggle removal is a cleanup. The two areas requiring careful execution are: (1) the live PM CLAUDE.md must be regenerated via compose.py as part of the task — QA must test the composed output, not just the sub-skill source; and (2) the `auto_boot_agents` field removal from cycle-input.json must be coordinated with any PM template references to that field. Both are well-understood, deterministic steps. The dev agent should sequence changes as: scripts first (boot_remote.py guard removal, cycle_pre.py boot_results addition), then config.md section removal, then sub-skill update, then compose rerun, then start-squad file creation.
