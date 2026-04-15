# FEAT-SKILL-942 Re-Audit — Boot Process

**Date**: 2026-04-14
**Auditor**: PM research agent
**Scope**: Post-merge audit of PR #959 against original CONTEXT.md locked decisions, plus five newly discovered issues.

---

## Original Plan vs Reality

| Locked Decision | Implemented? | Working? | Gaps |
|----------------|-------------|----------|------|
| Wrapper writes `.health` (booting/alive/restarting/backoff/dead/error) | YES — both PS1 and sh templates have `write_health`/`Write-Health` with atomic tmp+rename pattern | YES — full lifecycle coverage: booting at pre-flight, alive at loop start, restarting on self-restart/context-pressure, backoff on fast crash, dead on stop/exit, error on max restarts and pre-flight failures | None |
| Agent keeps writing `current-state` for cycle-level detail | YES — boot scripts reset `current-state` to `idle|Initializing...` each loop iteration; agent CLAUDE.md still writes per-step | YES — health_check.py reads both `.health` for liveness and `current-state` for phase info | None |
| health_check.py reads `.health` for liveness, `current-state` for phase info | YES — `_parse_health_file()` added, primary path checks `.health`, fallback to mtime | YES — clean separation: `.health=alive` + stale mtime = STALLED (line 238), `.health=alive` + fresh mtime = HEALTHY. Fallback for missing `.health` preserves backward compat | None |
| Post-spawn poll: boot_remote.py waits up to 30s for `.health=alive` | YES — `_poll_health_after_spawn()` with 2s interval, 30s timeout | MOSTLY — polls correctly, returns `confirmed=True` for `alive` or `booting` (lenient). Returns `confirmed=False` only for `error`. Timeout returns `confirmed=True` with `unknown` status, which is generous but safe | Minor: timeout returning `confirmed=True` means boot_remote never reports a spawn as failed due to slow boot. Acceptable trade-off — avoids false negatives |
| Pre-flight checks: gh auth + main branch, failures write to `.health` and exit without restart loop | YES — both templates check `gh auth status` and `git branch --show-current` before PID lock | YES — writes `error|gh auth failed` or `error|wrong branch: X (expected main)` and exits with code 1. No restart loop entered. PID file NOT written (pre-flight runs before PID lock) | None |
| #941 merged into #942 | YES — pre-flight checks are in the boot script templates | YES | None |
| Wrapper enforces self-restart rate limit (3/hour, hard) | YES — both templates parse `restart-log.txt`, count `self-restart` entries in last hour, block when >= 3 | YES — blocked restarts logged as `self-restart-BLOCKED`. Falls through to normal crash handling when blocked | Minor: sh template uses `date -d` (GNU) with `date -v` (BSD) fallback. If both fail (e.g., BusyBox), `ONE_HOUR_AGO=0` which effectively disables the rate limit. Edge case, low risk |
| Re-compose QA and DM CLAUDE.md to fix stale wizard refs | YES — grep for "wizard" in `.squidsquad/*/CLAUDE.md` returns zero matches | YES | None |
| Context-pressure disk-write added to all agents (PM/QA/DM) | YES — PM CLAUDE.md and QA CLAUDE.md both have the `context-pressure` sub-skill with atomic write instruction | YES — `echo "[PERCENTAGE]" > context-pressure.tmp && mv -f` pattern present | None |
| health_check.py graceful fallback for missing `.health` | YES — `health_source` field distinguishes `health-file` vs `mtime-fallback` | YES — missing `.health` falls through to mtime-based detection cleanly | None |
| boot_remote.py reads `.health` instead of raw PID checks, with PID fallback | YES — `_needs_boot()` checks `.health` first, falls back to PID | YES — alive/booting/restarting = skip, dead/error = boot, backoff = skip (wrapper handling), no `.health` = PID fallback | None |
| boot_remote.py only reads config.md for agent list (#943) | YES — `_get_all_roles()` reads Dev Agents + checks DM/QA config sections. No directory scanning. No hardcoded role list | YES — `designer` no longer in code or config | None (but Issue #943 is still OPEN on GitHub — should be closed) |

**Summary**: 11/11 locked decisions implemented. 10/11 working with no gaps. 1 has a minor tolerance issue (post-spawn timeout returning confirmed=True). Overall: PR #959 delivered what was planned.

---

## New Issues Found Post-Merge

### Issue A: Deployment gap (chicken-and-egg) — boot scripts don't `git pull`

- **Status**: OPEN — not addressed in PR #959
- **Impact**: Agent clones run with stale boot scripts. When templates are updated (e.g., `.health` writes added), the boot script that launches Claude is still the OLD version because the clone hasn't pulled yet. The `.health` file is never written, so `health_check.py` falls back to mtime, and `boot_remote.py` falls back to PID checks — negating the entire purpose of PR #959 for non-PM clones until the agent's first Ralph Loop `git pull`. Worse: if the old boot script has a bug that was fixed in the new template, the agent keeps hitting the bug every restart.
- **Proposed fix**: Add `git pull --rebase` to both `start-role.ps1` and `start-role.sh` BEFORE the pre-flight checks. Place it after `cd "$(git rev-parse --show-toplevel)"` but before the squid logo. This ensures every boot starts with the latest code, templates, and scripts. The pull should be non-fatal (network blip should not prevent boot) — use `|| true` on sh, `try/catch` on PS1.
- **Regression risk**: If `git pull` hits a merge conflict (e.g., agent left uncommitted changes), the boot would stall. Mitigation: use `git stash && git pull --rebase && git stash pop` pattern, same as `git_ops.py pull`.

### Issue B: Phantom designer (#943)

- **Status**: FIXED in PR #959 (code-level) but OPEN on GitHub
- **Impact**: No longer a problem. `_get_all_roles()` in `boot_remote.py` (line 87-107) now only reads from `config.md` Dev Agents + DM/QA config sections. No hardcoded role list. No directory scanning. `designer` does not appear anywhere in boot_remote.py or config.md.
- **Proposed fix**: Close Issue #943 on GitHub with a comment referencing PR #959. No code changes needed.

### Issue C: State files in PRs (#960)

- **Status**: PARTIAL — most state files are now gitignored, but `working-state.md` is NOT
- **Impact**: `.gitignore` now covers: `current-state`, `.pid`, `context-pressure`, `.health`, `.health.tmp`, `boot-lock`, `boot-attempts.log`, `scheduled_tasks.lock`. However, `working-state.md` is NOT gitignored. This file is intentionally tracked (agents need it to resume after context resets, and it must survive across clones). The real problem is that agents on feature branches commit their `working-state.md` changes alongside code changes, causing noise in PRs.
- **Proposed fix**: Two options:
  1. **Gitignore it**: Add `.squidsquad/*/working-state.md` to `.gitignore`. Agents would need a different persistence mechanism (e.g., always on main, never on feature branches).
  2. **Agent discipline**: Update agent CLAUDE.md to explicitly exclude `working-state.md` from feature branch commits (use `git add <specific files>` instead of `git add -A`). This is already best practice per the global instructions ("prefer adding specific files by name").
  - **Recommended**: Option 2. `working-state.md` is legitimately tracked for resume-across-sessions. The fix is behavioral, not structural. Add an explicit rule to agent templates: "Never commit working-state.md on feature branches."

### Issue D: Recompose not propagated

- **Status**: OPEN — not addressed in PR #959
- **Impact**: `compose.py deploy-all` only runs in PM's clone. Other agent clones have old generated boot scripts and CLAUDE.md files until they pull AND someone re-runs compose in their clone. Even after `git pull`, the recompose does not auto-run. This means:
  1. Agent clones get the updated templates in `references/templates/` via pull.
  2. But the generated scripts (`.squidsquad/start-<role>.ps1/sh`, `.squidsquad/<role>/CLAUDE.md`) are still the old versions.
  3. The boot script runs the old generated script, not the new template.
- **Proposed fix**: The boot script should run `python references/scripts/compose.py boot {{ROLE}}` after `git pull --rebase` (if Issue A fix is applied). This regenerates the boot script from the latest template. However, this creates a self-modifying script situation: the running script regenerates itself. This is safe because:
  - The shell/PowerShell has already loaded the script into memory (sh reads line-by-line but the while loop is already parsed; PS1 compiles the script on load).
  - The regenerated script will be used on the NEXT boot, not the current one.
  - Alternative: `compose.py deploy {{ROLE}}` to update CLAUDE.md only. The boot script itself stays old until next recompose, but at least the agent instructions are current.
- **Recommended**: Boot script runs `compose.py deploy {{ROLE}}` after pulling (updates CLAUDE.md). Running `compose.py boot {{ROLE}}` in addition is optional and riskier (self-modifying). The CLAUDE.md update is more impactful — it controls agent behavior.

### Issue E: False reboots from health_check.py

- **Status**: MOSTLY FIXED by PR #959, with one remaining gap
- **Impact**: Pre-PR #959, health_check.py used only mtime, and a freshly booted agent (30 min ago) could appear stalled if it hadn't written `current-state` yet. Post-PR #959:
  - If `.health=alive` and no `current-state` yet: reports HEALTHY with reason `.health=alive (no current-state yet -- freshly booted)` (line 245-247). This correctly handles the fresh-boot case.
  - If `.health=booting`: reports HEALTHY (line 249-250). Correct.
  - If `.health=restarting`: reports HEALTHY (line 252-253). Correct.
  - **Remaining gap**: If the agent clone has OLD boot scripts (no `.health` file), health_check.py falls back to mtime. A freshly booted agent that hasn't written `current-state` yet will show as UNKNOWN ("no .health file, no current-state file"). PM might try to reboot it. This is the chicken-and-egg from Issue A — the fix is the same: boot scripts must `git pull` to get `.health`-aware templates.
- **Proposed fix**: Issue A fix (git pull in boot scripts) eliminates this gap. Once all clones have `.health`-aware boot scripts, the mtime fallback path is only for truly old/broken setups.

---

## Additional Observations

### #943 should be closed
The code fix shipped in PR #959 (`_get_all_roles()` reads only from config.md). The GitHub Issue is still OPEN. It should be closed with a reference to PR #959.

### health_check.py has a subtle STALLED false positive
When `.health=alive` but `current-state` mtime is stale (> 2x interval), health_check.py reports STALLED (line 238-243). This can happen legitimately:
- Agent is in a long tool call (e.g., running tests for 70+ minutes)
- Agent's `/loop` timer is longer than 2x interval
- Agent just completed a self-restart and hasn't written `current-state` yet

The `.health=alive` + stale mtime = STALLED logic is correct in principle (wrapper is alive but agent is stuck), but PM should not auto-reboot on this signal alone. The boot_remote.py correctly does NOT reboot when `.health=alive` — it only reboots on `dead` or `error`. So the STALLED report is informational only for PM's health check output. This is fine.

### PS1 atomic write has a subtle path resolution issue
The PS1 `Write-Health` function (line 67) uses `(Resolve-Path $RoleDir).Path + "/.health.tmp"` for WriteAllText but `$tmp = "$HealthFile.tmp"` for Move-Item. If `$RoleDir` is relative and the working directory changes mid-script, Resolve-Path and `$tmp` could diverge. In practice, the script sets `Set-Location $repoRoot` once at the top and never changes directory, so this is safe. But it's fragile.

---

## Updated Scope (what still needs to be done)

### Must-fix (P0)

- **Issue A: `git pull --rebase` in boot scripts**: Without this, all PR #959 improvements are inert for non-PM clones. Health files aren't written, pre-flight checks don't exist, rate limits don't apply. The entire boot overhaul only works in PM's clone. This is the single most important remaining fix.

### Should-fix (P1)

- **Issue D: `compose.py deploy` after pull**: Even with git pull, the generated CLAUDE.md files are stale until recomposed. Boot scripts should run `compose.py deploy {{ROLE}}` after pulling to update agent instructions. Without this, agents run with old CLAUDE.md despite having new templates available.
- **Close #943**: The code fix shipped. The issue should be closed to avoid confusion and stale tracking.

### Nice-to-have (P2)

- **Issue C: working-state.md on feature branches**: Add agent template rule to never commit working-state.md on feature branches. Not gitignored because it's legitimately tracked for resume. Behavioral fix, not structural.
- **Issue D extension: `compose.py boot` after pull**: Regenerate the boot script itself (not just CLAUDE.md). Lower priority because the boot script changes less frequently than CLAUDE.md, and the self-modifying script pattern adds risk.
- **PS1 Write-Health path robustness**: Use consistent path resolution in the Write-Health function. Low severity — only fails if working directory changes, which doesn't happen today.

---

## Regression Risks of Remaining Fixes

- **git pull in boot scripts could hit merge conflicts**: If the agent's clone has uncommitted changes or is mid-rebase, `git pull --rebase` will fail. Mitigation: use `git stash && git pull --rebase && git stash pop || true` pattern. If stash pop fails, the boot should still proceed (the agent will deal with conflicts in its first cycle).
- **git pull in boot scripts adds network dependency**: If GitHub is unreachable, the pull fails and the boot stalls (if implemented as fatal). Mitigation: make the pull non-fatal — `git pull --rebase || echo "[SquidSquad] git pull failed — continuing with current code"`. Boot should work offline.
- **compose.py deploy in boot scripts could fail**: If `compose.py` has a bug or missing dependency, it blocks the boot. Mitigation: wrap in try/catch (PS1) or `|| true` (sh). Failed recompose should not prevent Claude from launching.
- **Self-modifying boot script (compose.py boot)**: The running script regenerates itself. On sh, the shell reads the script sequentially, so if the file changes after the current read position, behavior is undefined. On PS1, the script is compiled on load so the file change is safe. Mitigation: skip `compose.py boot` in the running script — only run `compose.py deploy` (CLAUDE.md update). The boot script itself gets updated on the NEXT manual recompose.
- **Rate limit bypass on BusyBox**: The sh template's date fallback chain (`date -d` GNU, `date -v` BSD) returns `0` if both fail. `ONE_HOUR_AGO=0` means all restart log entries appear "within the last hour," which actually OVER-counts and makes the rate limit MORE restrictive (blocks after any 3 self-restarts ever). Not a bypass — a false-positive block. Low severity, rare environment.

---

## Updated Recommendation

**PR #959 was a solid implementation.** All 11 locked decisions were delivered correctly. The split-brain is resolved, pre-flight checks prevent crash loops, self-restart rate limiting is hard-enforced, phantom designer is gone, wizard refs are cleaned, and context-pressure disk-write works for all agents. QA verified 34/34 test cases.

**However, the implementation is currently inert for non-PM agent clones** due to Issue A (no git pull in boot scripts). This is not a regression -- agents were already running without `.health` files before PR #959. But it means the benefits of the overhaul won't materialize until Issue A is fixed.

**Immediate action needed:**

1. **P0**: Ship a follow-up PR that adds `git pull --rebase` to both boot script templates (start-role.ps1 and start-role.sh), placed after `cd` but before pre-flight checks. Include `compose.py deploy {{ROLE}}` after the pull to update CLAUDE.md. This is a small, low-risk change that unlocks the full value of PR #959.
2. **P1**: Close Issue #943 on GitHub.
3. **P2**: Add agent template rule about working-state.md on feature branches.

**Is it safe to keep running?** Yes. The current state is no worse than before PR #959 — PM's clone has all the improvements, and other clones degrade gracefully to the old PID/mtime behavior. There is no urgency to roll back. The follow-up PR is a small additive fix, not an emergency.
