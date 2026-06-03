# PRD: INSTALLER-ARCH alignment (TRD audit follow-up)

## Source

DS audit of `docs/INSTALLER-ARCH.md` against shipped + in-flight work (2026-06-03).
Audit doc: `.squidsquad/pm/planning/AUDIT-TRD-INSTALLER-ARCH-DS.md`.

## Verdict tally

13 CONFIRMED · 3 IN PROGRESS · 1 HELD · **5 GAP** · **7 DRIFT** · 0 STALE

## Critical findings (must address)

### HIGH severity

1. **Migration walk framework missing** (TRD §4.3, §10 — audit Finding 18)
   - TRD specs a full per-version migration system: `references/migrations/`, three-gate model, walk semantics, stamp updates.
   - Reality: `references/migrations/` doesn't exist; `wizard.py` has zero migration code; `WIZARD.md` Step 0b offers a 3-way prompt (abort/regenerate/rebuild) instead.
   - **Decision needed Phase 2**: implement the migration walk OR demote TRD §10 to "planned"?

2. **`references/VERSION` file missing** (TRD §3.2, §4.8 step 3, §10 step 2 — audit Finding 19)
   - TRD says version stamp reads from `references/VERSION`.
   - Reality: `wizard.py:2415-2421` reads `config.get_field("version")` with hardcoded fallback `"0.36.0"`.
   - **Decision needed Phase 2**: create the file + wire it OR update TRD to describe the actual mechanism?

3. **`squidsquad_version:` field name mismatch** (TRD §3.2, §10 step 2 — audit Finding 23)
   - TRD: YAML-style `squidsquad_version: <semver>`.
   - Reality: bullet `- **SquidSquad Version**: 0.43.0` (Title Case, markdown bullet).
   - **Decision needed Phase 2**: rename config field to match TRD OR update TRD to reference actual field name?
   - Migration walk reliability depends on this name being canonical.

### MEDIUM severity

4. **Vault subdirectories not created at install** (TRD §5 — audit Finding 20)
   - TRD: vault structured as `projects/`, `areas/`, `resources/`, `archives/`, `galaxy/` + `BRIEFING.md`.
   - Reality: `wizard.py` scaffold doesn't create vault subdirectories; only `BRIEFING.md` + `.relevance-index.json` exist.

5. **Post-installer harness restart not implemented** (TRD §10.3 — audit Finding 22)
   - TRD: installer triggers per-agent restart via `POST /agents/<alias>/stop` + `/start`, fall-through to `start.sh`.
   - Reality: no HTTP client code in `wizard.py`; ends at commit/push.

6. **wizard.py subcommands in TRD §6 don't match code** (audit Finding 25)
   - TRD lists: `check-gh`, `detect-stack`, `scaffold`, `enrich-l4`, `ensure-labels`, `serialize-spec`.
   - Reality: `detect-stack`, `enrich-l4`, `serialize-spec` don't exist. Actual subcommands include `check-gh`, `check-existing`, `repo-info`, `project-name-default`, `build-config-md`, `scaffold`, `ensure-labels`, `list-issues-by-label`, `migrate-label`, `migrate-labels-staged`.

7. **L4 Project Context seeding writes wrong files** (TRD §4.8 step 4 — audit Finding 26)
   - TRD: write Phase 1 answers to `.squidsquad/project/<role-class>.md` under `## Project Context` H2.
   - Reality: `_write_l4_project_files()` writes to `shared-stack-details.md`; `_copy_l4_seed_stubs()` copies legacy multi-file stubs the TRD itself says is retired.

8. **`## Aliases` registry format mismatch** (TRD §3.2, §4.8 step 3 — audit Finding 24)
   - Already documented at COMPOSE-ARCH (PRD-A audit), but also INSTALLER-ARCH-side cleanup needed.
   - TRD: 3-column table; reality: bullet list.

### LOW severity

9. **Phase 7 initial issue seeding not implemented** (TRD §4.10 — audit Finding 21)
   - TRD: "may seed initial issues — configurable per-install."
   - Reality: not implemented; TRD itself hedges with "may."

Plus 3 more drift items (full list in audit doc).

## Scope / what this PRD delivers

Phase 1 (Research) decides PER FINDING whether to:
- Implement the TRD-promised feature
- Update the TRD to match reality
- Defer/document as planned

Phase 2 (Discussion) locks the per-finding direction.
Phase 3 (AC drafting) produces story breakdown.
Implementation in stories (PRD-INSTALLER-A1, A2, ...).

## Gating

- Independent of E6 (#10685) — touches `wizard.py` + `references/migrations/` + `wizard/` doc; no overlap with E6 compose changes.
- Can proceed to Phase 1 research now.

## Pre-implementation review requirement (HARD GATE)

**By the time this PRD reaches implementation, COMPOSE-ARCHITECTURE PRDs A–E will have completed** (E6 cutover shipped + PRD-D Skill materialization either shipped or in flight). Several COMPOSE-ARCH outcomes change the install landscape this PRD operates in:

- **Post-E6**: v1 paths deleted; `compose.py deploy` uses alias semantics (no `--v2` flag); `_load_manifest` and `deploy_role` v1 removed.
- **Post-PRD-D**: catalog has tier + skill-description columns; standing rules (`self-restart`, `context-pressure`, `cycle-runner`) removed from catalog; `.claude/skills/` populated per-clone via per-agent filter.
- **References/VERSION** decisions and version-stamp mechanics interact with the freshness-checking work delivered by PRD-E (E1–E5).

**Skill must, before starting implementation**:
1. Re-read `docs/COMPOSE-ARCHITECTURE.md` (post-cutover state) and `docs/INSTALLER-ARCH.md` (current).
2. Confirm each Finding in this CONTEXT still applies — some may have been resolved as side effects of E6 or PRD-D.
3. Confirm the chosen direction for each Finding (from Phase 2 lock) is still feasible given the new arch.
4. Note any newly-introduced contradictions for re-discussion with PM before coding.

If a Finding no longer applies, document why and drop it from scope — do not work around assumptions that have changed.

## Pre-locked decisions (PM + operator, 2026-06-03)

These directions are settled before Phase 1 research begins, so research surfaces *how* not *whether*. Phase 2 may still re-discuss if research uncovers blockers.

### Finding 26 — L4 Project Context seeding direction

**Direction (A): Make wizard match `deploy_role_v2` (TRD-aligned).**

- Rewrite `wizard.py:_write_l4_project_files()` (lines 901–938) to write Phase 1 project-intake answers to `.squidsquad/project/<role-class>.md` under the `## Project Context` H2 section, per TRD §4.8 step 4.
- Delete `wizard.py:_copy_l4_seed_stubs()` (lines 941–972) — or, if fresh-vs-upgrading detection logic is needed for transitional installs, gate it tightly on `existing-install` + scheduled removal. Default is deletion; gating is the fallback if research surfaces a real upgrade-path need.
- Remove the legacy multi-file L4 stubs (`worker-instructions.md`, `worker-responsibility.md`, `worker-soul-directives.md`, etc.) from `references/sub-skills/project/` once `_copy_l4_seed_stubs()` is gone — they are unreferenced after the wizard fix.
- This also closes Finding 27 (legacy stubs created by installer) — same root cause.

**Rejected: Direction (B) — change `deploy_role_v2` to fall back to `shared-stack-details.md` + multi-file stubs.** Contradicts TRD §4.8 step 4 + "Historical context" note, perpetuates the retired multi-file pattern, contradicts the E6 spirit (v2 = canonical). Skill-lead concurs (cycle 1552 readout on #10685).

**Why pre-locked**: skill-lead flagged this contradiction in the cycle 1552 strategy readout, asking PM to settle direction so research phase doesn't re-litigate. Operator confirmed (A) 2026-06-03.

**Research phase still owns**:
- The exact write mechanism into `<role-class>.md` (idempotency, merge-vs-overwrite when section exists, file creation when role-class file doesn't yet exist).
- Whether `_copy_l4_seed_stubs()` deletion is unconditional or transitional-install-gated.
- Migration path for existing installs that have the legacy multi-file stubs already on disk.
- Test surface (CQ for the wizard step; fresh-install + existing-install scenarios).

## Related

- DS audit: `.squidsquad/pm/planning/AUDIT-TRD-INSTALLER-ARCH-DS.md`
- TRD: `docs/INSTALLER-ARCH.md`
- Pattern: same intake as COMPOSE-ARCHITECTURE PRDs (PRD-A → PRD-E)
- Pre-lock origin: skill-lead cycle 1552 readout on #10685 + operator 2026-06-03 confirmation
