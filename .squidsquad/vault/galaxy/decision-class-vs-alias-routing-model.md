---
type: decision
tags: [architecture, routing, harness, agents, permission]
created: 2026-05-25
updated: 2026-05-25
status: active
confidence: high
source: conversation
owner: pm
---

# Decision — Class vs alias as routing primitive; no harness permission table

## Decision

Three coordinated architectural commitments locked together:

1. **Routing targets aliases, not role classes.** Every running agent has a unique `target_alias`. `/work/assign` always names a specific alias. The 4 categorical role classes (`pm`, `dm`, `worker`, `verifier`) define behavior contracts; aliases identify the specific running instances.

2. **`responsibility.md` is retired.** Its prose was ~90% redundant with L2/L3 (which compose into each agent's CLAUDE.md anyway). Its only load-bearing content was the `## Bus contract` section, retired in (3).

3. **Harness has no class-from-class permission table.** Two minimal checks remain: alias existence (404 if unknown) and self-assign invariant (structural anti-loop). Any alias may assign-to any other alias. Process discipline lives in each agent's L2/L3/L4 + SOUL.md, not in a harness gate.

## Rationale

- **Why aliases over classes**: multi-instance installs (e.g., 2 frontend + 2 backend worker-class agents) need a way to identify the specific recipient. Specialty lives in **L3 (the domain layer)** and is shared by same-domain agents: 2 FE workers share L1 + L2 (worker class) + L3 (FE domain); 2 BE workers share L1 + L2 + L3 (BE domain). Same layering applies to verifier-class agents (FE verifiers share an FE L3, BE verifiers a BE L3). Per-agent identity lives in SOUL.md; install-specific overrides live in L4. Aliases name the running instance and disambiguate routing when multiple agents share class + domain (or even just class, in the single-domain case).
- **Why no permission table**: it duplicated discipline that already exists in L2/L3/L4. It conflicted with [[decision-event-bus-architecture-redesign]]'s "harness is a transport bus, not an orchestrator" principle (adding a permission table makes the harness gate-keep work assignment). The human-team analogy applies — no security guard checks every ticket assignment; recipients recognize "not mine" and re-route. Agents are documented to push back on mis-routed work in L2/L3.
- **Why retire `responsibility.md`**: with the permission table gone, the bus-contract section has no consumer. The prose content lives in L2/L3 (which agents actually read). Keeping the file alive would be cargo-culted infrastructure.

## Mis-route recovery (the replacement for the permission table)

When an agent receives `assigned-to` work outside its declared domain:

1. Recognize the mismatch (per its own L2/L3/L4 + SOUL.md).
2. Re-`/work/assign` to the correct alias. Same wire format, no special re-assign event type.
3. If recipient is unknown, route to `pm` with `event_context="route-help"`.

This is the only recovery mechanism. Mirrors human-team workflow.

## Wire-format change

- Field name: `target_role` → `target_alias`
- Care filter: `target_alias == my_alias` (replaces `target_role == my_role`)
- Tracker.py CLI: `--target` → `--target-alias`
- Issue `role:*` label IS the target alias (shared namespace); single-instance alias = class name; multi-instance uses specific alias

## Where this lives in docs

- [[AGENT-RUNTIME]] §Terminology (class vs alias hierarchy)
- [[AGENT-RUNTIME]] §7.3 (`/work/assign validation + mis-route recovery` — replaces the prior permission-model subsection)
- [[AGENT-RUNTIME]] §4.5 / §4.6 / §7.4 / §8.5 / §9 (all retargeted to alias-level)
- [[AGENT-RUNTIME]] §10.4 rev 10 entry captures the full change set

## Out of scope

- The code-side implementation (deleting `responsibility.md` files, dropping the harness permission-table build, renaming `target_role` field, renaming `--target` flag) is deferred to a bundled skill task per the plan-first rule. This decision describes the architectural target; current code still maintains the permission table and emits `target_role`.
- Variant-as-its-own-class (Model B from the design discussion) was rejected in favor of per-agent specialization via SOUL.md + L4. Adding a `variant` class layer was considered and dropped — uniform L2/L3/bus contract per role class is simpler and covers the multi-instance case via aliasing alone.

## Related

- [[decision-event-bus-architecture-redesign]] — "harness is a transport bus, not an orchestrator" principle this aligns with
- [[VAULT-ARCH]] §7 (similar "intelligence in the agent, not the framework" principle for vault sub-skill execution lanes)

## Changelog

- 2026-05-25 — Created by pm-lead. Decision locked during AGENT-RUNTIME class-vs-alias + permission-table retirement pass (rev 10).
