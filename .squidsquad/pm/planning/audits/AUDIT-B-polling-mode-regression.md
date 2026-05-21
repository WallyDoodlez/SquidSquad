Now I have all the information needed. Let me compile the final audit report.

---

# AUDIT-B-polling-mode-regression Research — Polling Mode Standalone-Fitness After #9588

## Summary

I analyzed the full polling-mode code path from boot to cycle completion after the #9588 lazy-load bootstrap shipped. The architecture is sound: `boot-bootstrap.md` is properly composed as the first instruction in all 4 active agent CLAUDE.md files (skill, pm, qa, dm), and it correctly branches to polling mode when `event-driven:` is absent/set to `no` OR when the harness is unreachable. The polling fragment (`ralph-loop-overview.md`) is successfully excluded from inline composition and is Read at runtime — confirmed by marker absence in all 4 deployed files. `/loop` registration is owned exclusively by the bootstrap (Step 4b), with a compose-time substituted interval, and the runtime-loaded polling fragments contain zero `/loop` invocations (verified by `test_polling_fragment_source_does_not_invoke_loop`).

The primary risk is a **stale `references/agent-instructions.md`** (the `compose all` template output) that still contains the old inline polling fragment without `boot-bootstrap`. This file is not what active agents read (they use `.squidsquad/<role>/CLAUDE.md`), but any agent or human reading it as a reference would get conflicting instructions. A secondary risk is the **runtime placeholder substitution dependency**: polling fragments (especially dev's) still contain `[ROLE]` placeholders that the agent must self-substitute at runtime — if an agent skips the bootstrap's substitution teaching, path construction breaks silently.

**Recommendation**: Feasible with caveats. Polling mode is standalone-fit at **high confidence** for the 4 active agents. Re-run `compose.py all` to regenerate the stale reference template. Add a CI guard to prevent `agent-instructions.md` from drifting.

## Vault Context

- **BRIEFING.md priorities**: #7630 (event-driven architecture) is shipped; #9242 (harness unreachable for 5+ cycles) is open — makes the polling fallback path actively exercised and critical. Mechanical cycle operations should be programmatic per human preferences.
- **Related decisions**: [[decision-cycle-runner-architecture]] — the mechanical shell/agent core split is the foundation that polling mode depends on. cycle_pre.py/cycle_post.py are the transport layer for every polling cycle.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — the bootstrap replacing prose mode-detection with a structured decision tree is consistent with this pattern. The `/loop` scheduling being moved from prose in `ralph-loop-overview.md` to a deterministic instruction in `boot-bootstrap.md` is an instance of this pattern.
- **Human preferences**: "Mechanical cycle operations should be deterministic code, not LLM prose interpretation" — the bootstrap + `/loop` + cycle_pre/post architecture honors this. "Prefer direct/mechanical checks over indirect state files" — the harness reachability check via `curl /status` (direct HTTP probe) honors this.
- **Related learnings**: None directly applicable.

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/common/boot-bootstrap.md` — new: bootstrap fragment (the mode-detection gate)
  - `references/scripts/compose.py:33-52` — `RUNTIME_READ_FRAGMENTS` set prevents mode-specific inlining
  - `references/scripts/compose.py:578-581` — `[POLLING_FRAGMENT_PATH]` placeholder substitution
  - `references/sub-skills/common-events/l1-base.md:23-24` — degraded-mode branch removed; now asserts harness reachability is guaranteed by bootstrap
  - `references/roles/*/includes.yml` + `includes-events.yml` — all 8 manifests: `common/boot-bootstrap` added as first entry, mode-specific entries removed
  - `references/roles/dev/instructions.md` — template retains `{{include:}}` directives for mode-specific fragments but they're guarded by HTML comments explaining `RUNTIME_READ_FRAGMENTS` short-circuit
  - `.squidsquad/{skill,pm,qa,dm}/CLAUDE.md` — all 4 recomposed with boot-bootstrap
  - `tests/test_compose_9588.py` — 7 regression tests (D7)
- **Behavior changes**:
  - Agent boot: first instruction is now the bootstrap decision tree instead of an inline `/loop` invocation
  - Mode decision: happens at runtime via config.md read + curl harness probe, not at compose time
  - Polling fragment: Read at runtime via Read tool instead of inlined at compose
  - `/loop` scheduling: owned by bootstrap Step 4b (with compose-substituted interval), not by polling fragment
  - Event-mode degraded path: removed from l1-base.md in favor of polling fallback at boot
- **Dependencies**: `curl` must be available on PATH for harness reachability probe (Step 2). `tracker.py check-gh` must work for GitHub Issues access verification (Step 4a).

## Side Effects

- **Risk 1 — Stale `references/agent-instructions.md`**: The `compose all` output still contains the pre-#9588 inline `ralph-loop-overview` (lines 198-244) and zero `boot-bootstrap`. Any human or tool reading this as the canonical agent template gets incorrect instructions. Active agents are unaffected (they use `.squidsquad/<role>/CLAUDE.md`). — **Severity: M** — **Mitigation**: Re-run `compose.py all` immediately. Add a CI check that `references/agent-instructions.md` matches a fresh compose output.
- **Risk 2 — `.squidsquad/dev/CLAUDE.md` stale**: Also pre-#9588 (inline `ralph-loop-overview` at line 195, no `boot-bootstrap`). `dev` is not an active agent (config lists `skill`), but the file on disk would give incorrect instructions if someone manually starts a `dev` agent. — **Severity: L** — **Mitigation**: Re-deploy with `compose.py deploy dev` or delete the stale file.
- **Risk 3 — Runtime placeholder substitution is LLM-dependent**: The polling fragment for dev (`roles/dev/ralph-loop-overview.md` line 26-27) uses `[ROLE]` in `cycle.py status-bar [ROLE]` and `.squidsquad/[ROLE]/current-state`. The bootstrap teaches agents to self-substitute (lines 272-281), but this is prose teaching, not deterministic code. If context pressure truncates the teaching or the agent glosses over it, path/arg construction silently breaks. — **Severity: M** — **Mitigation**: The bootstrap's prominence ("FIRST instruction... BEFORE any other section") makes it unlikely to be skipped. The regression test `test_bootstrap_documents_role_runtime_substitution` verifies the teaching section survives compose. Long-term: replace `[ROLE]` in polling fragments with a script-level substitution or hardcode per-role copies.
- **Risk 4 — `curl` dependency on Windows**: The harness reachability probe uses `curl -sf --max-time 5`. On native Windows (no curl in PATH), the probe exits non-zero → harness "unreachable" → forced polling. This is the safe fallback (polling is always available), but an operator who expects event-mode to work on Windows without curl installed will be silently downgraded to polling. — **Severity: L** — **Mitigation**: Document curl requirement. The bootstrap comment about Windows shells (line 222) shows awareness. The safe default (polling) means this degrades gracefully.

## Edge Cases

- **Config.md absent/unreadable**: Bootstrap Step 1 explicitly handles this — "POLLING mode confirmed, skip Step 2 and jump to Step 4." Mirrors `_get_wake_mode`'s `return "polling"` default. Verified in source at `boot-bootstrap.md:10`.
- **`.harness-port` file missing**: Bootstrap Step 2 defaults port to 7373. This is the same default as `cycle_post.py:_discover_harness_port` (line 649). Consistent.
- **Harness reachable but `/status` returns non-2xx**: `curl -f` makes any HTTP error exit non-zero → harness "unreachable" → polling. This is intentional per CONTEXT-9588 D3 (the harness is only "proven" when `/status` returns 200).
- **GH Issues permission check fails mid-boot**: Bootstrap Step 4a runs `tracker.py check-gh` BEFORE `/loop` is scheduled. On failure, agent prints error and exits. This prevents a session that can't reach GitHub from entering the loop. Previously this check lived inside the polling fragment — moving it up is correct.
- **Mid-session harness failure in polling mode**: No impact. cycle_pre.py's `_query_harness_status()` (line 268-285) is informational only — it populates `harness_status` in `cycle-input.json` but no code branches on it. cycle_post.py's `_query_harness_intent()` (line 652-670) returns `None` on failure, and `_do_stop_after_cycle_check` (line 707-757) treats `None` intent as "continue running." `event_bus.emit()` is fire-and-forget with silent no-op on failure (line 108-109).
- **Interval changed in config.md mid-session**: Bootstrap says "Loaded mode is sticky" — the interval used in `/loop` was substituted at compose time. If the operator changes `Minutes: 30` to `Minutes: 15`, the agent keeps using 30 until restart. The old `interval-sync.md` sub-skill (which checks for interval changes) is included in the polling manifest (`common/interval-sync` at `includes.yml` line 19) and handles this at the creative-work level — the agent can re-invoke `/loop` with the new interval during its cycle. This is correct two-layer behavior.

## Integration Risks

- **`references/agent-instructions.md` as human reference**: If a human reads this file to understand agent behavior, they'll see the old inline `/loop` instructions and miss the bootstrap entirely. This could lead to incorrect mental models during debugging. Mitigated by the file's "GENERATED FILE — DO NOT EDIT" header, but no CI enforces it's up-to-date.
- **Event-mode test infrastructure (#9398)**: The event-mode tests rely on harness reachability. The polling path is tested only by `test_compose_9588.py` at the compose level — there are no integration tests that verify a polling agent boots, reads the fragment, and fires a cycle end-to-end. This is a test coverage gap but consistent with the pre-#9588 state.
- **`statusline_data.py` mode awareness**: The status bar script correctly distinguishes event-driven vs polling modes (line 102). In polling mode, it falls back to reading `current-state` from disk. This is correct and tested.

## Upgrade & Migration

- **New config values**: `event-driven: yes` and `event-driven-<role>: yes` (both already existed in config.md schema, `config.py:70` and `config.py:156` with default `no`). No new fields.
- **New files**: `references/sub-skills/common/boot-bootstrap.md` (93 lines). `tests/test_compose_9588.py` (267 lines, 7 test functions).
- **Template changes**: `references/roles/dev/instructions.md` now has `{{include: common/boot-bootstrap}}` at line 21, followed by HTML-commented mode-specific includes. All 4 role `instructions.md` files were updated.
- **Upgrade steps**: Re-run `compose.py deploy-all` to regenerate all `.squidsquad/<role>/CLAUDE.md` files. Re-run `compose.py all` to regenerate `references/agent-instructions.md`. Distribute updated CLAUDE.md files to each clone. Agent restart picks up the new bootstrap on next session start.
- **Graceful degradation**: If an agent restarts before upgrade, it uses the old inline polling fragment (still works — the old code path is fully functional). If `event-driven: yes` is set before all agents are upgraded, non-upgraded agents will still try the old event path (which may include the now-removed degraded mode in l1-base.md). The hard cutover (D5) means partial upgrades are not supported — deploy to all 4 clones atomically.

## Open Questions

- **Q1**: Should `references/agent-instructions.md` be regenerated on every `deploy-all` to prevent drift? — **Why**: Currently it's only regenerated by explicit `compose all`, which is easily forgotten. The file was stale at audit time.
- **Q2**: Should the `[ROLE]` placeholders in `ralph-loop-overview.md` source files be replaced with a deterministic substitution (script or compose-time per-role copies) to eliminate the LLM-dependent self-substitution? — **Why**: This is the only remaining prose-dependent mechanical step in the polling boot path. Human preference is "mechanical operations should be deterministic code."
- **Q3**: Should there be an integration test that simulates a full polling-mode boot → cycle_pre → creative → cycle_post flow with `event-driven: no`? — **Why**: The `test_compose_9588.py` tests verify compose output but not runtime behavior. The event-mode path has integration tests (#9398); the polling path has none.

## Recommendation

**Feasible with caveats.** Polling mode is standalone-fit at high confidence for all 4 active agents. The bootstrap architecture is well-designed: mode detection is explicit, the decision tree is unambiguous, and all harness-dependent code paths degrade gracefully to safe defaults. The two stale files (`references/agent-instructions.md` and `.squidsquad/dev/CLAUDE.md`) are deployment hygiene issues, not architectural flaws. The runtime placeholder substitution is the only LLM-dependent mechanical step — acceptable for now but worth hardening in a follow-up.

**Confidence**: HIGH — 7 regression tests pass, all 4 active agents have correct compose output, all harness-dependent code paths handle unreachability gracefully, and the polling fragment sources have been verified free of `/loop` invocations and `[INTERVAL]` placeholders.

## Vault Candidates

- **Type**: pattern — **Polling-mode boot path: bootstrap gate → `/loop` schedule → runtime fragment Read** — **Why**: This 3-step pattern (bootstrap decides mode, schedules `/loop` with compose-substituted interval, then Reads the polling contract at runtime) is novel and worth preserving as a reference for any future boot-path changes. The key insight is that `/loop` scheduling MUST happen in compose-inlined content (so placeholders substitute) while cycle content CAN be runtime-loaded.
- **Type**: learning — **`compose all` output (`agent-instructions.md`) drifted stale after #9588 deploy** — **Why**: The `deploy-all` command updates per-agent CLAUDE.md files but does not automatically regenerate the reference template. This will happen again if not automated. A CI guard or makefile dependency would prevent it.
- **Type**: decision — **Harness-unreachable fallback is always polling, never a degraded event-mode path** — **Why**: CONTEXT-9588 D3 locks this decision, but it's worth vaulting because it represents a philosophy choice: when infrastructure is unreliable, fall back to the simplest battle-tested mechanism rather than maintaining a third execution mode. This principle applies beyond event-driven architecture.
- **Type**: learning — **Windows `curl` availability is not guaranteed; probe failures default to safe fallback** — **Why**: The bootstrap's curl probe uses `-sf` flags specifically to avoid shell-redirect issues on Windows. The design choice to treat "curl missing" as "harness unreachable → polling" is a graceful degradation pattern that future infrastructure probes should replicate.
- **Type**: pattern — **RUNTIME_READ_FRAGMENTS frozenset in compose.py as defense-in-depth** — **Why**: Even though manifests no longer list mode-specific fragments, the `RUNTIME_READ_FRAGMENTS` short-circuit in `_resolve_includes_with_manifest` (line 328) prevents accidental re-inlining from template-side `{{include:}}` directives or variant-resolution fallback heuristics. This is a defense-in-depth pattern worth replicating for any future lazy-load refactors.