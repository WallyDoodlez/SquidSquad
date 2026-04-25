# FEAT-PM-2724 Test Plan — Move agent boot detection to cycle_pre.py and create start-squad script

## Test Cases

### TC-1: Auto Boot Agents section removed from config.md
- **Precondition**: `.squidsquad/config.md` currently contains an `## Auto Boot Agents` section with `Enabled: yes` or `Enabled: no`.
- **Steps**: After the task ships, open `.squidsquad/config.md`.
- **Expected**: No `## Auto Boot Agents` heading, no `Enabled:` line under that section. The section is fully absent.
- **Verification**: `grep -n "Auto Boot" .squidsquad/config.md` returns no matches.

---

### TC-2: auto-boot field removed from config.py FIELD_MAP
- **Precondition**: `references/scripts/config.py` FIELD_MAP currently contains `"auto-boot": ("Auto Boot Agents", "Enabled")` at line 53.
- **Steps**: After the task ships, read `references/scripts/config.py`.
- **Expected**: The `"auto-boot"` key is absent from `FIELD_MAP`. No other FIELD_MAP entries are removed or altered.
- **Verification**: `grep "auto-boot" references/scripts/config.py` returns no matches. `grep -c '".*":' references/scripts/config.py` produces a count one less than before.

---

### TC-3: config.py get auto-boot returns empty/error after field removal
- **Precondition**: `auto-boot` key removed from FIELD_MAP.
- **Steps**: Run `python references/scripts/config.py get auto-boot`.
- **Expected**: Script exits non-zero or returns an empty string — does not crash with an unhandled exception, does not return a stale value.
- **Verification**: Exit code is non-zero or output is blank. No traceback.

---

### TC-4: boot_remote.py config guard block removed
- **Precondition**: `references/scripts/boot_remote.py` currently contains a try/except block (lines 459–467) that reads `Auto Boot.*: yes/no` from config.md and exits early with `action: disabled` if the value is `no`.
- **Steps**: After the task ships, read `references/scripts/boot_remote.py`.
- **Expected**: The `re.search(r"Auto Boot.*?:\s*(yes|no)")` block is absent. The `main()` function proceeds directly to the `# Run` block after prerequisite checks.
- **Verification**: `grep -n "Auto Boot" references/scripts/boot_remote.py` returns no matches. `grep -n "disabled" references/scripts/boot_remote.py` returns no matches (unless the word appears elsewhere for unrelated reasons).

---

### TC-5: boot_remote.py runs unconditionally when called without config guard
- **Precondition**: Config guard removed. `.squidsquad/config.md` does NOT contain an `Auto Boot Agents` section (post-task state).
- **Steps**: Run `python references/scripts/boot_remote.py --all --dry-run --json`.
- **Expected**: Script does not exit with `action: disabled`. It runs the boot detection logic and returns a JSON array of per-agent results. Each entry has `action`, `success`, `role`, and `message` fields.
- **Verification**: Output is a valid JSON array. No entry has `"action": "disabled"`. Exit code is 0 if no spawn failures.

---

### TC-6: auto_boot_agents field absent from cycle-input.json
- **Precondition**: Before the task, `_build_pm_input()` in `cycle_pre.py` sets `config["auto_boot_agents"] = _config_get("auto-boot-agents").lower() == "yes"`.
- **Steps**: After the task ships, run `python references/scripts/cycle_pre.py pm` and read `.squidsquad/pm/cycle-input.json`.
- **Expected**: The `config` block in cycle-input.json does NOT contain an `auto_boot_agents` key.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert 'auto_boot_agents' not in d.get('config', {}), 'auto_boot_agents still present'"` exits 0.

---

### TC-7: boot_results field present in cycle-input.json
- **Precondition**: cycle_pre.py modified to call `boot_remote.py --all --json` and capture results.
- **Steps**: Run `python references/scripts/cycle_pre.py pm` and read `.squidsquad/pm/cycle-input.json`.
- **Expected**: The JSON contains a `boot_results` key at the top level (or within the role-specific block). Its value is a list. Each element (if any) has at minimum `role`, `action`, and `success` fields matching boot_remote.py's `--json` output format.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert 'boot_results' in d, 'boot_results missing'; assert isinstance(d['boot_results'], list), 'boot_results not a list'"` exits 0.

---

### TC-8: boot_results populated correctly when agents need booting
- **Precondition**: At least one configured dev agent has a dead/absent `.health` file (simulate by removing `.squidsquad/<role>/.health`). No `.stop` sentinel for that role.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`. Read `.squidsquad/pm/cycle-input.json`.
- **Expected**: `boot_results` contains an entry for the dead agent with `action: "spawn"` (or `action: "dry-run"` if cycle_pre calls with `--dry-run`). `success` is `true` if spawn succeeded or platform supports it.
- **Verification**: Parse `boot_results` from cycle-input.json. Filter for the target role. Assert `action` is not `"skip"`.

---

### TC-9: boot_results populated correctly when all agents are already running
- **Precondition**: All configured dev agents have a fresh `.health` file (write a recent epoch to each agent's `.squidsquad/<role>/.health`).
- **Steps**: Run `python references/scripts/cycle_pre.py pm`. Read `.squidsquad/pm/cycle-input.json`.
- **Expected**: `boot_results` contains an entry for each configured agent with `action: "skip"` and a message indicating the agent is alive.
- **Verification**: Parse `boot_results`. All entries have `"action": "skip"`. Exit code of cycle_pre.py is 0.

---

### TC-10: No agents configured — boot_results graceful empty
- **Precondition**: `.squidsquad/config.md` has no dev agents listed (or the dev agents section is empty). Simulate on a minimal test install.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`. Read `.squidsquad/pm/cycle-input.json`.
- **Expected**: `boot_results` is an empty list `[]` or a single-element list with a "no agents configured" skip entry. cycle_pre.py does not crash or raise an exception.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); r=d.get('boot_results', None); assert r is not None, 'boot_results key missing'; assert isinstance(r, list), 'not a list'"` exits 0.

---

### TC-11: PM itself excluded from boot_results
- **Precondition**: The `pm` role is listed in `config.md` Dev Agents. All agents including pm have dead health files.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`. Read `.squidsquad/pm/cycle-input.json`.
- **Expected**: `boot_results` does NOT contain an entry with `role: "pm"`. `_get_all_roles()` discards "pm" before calling boot logic.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); roles=[r.get('role') for r in d.get('boot_results',[])]; assert 'pm' not in roles, 'pm found in boot_results'"` exits 0.

---

### TC-12: .stop sentinel respected when called from cycle_pre
- **Precondition**: A configured dev agent has a dead `.health` file AND a `.squidsquad/<role>/.stop` file.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`. Read `.squidsquad/pm/cycle-input.json`.
- **Expected**: `boot_results` entry for the stopped agent has `action: "skip"` with a message mentioning `.stop` sentinel. No terminal is spawned for that agent.
- **Verification**: Parse `boot_results`, find the stopped role, assert `"action": "skip"` and message contains "stop".

---

### TC-13: Spawn failure captured in boot_results
- **Precondition**: A configured dev agent needs booting (dead health). Terminal spawner will fail (e.g., `wt.exe` not found on a CI machine, or simulate by temporarily renaming the boot script).
- **Steps**: Run `python references/scripts/cycle_pre.py pm`. Read `.squidsquad/pm/cycle-input.json`.
- **Expected**: `boot_results` entry for the agent has `action: "spawn"` and `success: false`. cycle_pre.py does not crash. The PM cycle continues (spawn failure is captured, not fatal to the pre-cycle script).
- **Verification**: Parse `boot_results`, find the failing role, assert `"success": false`. cycle_pre.py exits 0 (spawn failure is non-fatal to pre-cycle).

---

### TC-14: Boot Remote Agents step absent from composed PM CLAUDE.md
- **Precondition**: `references/sub-skills/common/boot-remote-agents.md` has been updated and `compose.py deploy pm` has been run.
- **Steps**: Read `.squidsquad/pm/CLAUDE.md`. Search for the "Boot Remote Agents" step header and the `Auto Boot Agents` config check.
- **Expected**: No `### Step — Boot Remote Agents (PM Only)` heading. No `Check \`Auto Boot Agents\` in \`config.md\`` instruction. No `python references/scripts/boot_remote.py --all --json` call in the template step (this call is now in cycle_pre.py, not in the template).
- **Verification**: `grep -n "Boot Remote Agents" .squidsquad/pm/CLAUDE.md` returns no matches. `grep -n "Auto Boot" .squidsquad/pm/CLAUDE.md` returns no matches.

---

### TC-15: PM template still references reboot_agent.py for governance
- **Precondition**: `.squidsquad/pm/CLAUDE.md` has been recomposed.
- **Steps**: Read `.squidsquad/pm/CLAUDE.md`. Search for `reboot_agent.py`.
- **Expected**: `reboot_agent.py` references remain in the Agent Lifecycle section (safe reboot, force reboot, reboot all). The governance tool is still available to PM.
- **Verification**: `grep -c "reboot_agent.py" .squidsquad/pm/CLAUDE.md` returns a count ≥ 1.

---

### TC-16: PM template references boot_results in cycle-input instructions
- **Precondition**: `.squidsquad/pm/CLAUDE.md` has been recomposed after sub-skill update.
- **Steps**: Read the cycle-input.json reading instructions in `.squidsquad/pm/CLAUDE.md`.
- **Expected**: The PM template either (a) mentions `boot_results` as a field PM should read and act on, or (b) the boot-remote-agents sub-skill has been replaced with a "read boot_results" note so PM knows what to do with spawn failures. There is no instruction to call `boot_remote.py` directly as a template step.
- **Verification**: `grep -n "boot_results" .squidsquad/pm/CLAUDE.md` returns ≥ 1 match (or the sub-skill note is present). `grep -n "boot_remote.py --all" .squidsquad/pm/CLAUDE.md` returns no matches in a template step context.

---

### TC-17: start-squad.ps1 exists and calls boot_remote.py --all
- **Precondition**: Task complete, start-squad scripts written to their target directory.
- **Steps**: Read `.squidsquad/start-squad.ps1` (or the path chosen by dev).
- **Expected**: File exists. It calls `python references/scripts/boot_remote.py --all` (with or without `--json`). It does not call individual `start-role.ps1` scripts directly. It does not reimplement role enumeration logic.
- **Verification**: File is present. `grep "boot_remote.py" .squidsquad/start-squad.ps1` returns a match with `--all`.

---

### TC-18: start-squad.sh exists and calls boot_remote.py --all
- **Precondition**: Task complete, start-squad scripts written to their target directory.
- **Steps**: Read `.squidsquad/start-squad.sh` (or the path chosen by dev).
- **Expected**: File exists. It calls `python references/scripts/boot_remote.py --all` (with or without `--json`). It does not call individual `start-role.sh` scripts directly.
- **Verification**: File is present. `grep "boot_remote.py" .squidsquad/start-squad.sh` returns a match with `--all`.

---

### TC-19: start-squad.sh is executable and handles output
- **Precondition**: `start-squad.sh` written.
- **Steps**: On a Unix-like system (WSL, macOS, Linux), run `bash .squidsquad/start-squad.sh` (without actual agents configured to avoid spawning terminals).
- **Expected**: Script runs without syntax errors. Output is printed or suppressed cleanly. Exit code reflects boot_remote.py's result (0 on skip/alive, non-zero on spawn failure if applicable).
- **Verification**: `bash -n .squidsquad/start-squad.sh` exits 0 (no syntax errors). Running with `--dry-run` if supported produces output without spawning terminals.

---

### TC-20: start-squad called while agents already running — no duplicate spawn
- **Precondition**: At least one agent is running (alive `.health` file, valid PID).
- **Steps**: Run `python references/scripts/boot_remote.py --all --dry-run --json` (simulating what start-squad calls).
- **Expected**: Agents with alive health status produce `action: "skip"` entries. No double-boot attempted.
- **Verification**: JSON output has no `action: "spawn"` entries for already-running agents.

---

### TC-21: compose.py rerun regenerates PM CLAUDE.md from updated sub-skill
- **Precondition**: `references/sub-skills/common/boot-remote-agents.md` has been updated by the dev. `.squidsquad/pm/CLAUDE.md` still contains the old boot step.
- **Steps**: Run `python references/scripts/compose.py deploy pm`.
- **Expected**: `.squidsquad/pm/CLAUDE.md` is regenerated. The old "Boot Remote Agents" step content is gone. Any updated boot-remote-agents sub-skill content (or its replacement) is reflected in the output.
- **Verification**: Check mtime of `.squidsquad/pm/CLAUDE.md` is newer than before the compose run. `grep "Auto Boot Agents" .squidsquad/pm/CLAUDE.md` returns no matches.

---

### TC-22: agent-instructions.md no longer references Auto Boot config check
- **Precondition**: `references/agent-instructions.md` currently references the Auto Boot Agents config check at line 436.
- **Steps**: After the task ships, read `references/agent-instructions.md`.
- **Expected**: No reference to `Auto Boot Agents` config check at the former line 436 location. The line is removed or replaced with boot_results guidance.
- **Verification**: `grep -n "Auto Boot" references/agent-instructions.md` returns no matches.

---

### TC-23: Existing tests pass — python tests/run_tests.py
- **Precondition**: All code changes applied, compose rerun done.
- **Steps**: Run `python tests/run_tests.py` from the repo root.
- **Expected**: All 913 (or current total) tests pass. Zero failures, zero errors.
- **Verification**: Exit code 0. Output does not contain "FAILED" or "ERROR". Test count matches or exceeds pre-task baseline.

---

### TC-24: PID singleton still works — no duplicate agents
- **Precondition**: An agent is already running (valid PID in `.squidsquad/<role>/.pid`, process alive).
- **Steps**: Run `python references/scripts/boot_remote.py --all --json`.
- **Expected**: The running agent's entry has `action: "skip"`. The start-role wrapper script (if called directly) would print "Agent already running" and exit 1 without spawning a duplicate.
- **Verification**: boot_remote.py JSON shows `"action": "skip"` for the running agent. No second Claude process spawned.

---

### TC-25: cycle_pre.py boot call does not block the pre-cycle phase
- **Precondition**: boot_remote.py spawns terminals via `subprocess.Popen` with `DETACHED_PROCESS` (non-blocking). cycle_pre.py calls it synchronously to read JSON output.
- **Steps**: Run `python references/scripts/cycle_pre.py pm` and measure elapsed time. No agents should need booting (all alive or stopped).
- **Expected**: cycle_pre.py completes in a time consistent with normal pre-cycle duration (no indefinite hang). Even if a terminal spawn occurs, cycle_pre.py captures the JSON result and returns.
- **Verification**: `time python references/scripts/cycle_pre.py pm` completes within a reasonable bound (e.g., under 30 seconds on a standard machine with all agents alive).

---

### TC-26: cycle_pre.py handles boot_remote.py non-zero exit gracefully
- **Precondition**: boot_remote.py returns exit code 1 when a spawn fails.
- **Steps**: Simulate a spawn failure (e.g., remove the boot script for a configured agent). Run `python references/scripts/cycle_pre.py pm`. Read cycle-input.json.
- **Expected**: cycle_pre.py does not crash. `boot_results` is present with the failure captured (`success: false`). cycle_pre.py itself exits 0 (spawn failures are informational, not fatal to the pre-cycle).
- **Verification**: cycle_pre.py exit code is 0. `boot_results` contains the failure entry. No Python traceback in stderr.

---

### TC-27: Regression — boot-remote-agents sub-skill source file still exists
- **Precondition**: Task complete.
- **Steps**: Check for the existence of `references/sub-skills/common/boot-remote-agents.md`.
- **Expected**: File still exists (it is kept as documentation/reference per locked decision — only the PM template step is removed, not the source file).
- **Verification**: `ls references/sub-skills/common/boot-remote-agents.md` exits 0.

---

### TC-28: Regression — reboot_agent.py is unchanged and still functional
- **Precondition**: Task complete.
- **Steps**: Run `python references/scripts/reboot_agent.py --help` (or dry-run equivalent).
- **Expected**: reboot_agent.py is unchanged from pre-task state. It accepts `--force`, `--all`, `--timeout` flags. It does not reference `Auto Boot Agents` config.
- **Verification**: `python references/scripts/reboot_agent.py --help` exits 0 without error. `grep "Auto Boot" references/scripts/reboot_agent.py` returns no matches (it never referenced it, confirming no regressions).

---

### TC-29: Regression — start-role scripts unaffected
- **Precondition**: Task complete.
- **Steps**: Read `.squidsquad/start-pm.sh` and `.squidsquad/start-pm.ps1` (or the skill agent's start scripts). Compare to pre-task state.
- **Expected**: start-role scripts are unchanged. They still contain PID singleton check, pre-flight checks, branch setup, heartbeat, and Claude spawn. No references to `Auto Boot Agents` were ever in these files.
- **Verification**: `grep "Auto Boot" .squidsquad/start-*.sh .squidsquad/start-*.ps1` returns no matches. Scripts are byte-for-byte identical to pre-task versions (or differ only if they were legitimately regenerated by a separate compose run).

---

## Smoke Tests

- [ ] `grep -n "Auto Boot" .squidsquad/config.md` — no matches
- [ ] `grep -n "auto-boot" references/scripts/config.py` — no matches
- [ ] `grep -n "auto_boot_agents" references/scripts/cycle_pre.py` — no matches
- [ ] `grep -n "Auto Boot" references/scripts/boot_remote.py` — no matches
- [ ] `python references/scripts/boot_remote.py --all --dry-run --json` — exits 0, returns JSON array with no `disabled` action
- [ ] `python references/scripts/cycle_pre.py pm` — exits 0, `.squidsquad/pm/cycle-input.json` contains `boot_results` and no `auto_boot_agents`
- [ ] `grep "boot_results" .squidsquad/pm/cycle-input.json` — matches
- [ ] `grep -n "Boot Remote Agents" .squidsquad/pm/CLAUDE.md` — no matches
- [ ] `grep -n "reboot_agent.py" .squidsquad/pm/CLAUDE.md` — at least 1 match (governance access preserved)
- [ ] `.squidsquad/start-squad.ps1` exists
- [ ] `.squidsquad/start-squad.sh` exists
- [ ] `grep "boot_remote.py.*--all" .squidsquad/start-squad.ps1` — matches
- [ ] `grep "boot_remote.py.*--all" .squidsquad/start-squad.sh` — matches
- [ ] `python tests/run_tests.py` — all tests pass, exit code 0

---

## Regression Risks

- **Silent boot skip**: If `auto_boot_agents` is removed from cycle-input.json but the PM template still contains an `if auto_boot_agents` check referencing it, the PM will silently skip boot processing. Watch for: PM agent logs that show boot step skipped even though no `boot_results` guidance was followed.
- **Double-boot race**: If both cycle_pre.py and a leftover PM template step call `boot_remote.py --all`, the same agent could receive two spawn attempts in rapid succession. Watch for: duplicate terminal windows for the same role on the first cycle after upgrade.
- **Live PM running old template**: If `.squidsquad/pm/CLAUDE.md` is NOT recomposed after sub-skill changes, the live PM continues running the old boot step (with the `Auto Boot Agents` config check). Since the config section is removed, the check will find no match and fall through — meaning boot detection runs from the old step AND from cycle_pre.py. Watch for: two boot_remote.py invocations per PM cycle in the cycle log.
- **PM reading stale `auto_boot_agents: false`**: On an install that has both the new cycle_pre.py (no `auto_boot_agents` field) and an old PM CLAUDE.md (still references `auto_boot_agents`), the PM will read `undefined` as falsy and skip boot governance entirely. Ensure compose rerun is atomic with cycle_pre.py changes.
- **start-squad enumerating roles independently**: If start-squad scripts iterate config.md directly instead of delegating to `boot_remote.py --all`, they bypass `.stop` sentinel checks and liveness detection. Watch for: agents with `.stop` files being spawned by start-squad.
- **config.py test coverage**: Tests that call `config.py get auto-boot` may fail if the test suite hardcodes an expected return value. Watch for: test failures in `tests/test_config.py` or related config tests after FIELD_MAP change.
- **boot_remote.py called on installs still using old config**: Installs that have `Auto Boot Agents: no` and have not yet run squidsquad-upgrade will see boot detection activate after upgrade (guard removed). This is intentional but a behavioral surprise. Watch for: user reports of agents being spawned unexpectedly after upgrade.

---

## Comprehension Questions (task touches LLM-consumed instructions)

### CQ-1: Does the PM template include a step to call boot_remote.py directly?
- **Files**: `.squidsquad/pm/CLAUDE.md`
- **Expected**: No. The PM template does not contain a "Boot Remote Agents" step. Boot detection is handled by `cycle_pre.py` before the creative phase begins. The PM reads pre-computed `boot_results` from `cycle-input.json` rather than running `boot_remote.py` itself.

### CQ-2: Where does the PM find out which agents were booted this cycle?
- **Files**: `.squidsquad/pm/CLAUDE.md`, description of cycle-input.json fields
- **Expected**: The PM reads `boot_results` from `cycle-input.json` (written by cycle_pre.py). The `boot_results` field is a list of per-agent result objects, each with `role`, `action`, `success`, and `message`. The PM uses this to log spawn failures and take governance actions — it does not call boot_remote.py to get this information.

### CQ-3: Can the PM use reboot_agent.py, and when should it?
- **Files**: `.squidsquad/pm/CLAUDE.md` (Agent Lifecycle section)
- **Expected**: Yes. `reboot_agent.py` is available for deliberate governance actions: rebooting an agent after a template change ships, force-rebooting a stuck agent, or rebooting all agents. It is distinct from the automatic liveness boot-detection in cycle_pre.py. The PM uses `reboot_agent.py` when it decides a reboot is warranted, not for routine liveness checks.

### CQ-4: Is there a config toggle to disable automatic agent booting?
- **Files**: `.squidsquad/pm/CLAUDE.md`, `.squidsquad/config.md`
- **Expected**: No. The `Auto Boot Agents` config toggle no longer exists. Boot detection runs unconditionally every PM cycle. The per-role opt-out mechanism is placing a `.stop` file at `.squidsquad/<role>/.stop` — this prevents boot_remote.py from spawning that specific agent even when it is dead.

### CQ-5: What does a PM agent do when boot_results shows a spawn failure?
- **Files**: `.squidsquad/pm/CLAUDE.md`
- **Expected**: The PM reads `boot_results` from cycle-input.json during Phase 2 creative work. If any entry has `success: false` and `action: "spawn"`, the PM logs the failure in Discussion on the agent's current task issue — the same behavior that was previously described in the old boot-remote-agents sub-skill step.

### CQ-6: What is start-squad and how does it relate to cycle_pre boot detection?
- **Files**: `.squidsquad/start-squad.ps1` or `.squidsquad/start-squad.sh`
- **Expected**: `start-squad` is a human-facing convenience script that boots all configured agents at once. It calls `boot_remote.py --all` and exits. It is for manual use ("start everything") not for automated/recurring boot detection. Recurring boot detection is cycle_pre.py's responsibility, running each PM cycle.
