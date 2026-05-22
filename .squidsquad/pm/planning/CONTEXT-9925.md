# CONTEXT-9925 — Cross-role responsibility awareness + per-role/per-variant scope layering

**Issue**: #9925
**Phase**: 2 (Locked Decisions, post-human-correction-2)
**Author**: pm-lead
**Date**: 2026-05-22
**Status**: planning → planned (after human approval of these locks)
**Supersedes**: prior CONTEXT-9925.md drafts (first one had L1 as N×N prohibition table; second one left L2/L3 underspecified as just "existing files unchanged" + "stubs").

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/CONTEXT-9925.md`. Read this artifact in full before pickup. The bullets in the issue body are a summary; this planning artifact is the contract.

---

## Authoritative Scope Statement

Three-layer responsibility model, with progressively narrowing scope at each layer:

- **L1 — Team awareness.** Every agent reads a roster of every other role's public responsibility. Source of truth: each role's `manifest.yaml` (`display_name` + `tagline` + `description` — already declared as "the role's public contract"). Compose-time auto-propagation.
- **L2 — The role in general.** Every agent reads its OWN role's general responsibility in domain terms — what this role does, and what this role does NOT do at the broad scope level. Examples: "QA verifies the product being delivered; QA does NOT do technical implementation work." "PM manages workflow and processes; PM does NOT write code." Lives in a new per-role file.
- **L3 — Role × variant.** Variant-specific narrowing of L2. Example: an iOS dev variant writes unit tests but NOT end-to-end tests. Lives in a per-variant file. Stub where no variant-specific scope exists yet.

The three layers cover three different questions:
1. *"What do my teammates do?"* (L1, every agent, same content)
2. *"What do I do in general?"* (L2, own role only, role-specific content)
3. *"What's specific to my variant?"* (L3, own variant only, variant-specific content — often empty stub)

Scope boundary: this task ships the layering machinery + L2 content for the 4 base roles (pm/qa/dm/dev) + L3 stubs for all 20 variants. **Variant-specific L3 content (e.g., iOS dev's testing pyramid) is deferred to follow-up issues per variant.** The user's iOS-dev example is illustrative of what L3 will eventually hold, not a deliverable of #9925.

---

## Locked Decisions

### D1 — L1 is awareness, not prohibition (LOCKED, human correction 2026-05-22 #1)

L1 file `references/sub-skills/common/agent-boundaries.md` contains:

1. A single short instruction: *"Know each other's responsibilities. When you decline work that isn't yours, route accurately — name the role and the reason. Bare 'not my domain' is not enough."*
2. A compose-time marker (`{{role-roster}}`) where compose.py injects auto-generated summaries of every role.

L1 explicitly does NOT contain: a cross-role rules table, per-role prohibitions, or strict `DO NOT` directives about other agents' work. Those belong in L2.

### D2 — Source of truth for L1 roster is manifest.yaml (LOCKED)

`compose.py` reads each role's `references/roles/<role>/manifest.yaml` and extracts:
- `display_name` — short label (e.g., "PM", "QA", "DM", "Skill").
- `tagline` — one-line role purpose (e.g., "Coordinates the team and talks to you").
- `description` — multi-line responsibility statement (domain-terms only per existing manifest discipline).

Roster propagation discipline: the manifest's existing rule ("Describe the role in domain terms… Do NOT reference internal file paths, status labels, scripts, or storage mechanisms" — PM manifest lines 7–10) MUST hold, because compose-time propagation puts these fields into every agent's CLAUDE.md. Drift detection on `description` is out of scope for #9925 but is a flagged follow-up risk.

### D3 — Roster propagation is identical across all agents (LOCKED)

Every agent's composed CLAUDE.md gets the same `{{role-roster}}` block — including a self-entry for the role being composed. Self-entries catch drift between L2 "what I do in detail" and the L1 manifest summary "what the team thinks I do".

### D4 — L2 is "the role in general" (LOCKED, human correction 2026-05-22 #2)

NEW per-role L2 file: `references/sub-skills/roles/<role>/responsibility.md`. One file each for pm, qa, dm, dev (4 files total).

Content shape (locked template):

```markdown
# <Role> — General Responsibility

## What this role does

<3–6 bullet domain-level statements of the role's scope. Same scope as manifest.yaml description, but written from the inside — addressed to the agent acting in this role, can reference internal mechanisms where they help the agent act.>

## What this role does NOT do

<3–5 bullet explicit exclusions at the general level. NOT exhaustive procedural prohibitions (those stay in prohibitions.md). Examples:
- PM: does not write production code, does not implement fixes directly, does not run E2E tests itself.
- QA: does not write production code, does not redesign features, does not perform delivery.
- DM: does not modify dev/skill template logic, does not gate-keep verification.
- dev: does not approve tasks, does not run delivery, does not write QA test plans.>

## Why this matters

<1–2 sentences on why these boundaries exist for THIS role. References to seam partners ("verification is QA's lane", "delivery is DM's lane") are encouraged but optional.>
```

Distinguishing L2 responsibility.md from existing L2 files:
- `responsibility.md` (NEW): general scope contract — what role does / does NOT do at the broad level.
- `prohibitions.md` (EXISTING): strict procedural `DO NOT` rules (e.g., "Never push without pulling first", "Never edit Discussion entries").
- `instructions.md` "Your Responsibilities" section (EXISTING): per-cycle procedural responsibilities (e.g., "Run pipeline sentinel each cycle").
- Other L2 files (checkin.md, delivery.md, etc.): specific procedural sub-skills.

`responsibility.md` is the broadest of these and is the answer to *"what does this role do, in general?"* — distinct from the narrower behavioral and procedural files.

### D5 — Memory entries absorbed into appropriate L2 file by category (LOCKED)

Each named `feedback_*` memory entry is absorbed into the L2 file whose shape best matches the entry. Each absorption carries an HTML-comment lineage tag (`<!-- absorbed from feedback_X -->`).

Categorized placement (10 entries):

| Memory entry | Target file | Reason |
|---|---|---|
| `feedback_dont_do_qa_job` | PM `responsibility.md` (does NOT) | Scope boundary: PM does not verify pending-test |
| `feedback_bugs_behavior_only` | PM `responsibility.md` (does NOT) | Scope boundary: PM describes behavior, does not RCA |
| `feedback_test_workflow_separation` | PM + QA + dev `responsibility.md` (does NOT, all three) | Scope boundary spanning 3 roles |
| `feedback_dm_optional` | DM + PM `responsibility.md` (does) | Scope flexibility: PM can act as DM if DM absent |
| `feedback_no_ship_failed_tc` | QA + DM `responsibility.md` (does NOT) | Scope boundary: no ship with failed TCs |
| `feedback_no_ship_with_gaps` | QA + DM `responsibility.md` (does NOT) | Scope boundary: no ship with gaps |
| `feedback_auto_approve_bugs` | PM `responsibility.md` (does) | Scope clarification: bugs auto-approved |
| `feedback_fix_pm_bugs_immediately` | PM `prohibitions.md` | Behavioral rule (timing), not scope |
| `feedback_manual_agents` | PM `prohibitions.md` (positive directive) | Behavioral rule (boot dead agents), not scope |
| `feedback_dont_ask_before_verifying` | PM `prohibitions.md` (positive directive) | Behavioral rule (don't ask permission), not scope |

### D6 — L3 is variant-specific narrowing; stubs in v1 (LOCKED)

NEW per-variant L3 file: `references/roles/<role>/<variant>/responsibility.md`. 20 files total, one per variant directory (`references/roles/{dev,dm,pm,qa}/{android,fullstack,ios,skill,web}/`).

All 20 ship as STUBS in v1. Stub content (locked template):

```markdown
# <Role>/<Variant> — Variant-Specific Responsibility

No variant-specific responsibility narrowing for `<role>/<variant>` at this time.
Refer to L2 at `references/sub-skills/roles/<role>/responsibility.md` for the general role scope, and the L1 team roster for cross-role awareness.

<!-- Future variant-specific content will replace this stub. Example shape (illustrative, not a deliverable for #9925):
     For dev/ios: "iOS dev writes unit tests for delivered features but not end-to-end tests; e2e tests are QA's variant of the iOS test pyramid." -->
```

L3 stubs are NOT wired into the variant's `includes.yml` `additional_includes` in v1 — they are passive markers. When a variant fills in real content in a follow-up issue, that issue MUST wire it into `additional_includes` in the same PR.

### D7 — compose.py changes (LOCKED)

Three changes to `compose.py`:

1. **L1 fragment include** — Each role's `references/roles/<role>/includes.yml` AND `includes-events.yml` adds `common/agent-boundaries` to the `includes:` list. (Same wiring pattern as any other L1 fragment.)

2. **L2 fragment include** — Each role's `references/roles/<role>/includes.yml` AND `includes-events.yml` adds `roles/<role>/responsibility` to the `includes:` list. (Same pattern; per-role inclusion only — pm gets pm's, qa gets qa's, etc.)

3. **Role-roster injection** — New compose-time logic:
   - Discover all role manifests at `references/roles/*/manifest.yaml`.
   - Extract `display_name`, `tagline`, `description` from each.
   - Render them into a markdown roster block (format below).
   - Replace the `{{role-roster}}` marker in the inlined L1 `agent-boundaries.md` content.

Roster block format (locked):

```markdown
## Your Teammates' Responsibilities

### {{display_name}} — {{tagline}}

{{description}}

[repeat per role, sorted alphabetically by manifest id for stable output]
```

If a role is missing `tagline` or `description` from its manifest, compose emits a build warning to stderr but does NOT fail — defensible default is an empty section under `display_name`. Missing `display_name` IS a build error (every role must be name-able).

### D8 — Compose ordering and stability (LOCKED)

- Role roster is sorted alphabetically by manifest `id` (stable output).
- Manifest reads are cached within a single compose run (one read per role, not per agent).
- If `{{role-roster}}` marker is absent in `agent-boundaries.md`, compose emits a stderr warning and skips the injection — the L1 file stays in but with no roster (degraded mode).
- If `agent-boundaries.md` is missing entirely, compose emits a stderr warning and continues (no L1 fragment inlined — same as any other missing include).
- If a role's `responsibility.md` (L2) is missing, compose emits a stderr warning for THAT role's compose only.

---

## Acceptance Criteria (revised after human correction #2)

- **AC1** — File `references/sub-skills/common/agent-boundaries.md` exists with the D1 awareness instruction and the `{{role-roster}}` marker.

- **AC2** — `compose.py` is modified per D7: L1 fragment inclusion works, L2 fragment inclusion works, and the role-roster injection replaces `{{role-roster}}` with the rendered block.

- **AC3** — Each role's `includes.yml` AND `includes-events.yml` contains both `common/agent-boundaries` (L1) AND `roles/<role>/responsibility` (L2) in `includes:`. Verification: grep the manifests.

- **AC4** — Running `python references/scripts/compose.py deploy <role>` for each of pm/qa/dm/dev produces a composed CLAUDE.md that contains:
  - The L1 awareness instruction text (literal string match for "Know each other's responsibilities").
  - The "Your Teammates' Responsibilities" header from D7's roster format.
  - At least one rendered teammate entry per OTHER active role from `config.md`.
  - The role's OWN L2 responsibility.md content (literal match for the role's "What this role does" header).
  - The role's OWN L2 responsibility.md "What this role does NOT do" section.

- **AC5** — Four L2 `responsibility.md` files exist at `references/sub-skills/roles/{pm,qa,dm,dev}/responsibility.md`. Each matches the D4 template structure (has all three required sections: "What this role does", "What this role does NOT do", "Why this matters") with at least 3 bullets in each of the first two sections.

- **AC6** — All 10 memory entries listed in D5 are absorbed into the indicated L2 file with HTML-comment lineage tags (`<!-- absorbed from feedback_X -->`). Verification: grep for each lineage tag in the predicted file.

- **AC7** — All 20 L3 stub files at `references/roles/<role>/<variant>/responsibility.md` exist and match the D6 template (literal string match for "No variant-specific responsibility narrowing"). None are wired into `additional_includes`.

- **AC8** — Compose ordering is stable per D8: running `compose.py deploy pm` twice with no source changes produces byte-identical output.

- **AC9** — Compose degraded modes per D8 work without crashing: missing `tagline`/`description` produces warnings + valid output; missing `display_name` produces a build error with exit code != 0; missing role `responsibility.md` produces a warning + valid output for other roles.

- **AC10** — Regression test at `tests/test_agent_boundaries.py` covers: (a) AC4 across all 4 roles, (b) AC6 lineage tags, (c) AC7 stub files, (d) AC8 byte-identical re-runs, (e) AC9 degraded modes.

---

## Out of Scope

- **Variant-specific L3 content** (e.g., iOS dev's testing pyramid scope) — deferred to follow-up issues per variant. The iOS dev example in the user's direction is illustrative of what L3 will eventually hold, not a deliverable here.
- Auditing or revising any role's manifest `description` field — that's per-manifest hygiene.
- Drift detection between L2 `responsibility.md` and manifest `description` — both can describe the role; manifest is the outward-facing summary, L2 is the inside view. They can diverge in detail without conflict.
- Restructuring existing L2 files (`prohibitions.md` consolidation, `instructions.md` "Your Responsibilities" section refactor) — out of scope.
- Removing absorbed memory entries from `MEMORY.md` — additive only; memory layer is a separate concern.
- Tooling enforcement (linter for finger-pointing patterns) — possible future issue.

---

## Why earlier CONTEXT-9925.md drafts were wrong

**Draft 1** (pre-human-correction-1): framed L1 as a restrictive N×N role × responsibility table with strict cross-role prohibitions. Wrong because L1 is for *awareness*, not *restriction*; restrictions belong in L2.

**Draft 2** (post-correction-1, pre-correction-2): correctly reframed L1 as awareness + roster propagation, but left L2 underspecified ("existing files unchanged") and L3 as pointer-only stubs. Wrong because L2 is supposed to carry the role's general responsibility statement — which doesn't have a clean home in the existing L2 files. A new `responsibility.md` per role is needed.

**This draft** (post-correction-2): three-layer model with explicit content shapes at each layer. L1 propagates manifest summaries (awareness). L2 carries each role's general scope contract in a new `responsibility.md` (the role in general — what it does and does NOT do). L3 stubs everywhere in v1; variant-specific content arrives in follow-up issues.

---

## DS Review Findings — Resolution Map (post-correction-2)

| Finding | Severity | Resolution |
|---|---|---|
| F1 (compose wiring missing) | error | D7 + AC2 + AC3 (now covers L1 AND L2 wiring) |
| F2 (L3 path ambiguity) | error | D6 specifies `references/roles/<role>/<variant>/` (variant tree) |
| F3 (top-N not testable) | warning | Moot — no top-N enumeration in new design |
| F4 (referenced OR absorbed) | error | D5 locks ABSORB into the categorized L2 file (responsibility.md or prohibitions.md) |
| F5 (no seam-coverage AC) | warning | Moot — seams emerge from L2 "What this role does NOT do" + L1 roster, not from a handwritten table |
| F6 (skill is variant, not peer) | warning | Moot — compose reads existing manifests, agnostic |
| F7 (L3 stub spec missing) | warning | D6 specifies filename + content + non-wiring |
