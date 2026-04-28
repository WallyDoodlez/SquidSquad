# FEAT-PM-3807 Context — Universal Sentinel-Based Agent Lifecycle

## Scope

Replace fragmented agent lifecycle (5 entry points, 2 sentinel types, PM auto-boot) with a unified sentinel-based model. One start_team.py entry point, wrapper loops with .stop-after-cycle sentinel, agents are fully passive, PM only monitors.

## Locked Decisions (human decided)

- **PM auto-boot**: No auto-boot. PM only reports missing agents to human. Periodic health report every 10 cycles. Human decides whether to boot.
- **Context pressure trigger**: cycle_post.py reads pressure from cycle-input.json and writes .stop-after-cycle mechanically if exceeded. Wrapper stays simple — no polling.
- **Clean exit without sentinel**: Wrapper stops. Zero exit without .stop-after-cycle = agent done, wrapper exits. Prevents infinite loops.
- **DM reboot interface**: Switch to start_team.py --reboot <role>. reboot_agent.py becomes deprecated shim for one version.
- **Sentinel transition**: One version overlap — wrapper checks both .restart and .stop-after-cycle, then .restart removed next version.
- **Agents are fully passive**: Agents never orchestrate, poll, or wait for reboots. They see sentinel and stop. Period.
- **All reboot mechanics in scripts/wrapper**: Not agents.
- **Single entry point**: start_team.py replaces boot_remote.py --all, reboot_agent.py, start-squad.ps1/sh
- **Wrapper loops indefinitely**: .stop is the only brake. Crash backoff: exponential up to 5 min, .stop after 5 consecutive crashes.

## Dev Discretion (dev agent can choose)

- Internal structure of start_team.py (can import boot_remote spawn logic)
- How to structure the wrapper loop in PowerShell/bash templates
- Exponential backoff implementation details
- How to handle the deprecated .restart shim logging

## Side Effect Mitigations (required)

- cycle_post.py .stop-after-cycle check must be LAST operation (after commit, after iteration log)
- Working state checkpoint must happen BEFORE sentinel exit
- Wrapper writes "restarting" to .health during inter-cycle gap (prevents false STALLED readings)
- Clean stale .restart files across all clones during migration
- cycle_pre.py continues providing boot_results as empty [] until all agents redeployed
- Wrapper checks age of context-pressure file — if stale (>1 interval), treat as 0%

## Upgrade Path (required)

1. Stop all agents (write .stop to each role dir)
2. Deploy new wrapper templates: compose.py boot-all in each clone
3. Deploy new CLAUDE.md files: compose.py deploy-all in each clone
4. Clean stale .restart sentinels across all clones
5. Remove .stop files
6. Start via start_team.py --all

## Out of Scope

- Changing health_check.py internals (already works with new model)
- Vault or config.md schema changes
- PR flow or auto-merge changes
