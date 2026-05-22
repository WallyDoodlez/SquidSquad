# CONTEXT-9925 — Cross-role responsibility awareness + per-role/per-variant scope layering

**Issue**: #9925
**Phase**: 2 (Locked Decisions, post-human-correction-2)
**Author**: pm-lead
**Date**: 2026-05-22
**Status**: planning → planned (after human approval of these locks)
**Supersedes**: prior CONTEXT-9925.md drafts (first one had L1 as N×N prohibition table; second one left L2/L3 underspecified; third one missed L4 — the install-specific override layer that compose.py already supports).

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/CONTEXT-9925.md`. Read this artifact in full before pickup. The bullets in the issue body are a summary; this planning artifact is the contract.

---

## Authoritative Scope Statement

Four-layer responsibility model, with progressively narrowing scope at each layer:

- **L1 — Team awareness.** Every agent reads a roster of every other role's public responsibility. Source of truth: each role's `manifest.yaml` (`display_name` + `tagline` + `description` — already declared as "the role's public contract"). Compose-time auto-propagation.
- **L2 — The role in general.** Every agent reads its OWN role's general responsibility in domain terms — what this role does, and what this role does NOT do at the broad scope level. Examples: "QA verifies the product being delivered; QA does NOT do technical implementation work." "PM manages workflow and processes; PM does NOT write code." Lives in a new per-role file.
- **L3 — Role × variant.** Variant-specific narrowing of L2. Example: an iOS dev variant writes unit tests but NOT end-to-end tests. Lives in a per-variant file. Stub where no variant-specific scope exists yet.
- **L4 — Install-specific overrides (human-authored).** The human's place to spell out responsibility additions or narrowings specific to THIS install — e.g., "in this install, PM also owns reading the Slack channel each cycle." Lives in `.squidsquad/project/<role>-responsibility.md` (already a supported L4 mechanism in compose.py; see compose.py:393–419). Stub by default; human fills in when they want install-specific direction.

The four layers cover four different questions:
1. *"What do my teammates do?"* (L1, every agent, same content)
2. *"What do I do in general?"* (L2, own role only, role-specific content)
3. *"What's specific to my variant?"* (L3, own variant only, variant-specific content — often empty stub)
4. *"What did the operator/human spell out specifically for me on this install?"* (L4, own role only, install-specific content — often empty stub)

Scope boundary: this task ships the layering machinery + L2 content for the 4 base roles (pm/qa/dm/dev) + L3 stubs for all 20 variants + L4 stubs for all 4 base roles + 1 shared L4 stub. **Variant-specific L3 content and install-specific L4 content are deferred to the human / follow-up issues.** The user's iOS-dev example is illustrative of what L3 will eventually hold; L4 stubs are intentionally empty so the human can fill them later.

---

## Locked Decisions

### D1 — L1 is awareness, not prohibition (LOCKED, human correction 2026-05-22 #1)

L1 file `references/sub-skills/common/agent-boundaries.md` contains:

1. A single short instruction: *"Know each other's responsibilities. When you decline work that isn't yours, route accurately — name the role and the reason. Bare 'not my domain' is not enough."*
2. A compose-time marker (`{{role-roster}}`) where compose.py injects auto-generated summaries of every role.

L1 explicitly does NOT contain: a cross-role rules table, per-role prohibitions, or strict `DO NOT` directives about other agents' work. Those belong in L2.

### D2 — Source of truth for L1 roster is manifest.yaml (LOCKED, F2 fixed)

`compose.py` reads each role's `references/roles/<role>/manifest.yaml` and extracts:
- `id` — manifest identifier (e.g., "pm", "qa", "dm", "dev"). Used as the stable sort key in D8.
- `display_name` — short label (e.g., "PM", "QA", "DM", "Skill").
- `tagline` — one-line role purpose (e.g., "Coordinates the team and talks to you").
- `description` — multi-line responsibility statement (domain-terms only per existing manifest discipline).

**Source filter (F4 lock)**: roster includes ONLY the roles active in this install's `config.md` — not every manifest under `references/roles/`. Rationale: the L1 roster is for operational awareness ("know your actual teammates on this install"), not architectural documentation. A manifest existing for an uninstalled role would clutter the roster with phantom teammates. New installs that add a role pick it up automatically via their `config.md`.

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

### D6a — L3 is variant-specific narrowing; stubs in v1 (LOCKED)

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

### D6b — L4 is install-specific human overrides; stubs in v1 (LOCKED, human correction 2026-05-22 #3)

L4 already has a working mechanism in `compose.py:393–419`. Files at `.squidsquad/project/<prefix>-<topic>.md` are auto-included into the matching role's composed CLAUDE.md based on filename prefix:

- `<role-identity>-*.md` — included for the matching role only (e.g., `pm-responsibility.md` → only PM's CLAUDE.md).
- `shared-*.md` — included for all roles.
- Unprefixed `*.md` — included for all roles.

**Filename-prefix routing semantics** (per compose.py:404–410, locked F5 fix — fourth case added):
- `<role-identity>-*.md` (prefix matches a known role identity in `{dev, dm, pm, qa}`) — included for that role only.
- `shared-*.md` — included for all roles.
- Unprefixed `*.md` (no hyphen in filename) — included for all roles.
- `<unknown-prefix>-*.md` (prefix has a hyphen but doesn't match any known role identity, e.g., `setup-upgrade-gate.md`) — included for all roles. *This case is implicit in the compose.py code path but undocumented in the original D6b draft; called out explicitly so future L4 authors don't expect role-scoping from arbitrary prefixes.*

NEW L4 stub files for this task (placed in BOTH `references/sub-skills/project/` as seed templates AND `.squidsquad/project/` as live stubs for THIS install):

- `pm-responsibility.md` — install-specific PM responsibility additions/narrowings.
- `qa-responsibility.md` — install-specific QA responsibility additions/narrowings.
- `dm-responsibility.md` — install-specific DM responsibility additions/narrowings.
- `dev-responsibility.md` — install-specific dev responsibility additions/narrowings.
- `shared-responsibility.md` — install-specific cross-role responsibility additions (applies to all 4 roles).

5 new L4 files. All ship as STUBS in v1. Stub content (locked template):

```markdown
# <Role-Or-Shared> — Install-specific responsibility additions (L4)

No install-specific responsibility additions for <role-or-shared> at this time.

To add: replace this stub with directives in the same shape as L2 (`What this role does / does NOT do / Why`),
or freeform install-specific notes about responsibility scope. Content here is appended to <role>'s
composed CLAUDE.md after L1, L2, and L3 — operator intent is the most specific layer.

<!-- L4 stub for #9925 — fill in to spell out install-specific role responsibilities -->
```

L4 stubs use the EXISTING compose mechanism. No new compose.py logic is required for L4 — the existing project-skills loader at compose.py:393–419 already discovers files by filename prefix.

`wizard.py` updates to copy L4 responsibility stubs from `references/sub-skills/project/` to `.squidsquad/project/` for new installs is OUT OF SCOPE for this task. The seed templates exist for future install/upgrade flows; this install gets the live stubs hand-placed in `.squidsquad/project/` by skill at pickup. Future installs may copy from seed manually until a follow-up issue (#9925-followup-wizard) automates it.

### D7 — compose.py changes (LOCKED)

Four changes to `compose.py` (L4 needs zero changes — existing mechanism handles it). The wiring requires BOTH manifest entries (which roles' compose pipelines include the file) AND template directives (where in the composed output the file appears) — DS F1 (compose wiring) was missed in earlier drafts because the directive half was implicit:

1. **L1 fragment — manifest + directive** — Each role's `references/roles/<role>/includes.yml` AND `includes-events.yml` adds `common/agent-boundaries` to the `includes:` list. AND `references/roles/<role>/instructions.md` gains a `{{include: common/agent-boundaries}}` directive at the position the L1 awareness content should appear in the composed output (recommended placement: near the top, after the "## Your Responsibilities" section).

2. **L2 fragment — manifest + directive** — Each role's `references/roles/<role>/includes.yml` AND `includes-events.yml` adds `roles/<role>/responsibility` to the `includes:` list. AND `references/roles/<role>/instructions.md` gains a `{{include: roles/<role>/responsibility}}` directive at the position the L2 general-responsibility content should appear (recommended placement: immediately after the L1 directive).

3. **Role-roster injection** — New compose-time logic, runs AFTER `_resolve_includes_with_manifest` returns the fully-resolved content (F6 lock — post-processing stage, not a new directive type, so the marker won't tangle with the existing `{{include:}}`/`{{runtime:}}`/`{{capability:}}` resolvers and won't fire if `{{role-roster}}` appears inside a code block in an unrelated file):
   - Read this install's `config.md` to determine the list of active role ids (F4 lock — active-only, not all manifests).
   - For each active role id, read `references/roles/<id>/manifest.yaml` and extract `id`, `display_name`, `tagline`, `description`.
   - Sort the extracted entries alphabetically by `id` (D8 stable order).
   - Render them into a markdown roster block (format below).
   - Scan the post-resolve content for the literal token `{{role-roster}}` and replace each occurrence with the rendered roster block. If the token is absent, emit a stderr warning and continue (D8 degraded mode).

4. **No changes needed for L3 or L4** — L3 stubs are passive files not included via `additional_includes`. L4 stubs use the existing project-skills loader at compose.py:393–419 (filename-prefix routing per D6b).

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
  - EXACTLY ONE rendered roster entry per active role from this install's `config.md` (F4 lock — roster sourced from config.md, not from all manifests). For the current install with `config.md` listing `Dev Agents: skill` + the mandatory PM/QA/DM, the roster MUST contain exactly 4 entries (one per: pm, qa, dm, dev). Roles whose manifests exist but are not active in `config.md` MUST NOT appear.
  - The role's OWN L2 responsibility.md content (literal match for the role's "What this role does" header).
  - The role's OWN L2 responsibility.md "What this role does NOT do" section.

- **AC5** — Four L2 `responsibility.md` files exist at `references/sub-skills/roles/{pm,qa,dm,dev}/responsibility.md`. Each matches the D4 template structure (has all three required sections: "What this role does", "What this role does NOT do", "Why this matters") with at least 3 bullets in each of the first two sections.

- **AC6** — All 10 memory entries listed in D5 are absorbed into the indicated L2 file with HTML-comment lineage tags (`<!-- absorbed from feedback_X -->`). Verification: grep for each lineage tag in the predicted file.

- **AC7** — All 20 L3 stub files at `references/roles/<role>/<variant>/responsibility.md` exist and match the D6a template (literal string match for "No variant-specific responsibility narrowing"). None are wired into `additional_includes`.

- **AC8** — All 5 L4 stub files exist as seed templates at `references/sub-skills/project/{pm,qa,dm,dev,shared}-responsibility.md`, AND the same 5 files exist as live stubs at `.squidsquad/project/{pm,qa,dm,dev,shared}-responsibility.md`. Each matches the D6b template (literal string match for "Install-specific responsibility additions").

- **AC9** — Compose pickup of L4 stubs is verified: running `compose.py deploy pm` produces a composed CLAUDE.md that contains:
  - The PM-specific L4 content from `.squidsquad/project/pm-responsibility.md` (under a `<!-- sub-skill: project-pm-responsibility -->` marker per existing compose conventions).
  - The shared L4 content from `.squidsquad/project/shared-responsibility.md` (under a `<!-- sub-skill: project-shared-responsibility -->` marker).
  - Does NOT contain QA/DM/dev-specific L4 content (filename-prefix filtering).

- **AC10** — Compose ordering is stable when `agent_compose` is disabled (F3 lock): running `compose.py deploy pm` twice with no source changes AND `agent-compose: no` (or absent) in `config.md` produces byte-identical output. When `agent-compose: yes` is set, byte-identical stability is not guaranteed because the LLM coherence polish at compose.py:806–890 is inherently non-deterministic. AC10's test MUST run with `agent_compose` disabled — either by toggling `config.md` for the test run, or by passing a future test-only flag if one is added.

- **AC11** — Compose degraded modes per D8 work without crashing: missing `tagline`/`description` produces warnings + valid output; missing `display_name` produces a build error with exit code != 0; missing role `responsibility.md` (L2) produces a warning + valid output for other roles; missing L4 stub files do not crash compose (existing behavior — L4 files are optional).

- **AC12** — Regression test at `tests/test_agent_boundaries.py` covers: (a) AC4 across all 4 roles, (b) AC6 lineage tags, (c) AC7 L3 stub files, (d) AC8 L4 stub files present in both seed + live locations, (e) AC9 L4 prefix-filtered inclusion in composed output, (f) AC10 byte-identical re-runs, (g) AC11 degraded modes.

---

## Out of Scope

- **Variant-specific L3 content** (e.g., iOS dev's testing pyramid scope) — deferred to follow-up issues per variant. The iOS dev example in the user's direction is illustrative of what L3 will eventually hold, not a deliverable here.
- **Install-specific L4 content** — the L4 stubs ship empty by design; the human fills them when they want install-specific direction. No L4 content is shipped in v1.
- **`wizard.py` automation of L4 stub copying** for new installs — out of scope. v1 places stubs in `.squidsquad/project/` by hand (skill at task pickup). A follow-up issue can wire the wizard's L4 copying step to include the new responsibility templates.
- Auditing or revising any role's manifest `description` field — that's per-manifest hygiene.
- Drift detection between L2 `responsibility.md` and manifest `description` — both can describe the role; manifest is the outward-facing summary, L2 is the inside view. They can diverge in detail without conflict.
- Restructuring existing L2 files (`prohibitions.md` consolidation, `instructions.md` "Your Responsibilities" section refactor) — out of scope.
- Removing absorbed memory entries from `MEMORY.md` — additive only; memory layer is a separate concern.
- Tooling enforcement (linter for finger-pointing patterns) — possible future issue.

---

## Why earlier CONTEXT-9925.md drafts were wrong

**Draft 1** (pre-human-correction-1): framed L1 as a restrictive N×N role × responsibility table with strict cross-role prohibitions. Wrong because L1 is for *awareness*, not *restriction*; restrictions belong in L2.

**Draft 2** (post-correction-1, pre-correction-2): correctly reframed L1 as awareness + roster propagation, but left L2 underspecified ("existing files unchanged") and L3 as pointer-only stubs. Wrong because L2 is supposed to carry the role's general responsibility statement — which doesn't have a clean home in the existing L2 files. A new `responsibility.md` per role is needed.

**Draft 3** (post-correction-2, pre-correction-3): three-layer model with explicit content shapes at each layer. Wrong because it missed L4 — the install-specific layer that `compose.py` already supports for human-authored overrides.

**This draft** (post-correction-3): FOUR-layer model. L1 propagates manifest summaries (awareness). L2 carries each role's general scope contract in a new `responsibility.md`. L3 has variant-specific stubs (real content in follow-ups). L4 has install-specific human-authored stubs (5 new files in `.squidsquad/project/`, leveraging the existing L4 mechanism in compose.py). All four layers stub-ready so the human can spell out role responsibilities at whichever specificity level they need.

---

## DS Review Findings — Resolution Map (Draft 2/3 review)

| Finding | Severity | Resolution |
|---|---|---|
| F1 (compose wiring missing) | error | D7 items 1+2 now cover BOTH manifest entry AND `{{include:}}` directive in instructions.md (DS-v4 F1 fix) |
| F2 (L3 path ambiguity) | error | D6a specifies `references/roles/<role>/<variant>/` (variant tree) |
| F3 (top-N not testable) | warning | Moot — no top-N enumeration in new design |
| F4 (referenced OR absorbed) | error | D5 locks ABSORB into the categorized L2 file (responsibility.md or prohibitions.md) |
| F5 (no seam-coverage AC) | warning | Moot — seams emerge from L2 "What this role does NOT do" + L1 roster, not from a handwritten table |
| F6 (skill is variant, not peer) | warning | Moot — compose reads `config.md` active roles, agnostic |
| F7 (L3 stub spec missing) | warning | D6a specifies filename + content + non-wiring |

## DS Review Findings (v4 review, post-correction-3) — Resolution Map

| Finding | Severity | Resolution |
|---|---|---|
| v4-F1 (D7 missed `{{include:}}` directive half of wiring — same root cause as original F1) | error | D7 items 1+2 expanded: manifest entry AND directive in `instructions.md` |
| v4-F2 (`id` not in D2 extraction list but referenced in D8 sort) | warning | D2 now extracts `id` explicitly |
| v4-F3 (AC10 byte-identical broken by `agent_compose` LLM polish) | warning | AC10 locks "agent_compose disabled" as precondition |
| v4-F4 (AC4 vs D7 inconsistent roster source — config.md vs all-manifests) | warning | D2 + D7 + AC4 lock "active roles from config.md" |
| v4-F5 (D6b missed fourth L4 routing case — unknown-prefix → all roles) | warning | D6b now lists all 4 prefix-routing cases explicitly |
| v4-F6 (D7 didn't specify pipeline stage for `{{role-roster}}` substitution) | warning | D7 item 3 locks post-`_resolve_includes_with_manifest` stage |
