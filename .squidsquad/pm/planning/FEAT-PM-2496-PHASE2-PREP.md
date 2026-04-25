# FEAT-PM-2496 Discussion Prep — Unify Agent Lifecycle

## Recommended Question Order

1. **Q1: What does `.pid` represent?** — This is a factual/definitional question that constrains all other answers. If `.pid` means "wrapper PID" universally, reboot can safely kill-and-respawn. If it means "child PID" in some roles, every subsequent design choice changes. Resolve this first to narrow the solution space.
2. **Q2: Should reboot treat "not running" as "boot it"?** — Once PID semantics are settled, this question decides the behavioral contract of `reboot_agent.py`. The answer directly determines what the wrapper supervisor (Q3) needs to do, so it must come second.
3. **Q3: Should we build a dedicated Python supervisor?** — This is the architectural question. It depends on the answers to Q1 (PID ownership) and Q2 (reboot semantics) because the supervisor's responsibilities change based on those decisions.

## Q1: What does `.squidsquad/<role>/.pid` represent across all roles/versions — wrapper PID or Claude child PID?
> Why this matters: Reboot correctness depends on killing the right process. If `.pid` is the wrapper PID, killing it stops the restart loop and spawning a new wrapper is safe. If `.pid` is the child PID, killing it leaves the wrapper alive (potential double-start on respawn) or kills the wrong process entirely.

### Option A: Standardize `.pid` as wrapper PID (RECOMMENDED)
**Pros:**
- Killing the wrapper PID guarantees the child dies too (child is a subprocess of the wrapper).
- Spawning a new wrapper after kill is always safe — no orphaned wrapper to cause double-start.
- Aligns with the existing `start-skill.sh` behavior (line 97 writes `$$`, which is the wrapper PID).
- Simple mental model: one PID = one lifecycle owner.

**Cons:**
- Requires auditing all generated wrappers and templates to confirm/enforce this convention.
- If any role currently writes child PID, those wrappers need template updates and regeneration.
- Slight risk during migration if old wrappers coexist with new reboot logic.

### Option B: Standardize `.pid` as child (Claude) PID
**Pros:**
- More direct for health checks — the PID you care about (Claude) is the one recorded.
- Some monitoring tools prefer tracking the actual worker process.

**Cons:**
- Killing child PID leaves the wrapper alive. Wrapper may respawn the child (race condition with reboot's own respawn logic).
- Requires reboot to discover and kill the wrapper separately, adding complexity.
- Breaks the "single PID = single lifecycle" model — now you need to track two processes.

### Option C: Write both PIDs (wrapper + child) to separate files
**Pros:**
- Maximum information — reboot and health checks can target whichever process is relevant.
- No information loss; supports both use cases.

**Cons:**
- Added complexity in every wrapper template (two files to write, two to clean up).
- Every consumer (reboot, health check, boot_remote) must know which file to read and when.
- More failure modes (files out of sync, partial writes, stale entries).
- Over-engineered for the current need — YAGNI concern.

---

## Q2: Should `reboot_agent.py` treat "agent not running" as "boot it" (reboot == ensure running), or keep the current no-op success?
> Why this matters: Today, if an agent is dead and you run `reboot_agent.py`, it returns success and does nothing — the agent stays dead. This affects operator expectations and whether reboot becomes a recovery tool or remains strictly a restart-running-agent tool.

### Option A: Reboot == ensure running (RECOMMENDED)
**Pros:**
- Eliminates the "agent dies permanently" failure mode — any reboot call guarantees the agent comes back.
- Simplifies operator mental model: "reboot" means "make sure it's running," regardless of current state.
- Aligns with the self-healing direction from `[[decision-self-healing-sentinel]]`.
- PM and DM can use a single command for both "restart stuck agent" and "recover dead agent."

**Cons:**
- Must respect `.stop` sentinel — "ensure running" should not override an explicit human stop.
- Adds spawn logic to `reboot_agent.py`, increasing its complexity and coupling it to `boot_remote.py`.
- Risk of spawning during timeout edge case (agent was busy, timed out, now dead — spawning mid-cycle is dangerous). Mitigation: only spawn when kill was successful or agent was already dead, never on timeout.

### Option B: Keep no-op success (current behavior)
**Pros:**
- Simple — reboot only restarts what's already running.
- No risk of unintended spawns.
- Clear separation: `reboot_agent.py` = restart, `boot_remote.py` = start.

**Cons:**
- Leaves the "agent dies permanently" failure mode intact.
- Operators must know to use `boot_remote.py` for dead agents and `reboot_agent.py` for stuck agents — two tools for related problems.
- PM health-check already detects dead agents but has no single-command recovery path.

### Option C: Add a `--ensure` flag (opt-in boot-on-dead)
**Pros:**
- Backward compatible — default behavior unchanged.
- Operators who want recovery can pass `--ensure`.
- Gradual adoption without breaking existing scripts or expectations.

**Cons:**
- Two behaviors behind one command name — confusing documentation and mental model.
- PM/DM scripts must be updated to pass `--ensure` everywhere, or the failure mode persists.
- Flag proliferation — adds yet another option to an already flag-heavy script (`--force`, `--timeout`, `--all`).

---

## Q3: Should we refactor lifecycle into a dedicated Python "wrapper supervisor" (per `[[decision-watchdog-supervisor]]`), or unify within the existing `reboot_agent.py` + `boot_remote.py` scripts?
> Why this matters: The vault decision `[[decision-watchdog-supervisor]]` envisions a centralized supervisor, but `watchdog.py` does not exist yet. Building it now could be the right long-term move but adds scope. Patching the existing scripts is faster but may create tech debt if the supervisor is built later.

### Option A: Patch existing scripts (reboot_agent.py calls boot_remote.py logic) (RECOMMENDED)
**Pros:**
- Smallest scope — only `reboot_agent.py` and possibly `boot_remote.py` change.
- Ships faster — unblocks the lifecycle gap without a new architectural component.
- Low risk — reuses proven spawn logic from `boot_remote.py`.
- If a supervisor is built later, this work is not wasted — the shared spawn function becomes part of the supervisor.

**Cons:**
- Does not fully realize the `[[decision-watchdog-supervisor]]` vision.
- Clone-path parsing must be unified between the two scripts (Risk 2 from research), adding coupling.
- Two scripts sharing lifecycle responsibility is messier than one authoritative supervisor.

### Option B: Build `watchdog.py` as the single lifecycle authority now
**Pros:**
- Fully realizes the vault decision — one process owns all start/stop/restart/health.
- Clean architecture: wrappers, reboot, and boot all delegate to the watchdog.
- Long-term maintainability — no scattered lifecycle logic.

**Cons:**
- Significant scope increase — new script, new process model, new failure modes.
- Watchdog itself becomes a single point of failure (who watches the watchdog?).
- Requires rethinking wrapper templates (they currently own the restart loop).
- Delays shipping the fix for the immediate lifecycle gap.
- Higher risk of bugs in a brand-new component vs. patching proven code.

### Option C: Hybrid — patch now, file a follow-up task for watchdog.py
**Pros:**
- Gets the immediate fix shipped quickly (same as Option A).
- Explicitly acknowledges the architectural direction without blocking on it.
- Follow-up task ensures the supervisor vision is not forgotten.
- Low risk now, clean architecture later.

**Cons:**
- Follow-up tasks can languish — the supervisor may never get built.
- Interim state has two scripts sharing lifecycle logic (same as Option A con).
- If the supervisor is built, the patch work gets partially replaced (some wasted effort, though minimal).
