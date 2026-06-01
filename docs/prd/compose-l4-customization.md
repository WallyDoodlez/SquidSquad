# PRD C — L4 Customization (Runtime L4 Writes by Agents)

> **Status**: PRD draft, 2026-05-31. Derived from TRD [[COMPOSE-ARCHITECTURE]] §3.3 (L4 ops + per-slot constraints) + §4.2 (compose-time L4 application — read-side) + §7 (runtime L4 writes — write-side, the focus of this PRD). Part of the COMPOSE-ARCH PRD slice family: A (link) / B (assemble) / C (this) / D (catalog + wake-mode) / E (harness-owned freshness).
>
> **Scope:** the **write path** for L4 customization — the `l4-curation` sub-skill that detects customization requests in human-agent conversation, elicits scope, classifies the structural op, runs the three safety gates (DS audit + mini-CQ + dry-run), and commits the L4 change. Excludes compose-time L4 reading mechanics (PRD A), the LLM assemble pass (PRD B), sub-skill catalog enforcement (PRD D), and harness-owned freshness (PRD E).

---

## 1. Goal

Today, when a human says "from now on, before filing a bug, also check `incidents/`", that customization either gets lost (only that conversation remembers it) or muddled (the agent makes ad-hoc behavior changes that no other instance of the same role-class sees, no audit trail captures, and the next session forgets). PRD-C delivers the **durable + safe** path: the human's conversational customization is captured once in `l4-curation`'s elicitation dialog, classified into a structural op (replace / insert-before / insert-after / append), gated by three safety checks (DS audit, mini-CQ confirmation, compose dry-run), committed atomically to `.squidsquad/project/<role-class>.md`, and immediately effective for all instances of that role-class on the next cycle via a post-commit recompose.

## 2. User-facing outcomes

| Persona | Outcome |
|---|---|
| **Human giving a durable instruction in conversation** | The agent detects the customization, elicits scope (role-class? which step?), drafts the change in §7.3 H3-op format, asks for explicit confirmation, then commits — no ad-hoc behavior change without an audit trail |
| **Human reviewing the L4 commit later** | Commit message names the slot + op + target; commit body quotes the human directive verbatim; HTML-comment metadata trailer records `authored-by`, `authored-at`, `source-conversation` |
| **Human running `git blame` on a behavior change** | Sees which conversation produced which L4 op, with timestamp and authoring agent — the audit trail is git-native, no separate log |
| **Other agents of the same role-class** | Pick up the customization on next cycle automatically — post-commit hook recomposes their CLAUDE.md so the new L4 op lands in their composed output without any per-agent ceremony |
| **Human wanting to roll back a customization** | `git revert` the L4 commit, or surface a fresh request that the agent translates into a counter-entry (e.g., `replace` with empty body) committed via the same path |
| **Agent encountering an ambiguous customization request** | Surfaces one clarifying question to the human before persisting; never silently picks between `replace` and `insert-after` on the agent's own judgment |
| **Agent that would have introduced a conflict with L1-L3** | `l4-curation` pre-empts by detecting the contradicting prose and proposing a `replace` reframing or surfacing the conflict to the human — the §4.6 assemble pass would resolve it anyway, but pre-emption avoids the runtime conflict-report noise |

## 3. Success criteria

PRD-C is "done" when ALL of the following hold:

1. A `references/sub-skills/common/l4-curation.md` sub-skill exists and is composed into every role-class's CLAUDE.md (instructions slot). Its content covers the §7.1 detection patterns (durable vs one-off, customization vs feature request), the §7.2 decision tree (the five-step classification logic), the §7.3 file format authoring rules, and the §7.4 safety gates.
2. **Detection**: when the human gives a customization-shaped directive (durable, role-class-scoped, project-local — heuristics per §7.1), the agent invokes `l4-curation` before responding with implementation work. One-off requests (e.g., "do X this once") and feature requests (e.g., "we need a new sub-skill that does Y") are explicitly NOT classified as L4 writes.
3. **Elicitation**: the dialog explicitly surfaces role-class scope to the human ("This will affect all instances of `worker` — FE and BE — confirm?") before proceeding to draft.
4. **Decision tree (§7.2)**: classifies the op as one of `replace step:cycle/<id>` / `insert-before step:cycle/<id>` / `insert-after step:cycle/<id>` / `append` (Instructions slot) or appended prose (Project Context / Identity / Soul slots). Refuses to write an op against a slot the spec forbids (e.g., L4 vault, L1-L3 project-context).
5. **Conflict pre-emption (§7.1 paired with §4.6)**: before drafting, `l4-curation` reads the linked composite for the target slot (via PRD-A's `--check` path or equivalent). If new entry would materially contradict existing L1-L3 prose, prefer `replace`, reword to refine, or surface to human — never silently write the conflicting op.
6. **Gate 1 — DS audit**: classification (op + target) is reviewed by a `deepseek` model via `model_router`. Rejection blocks the write and re-prompts the agent for clarification.
7. **Gate 2 — mini-CQ confirmation**: agent confirms the exact L4 change back to the human ("Adding `insert-before step:cycle/file-bug` — OK?"). Confirmation is the commit trigger.
8. **Gate 3 — compose dry-run**: a per-alias `compose.py deploy <alias> --check` runs in-memory against the **staged** L4 file (the to-be-committed content, NOT the on-disk version). Any error — orphan step-ID target, per-slot constraint violation (the validation rules in [[compose-link-stage]] §3 criterion 6), duplicate H3 op under the same slot, or unresolved sub-skill reference — aborts before commit. This semantic (staged-content per-alias validation) is distinct from [[compose-link-stage]] story A4's `deploy-all --check` (on-disk drift detection for PRD E). Reconciliation of the two `--check` shapes is captured as open question Q-C5 below.
9. **Atomic commit**: write `.squidsquad/project/<role-class>.md` + commit (message `<role>: L4 write — <slot>/<op>/<target>`; body quotes human directive verbatim; HTML-comment metadata trailer present) + push happen atomically. No partial state on the file system.
10. **Post-commit recompose**: a hook (file-watch or post-commit) detects `.squidsquad/project/*.md` change, triggers `compose.py deploy-all` for the affected role-class's aliases, and (per [[project_compose_freshness_harness_owned]]) the harness emits `restart-required` to the affected agents. Affected agents pick up the new CLAUDE.md on next cycle.
11. **Recompose-failure recovery (§7.4 step 3 race)**: if the post-commit recompose fails (e.g., concurrent L1-L3 PR renamed a step ID between dry-run and commit), the writing agent `git revert`s the L4 commit, alerts the human via tracker comment with the diagnostic, and aborts the cycle. No broken CLAUDE.md ever lands on `main`.
12. **Iteration-log entry**: the cycle that performed the L4 write logs the directive, classification, gate results, and commit SHA in the alias's iteration file.
13. **Counter-entry / removal flow** (§7.5 + §7.7): the human can request removal of a prior customization through the same dialog. Agent writes either a counter-entry (`replace` with empty body, or matching removal op) or — with explicit human confirmation — deletes the H3 block in-place. Both paths go through the same three gates.

## 4. Non-goals

- Compose-time L4 reading (slot grammar, H3 op processor, validation rules R1-R6) — [[compose-link-stage]] (PRD A).
- LLM assemble pass on the linked composite — [[compose-assemble-stage]] (PRD B).
- Authoring **new sub-skills** (catalog additions) — §7.2 step 5 explicitly excludes this from L4 customization; new sub-skills are shipped-content work upstream in `references/sub-skills/`, not L4 ops.
- Sub-skill catalog gate enforcement at compose time — PRD D.
- Harness boot-time check + L4-write trigger mechanism — PRD E (the trigger that runs the post-commit hook is harness-side; the hook contract is shared between this PRD and PRD E).
- Migrating this repo's existing legacy multi-file `.squidsquad/project/*.md` content into single-file `<role-class>.md` form — companion one-shot task (A2.5 per A1-audit recommendation), not PRD-C scope.
- Vault writes (`vault-create`, `vault-update`) — separate sub-skills; PRD-C only governs L4 file writes.

## 5. Architectural anchors

- **TRD §3.3** — L4 file model: one file per role-class, H2 slot sections, H3 op grammar, per-slot constraints (the read-side rules PRD-A must enforce; PRD-C must produce content that conforms).
- **TRD §4.2** — Compose-time L4 application (read-side); informs what `l4-curation`'s dry-run gate exercises.
- **TRD §7.1** — Trigger detection: durable vs one-off, customization vs feature, shared write effect across role-class instances.
- **TRD §7.2** — Agent decision tree (the five-step classification logic).
- **TRD §7.3** — L4 file format: H2 slot, H3 op + target, HTML-comment metadata trailer.
- **TRD §7.4** — Safety: DS audit + mini-CQ + dry-run (the three gates).
- **TRD §7.5** — Audit trail: commit, log, reversibility.
- **TRD §7.6** — End-to-end sequence diagram.
- **TRD §7.7** — Curation is one-shot + durable: no recurring scan, no drift detector, no auto-conflict-resolver.

## 6. Dependencies

| Dependency | From | Why |
|---|---|---|
| PRD-A: L4 H3 op grammar + per-slot constraints implemented in `compose.py` | [[compose-link-stage]] | Gate 3 (dry-run) exercises the compose-side L4 reader. Without PRD-A's L4 op processor, dry-run can't validate the staged change. |
| PRD-A: a per-alias `--check` variant of `compose.py deploy <alias>` with **staged-content** semantics — distinct from PRD-A A4's existing on-disk `deploy-all --check` | [[compose-link-stage]] (needs scope clarification — see Q-C5) | Gate 3 invokes this against the staged L4 file before commit. The variant either (a) extends A4's scope or (b) lands as a separate PRD-A story; either way, PRD-C cannot ship C5 until it exists |
| PRD-A: `## Aliases` parser (story A5) | [[compose-link-stage]] | `l4-curation` needs alias → role-class resolution to elicit the right scope from the human |
| `model_router` with a deepseek provider for the DS audit gate (Gate 1) | Existing | Already in place — Gate 1 calls `model_router code-review` or a new dedicated `l4-audit` task type |
| Post-commit hook infrastructure on `.squidsquad/project/*.md` | PRD-E (file-watch) + harness | PRD-E's harness file-watch is the canonical mechanism; PRD-C's contract is that **writing to `.squidsquad/project/`** is sufficient — the harness picks up the rest |
| Sub-skill catalog (for §7.2 step 5 catalog check) | PRD-D | Step 5's check ("is this sub-skill in the catalog?") needs the catalog implementation to be meaningful; until PRD-D, the check degrades to "is there a file at `references/sub-skills/<name>.md`?" — acceptable interim |

## 7. Story breakdown (proposed)

| # | Story | TRD anchor | Effort | Notes |
|---|---|---|---|---|
| **C1** | Author `references/sub-skills/common/l4-curation.md` — the sub-skill itself: detection patterns + elicitation dialog + decision tree + safety gates. This is the bulk of PRD-C — most of the work is well-crafted prose the agent reads at runtime. | §7.1 + §7.2 + §7.4 | L | Largest single deliverable; needs careful authoring + comprehension-test coverage per `feedback_comprehension_tests_required` |
| **C2** | Add `## Instructions` reference to `l4-curation` in every role-class's `references/roles/<class>/instructions.md` (or via composed include) so every agent loads it at boot | §7 | S | Mechanical; gated on C1 |
| **C3** | DS-audit gate (Gate 1) — wire `model_router` invocation; classify-op + target review; reject path returns to `l4-curation`'s decision tree for retry | §7.4 step 1 | M | Add `l4-audit` task type to `model_router` if `code-review` is too generic |
| **C4** | mini-CQ confirmation gate (Gate 2) — agent emits exact-form confirmation; treats only an explicit "yes / approved / go" as commit trigger; ambiguous reply re-prompts | §7.4 step 2 | S | Prose + a small parser for "approval-shaped" replies |
| **C5** | Compose dry-run gate (Gate 3) — invoke `compose.py deploy <alias> --check` against staged file; surface any error to the agent for human disclosure | §7.4 step 3 | S | Depends on PRD-A's A4 (`--check` mode) |
| **C6** | Atomic L4 write + commit + push — write `.squidsquad/project/<role-class>.md`, commit with the §7.5 message/body/metadata-trailer format, push | §7.5 | M | Includes the HTML-comment metadata trailer emission |
| **C7** | Recompose-failure recovery (§7.4 step 3 race) — when post-commit recompose fails, `git revert` + tracker comment + abort | §7.4 race recovery | S | Pure failure-path handling |
| **C8** | Conflict pre-emption (§7.1 + §4.6 pairing) — `l4-curation` reads linked composite for the target slot, detects materially-contradicting prose, proposes `replace` reframing or surfaces conflict | §7.1 + §4.6 pre-emption | M | Couples with PRD-B's conflict-detection vocabulary; ship after PRD-B B4 if possible |
| **C9** | Counter-entry / removal flow — dialog branch for "undo a prior customization"; produces a counter-op or in-place H3 deletion | §7.5 + §7.7 | S | Reuses C3–C7 gates |
| **C10** | Comprehension tests (CQ specs) for `l4-curation` — fresh-agent quiz that the sub-skill content reliably teaches the decision tree + gate behavior | `feedback_comprehension_tests_required` | M | Standard for any sub-skill that adds agent instructions |

Effort scale: S = 1–2 days, M = 3–5 days, L = 1+ week.

**Recommended pickup order** (lowest risk first; respects dependencies):

1. **C1** — sub-skill authoring (no code dependencies; can start anytime once content is approved)
2. **C10** — comprehension tests in parallel with C1 (the tests validate the prose)
3. **C2** — wire into role-class instructions (mechanical)
4. **C4** — mini-CQ (pure prose + simple parsing; no LLM dependency)
5. **C6** — atomic write + commit (depends on PRD-A's H3 grammar to know what to write)
6. **C3** — DS audit gate (independent code path)
7. **C5** — compose dry-run gate (depends on PRD-A A4)
8. **C7** — failure recovery (after C5/C6)
9. **C8** — conflict pre-emption (after PRD-B B4 if possible)
10. **C9** — counter-entry/removal (after C3–C7)

## 8. Open questions for this PRD

| # | Question | Resolution path |
|---|---|---|
| Q-C1 | Should `l4-curation` be a sub-skill in `common/` (every role loads it) or only in `pm/` (PM is the human-facing role)? Worker agents also receive durable instructions in some flows. | Decide in C1 — recommend `common/` per TRD §7.1's framing ("agent of any role-class"); PM is the most common but not exclusive |
| Q-C2 | Should Gate 1 (DS audit) use the existing `code-review` task type or a new `l4-audit` task type with a dedicated prompt? | Decide in C3 — recommend new `l4-audit` task type; the prompt is specific (classify op + target, not general review) |
| Q-C3 | Where does the post-commit hook live? In `.git/hooks/post-commit` (local), in the harness's file-watch (PRD-E), or both? | Decide in coordination with PRD-E — recommend harness file-watch is the canonical path; local git hook is optional convenience for human-driven L4 edits outside the agent dialog |
| Q-C4 | Should `l4-curation` block the agent from picking up new work until the L4 write completes, or is the write asynchronous? | Decide in C6 — recommend synchronous: the human is in the conversation expecting confirmation; the write is short (single file + commit + push); blocking the cycle is acceptable |
| Q-C5 | PRD-A A4 defines `deploy-all --check` with on-disk drift semantics (for PRD-E). PRD-C Gate 3 needs `deploy <alias> --check` with **staged-content** semantics (validate the to-be-committed L4 against L1-L3 sources without writing). Should PRD-A A4 expand to cover both shapes, or should a new PRD-A story land for the per-alias staged variant? | Coordinate with PRD-A — recommend new dedicated PRD-A story (e.g., A4.5) for the staged-content variant; keeping A4 focused on on-disk drift keeps PRD-E's consumer signature clean |

## 9. Out of scope — explicit list

For traceability, these belong to other PRDs:

- L4 H3 op processor at compose time ([[compose-link-stage]] / TRD §4.2)
- Validation rules R1-R6 ([[compose-link-stage]] / TRD §3.3)
- Assemble pass conflict report ([[compose-assemble-stage]] / TRD §4.6)
- Sub-skill catalog gate at compose time (PRD D / TRD §4.5 full)
- Wake-mode selection (PRD D / TRD §6.5)
- Harness file-watch on `.squidsquad/project/` (PRD E / TRD §8.2) — PRD-C's contract ends at the L4 file commit; the trigger that runs `compose.py deploy-all` is the harness's job
- L4 multi-file → single-file migration of this repo's existing content (companion task A2.5)
- Vault writes (separate sub-skills)

## 9a. Coexistence with v1 — no broken installs during the transition

**Family-wide constraint** (applies to all PRDs A–E): the existing v1 `.squidsquad/<alias>/CLAUDE.md` MUST remain the runtime contract until the family-wide **v2 switch PR** ships. No PRD-C PR is allowed to:

1. Modify the v1 output path or its bytes
2. Break the v1 compose pipeline (existing `compose.py deploy <role>` must keep producing byte-identical v1 output)
3. Land `l4-curation` writes on the default code path against the v1 L4 file shape — until the switch, `l4-curation` writes target the v2 single-file `<role-class>.md` location, NOT the legacy multi-file pattern

**PRD-C-specific application**:
- C1's authored `l4-curation.md` sub-skill is composed-in only by the v2 compose path. Until v2 is the default (post-switch PR), the live install's L1-L3 instructions do NOT yet teach agents to invoke `l4-curation`, so the runtime L4 write flow is dormant — by design. Operators get the new behavior only when v2 outputs land at the v1 path during the switch.
- C5 dry-run gate invokes v2 `compose.py deploy <alias> --check --v2` (or the equivalent opt-in flag) against the staged v2 L4 file. Failure aborts before commit. v1 outputs are NOT touched by C5's path.
- C6 atomic write targets `.squidsquad/project/<role-class>.md` — but a write here only takes effect on the runtime when v2 compose reads it. Until the switch, writes accumulate harmlessly in the v2 source tree.
- The v2 switch PR (last in the family) flips the default so v1 multi-file L4 routing is removed and `<role-class>.md` becomes the only L4 source.
- Loop-mode fallback during the switch is automatic per [[AGENT-RUNTIME]] §8.3 boot probe — no new mechanism needed.

This means **PRD-C can ship its sub-skill (C1) and gate code (C3–C7) without disrupting any running install**. Behavior changes only at the switch.

## 10. Acceptance

This PRD is "done" when:

- All 10 stories (C1–C10) have shipped or been explicitly deferred (with rationale + target).
- The 13 success criteria above are demonstrably met against this repo's own `.squidsquad/` install (we eat our own dogfood).
- At least one end-to-end smoke: human says "from now on, before X do Y" → agent invokes `l4-curation` → decision tree classifies → DS audit approves → mini-CQ confirmation → dry-run passes → commit lands → CLAUDE.md regenerates → next cycle the agent reads the new instruction.
- At least one failure smoke per gate: DS rejects → re-prompt; mini-CQ rejected → abort; dry-run orphan → abort; post-commit recompose fails → revert + alert.
- Comprehension tests (C10) pass: a fresh agent given only `l4-curation.md` can correctly classify three example human directives.

## 11. References

- TRD: [[COMPOSE-ARCHITECTURE]] (canonical spec — §3.3 + §4.2 + §7)
- Sibling architecture: [[AGENT-RUNTIME]] (cycle integration), [[HARNESS-ARCH]] (post-commit hook + harness file-watch), [[INSTALLER-ARCH]] (initial L4 file seeding)
- Companion PRDs: [[compose-link-stage]] (A — compose-time L4 reading), [[compose-assemble-stage]] (B — conflict resolution at compose time), [[compose-catalog-and-wake-mode]] (D, forthcoming), [[compose-freshness]] (E, forthcoming)
- Memory rules: [[project_trd_prd_delivery_model]], [[project_l4_long_living]], [[project_l4_autonomous_writes]], [[project_compose_freshness_harness_owned]], [[project_assemble_unconditional]]
- Existing design discussion: #8997 (L4 autonomous-write design)
- Existing sub-skill: `references/sub-skills/common/l4-curation.md` — **needs creation**; placeholder noted in `docs/sub-skill-catalog.md` per memory rule [[project_subskill_directory]]
