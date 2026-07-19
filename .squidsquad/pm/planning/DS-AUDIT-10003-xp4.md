Now I have enough information to produce the audit. Let me compile the findings.

---

# 10003-ds-audit-xp4-installer Research — Cross-Pair Consistency Audit: VAULT-ARCH v2 vs INSTALLER-ARCH

## Summary

Audited `docs/VAULT-ARCH.md` (v2 TRD, prescriptive TARGET design) against `docs/INSTALLER-ARCH.md` (CURRENT-state installer doc) for cross-pair consistency. The two docs are broadly aligned on vault fundamentals: both agree vault lives at `.squidsquad/vault/`, is git-tracked, is preserved across upgrades/clean-rebuild, and has all-agents-R/W access. VAULT-ARCH §12.2 already flags the four major reconciliation needs (seed `vault-schema.json`, seed `.telemetry/.gitattributes`, add M0–M4 migration entry, extend vault preservation to shards). The audit found **3 findings** beyond these flagged items — all minor or nit, no blockers. The docs are converged enough that cutover reconciliation can proceed as planned; the findings are documentation-precision items that should be addressed alongside the §12.2-flagged changes rather than blocking them.

## Vault Context

- **BRIEFING.md priorities**: The DS re-audit of #10837 + #10839 is gated (line 50: "DS re-audit needed for #10837 + #10839 before PM picks them up"). This audit directly addresses #10838 (VAULT-ARCH) vs #10836 (INSTALLER-ARCH) cross-reference. The related umbrella PRDs (#10836–#10839) are "operator-paced post-cutover."
- **Related decisions**: Audit refresh strategy (line 35): "HARD GATE for #10836/#10838; DS re-audit needed for #10837/#10839 before PM pickup." This audit is the #10838 half of that hard gate.
- **Related patterns**: [[pattern-parallel-axis-audit]] — the cross-pair audit methodology defined in `.squidsquad/vault/galaxy/pattern-parallel-axis-audit.md`. The rules (target-vs-current, §12.2-flagged items excluded, four criteria) derive from this pattern.
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." This audit output is a markdown artifact committed to the repo.
- **Related learnings**: [[learning-doc-first-for-architecture-changes]] — this audit is part of the doc-first process required before implementation tasks are filed against the v2 redesign.

## Impact Analysis

- **Files touched**: `docs/VAULT-ARCH.md` (reviewed, no edits needed), `docs/INSTALLER-ARCH.md` (findings documented, reconciliation edits to follow at cutover)
- **Behavior changes**: None — this is a documentation audit, not a code change
- **Dependencies**: `docs/COMPOSE-ARCHITECTURE.md` (vault slot L1-exclusivity), `docs/AGENT-RUNTIME.md` (cycle-integration touchpoints), `docs/HARNESS-ARCH.md` (instance-id minting, scheduled maintenance)

## Side Effects

- **Risk 1**: Reconciliation of findings B1/B2 alongside §12.2-flagged items could be done incompletely if the §12.2 list is followed literally without reading this audit — Severity: L — Mitigation: this audit's findings should be transcribed into the cutover task's reconciliation checklist.

## Edge Cases

- **`archives/` directory still physically exists in current vault**: VAULT-ARCH §3.4 says `archives/` is "retired as a folder" but the v2 directory tree (§3.2) still shows `archives/` with an updated comment. INSTALLER-ARCH's scaffold should reflect this nuance — the directory may still exist (from v1 migration) but new notes aren't moved there. The scaffold for a FRESH v2 install could arguably omit `archives/` entirely since no notes ever get moved there. VAULT-ARCH should clarify whether the empty `archives/` directory should be scaffolded in fresh v2 installs or only preserved from v1 upgrades.
- **Node preflight gated on open item #2**: VAULT-ARCH §7.5 prescribes Node preflighting but §11 open item #2 questions whether Node is guaranteed alongside Claude Code. Until resolved, the preflight requirement is contingent — this finding should not be actioned until #2 is closed.

## Integration Risks

- **Risk**: The M0–M4 vault migration (VAULT-ARCH §10) and the installer's per-version migration walk (INSTALLER-ARCH §10) are different mechanisms. The M0–M4 migration is a one-time v1→v2 content transform; the per-version walk handles ongoing schema breaks. VAULT-ARCH §12.2 says "the migrations model gains the M0–M4 `references/migrations/` entry" — this implies the M0–M4 migration ships as one or more per-version migration files. The integration risk is that M0–M4's multi-phase (M0 freeze → M1 mechanical → M2 distillation → M3 human gate → M4 cutover) doesn't fit cleanly into the single-migration-file-per-version-step model. The INSTALLER-ARCH migration model applies one file at a time with a three-gate process per file; M0–M4's freeze-and-distill phases span multiple migration files and involve agent judgment (M2), not just deterministic transforms. This is an architectural tension that neither doc currently addresses. Severity: M — the migration walk model may need extension for multi-phase migrations.

## Upgrade & Migration

- **New config values**: `vault-schema.json` at vault root (not config.md) — "none" for config.md
- **New files**: `.squidsquad/vault/vault-schema.json`, `.squidsquad/vault/.telemetry/` directory, `.squidsquad/vault/.telemetry/.gitattributes`, `.squidsquad/vault/systems/` directory
- **Template changes**: `references/vault-templates/` templates updated to v2 frontmatter (§4.3 droppage of `confidence`/`source`/`links`; `style.md` deleted; `system.md` added)
- **Upgrade steps**: M0–M4 migration walk per VAULT-ARCH §10; INSTALLER-ARCH §10 migration model extended with M0–M4 per-version files
- **Graceful degradation**: Existing vault content survives migration unchanged (folders and galaxy prefixes stay); telemetry starts cold, ranking degrades to tier + recency + type weight

## Open Questions

- **Q1**: Should a fresh v2 install scaffold an empty `archives/` directory? VAULT-ARCH says `archives/` is "retired as a folder" (§3.4) but the directory tree still shows it (§3.2). INSTALLER-ARCH can't reconcile this until VAULT-ARCH is unambiguous. — **Why**: The scaffold either creates the directory (wasteful but harmless) or omits it (cleaner but inconsistent with the v2 tree diagram). Getting it wrong means either a phantom empty directory or a doc-vs-code drift.
- **Q2**: How does the multi-phase M0–M4 vault migration integrate with the single-file-per-version-step migration walk in INSTALLER-ARCH §10? — **Why**: If M0–M4 requires agent judgment (M2 distillation), it may break the deterministic three-gate-per-file model. A wrong fit could make the vault migration unreproducible or prompt-heavy for consuming installs.

## Recommendation

**Feasible with caveats.** The two docs are fundamentally consistent on shared invariants. The 3 findings are documentation-precision items — no architectural contradictions, no blocked cutover paths. The one substantive concern is the integration risk around M0–M4 migration vs the per-version walk model, which needs explicit design before implementation.

## Vault Candidates

- **Type**: learning — M0–M4 multi-phase migration may not fit INSTALLER-ARCH's single-file-per-version-step model; the tension between a phased content migration (freeze→transform→distill→gate→cutover) and a linear per-version walk (one file, three gates, next file) reveals a general limitation of the migration model that may recur for future large-scale content migrations. — **Why**: This is the kind of architectural tension that, if resolved with a pattern extension, should be documented for future migration authors.
- **Type**: decision — Fresh v2 installs: should `archives/` directory be scaffolded? VAULT-ARCH §3.4 says it's "retired as a folder" but the v2 directory tree still shows it. The resolution (scaffold it / don't scaffold it) is a small but concrete decision that downstream implementers will need. — **Why**: Avoids implementer guesswork at cutover time.

---

## Findings

### Finding 1 — `systems/` directory and `archives/` semantics not called out in §12.2 INSTALLER reconciliation

- **Criterion**: (b) — §12.2's INSTALLER entry misses a location needing cutover reconciliation
- **VAULT-ARCH ref**: §3.2 (PARAG directory tree adds `systems/`, `archives/` comment updated), §3.4 (archives retired as a folder), §4.1 (archives retired as a folder)
- **INSTALLER-ARCH ref**: §3.2 outputs row (line 102): *"Shared memory layer skeleton (BRIEFING.md + the five vault dirs: projects/, areas/, resources/, archives/, galaxy/)"* — hardcodes "five" and lists `archives/` as an active dir; §5 file layout tree (lines 346–352) shows v1 vault tree without `systems/`, `vault-schema.json`, or `.telemetry/`
- **What's happening**: VAULT-ARCH v2 adds `systems/` as a new directory (connective hub layer) and redefines `archives/` from an active-move target to a retired-by-semantics directory. INSTALLER-ARCH's explicit enumeration ("five vault dirs" with listed names) and the §5 tree diagram both become factually incorrect post-cutover. §12.2 says "install scaffold seeds `vault-schema.json` (default profile)" which implicitly drives directory creation, but does NOT flag that the hardcoded directory count, name list, and tree diagram need updating.
- **Severity**: **minor** — the schema seeding implicitly covers directory creation, but explicit prose becomes wrong; implementers reading INSTALLER-ARCH literally would see "five vault dirs" and not know to add `systems/`

### Finding 2 — VAULT-ARCH §7.5 Node preflight dependency absent from INSTALLER-ARCH dependency model, not flagged in §12.2

- **Criterion**: (b) — §12.2's INSTALLER entry misses a location needing cutover reconciliation
- **VAULT-ARCH ref**: §7.5 (lines 386–388): *"The wizard/installer preflights `node --version` when enabling the engine; absent Node, the feature degrades per §6.2/§9.9 (search falls back to engine-unavailable receipts; ranking to tier + recency) — and the Python-port fallback (planning §9.4.2) remains the contingency if Skill-based packaging proves unreliable in practice."*
- **INSTALLER-ARCH ref**: §4.1 Phase 0 dependency table (lines 155–163) — lists `gh`, Python 3, `pip`, runtime packages, `claude` CLI; Node is absent. The corresponding `gather_deps` function in `references/scripts/wizard.py` (lines 458–636) enumerates 6 dependencies (gh, gh_auth, python3, pip, packages, claude) — no Node check.
- **What's happening**: VAULT-ARCH prescribes a Node preflight as a soft prerequisite for the engine. §12.2's reconciliation list for INSTALLER-ARCH doesn't mention adding Node to the Phase 0 dependency set. However, VAULT-ARCH §11 open item #2 (*"Node-alongside-Claude-Code guarantee — is Node present on a target machine just because Claude Code is?"*) makes this contingent — the preflight requirement depends on whether Node is independently needed vs guaranteed by the Claude Code install.
- **Severity**: **minor** — contingent on open item #2 resolution; if Node is confirmed as an independent prerequisite, INSTALLER-ARCH §4.1 needs a Node entry and wizard.py `gather_deps` needs a `node` check; if Node is guaranteed alongside Claude Code, the preflight is unnecessary and this finding evaporates.

### Finding 3 — VAULT-ARCH §12.1 INSTALLER-ARCH line references are stale (drifted from v1 snapshot)

- **Criterion**: (d) — VAULT-ARCH cites an INSTALLER section by line number that no longer corresponds
- **VAULT-ARCH ref**: §12.1 (line 580): *"L100, L228, L292-293, L436, L464, L472"* — verified at v1 snapshot (2026-05-24)
- **INSTALLER-ARCH ref**: The cited content still exists but at different lines: §3.2 outputs row now at ~line 102 (was L100), Phase 5 scaffold now at ~line 261 (was L228), file layout tree now at ~lines 346–352 (was L292-293), §10.2 preservation now at ~line 539 (was L436), etc. INSTALLER-ARCH has been edited multiple times since the v1 snapshot (clone-registry fixes #11519, dependency-provisioning rewrite #11537, compose-inline fix, event_poll correction, migration-walk implementation #12419, harness-restart #12420, WIZARD.md retirement #13336, and more — per §14 revision log).
- **What's happening**: VAULT-ARCH says these cross-references are "verified" but the line numbers are all wrong. The same section of §12.1 uses *"Line anchors intentionally omitted — they drift; navigate by section"* for AGENT-RUNTIME but does NOT apply this caveat to INSTALLER-ARCH. The content at the referenced locations still exists and says what VAULT-ARCH claims, so this is a precision error, not a missing-content error.
- **Severity**: **nit** — the sections exist and carry the claimed content; line-number staleness is cosmetic but undermines the "verified" claim

## Verdict

**CONVERGED (no blockers)** — 0 blockers, 2 minor findings, 1 nit. The two docs agree on vault fundamentals and the §12.2-flagged reconciliation items cover the major v2 changes. The findings above are documentation-precision items to address alongside cutover reconciliation; none block the audit gate.