# QA-RESULTS-10836 (R1) — VERDICT: PASS (zero gaps in R1 scope)

**Issue**: #10836 R1 (type:task, priority:high, role:pm) — INSTALLER-ARCH drift reconciliation. PR #11536 (`squidsquad/task/10836` → main), docs-only.
**Verified by**: verifier, 2026-06-12 20:19 on branch `squidsquad/task/10836`. Plan: TEST-PLAN-10836.md.

## Dimension walk (independent re-verify of PM's 3 asks)

### (a) No residual contradictions — PASS
- `~/.squidsquad/clones/`: every normative-body mention (§1.2 L31, §3.2 L105, §4.2 tree L168, §5 tree L343) marks it **legacy/vestigial** with `.local-config` canonical. The only "registry"-framing mentions (L603 E1 fix-note, L615 2026-05-23 entry) are in the **§14 revision log** — append-only history, newest-first, superseded by the R1 entry above them. Not body contradictions.
- "new L4 file": **0 residuals** (E4 → append-H3 to role-class L4 file).
- vault "read-only": body L322 = "all agents R/W (... read-only variant retired #11331)"; only other mention is §14 W4 fix-note. **0 body residuals.**

### (b) Cross-refs resolve — PASS
All 14 cited cross-doc sections resolve to real headings:
- HARNESS-ARCH §2 ✓, §7 ✓ (Agent lifecycle), §7.2 ✓ (Spawn/boot_agent — has the clone-path "First-boot discovery" + event_poll step W5 cites), §9 ✓ (State files — contains the "Vocabulary note — role vs alias" E3 cites).
- COMPOSE §3.3, §4.5.1, §5.5, §7.4, §7.5, §8.2, §10.4 — all ✓.
- AGENT-RUNTIME §6 ✓ (State persistence map), §7.5 ✓ (Context-pressure exit-42/respawn — L2/§10.3 recovery ref), §9.3 ✓, §11 ✓.
Semantic spot-checks (E3→§9 vocab, W5→§7.2 step, L2→§6+§7.5 recovery) all apt.

### (c) Code ground-truth — PASS
- `boot_remote.py`: `LOCAL_CONFIG = SQUIDSQUAD_DIR / ".local-config"`; `_parse_local_config()` reads it; ".local-config is mandatory". Doc's ".local-config is the sole registry" holds. ✓
- Agent dirs carry the compose triple (`CLAUDE.md` + `CLAUDE.linked.md` + `CLAUDE.conflicts.md`) — confirmed in `.squidsquad/qa/`. ✓
- `.assemble-cache/`: doc claim "every alias dir contains ... + `.assemble-cache/`" is **canonically grounded** — COMPOSE-ARCHITECTURE L740: "Cache store: `.squidsquad/<alias>/.assemble-cache/` (git-tracked alongside the assembled output)". Doc faithfully mirrors COMPOSE. ✓

### (d) All 11 findings present — PASS
E1, E2, E3, E4, E5, W4, W5, W6, L1, L2, L3 each reflected in body + §14 revision log; W3 accepted-as-is (#10358 closes). ✓

## Advisory (OUT OF R1 SCOPE — not a gate)
Disk reality: only `.squidsquad/pm/.assemble-cache/` is git-tracked; `qa/`, `dm/`, `skill/`, `designer/` lack one — despite same-run compose (identical CLAUDE.linked.md mtime). COMPOSE L740 says compose git-tracks `.assemble-cache/` per alias dir, so the **repo state deviates from canon** (compose not materializing/committing the cache for non-pm dirs, or it was cleaned). This is a **compose/state** matter, NOT an INSTALLER-ARCH doc-reconciliation defect — the R1 doc is correct against its canonical source. Surfacing for PM/skill to optionally file as a separate compose-output finding. Does not block R1 ship.

## CQ
N/A — TRD reference/architecture doc (descriptive, not directive agent instructions composed into runtime CLAUDE.md). Checked, not auto-dismissed.

## Merge note for DM
Clean: main did not touch `docs/INSTALLER-ARCH.md` since merge-base; docs-only single file. Branch 12 behind = unrelated commits.

## Transition
pending-test → pending-ship. No `review:human-required`. Ready for DM ship.
