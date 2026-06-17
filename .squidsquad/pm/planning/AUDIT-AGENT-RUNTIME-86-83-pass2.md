I have all the data needed. Here is the verdict:

---

# audit-AR-86-83-pass2 Research — Convergence Re-Audit (Pass 2)

## Summary

Pass-2 verification of the 3 errors from the prior DS audit of `docs/AGENT-RUNTIME.md` (§8.6.1 event-mode periodic driver + §8.2 liveness callout). PM-lane doc fixes have been applied to AGENT-RUNTIME.md. All three errors are accounted for: ERROR-3 is fully resolved (stale phrase purged, wording matches the locked model in HARNESS-ARCH §15.1); ERROR-1 and ERROR-2 remain as live inconsistencies in the sub-skill and config files, but AGENT-RUNTIME §8.6.1 now explicitly documents them as required-with-#12506-implementation / knowingly-inconsistent-until-then. This is acceptable for an arch-doc merge — every residual gap has a tracking entry and a scheduled resolution vehicle. No new drift was introduced by the 5 changed passages.

## Vault Context

- **BRIEFING.md priorities**: Harness liveness redesign (#12271) IN MOTION — locked model is activity-heartbeat + pause-aware guard; PID → teardown-only. AGENT-RUNTIME + HARNESS-ARCH reconciliation MERGED (#12417). **#12442** (DM event-mode auto-route GAP) active but not relevant here.
- **Related decisions**: [[decision-event-bus-architecture-redesign]] — the event-bus principles that anchor §8; no conflict.
- **Related patterns**: none directly constraining this audit.
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." — satisfied: the reconciliations paragraph creates an audit-trail breadcrumb for the #12506 tracked inconsistencies.
- **Related learnings**: none specific to this audit.

## Impact Analysis

- **Files touched**: `docs/AGENT-RUNTIME.md` (lines 903, 1100, 1110–1127 — the 5 changed passages); cross-referenced `docs/HARNESS-ARCH.md` §15.1 (lines 544–563), `references/sub-skills/common-events/idle-cooldown-loop.md` (lines 44–46), `.squidsquad/config.md` (lines 61–64).
- **Behavior changes**: None — doc-only convergence pass. No runtime behavior altered.
- **Dependencies**: #12506 (the implementation PR that must land with the sub-skill + config.md edits named in the reconciliations paragraph). #12271 (the liveness redesign referenced in §8.2 callout).

## Side Effects

- **Risk 1**: If #12506 lands without the sub-skill step-5 edit and the config.md `Idle Scan Burst`/`m`-unit additions, the "knowingly inconsistent" label becomes a real broken contract. — Severity: M — Mitigation: The reconciliations paragraph at line 1125 explicitly says "MUST land with it"; PM/reviewer gate on #12506 must enforce this.

## Edge Cases

- **`idle-cooldown-loop.md` step 5 read by a newly-composed event-mode agent before #12506 lands**: The agent reads "Monitor delivers NUDGE wake signals at a short fixed cadence" — which is false in event mode (Monitor only nudges on forge events). The agent would expect periodic wake-ups that never arrive. This is the exact #12506 dormancy — acceptable only because the reconciliations paragraph marks it as knowingly-inconsistent and #12506 is the fix vehicle.
- **Config.md `Improvement Scan Cool-Down: 30` (no unit) vs AGENT-RUNTIME throttle `30m`**: Ingesting code that reads `30` and treats it as minutes would work today by convention, but is fragile. The reconciliations paragraph explicitly calls out the `m` unit addition as part of #12506 — no action needed now, and the fix is pre-specified.

## Integration Risks

- **#12506 implementation completeness**: The reconciliations paragraph binds 3 artifacts (sub-skill step-5 edit, `Idle Scan Burst` key, `m` unit on cool-down) to a single implementation PR. If #12506 is sliced, all 3 must move together or the "knowingly inconsistent" label becomes stale. The paragraph doesn't name a fallback tracking issue if #12506 is split — low risk given the scope is small, but worth noting.

## Upgrade & Migration

- **New config values**: `Idle Scan Burst` (default 3, under `## Improvement Scanning`) — NOT YET added (tracked in #12506). `Improvement Scan Cool-Down` value will gain `m` suffix — NOT YET applied (tracked in #12506).
- **New files**: none.
- **Template changes**: `idle-cooldown-loop.md` step 5 will be rewritten — NOT YET applied (tracked in #12506).
- **Upgrade steps**: N/A — no upgrade impact until #12506 ships.
- **Graceful degradation**: N/A.

## Open Questions

- **Q1**: Is `#12506` scoped to deliver all 3 artifacts (sub-skill edit + `Idle Scan Burst` key + `m` unit) as one atomic unit, or could they ship in separate PRs? — **Why**: If split, the "knowingly inconsistent" breadcrumb in AGENT-RUNTIME must be updated to name the correct tracking issues for each remaining artifact.
- **Q2**: Does the `idle-cooldown-loop.md` step-5 edit also need to update the "After each empty poll interval" branching logic (lines 45-46) to reflect the cron-driver model rather than the Monitor-cadence model? — **Why**: The reconciliations paragraph names only the "step-5 assumption" correction; the surrounding procedural logic may also need rewriting to describe the driver-tick re-entry rather than Monitor-poll-based cadence.

## Recommendation

**CONVERGED** — merge-ready. The doc is internally consistent and every residual inconsistency is explicitly tracked-for-implementation (#12506). No new drift introduced.

## Error Status Table

| Error | Verdict | Evidence |
|---|---|---|
| **ERROR-3** (§8.2 stale "event_poll idle-ticks and acks") | **RESOLVED** | Phrase absent from entire file (grep: zero hits). §8.2 line 903 now reads "`claude-code hooks plus cycle_post heartbeats (with a pause-aware guard) — demoting PID to teardown-only`" — matches HARNESS-ARCH §15.1 locked model ("activity heartbeat + pause-aware guard"; "PID is used only to terminate a process, never to determine liveness" at line 548). |
| **ERROR-1** (idle-cooldown-loop.md step 5 "Monitor delivers NUDGE at a short fixed cadence") | **DOCUMENTED/TRACKED** | Sub-skill file at lines 44–46 still carries the stale statement. AGENT-RUNTIME §8.6.1 line 1125 explicitly names this exact step-5 assumption and marks its correction as #12506-gated: "The idle-cooldown-loop sub-skill's step-5 assumption … is corrected to name this driver as the cadence source." |
| **ERROR-2** (config.md lacks `Idle Scan Burst` key) | **DOCUMENTED/TRACKED** | `.squidsquad/config.md` lines 61–64 have only `Enabled` + `Improvement Scan Cool-Down: 30` (no unit, no burst key). AGENT-RUNTIME §8.6.1 line 1125 explicitly names "adding the Idle Scan Burst key (default 3) and the m unit on Improvement Scan Cool-Down in config.md" as #12506-gated. |

## Vault Candidates

- **Type**: pattern — **"knowingly inconsistent" breadcrumb pattern for multi-repo doc synchronization** — **Why**: The reconciliations paragraph format (`"That sub-skill edit … are part of the #12506 implementation and MUST land with it; until they do, the arch doc, the idle-cooldown-loop sub-skill, and config.md are knowingly inconsistent."`) is a reusable template for any arch-doc merge where implementation-lane fixes are deferred to a separate tracked issue. It creates a grep-able audit trail, prevents silent drift, and gives reviewers a clear gate condition.
- _(No other candidates — the remaining findings are verification-only, not reusable.)_