# FEAT-4 Test Plan — Boot Remote Agents Sub-Skill

**Feature**: #4 — PM auto-boots missing/stalled teammates via composable sub-skill
**Files under test**:
- `references/scripts/boot_remote.py` (new, ~150 lines)
- `references/sub-skills/common/boot-remote-agents.md` (new)
- `references/sub-skills/roles/pm-agent.md` (modified — composition anchor)
- `references/sub-skills/roles/pm-lean.md` (modified — composition anchor)
- `.squidsquad/config.md` schema (new `Auto Boot Agents` entry)

**Test approach**: Python unit tests for `boot_remote.py` detection + rate limiter + lock logic (mock `subprocess`, fake `.local-config`, fake clone dirs). Manual integration tests for actual terminal spawn per OS. Composition tests run against the real `compose.py` pipeline. Smoke tests end-to-end.

**Hard dependency**: #335 (`health_check.py`) must be shipped and verified before #4 starts implementation. Detection TCs consume `health_check.py --json` output as authoritative input.

---

## Scope

Tests cover detection-first logic (5 agent states), per-OS canonical terminal spawn (Windows/macOS/Linux), rate-limiter / cooldown, lock file races, sub-skill composition into PM, config.md integration, CLI surface of `boot_remote.py`, integration with `health_check.py`, integration with PM's Step 7 cycle, failure modes, and regression safety.

Platform-specific spawn tests are tagged `[Win]`, `[mac]`, `[Linux]` in the Type column so they can be run selectively.

All tests trace back to at least one acceptance criterion from `FEAT-4-CONTEXT.md`.

---

## Test Cases

### A. Detection Logic (unit tests for boot_remote.py)

These tests exercise the detection layer with synthetic clone directories. No real subprocess spawn — detection should decide "spawn or skip" before any Popen is called.

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-01 | `.stop` sentinel exists → SKIP (highest priority) | 1. Fake clone with `.squidsquad/skill/.stop` present. 2. Also create `.pid` with dead PID and a stale `current-state`. 3. Run `boot_remote.detect(role="skill")`. | Returns `SKIP` with reason `stopped`. No spawn attempted. `.stop` takes precedence over all other signals. | unit |
| TC-02 | `.pid` exists AND PID is alive → SKIP | 1. Fake clone with `.pid` containing PID of a real live process (e.g. current test process). 2. Run detect. | Returns `SKIP` with reason `running`. | unit |
| TC-03 | `.pid` exists BUT PID is dead → SPAWN (revive crashed) | 1. Fake clone with `.pid` containing `99999` (or any guaranteed-dead PID). 2. Run detect. | Returns `SPAWN` with reason `crashed`. | unit |
| TC-04 | No `.pid`, `current-state` mtime < 2× interval → SKIP (recently alive) | 1. Fake clone, no `.pid`, `current-state` with mtime = now - 10s, interval = 60s. 2. Run detect. | Returns `SKIP` with reason `recently-alive`. | unit |
| TC-05 | No `.pid`, `current-state` mtime ≥ 2× interval → SPAWN (stalled) | 1. Fake clone, no `.pid`, `current-state` with mtime = now - 300s, interval = 60s. 2. Run detect. | Returns `SPAWN` with reason `stalled`. | unit |
| TC-06 | No `.pid`, no `current-state` → SPAWN (fresh) | 1. Fake clone with nothing — first-ever boot scenario. 2. Run detect. | Returns `SPAWN` with reason `fresh`. | unit |
| TC-07 | `.stop` takes precedence even over dead PID + stale state | 1. Fake clone with `.stop`, `.pid` dead, `current-state` stale. 2. Run detect. | Returns `SKIP` with reason `stopped`. No spawn attempted. | unit |
| TC-08 | Detection reads `.local-config` correctly (cross-clone paths) | 1. Write `.local-config` with `- **skill**: /tmp/fake-skill-clone`. 2. Run detect for role `skill`. | Detection paths all resolve under `/tmp/fake-skill-clone/.squidsquad/skill/`. No hardcoded paths. | unit |
| TC-09 | Detection consumes `health_check.py --json` when available | 1. Stub `health_check.py --json` to return `{"skill": {"status": "stalled"}}`. 2. Run detect. | boot_remote.py uses the health_check output as authoritative and returns `SPAWN`. Does not re-read files. | unit |
| TC-10 | Detection falls back gracefully if `health_check.py` missing | 1. Remove / mock-absent `health_check.py`. 2. Run detect. | Reads `.pid` / `current-state` / `.stop` directly. Logs "health_check.py not available, using direct file reads". Still returns correct decision. | unit |
| TC-11 | Detection handles missing `current-state` + `.pid` present alive | 1. Fake clone with live `.pid` only, no `current-state`. 2. Run detect. | Returns `SKIP running` — PID aliveness is authoritative when present. | unit |
| TC-12 | Unknown role → error (not silent skip) | 1. Role not in `.local-config`. 2. Run detect. | Raises / returns error `unknown-role`. Exit code 2 (detection error). | unit |
| TC-13 | 5-state matrix: running / crashed / stalled / fresh / stopped | Parametrized test over all 5 states with a fixture per state. | Each state resolves to the correct SPAWN or SKIP decision per AC. | unit |

### B. Spawn Mechanism — Per OS

Integration tests that actually call `subprocess.Popen`. Some must be manual on the target OS. Marker env var technique: `boot_remote.py` injects `SQUIDSQUAD_BOOT_MARKER=<uuid>` into the spawned env; the fake boot script writes that marker to a file so we can assert the terminal started.

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-14 | Windows — `wt.exe` available → spawn Windows Terminal tab | 1. Windows host with Windows Terminal installed. 2. `boot_remote.py --role skill --force`. 3. Fake boot script writes marker file. | New wt tab appears. Marker file written with the injected UUID within 5s. Exit 0. | integration [Win] |
| TC-15 | Windows — `wt.exe` missing → fall back to `cmd /k` | 1. Mock `shutil.which("wt.exe")` → None. 2. Run spawn. | Falls back to `start "" cmd /k <script>`. New cmd window appears. Marker written. | integration [Win] |
| TC-16 | Windows — both unavailable → print manual command, fail | 1. Mock both wt and cmd unavailable. 2. Run spawn. | Prints full manual command for the human. Exit code 1 (spawn failed). No crash. | unit [Win] |
| TC-17 | macOS — Terminal.app spawn via osascript works | 1. macOS host. 2. Run spawn for role skill. 3. Fake boot script writes marker. | `osascript -e 'tell app "Terminal" to do script ...'` runs. New Terminal window appears. Marker written within 5s. | integration [mac] |
| TC-18 | macOS — Terminal.app unavailable → print manual, fail | 1. Mock osascript absent (or Terminal.app not installed — synthetic). 2. Run spawn. | Prints manual command. Exit 1. | unit [mac] |
| TC-19 | Linux — `tmux new-session -d` spawn works | 1. Linux host with tmux installed. 2. Run spawn. 3. Fake boot script writes marker. | tmux session `squidsquad-skill` created detached. Marker written within 5s. `tmux ls` shows the session. | integration [Linux] |
| TC-20 | Linux — tmux unavailable → print manual, fail | 1. Mock `shutil.which("tmux")` → None. 2. Run spawn. | Prints manual command. Exit 1. No crash. | unit [Linux] |
| TC-21 | Spawned terminal inherits parent env (marker var) | 1. Set `SQUIDSQUAD_BOOT_MARKER=test-uuid-abc` in parent env via boot_remote.py. 2. Spawn. 3. Fake boot script writes `$SQUIDSQUAD_BOOT_MARKER` to file. | File contents = `test-uuid-abc`. Confirms env inheritance works on the active OS. | integration |
| TC-22 | Spawn returns within 5 seconds (no hang) | 1. Run spawn. 2. Wall-clock timer around the Popen call. | `boot_remote.py` returns from the spawn within 5s regardless of whether the child terminal has finished booting the agent. | integration |
| TC-23 | Spawn never blocks on child terminal process | 1. Fake boot script sleeps 60s. 2. Run spawn. 3. Measure return time. | `boot_remote.py` returns immediately after Popen (no wait). Child is detached. | unit |

### C. Rate Limiter / Spawn-Spam Prevention

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-24 | First spawn of role X → succeeds, writes log entry | 1. Clean `.squidsquad/boot-attempts.log`. 2. Run boot_remote.py for skill. | Spawn proceeds. Log file gains one entry with timestamp, role, status, reason. | unit |
| TC-25 | Second spawn of role X within cooldown → SKIP cooldown | 1. After TC-24, immediately run spawn again for skill. | Returns `SKIP` with reason `cooldown-active`. Log gains a cooldown-skipped entry. No Popen called. | unit |
| TC-26 | Second spawn after cooldown expires → proceeds | 1. After TC-24, fake-advance the log timestamp backward by (cooldown + 1 min). 2. Run spawn. | Spawn proceeds. Log gains a new success entry. | unit |
| TC-27 | Separate roles unaffected by each other's cooldowns | 1. Run spawn for skill. 2. Immediately run spawn for pm. | pm spawn proceeds (independent cooldown). skill stays in cooldown. Both roles tracked independently. | unit |
| TC-28 | Cooldown window configurable or documented default (10 min) | Read boot_remote.py source or config.md schema. | Either a `Boot Cooldown Minutes:` entry in config.md (preferred) OR a clearly-named constant in boot_remote.py. Default is 10 min. | unit |
| TC-29 | `.squidsquad/boot-attempts.log` format is parseable | Inspect the log after several spawn attempts across roles. | Each line has: ISO timestamp, role, status (spawned/skipped-cooldown/failed), reason. Machine-readable (tab/JSON-line). | unit |
| TC-30 | Rate limiter state survives across boot_remote.py invocations | 1. Run spawn (success). 2. Exit boot_remote.py. 3. Run boot_remote.py again in cooldown window. | Second invocation still sees the cooldown (state persists via the log file, not in-memory). | unit |

### D. Race Condition / Lock File

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-31 | Two simultaneous boot_remote.py for role X — only one spawns | 1. Thread/process A acquires lock and spawns. 2. Thread/process B tries same role while A holds lock. | A spawns successfully. B sees lock, returns `SKIP lock-held`. Exactly one spawn. | integration |
| TC-32 | Lock file auto-expires after TTL (30s) | 1. Manually write `.squidsquad/boot-lock` with timestamp = now - 60s. 2. Run spawn. | Stale lock is detected, overwritten. Spawn proceeds normally. No deadlock. | unit |
| TC-33 | Lock file released on success | 1. Run spawn. 2. Inspect `.squidsquad/boot-lock` after completion. | Lock file absent (or marked released). Another boot_remote.py call can immediately acquire it. | unit |
| TC-34 | Lock file released on failure | 1. Force spawn to fail (missing boot script). 2. Inspect lock. | Lock released even on failure path. Next invocation can acquire. | unit |
| TC-35 | Lock is per-role, not global | 1. Hold lock for skill. 2. Try spawn for pm. | pm spawn proceeds — separate lock key or separate lock file. | unit |

### E. Sub-Skill Composition

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-36 | Sub-skill file exists at canonical path | Read `references/sub-skills/common/boot-remote-agents.md`. | File exists, non-empty, has a clear purpose section, and has invocation instructions referencing `boot_remote.py`. | unit |
| TC-37 | Sub-skill content is domain-only (Q-new14 rule) | Scan sub-skill for forbidden internal references. | No mention of `config.md`, `CLAUDE.md`, `tracker.py`, status labels, `.squidsquad/`, or other SquidSquad internals. Prose is describable as "how to boot a remote teammate" without squad context. | unit |
| TC-38 | Sub-skill listed in `references/sub-skills/manifest.md` | Read manifest. | `common/boot-remote-agents` appears in the inventory and in PM/QA composition order. | unit |
| TC-39 | PM CLAUDE.md template has composition anchor | Read `references/sub-skills/roles/pm-agent.md`. | An include anchor for `common/boot-remote-agents` exists immediately after Step 7 (Agent Health Check) and before the next include. | unit |
| TC-40 | pm-lean.md template has the same anchor | Read `references/sub-skills/roles/pm-lean.md`. | Same anchor present. | unit |
| TC-41 | Composition renders sub-skill at the anchor point | 1. Run `python references/scripts/compose.py deploy pm`. 2. Read `.squidsquad/pm/CLAUDE.md`. | Generated CLAUDE.md contains the sub-skill body inserted at the anchor. Step numbering still legible (Step 7 → Step 7b boot remote → rest). | integration |
| TC-42 | Re-composition is idempotent | 1. Run `compose.py deploy pm` twice in a row. 2. Diff the two outputs. | Identical. No duplicate sub-skill content. Hash-stable. | unit |
| TC-43 | `/squidsquad-upgrade` re-composes and picks up the sub-skill | 1. Install with an older template. 2. Add sub-skill to templates. 3. Run `/squidsquad-upgrade`. | PM's live CLAUDE.md now contains the sub-skill. | integration |

### F. Config.md Integration

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-44 | config.md schema gains `Auto Boot Agents: yes` (default) | 1. Fresh install via `/squidsquad-setup`. 2. Read `.squidsquad/config.md`. | Entry `Auto Boot Agents: yes` is present under a relevant section with default yes. | unit |
| TC-45 | `Auto Boot Agents: no` disables feature | 1. Set `Auto Boot Agents: no`. 2. Run boot_remote.py for any role. | Exits with message "Auto Boot Agents disabled in config.md". Exit code 3. No detection, no spawn. | unit |
| TC-46 | Missing entry defaults to `yes` (backward compat) | 1. Delete `Auto Boot Agents` line from config.md. 2. Run boot_remote.py. | Treats as `yes`, proceeds with detection and spawn. Logs a warning noting the default. | unit |
| TC-47 | `config.py get auto-boot-agents` returns correct value | Run the config accessor. | Returns `yes`/`no` matching config.md entry. | unit |

### G. CLI Interface — boot_remote.py

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-48 | `--role skill` checks just that role | 1. Run `python references/scripts/boot_remote.py --role skill`. | Processes only skill. Other roles untouched. Output names skill. | unit |
| TC-49 | `--all` checks every role in `.local-config` | 1. Run `python references/scripts/boot_remote.py --all`. | Iterates every role in `.local-config`, applies detection, spawns only those that need it. | unit |
| TC-50 | `--dry-run --role skill` reports action, no spawn | 1. Force skill to the `stalled` state. 2. Run `--dry-run --role skill`. | Reports "would spawn skill (stalled)". No Popen called. No lock acquired. Exit 0. | unit |
| TC-51 | `--json` emits machine-readable output | 1. Run `--all --json` with varied states. | stdout is valid JSON: `{"skill": {"action": "spawn", "reason": "stalled"}, "pm": {"action": "skip", "reason": "running"}}`. | unit |
| TC-52 | `--help` prints usage | 1. Run `--help`. | Prints all flags (--role, --all, --dry-run, --json, --force), exit 0. | unit |
| TC-53 | Exit code 0 — success (including skip-for-valid-reason) | Dry-run a healthy agent. | Exit 0. | unit |
| TC-54 | Exit code 1 — spawn failed | Force spawn failure (missing boot script). | Exit 1 with error on stderr. | unit |
| TC-55 | Exit code 2 — detection error | Unknown role / malformed `.local-config`. | Exit 2. | unit |
| TC-56 | Exit code 3 — disabled via config.md | `Auto Boot Agents: no`. | Exit 3. | unit |
| TC-57 | `--force` bypasses cooldown (dev discretion) | 1. In cooldown. 2. Run with `--force`. | Spawn proceeds anyway. Log entry notes force. | unit |

### H. Integration with #335 health_check.py

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-58 | boot_remote.py calls `health_check.py --json` for detection | Trace / mock the subprocess call inside boot_remote.py. | boot_remote.py invokes `python references/scripts/health_check.py --json` and consumes its output. | unit |
| TC-59 | health_check.py missing → graceful fallback | 1. Rename health_check.py temporarily. 2. Run boot_remote.py. | Falls back to direct file reads. Prints a warning. Still returns correct decisions. | unit |
| TC-60 | health_check.py reports all healthy → no spawns | 1. Stub `--json` output = all `running`. 2. Run `boot_remote.py --all`. | Detection returns `SKIP running` for every role. Zero Popen calls. Exit 0. | unit |
| TC-61 | health_check.py reports one stalled → spawn that one only | 1. Stub `--json` output with `skill=stalled`, rest running. 2. Run `--all`. | Only skill is spawned. Other roles skipped. | unit |
| TC-62 | health_check.py output is authoritative over direct reads | 1. Contradictory: health_check says stalled, direct file says running. 2. Run boot_remote.py. | Trusts health_check.py (spawns). Authoritative source per locked decision Q1. | unit |

### I. Integration with PM Cycle

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-63 | PM Step 7 detects stalled → invokes boot_remote.py → agent boots | 1. Running PM with composed CLAUDE.md. 2. Kill skill agent (delete `.pid`, stale `current-state`). 3. Let PM run one cycle. | PM invokes `boot_remote.py --role skill` in Step 7, terminal spawns, skill agent starts up. Iteration log records the spawn. | integration |
| TC-64 | PM continues cycle after spawn (non-blocking) | Same as TC-63, wall-clock timer on the PM cycle. | PM's Step 7 does not hang waiting for the new terminal. PM advances to Step 8+ promptly (< 5s after Popen). | integration |
| TC-65 | PM logs spawn attempt in iter-N.md | Read `.squidsquad/pm/iterations/iter-N.md` after TC-63. | File contains an entry naming boot_remote.py invocation, role, result. Human-auditable. | integration |
| TC-66 | Spawn failure does not crash PM | 1. Force boot_remote.py to fail (missing boot script). 2. Run PM cycle. | PM logs the failure in Discussion/iter log. Continues Step 8+. Does not crash or loop. | integration |
| TC-67 | PM does not spawn an agent that is already running | 1. Healthy skill agent running. 2. Run PM cycle. | Detection returns `SKIP running`. PM logs "skill healthy". No Popen called. | integration |
| TC-68 | PM respects `.stop` sentinel via boot_remote.py | 1. Skill agent has `.stop`. 2. Run PM cycle. | Detection returns `SKIP stopped`. PM does NOT spawn (Q-new2 hard requirement). | integration |

### J. Failure Modes

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-69 | Target clone path doesn't exist | 1. `.local-config` points skill at `/nonexistent/path`. 2. Run boot_remote.py --role skill. | Reports "clone missing: /nonexistent/path". Exit 1. No crash. | unit |
| TC-70 | Boot script missing in clone | 1. Clone exists but `start-skill.ps1`/`.sh` absent. 2. Run spawn. | Reports "boot script missing". Exit 1. | unit |
| TC-71 | `subprocess.Popen` raises PermissionError | 1. Mock Popen to raise PermissionError. 2. Run spawn. | Catches error, reports "permission denied", exit 1. | unit |
| TC-72 | `.local-config` has malformed entry | 1. Write `.local-config` with garbage (no `- **role**:` prefix). 2. Run. | Reports "malformed .local-config". Exit 2. | unit |
| TC-73 | Parent PM crashes mid-spawn | 1. Start spawn from PM. 2. Kill PM mid-Popen. | Spawned terminal still starts (detached process). Child is not a subprocess of PM. | integration |
| TC-74 | Missing `.local-config` file entirely | 1. Delete `.local-config`. 2. Run. | Reports ".local-config missing". Exit 2. Graceful. | unit |

### K. Regression

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-75 | PM Step 7 health check still works (detection unchanged) | Run PM cycle with all agents healthy. | Step 7 still reports healthy agents. No behavior change to existing health check logic. | regression |
| TC-76 | `.stop` sentinel still pauses an agent | Create `.stop` on a running agent. | Wrapper respects it (from #250 behavior). Unchanged. | regression |
| TC-77 | `start-skill.sh` / `.ps1` still work when run directly by human | Run `./start-skill.ps1` manually (no boot_remote.py involved). | Agent boots normally. No new dependencies, no new env vars required. | regression |
| TC-78 | Existing agents continue cycling normally | Run a full PM cycle with everything healthy. | No new blocking operations. Cycle time within normal bounds. | regression |
| TC-79 | `/squidsquad-upgrade` re-composes PM and includes sub-skill | Run upgrade on the current repo. | Post-upgrade PM CLAUDE.md has the new sub-skill composed in. | regression |
| TC-80 | #335 health_check.py behavior unchanged | Run health_check.py standalone. | Same JSON output as before #4. boot_remote.py is only a consumer, not a modifier. | regression |

---

## Smoke Tests

Fast end-to-end sanity checks (target < 5 min total across all items).

- [ ] **S1** — `python references/scripts/boot_remote.py --help` runs, prints usage, exit 0
- [ ] **S2** — `boot_remote.py --dry-run --all` on a repo with all agents running → reports "all healthy, no action", exit 0
- [ ] **S3** — Delete skill's `.pid` → `boot_remote.py --dry-run --role skill` → reports "would spawn (stalled/crashed)"
- [ ] **S4** — Create `.squidsquad/skill/.stop` → `boot_remote.py --dry-run --role skill` → reports "stopped, skipping"
- [ ] **S5** — Set `Auto Boot Agents: no` in config.md → `boot_remote.py --all` → exits with "disabled" message, exit 3
- [ ] **S6** — Run `compose.py deploy pm` → inspect `.squidsquad/pm/CLAUDE.md` → sub-skill content present at anchor point
- [ ] **S7** — Run full PM cycle with one stalled agent → PM auto-boots it end-to-end (composition + detection + spawn all wired)
- [ ] **S8** — Manual happy-path boot on Windows (`wt.exe` path) — human verifies new Windows Terminal tab appears with agent booting
- [ ] **S9** — Manual happy-path boot on at least one of macOS (Terminal.app) or Linux (tmux) — human verifies terminal appears and agent starts

---

## Coverage Matrix — Acceptance Criteria → TCs

| Acceptance Criterion (from CONTEXT.md) | Covered by |
|----------------------------------------|-----------|
| `boot_remote.py` with `--role` and `--all` modes | TC-48, TC-49, TC-52 |
| Reads `.local-config` and `health_check.py --json` | TC-08, TC-09, TC-58, TC-62 |
| Detection respects `.stop` FIRST | TC-01, TC-07, TC-68 |
| Detection checks `.pid` existence and liveness | TC-02, TC-03, TC-11 |
| Handles all 5 states (running/crashed/stalled/fresh/stopped) | TC-13 (+ TC-01..TC-07) |
| Canonical terminal spawn works on Windows (wt.exe) | TC-14, TC-15, S8 |
| Canonical terminal spawn works on macOS (Terminal.app) | TC-17, S9 |
| Canonical terminal spawn works on Linux (tmux) | TC-19, S9 |
| Fallback prints manual boot instructions | TC-16, TC-18, TC-20 |
| Rate limiter prevents spawn-spam | TC-24..TC-30 |
| Lock file prevents race between PM clones | TC-31..TC-35 |
| Sub-skill at canonical path, domain-only | TC-36, TC-37 |
| PM composes the sub-skill in Step 7 | TC-39, TC-40, TC-41, TC-63 |
| `Auto Boot Agents: yes` default in config.md | TC-44, TC-46 |
| Test: `.stop` honored | TC-01, TC-07, TC-68 |
| Test: running agent not re-spawned | TC-02, TC-67 |
| Test: stalled agent spawned | TC-05, TC-61, TC-63 |
| Test: crashed agent spawned | TC-03 |
| Test: cooldown prevents spam | TC-25 |
| Test: fallback when canonical terminal absent | TC-16, TC-18, TC-20 |
| Test: sub-skill composition renders correctly | TC-41, TC-42 |
| Manual test: happy-path on Windows + mac/Linux | S8, S9 |

---

## Side-Effect Mitigation Coverage

| Mitigation (from CONTEXT.md §Side Effects) | Covered by |
|---|---|
| #335 hard dependency — consume `health_check.py --json` | TC-58, TC-60, TC-61, TC-62 |
| `.stop` sentinel absolute priority | TC-01, TC-07, TC-68 |
| Spawn-spam prevention (cooldown + log) | TC-24..TC-30 |
| Race condition lock file (30s TTL) | TC-31..TC-35 |
| Environment variable inheritance | TC-21 |
| Spawn attempt logging (timestamp/role/reason) | TC-24, TC-29, TC-65 |

---

## Regression Risks

1. **#335 health_check.py regression** — if detection logic diverges between boot_remote.py and health_check.py, duplicate spawns are possible. Mitigation: TC-58/TC-62 assert boot_remote.py consumes health_check.py output as authoritative, not re-implementing. TC-80 confirms health_check.py is unchanged.
2. **PM Step 7 ordering** — sub-skill composes after Step 7 (health check), before rest of PM cycle. If composition anchor lands at the wrong position, PM might try to boot agents without first detecting state or might block downstream steps. Mitigation: TC-39/TC-41 confirm anchor position.
3. **Windows spawn detached-process behavior** — on Windows, `subprocess.Popen` with wrong creation flags produces a child that dies with the parent. Mitigation: TC-23/TC-73 assert spawn is truly detached (outlives parent). Manual verification in S8.
4. **Cooldown log corruption from concurrent writes** — two PM clones writing to `.squidsquad/boot-attempts.log` simultaneously could produce garbage. Mitigation: lock file TC-31 + append-only writes. Consider atomic file writes (write temp + rename).
5. **`.local-config` format drift** — if `.local-config` schema changes (new fields, different quoting), detection could misparse. Mitigation: TC-08, TC-72 cover parsing failures gracefully.
6. **Environment variable inheritance surprises** — spawned terminal may not have `CLAUDE_API_KEY` if set at parent-process level only. Mitigation: sub-skill prose documents "set credentials at user-shell level". TC-21 verifies inheritance mechanism works for marker var.
7. **Detection false positives when interval changes mid-cycle** — if iteration interval changes from 60s to 10s, old "recently alive" windows become "stalled". Mitigation: detection reads current interval from config.md each run (TC-04, TC-05). No caching.
8. **Composition double-inclusion** — if `compose.py` is run twice and doesn't dedupe, PM's CLAUDE.md could have the sub-skill twice. Mitigation: TC-42 idempotency check.
9. **Spawn loop if agent immediately crashes after boot** — cooldown prevents this but only after first failure. Mitigation: TC-25 cooldown respect + document as accepted limitation (spawn once, wait 10 min, spawn again — is intended behavior).
10. **`.stop` sentinel removed unexpectedly** — if another tool removes `.stop`, boot_remote.py will spawn the agent next cycle. This is correct behavior, but document it in the sub-skill prose. No test needed (intended).

---

## Out of Scope (NOT tested in this plan)

- Multi-terminal-per-OS support (iTerm2, gnome-terminal, konsole, xterm, xfce4-terminal, alacritty, kitty, Git Bash) — deferred to v2
- WSL-specific spawn path — treated as Linux in v1, revisit v2
- Remote host / SSH spawn
- Auto-boot during `/squidsquad-setup` installer — #328 Q-new21 follow-up, separate feature
- Agent pooling / capacity management
- Auto-disable after repeated failures
- Interactive "want to boot this?" prompts
- Retry / backoff strategy for failed spawns (dev discretion — tests cover whatever ships)
- Detection beyond 5 canonical states
- `health_check.py` internal behavior (covered by #335's own test plan)

---

## Test Counts

- **Total TCs**: 80 (TC-01..TC-80)
- **Unit**: ~54
- **Integration**: ~22 (many platform-gated)
- **Regression**: 6
- **Smoke**: 9 (S1..S9)
- **Platform-specific**: 7 Win, 2 mac, 2 Linux (rest are platform-agnostic or mocked)
