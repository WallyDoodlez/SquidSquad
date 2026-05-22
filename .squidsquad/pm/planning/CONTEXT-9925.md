# CONTEXT-9925 — Clarify inter-agent work boundaries in L1 / L2 / L3

**Issue**: #9925
**Phase**: 2 (Locked Decisions, post-DeepSeek review)
**Author**: pm-lead
**Date**: 2026-05-22
**Status**: planning → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/CONTEXT-9925.md`. Read this artifact in full before pickup. The bullets in the issue body are a summary; this planning artifact is the contract.

---

## Authoritative Scope Statement

#9925 promotes the implicit and memory-only inter-agent work boundaries into the compose-time instruction pipeline so that agents see them at every boot, not only after erroring first. The deliverable is a 3-layer boundary contract:

1. **L1 canonical role × responsibility table** at `references/sub-skills/common/agent-boundaries.md`.
2. **L2 per-role "Your scope ENDS here" callouts** appended to each role's existing `prohibitions.md` (or new sibling file in the same directory).
3. **L3 variant stubs** at `references/roles/<role>/<variant>/boundaries.md` — empty pointers for now, present so future per-variant overrides have a layer to live in.

Scope boundary: this task documents existing boundaries; it does NOT redesign role responsibilities. Where memory entries and existing `prohibitions.md` files conflict, the existing prohibitions wins and a follow-up issue is filed (do not silently overwrite).

---

## Locked Decisions

### D1 — Placement is hybrid L1 + L2 + L3 stub (LOCKED, human Option A)

Three layers, three files:
- **L1**: single canonical table at `references/sub-skills/common/agent-boundaries.md`.
- **L2**: per-role section in `references/sub-skills/roles/<role>/prohibitions.md` (extend the existing file; do not create a sibling).
- **L3**: stub file at `references/roles/<role>/<variant>/boundaries.md` — see D7.

### D2 — Tone is strict explicit prohibitions (LOCKED, human Option A)

Use the form `DO NOT <action>. Route to <role> because <reason>.` Matches the existing `common/prohibitions.md` and `roles/pm/prohibitions.md` style. No soft "smell-and-pause" language.

### D3 — Finger-pointing target state: accurate routing with reason (LOCKED, human Option A)

Bare "not my domain" is BANNED. Every hand-off must carry the form `this belongs to <role> because <reason>`. The L1 contract enforces this as a normative rule (not a guideline).

### D4 — Canonical role coverage is pm/qa/dev/dm (LOCKED, human Option A, supersedes DS F6)

The L1 table covers **pm, qa, dev, dm** as canonical role abstractions. `skill` is a `dev` variant (not a peer role) and is covered via L3 inheritance. The table is reusable across SquidSquad installs that may use different dev variants (web, android, ios, fullstack, skill).

### D5 — Memory entries are ABSORBED, not referenced (LOCKED, human Option A, supersedes DS F4)

The behavioral rule from each named memory entry is **inlined** into an L1 or L2 directive as a strict prohibition. The memory entries themselves are not files in the repo — they exist only in agent context — so citation would be unverifiable. Absorption converts conversational memory into compose-time instruction. Required entries to absorb (exhaustive list — no "etc."):

1. `feedback_dont_do_qa_job` → L2 PM directive
2. `feedback_bugs_behavior_only` → L2 PM directive
3. `feedback_test_workflow_separation` → L1 PM/QA/dev seam
4. `feedback_dm_optional` → L1 DM scope footnote
5. `feedback_fix_pm_bugs_immediately` → L2 PM directive
6. `feedback_manual_agents` → L2 PM directive
7. `feedback_dont_ask_before_verifying` → L2 PM directive
8. `feedback_no_ship_failed_tc` → L2 QA + DM directives
9. `feedback_no_ship_with_gaps` → L2 QA + DM directives
10. `feedback_auto_approve_bugs` → L2 PM directive

### D6 — L1 manifest + entry-file wiring is REQUIRED (LOCKED, supersedes DS F1)

Creating `references/sub-skills/common/agent-boundaries.md` is necessary but not sufficient. Compose pipeline wiring is part of the deliverable:

- Each role's `references/roles/<role>/includes.yml` MUST add `common/agent-boundaries` to the `includes:` list.
- Each role's `references/roles/<role>/includes-events.yml` MUST add `common/agent-boundaries` to the `includes:` list (so event-mode agents see it too).
- Verification: running `python references/scripts/compose.py deploy <role>` produces a `.squidsquad/<role>/CLAUDE.md` that contains the inlined L1 table content (grep for a known sentinel string from the table).

### D7 — L3 stub filename is `boundaries.md`, pointer-only content (LOCKED, supersedes DS F2, F7)

- L3 path is `references/roles/<role>/<variant>/boundaries.md` (variant tree — NOT `references/sub-skills/`).
- Filename is exactly `boundaries.md` (no `-stub` suffix; matches `domain-context.md` naming pattern).
- Minimum content (template, single paragraph):
  ```
  # Variant Boundary Overrides — <role>/<variant>

  No variant-specific boundary overrides for `<role>/<variant>` at this time.
  Refer to L2 boundaries at `references/sub-skills/roles/<role>/prohibitions.md`
  and the L1 canonical table at `references/sub-skills/common/agent-boundaries.md`.
  ```
- L3 stub is NOT added to variant `includes.yml` `additional_includes`. It is a passive file marking the layer as present; future per-variant overrides will be wired in then.
- 20 stub files to create — one per existing variant directory under `references/roles/{dev,dm,pm,qa}/{android,fullstack,ios,skill,web}/`.

### D8 — Required boundary seams (LOCKED, supersedes DS F3, F5)

The L1 table MUST contain explicit entries for these specific seams (deterministic list — no "top N most common"):

| Seam | Owning role | Strict rule |
|---|---|---|
| Verification of acceptance criteria | QA | PM: `DO NOT verify pending-test items. Route to QA because verification is QA's lane.` |
| Bug RCA (root-cause analysis) | dev | PM: `DO NOT trace root causes for bug fixes. Route to dev because RCA is dev's lane.` |
| DM behavior bugs (template defects in dm scripts) | dev (skill variant) | DM: `DO NOT modify dm/* template logic. Route to dev because skill writes DM's templates.` |
| Direct-to-main fix workflow transition | dev (the one that landed the fix) | dev: `When a fix lands direct-to-main without a PR, you MUST transition the issue open → pending-test in the SAME cycle. Do not leave it at open expecting another role to do the transition.` |
| Delivery (CHANGELOG, version bumps, packaging) | DM | PM: `DO NOT perform delivery. Route to DM because delivery is DM's lane.` |
| Code implementation (any role except dev) | dev | PM, QA, DM: `DO NOT touch application code. Route to dev because code is dev's lane.` |
| Task approval (status: planned → approved) | human | PM: `DO NOT self-approve tasks. Wait for human approval gate.` |
| Bug approval (no gate) | PM | PM: `DO NOT wait for human approval on bugs. File and transition pending → approved directly per feedback_auto_approve_bugs.` |

---

## Acceptance Criteria (revised after DS review)

- **AC1** — File `references/sub-skills/common/agent-boundaries.md` exists and contains the full role × responsibility table from D8, plus a header section that states the D3 "accurate routing with reason" rule.

- **AC2** — Each role's `references/sub-skills/roles/<role>/prohibitions.md` contains a new section titled `## Your Scope ENDS Here` with at least one strict `DO NOT … Route to <role> because <reason>` directive for every seam in D8 that names that role on either side. Role-specific count target: PM ≥ 5, QA ≥ 3, dev ≥ 3, DM ≥ 3.

- **AC3** — All 20 L3 stub files exist at `references/roles/<role>/<variant>/boundaries.md` matching the D7 template. None are wired into `additional_includes`.

- **AC4** — Compose pipeline wiring per D6: `common/agent-boundaries` appears in `includes:` of `references/roles/{pm,qa,dm,dev}/includes.yml` AND `references/roles/{pm,qa,dm,dev}/includes-events.yml`. After running `python references/scripts/compose.py deploy <role>` for each role, the generated `.squidsquad/<role>/CLAUDE.md` contains a literal sentinel string from the L1 table (e.g., `"Direct-to-main fix workflow transition"`).

- **AC5** — All 10 memory entries listed in D5 have their behavioral rule absorbed into an L1 table row or L2 prohibition. Verification: grep for each entry's behavioral payload (e.g., for `feedback_dont_do_qa_job`, the directive must say something equivalent to "DO NOT verify, route to QA").

- **AC6** — All 8 seams in D8 appear in the L1 table verbatim. Verification: grep for the seam name string in `agent-boundaries.md`.

- **AC7** — A regression test at `tests/test_agent_boundaries.py` parses `agent-boundaries.md`, asserts every D8 seam is present, and asserts every D5 memory entry has at least one absorbing directive in either L1 or L2.

---

## Out of Scope

- Tooling enforcement (linter for finger-pointing patterns in agent comments) — possible v2.
- Redesign of any role's responsibilities — this task documents what exists.
- Updating the `MEMORY.md` index to remove absorbed entries — they remain in human memory; absorption is additive.
- Per-variant boundary content beyond the D7 stub — future per-variant work.

---

## DS Review Findings — Resolution Map

| Finding | Severity | Resolution |
|---|---|---|
| F1 (compose wiring missing) | error | D6 + AC4 |
| F2 (L3 path ambiguity) | error | D7 (correct path: `references/roles/<role>/<variant>/`) |
| F3 (AC2 "top 5" not testable) | warning | AC2 specifies per-role minimums tied to D8 |
| F4 (AC5 referenced OR absorbed) | error | D5 locks ABSORB, lists 10 exhaustive entries |
| F5 (no seam-coverage AC) | warning | AC6 + D8 |
| F6 (skill not a peer role) | warning | D4: canonical pm/qa/dev/dm |
| F7 (AC3 stub spec missing) | warning | D7 specifies filename + content + non-wiring |
