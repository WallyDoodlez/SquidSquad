# Review of #9272 — PM boot-remote policy changes

I've reviewed all 5 provided files (1 source sub-skill, 1 L4 project instruction, 1 composed CLAUDE.md, 2 comprehension fixtures). The new `boot-remote-agents` text is consistent across all 5 files. However, there are **genuine contradictions** with other sub-skills in the same composed output.

---

### Finding 1

- **File**: `.squidsquad/pm/CLAUDE.md` (and both `tests/comprehension/8697_fixtures/pm_*_CLAUDE.md`)
- **Line**: `health-check` sub-skill
- **Severity**: error
- **Issue**: The `health-check` sub-skill states: **"PM does not execute reboots directly — agent lifecycle is managed by the harness"**. The new `boot-remote-agents` text says: **"PM may invoke `python references/scripts/boot_remote.py --role <name>` directly to spawn the stalled agent."** These directly contradict each other within the same composed file. While "reboots" and "boots" are technically distinct operations, the `health-check` text broadly asserts "agent lifecycle is managed by the harness" with no carve-out — and an LLM agent reading both cannot determine which instruction takes precedence.
- **Evidence**: The `health-check` sub-skill (appearing in all 3 CLAUDE.md files) declares PM has zero direct lifecycle authority. The `boot-remote-agents` sub-skill (also in all 3 files) now grants PM explicit authority to invoke `boot_remote.py` directly on stall. A fresh agent given only these files would see a flat contradiction.
- **Suggested fix**: Add a sentence to the `health-check` sub-skill acknowledging the stall-recovery exception: *"On stall (harness down per #9242, or a specific agent stays dead despite auto-boot), PM may invoke `boot_remote.py --role <name>` directly — see `boot-remote-agents` sub-skill for the full policy."* Alternatively, remove the absolute "PM does not execute reboots directly" and replace with a cross-reference to the `boot-remote-agents` sub-skill.

---

### Finding 2

- **File**: `.squidsquad/pm/CLAUDE.md` (and both `tests/comprehension/8697_fixtures/pm_*_CLAUDE.md`)
- **Line**: `agent-lifecycle` sub-skill
- **Severity**: error
- **Issue**: The `agent-lifecycle` sub-skill states: **"Agents do not manage their own or other agents' processes directly."** This is a shared fragment (applies to all roles) and is unqualified — no exceptions, no carve-outs. The new `boot-remote-agents` text explicitly gives PM authority to manage other agents' processes via `boot_remote.py`. This is a direct contradiction between a shared rule and a role-specific permission.
- **Evidence**: `agent-lifecycle` sub-skill, first paragraph: *"Agent lifecycle is managed by the harness (harness.py) via REST API (#4966). Agents do not manage their own or other agents' processes directly."* Compare with `boot-remote-agents`: *"PM may invoke `python references/scripts/boot_remote.py --role <name>` directly to spawn the stalled agent."* Invoking a script to spawn another agent is, by definition, managing another agent's process directly.
- **Suggested fix**: Either (a) qualify the `agent-lifecycle` blanket rule with a PM exception: *"Agents do not manage their own or other agents' processes directly — except PM may boot stalled agents via `boot_remote.py` on stall (see `boot-remote-agents` sub-skill)."* Or (b) move the stall-boot authority into the `agent-lifecycle` sub-skill as an explicit carve-out so there's a single source of truth.

---

### Finding 3

- **File**: `.squidsquad/pm/CLAUDE.md` (and both `tests/comprehension/8697_fixtures/pm_*_CLAUDE.md`)
- **Line**: `pipeline-sentinel` sub-skill, section 4f ("In-progress on dead agent")
- **Severity**: warning
- **Issue**: Pipeline sentinel 4f detects in-progress tasks on dead/stalled agents and immediately transitions the task back to `approved`. With the new boot-remote permission, this is a missed coordination opportunity. When PM detects a dead agent with in-progress work, the logical sequence should be: **(1) try to boot the dead agent** (stall recovery per the new policy), **(2) if boot fails or agent remains dead**, then transition the task. The current text jumps straight to task re-queuing.
- **Evidence**: Pipeline sentinel 4f Tier 1 action: *"Transition the task back to approved so another agent (or the same agent after restart) can pick it up."* The newly permitted `boot_remote.py --role <name>` path is not mentioned as a first-resort action, even though a dead agent with in-progress work is exactly the stall scenario the new policy authorizes PM to address.
- **Suggested fix**: Add a step before the Tier 1 transition: *"If auto-boot is unavailable or the agent remained dead after auto-boot, invoke `python references/scripts/boot_remote.py --role <name>` to attempt stall recovery. Only if boot fails (or the agent remains unhealthy on next check), then transition the task back to approved."*

---

### `--all` Constraint Assessment

The constraint **"Use `--all` only on explicit human request"** is appropriately tight. Reasoning:
- `--all` boots every agent simultaneously — in a harness-down scenario, this could race with harness recovery or create duplicate processes.
- The single-role path (`--role <name>`) gives PM surgical precision: boot only the agent that's actually stalled.
- If multiple agents are dead during a harness outage, the human can assess the situation holistically before authorizing a mass boot. This gate is proportionate to the blast radius — no change needed.

---

## Summary

| # | Severity | What | Where |
|---|----------|------|-------|
| 1 | **error** | `health-check` says PM never touches lifecycle; `boot-remote-agents` now permits it | All 3 CLAUDE.md files |
| 2 | **error** | `agent-lifecycle` says agents never manage processes directly; PM now does | All 3 CLAUDE.md files |
| 3 | **warning** | Pipeline sentinel 4f skips boot attempt before re-queuing dead-agent tasks | All 3 CLAUDE.md files |

All three findings apply to `.squidsquad/pm/CLAUDE.md`, `pm_events_CLAUDE.md`, and `pm_polling_CLAUDE.md` — they share the same sub-skill fragments. The source file `references/sub-skills/common/boot-remote-agents.md` is internally consistent and well-scoped; the contradictions arise from other sub-skills that were not updated to acknowledge the new policy.