# INSTALLER-ARCH Cross-Doc Consistency Audit

**Date**: 2026-06-12 (cycle 2322/2323)
**Doc under audit**: `docs/INSTALLER-ARCH.md` (v1 draft, last touched 2026-05-30)
**Audited against**: AGENT-RUNTIME, COMPOSE-ARCHITECTURE, HARNESS-ARCH, VAULT-ARCH, ARCHITECTURE
**Auditor**: PM (sonnet sub-agent)
**Trigger**: operator-prompted review while agents idle for event-mode validation
**Status**: findings captured; no task filed yet (awaiting operator direction)

---

## Summary

5 ERROR / 6 WARNING / 3 LOW. Real architectural drift in 4 places; the rest are cross-ref/pointer imprecision. The drift suggests INSTALLER-ARCH was authored before/during the compose-architecture stabilization (#11331 polish session + #11400 sub-skill-authoring decisions) and has not been swept since.

## Architectural drift (file fix before any installer code lands)

### E1+W2 — Phantom clone registry
**INSTALLER-ARCH §1.2 + §3.2** say the harness reads `~/.squidsquad/clones/<alias>` at boot for clone-path discovery.
**HARNESS-ARCH §7.2** says harness reads `.squidsquad/.local-config` on first boot, then `.harness-state.json`. `~/.squidsquad/clones/` appears nowhere in HARNESS-ARCH.
INSTALLER-ARCH also contradicts itself: §1.2 says "harness reads at boot" but §3.2 separately describes `.local-config` as "harness reads it at boot to populate per-alias `clone_path`".
**Implication**: `~/.squidsquad/clones/` may be phantom infrastructure — installer creates it, nothing consumes it. Need to decide which is canonical before any installer code is written.

### E4 — L4 write model contradicts COMPOSE
**INSTALLER-ARCH §8.2** (post-install tool/MCP directives): "the agent persists the directive to **a new L4 file** in `.squidsquad/project/`".
**COMPOSE-ARCHITECTURE §7.5**: "One file per role-class per §3.3; new ops accumulate as H3 sub-sections, they do not create new files."
**Implication**: Implementing per INSTALLER-ARCH would produce unbounded files per role-class and break the compose invariant.

### E5 — File layout missing compose artifact triple
**INSTALLER-ARCH §5** shows only `CLAUDE.md` per alias dir.
**COMPOSE-ARCHITECTURE §4.6**: compose emits `CLAUDE.md` + `CLAUDE.linked.md` + `CLAUDE.conflicts.md` atomically. The cache dir `.assemble-cache/` is also missing from §5.
**Implication**: Layout is incomplete; operators post-install will see 3 files per alias, not 1.

### E2 — Migration walk gate purpose mismatch
**INSTALLER-ARCH §10 step 3** says the inherited three-gate model's DeepSeek audit "reviews the proposed edit against the migration prose".
**COMPOSE-ARCHITECTURE §7.4**: the audit reviews the **op classification** (replace/insert/append) for the H3 op grammar.
**Implication**: Migration files are prose, not H3 op blocks. The inherited gate model doesn't transfer cleanly. Either re-spec the migration audit or stop claiming it's the "same gating".

### W4 — Stale vault access model
**INSTALLER-ARCH §5** layout: "PM + workers R/W, verifiers + DM read-only".
**VAULT-ARCH §7** (post-#11331 Iter 56): everyone has R/W; `vault-protocol-slim` retired when verifier/DM were granted write access for lane-specific patterns.
**Implication**: Pre-#11331 model still in INSTALLER-ARCH. Doc sweep miss.

### W6 — L4 seed format unspecified
**INSTALLER-ARCH §4.8 step 4**: Phase 1 answers written "into ... the `## Project Context` H2 section".
**COMPOSE-ARCHITECTURE §5.5**: the seed write must follow append-only `### append` H3 op grammar, structurally append-entry #1.
**Implication**: Naive implementation writes plain prose under `## Project Context`; compose rejects at §4.2 validation.

## Cross-ref / pointer drift

- **E3** — INSTALLER-ARCH §10.3 cross-refs `HARNESS-ARCH §4.1` for the `{role}` → `{alias}` rename tracking; actual location is HARNESS-ARCH §9 (vocabulary note).
- **W5** — INSTALLER-ARCH §6 helper-script table cross-refs `HARNESS-ARCH §8.2` for `event_poll.py` spawn; actual is §7.2 step 4.
- **W3** — Within INSTALLER-ARCH: §4.9 uses `<role>`, §6 uses `<alias>` for the same `compose.py deploy` command. Maintenance trap when #10358 rename lands.
- **L1** — §2 mental-model diagram omits the harness-restart step between Phase 8 and Phase 9 (described in §10.3).
- **L2** — §3.2 cross-refs `AGENT-RUNTIME §6` for harness state-file schemas; §6 is the state-persistence map, not schema docs.
- **L3** — §12 G2 mischaracterizes COMPOSE-ARCHITECTURE §10.4's L4-backfill framing (one-time migration tool, not installer step).

## Recommendation

File as a PM-owned PRD-class task under `#10836 INSTALLER-ARCH alignment` umbrella (already approved, blocking on PM pickup post-cutover) — these findings are sweeping enough to make the umbrella's first deliverable a reconciliation pass before any new dep-provisioning section is added.

Alternatively, file a standalone fix-the-drift task that lands before #10836 picks up. Operator direction needed.

## Disposition

- Captured here as planning artifact so findings survive context boundaries.
- No tracker task filed; awaiting operator decision on routing (standalone vs roll into #10836).
- Memory implications: `[[project_upgrade_is_fresh_install]]` confirmed correct (INSTALLER-ARCH §2 commitment 3 + §4.3 still say so); `[[feedback_pm_docs_only]]` applies — fix routes to PM (PRD-class doc work).
