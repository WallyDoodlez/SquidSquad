# FEAT-328 Context — Intent-driven setup wizard with role manifest registry

## Scope

Replace the dev-shaped setup flow with an intent-driven wizard that composes teams from a role manifest registry. PM and DM are always installed. Other roles are added based on user intent via curated presets.

This feature ships:
- A role manifest registry at `references/roles/<role>/manifest.yaml` covering 6 v1 roles
- A new setup wizard in SKILL.md that asks intent first and resolves the pipeline from manifests
- Two presets: `software-dev` and `design`
- A pipeline resolver that walks `routes_to` lists, skipping uninstalled roles
- Refactor of `compose.py`, `config.py`, and PM CLAUDE.md to remove hardcoded role names where the manifest registry can serve

## Locked Decisions (human decided 2026-04-11)

### From initial discussion
1. **Single feature** (not three) — manifest schema + wizard + presets ship together
2. **PM always installed** — the human's entry point
3. **DM always installed** — produces the actual delivery output (Google Drive, email, file export)
4. **Roles SquidSquad-defined for v1** — users customize variation via SOUL.md only. Custom user-defined roles deferred.
5. **Two presets v1**: `software-dev` and `design`
6. **YAML sidecar manifests** at `references/roles/<role>/manifest.yaml` (not frontmatter)
7. **Per-role decentralized `routes_to`** — no central graph file
8. **GitHub Issues ingestion default flipped to `Y`** in setup
9. **Conditional dev question** — only ask BE/FE/Fullstack if intent involves software
10. **Install base = this repo only (CORRECTED 2026-04-11)** — earlier "no install base" was wrong. SquidSquad's own repo IS the install base. Bounded migration: relabel this repo's existing GH Issues, update template references, but no external user installs to worry about.

### From Phase 2 discussion (10 decisions)

11. **Q1 — DM as universal terminal**: Append `dm` to every shipped manifest's `routes_to`. Decentralized, walker stays simple, no special cases. Example: `designer: routes_to: [dev, qa, dm]`, `qa: routes_to: [dm]`, `dev: routes_to: [qa, dm]`.

12. **Q2 — Schema versioning**: Every manifest YAML must have a top-level `schema_version: 1` field. Validator warns on mismatch, errors on unknown version.

13. **Q3 — Dev manifest shape**: Single `references/roles/dev/manifest.yaml` with `setup_questions.variant` field listing be/fe/fullstack. DRY — `routes_to: [qa, dm]` lives in one place. Resolver matches "dev family" to any installed variant.

14. **Q4 — Fullstack default**: Default `software-dev` preset to `be+fe` (two agents). Offer `fullstack` (one combined `dev` agent) as a secondary option in the variant question. Preserves today's default — no regression for existing users. Pipeline display defaults to `PM → Designer → [BE, FE] → QA → DM`.

15. **Q5 — PM → DM direct routing**: Runtime only via resolver fallback. **No third preset.** When the resolved install collapses to `[pm, dm]`, the wizard shows a friendly hint ("Just PM + DM? That's a planning + delivery team — perfect for proposals, briefs, and project plans"). Promote to dedicated preset in v2 if popular.

16. **Q6 — Custom-builder mode**: **Defer entirely to v2.** Honors the "two presets v1" lock. Document the workaround in README: users wanting a custom shape run the closest preset and hand-edit `config.md` + delete unwanted directories. v2 candidate.

17. **Q7 — Designer HITL loop (HUMAN OVERRIDE, REVISED 2x)**: Drop the `design-review` role idea entirely. Designer iterates with the human directly via a **HITL self-loop**. v1 role count stays at **5**: pm, dm, designer, dev (with variants), qa.

   **HITL mechanic** (corrected — designer NEVER pauses):
   - Each designer cycle, in the triage step, designer checks `pending-human` items assigned to itself **first** (priority over new approved features).
   - For each `pending-human` item, designer reads the issue's comments. If a new human comment exists since the designer's last comment on that issue, designer picks it up:
     - Transition `pending-human → in-progress`
     - Iterate on the design based on the human's feedback
     - Re-present (new tool output + new comment with link)
     - Transition `in-progress → pending-human` again
   - Designer moves on to the next pending-human item, or to the next approved feature, or ends the cycle. **Never blocks.**
   - Multiple `pending-human` items can be in flight simultaneously. Designer walks them in priority order each cycle.

   **Manifest representation**:
   - New manifest field: `iteration_mode: hitl`
   - Designer's `routes_to: [pm, dm]` (PM picks up after human approval, DM is the Q1 terminal fallback)
   - Wizard renders the design pipeline as `PM → Designer ↻ → DM` (the `↻` symbolizes HITL)

   **New status label**: `pending-human`
   - Added to the legal-transitions table in `tracker.py`
   - Legal transitions:
     - `in-progress → pending-human`
     - `pending-human → in-progress` (redirect from human)
     - `pending-human → pending-ship` (approval from human)
   - Updated in PM/skill/designer CLAUDE.md transition references

   **Designer produces designs, NOT specs (HUMAN OVERRIDE 3)**: Designer creates designs via an **external connected design tool** (Figma MCP, Google Stitch, etc.), not by writing markdown specs. Output lives in the external tool. Designer only posts a **link/reference** to the design in the issue comment thread. The `.squidsquad/designer/specs/` directory may exist as a thin index mapping `issue_number → tool URL` but the actual design artifact is always in the external tool.

   **HITL approval/redirect detection**:
   - Approval keywords (case-insensitive): `approved`, `approve`, `lgtm`, `ship it`, `looks good`
   - Anything else that's not an approval keyword counts as a redirect
   - Bot-author comments (PM, designer itself) are ignored when scanning for human input
   - First-cycle dev discretion: skill agent picks the exact approval-detection algorithm (regex, comment author check, label-based, etc.)

18. **Q8 — Re-running setup with existing `.squidsquad/`**: Three-way prompt:
   - **(1) Abort** (default, Enter key) — safe no-op
   - **(2) Regenerate templates only** — delegates to `/squidsquad-upgrade`
   - **(3) Full rebuild** — nukes `.squidsquad/` after typed confirmation. Warns about loss of working state, iteration logs, vault content.

19. **Q9 — Intent parser (HUMAN OVERRIDE)**: **LLM sub-prompt only**. The wizard runs inside Claude, so the LLM call is free. Wizard asks Claude to classify the free-text answer into `software-dev | design | unclear` with a short prompt. No local matcher. If `unclear`, fall through to manual preset picker.

20. **Q10 — Pipeline display**: ASCII arrow with bracket notation: `PM → Designer → [BE, FE] → QA → DM`. One-line, screenshot-friendly, matches the research doc's notation. Brackets handle parallel groupings. HITL roles are marked with `↻` (e.g. `PM → Designer ↻ → DM`).

### From Phase 2 follow-up discussion (4 new decisions: tool requirements + status taxonomy)

**Q-new4 — Status taxonomy clarity**: Any status that requires a HUMAN to act must have `human` explicitly in the name. Two human-required statuses:

- **`pending-human-approval`** (rename of today's `pending`) — first approval gate. Human decides: plan this feature (→ `planning`) or execute it directly (→ `approved`).
- **`pending-human-review`** (new, for HITL roles like designer) — human reviews an in-progress iteration. Human decides: approve and ship (→ `pending-ship`) or redirect (→ `in-progress`).

Existing `pending-test` and `pending-ship` stay unchanged — they are agent-driven (QA verifies, DM delivers), no human required.

Future "agent-on-agent" review statuses follow the same naming convention: `pending-agent-review`, `pending-agent-approval`, etc. The `human` / `agent` infix makes the actor explicit at a glance.



21. **Q-new1 — Universal `requires_tools` manifest field**: Every role manifest can declare `requires_tools` with `any_of` / `all_of` lists. Wizard validates tool availability at install time by inspecting the host Claude session's available MCP servers. This is a first-class manifest field, not a designer-only special case. Future roles (DM with delivery tools, marketers with analytics, etc.) use the same mechanism.

   **Schema**:
   ```yaml
   requires_tools:
     any_of:
       - figma_mcp
       - google_stitch
     all_of: []  # roles can require multiple tools simultaneously
   ```

   **Tool identifier convention**: Lowercase, snake_case, matches the MCP server name as registered in Claude (e.g., `figma_mcp`, `gmail_mcp`, `slack_mcp`). Validator does a fuzzy match against the registered MCP servers.

22. **Q-new2 — Missing tool behavior**: If a role's `requires_tools` cannot be satisfied at install time, the wizard **refuses to install the role** and prints a clear message:
   ```
   Designer requires one of: figma_mcp, google_stitch
   None are available in this Claude session.
   To install Designer, add one of these MCPs to Claude (see Claude docs)
   then re-run /squidsquad-setup.
   Skipping Designer for this install.
   ```
   - Strong invariant: a role only installs if it can actually function
   - The wizard continues with the rest of the preset (other roles still install)
   - If the missing tool is for a **required** role of the preset (not optional), the wizard prompts the user: abort install entirely, or fall back to a degraded preset
   - **Re-run handling**: when user re-runs setup with a tool that wasn't available before, the three-way prompt (Q8) gains an implicit fourth path: "regenerate to add newly-available roles"

23. **Q-new3 — v1 designer tool support (REVISED — added HTML fallback)**: Designer's `requires_tools.any_of` lists **figma_mcp**, **google_stitch**, and **local_html** for v1. Other tools (Penpot, Sketch, web-fetch, etc.) deferred to v2.
   - If the user has multiple of these installed/available, wizard asks which to use as the designer's primary tool (single-select)
   - The chosen tool ID is written to `config.md` under a new section: `## Tools` → `- **designer**: figma_mcp`
   - Designer's CLAUDE.md template is composed with tool-specific sub-skills: `references/sub-skills/designer-tools/figma.md`, `references/sub-skills/designer-tools/stitch.md`, `references/sub-skills/designer-tools/html.md`. Only the chosen tool's sub-skill gets composed in.

   **`local_html` is a built-in capability, not an MCP**: It requires no external server. The designer agent uses Read/Write/Edit to produce HTML/CSS/JS files at `.squidsquad/designer/designs/<issue-number>/index.html` (and supporting assets). The HITL link posted in the issue comment is a relative path or `file://` URL pointing to the local HTML file. Human opens it in a browser to review.

   **Tool identifier convention update**: A tool ID can refer to either:
   - An external MCP server (e.g. `figma_mcp`, `google_stitch`) — the validator inspects the host Claude session's MCP servers
   - A built-in capability (e.g. `local_html`) — always considered "available" by the validator, requires no external setup

   **Practical consequence**: Because `local_html` is always available, **designer can always install in v1**. The Q-new2 "refuse install" path never fires for designer. The path is reserved for future roles whose tool requirements have no built-in fallback (e.g. DM with delivery tools, where there's no "local fallback" for sending email).

   **HTML sub-skill scope** (`references/sub-skills/designer-tools/html.md`):
   - Folder structure: `.squidsquad/designer/designs/<issue>/index.html` + sibling assets
   - Use semantic HTML, inline CSS or one stylesheet per design
   - No build step, no framework, no JS bundler — plain HTML is the deliverable
   - Designer can include reference screenshots, mood boards, etc. as sibling files
   - Comment in issue references the local path: `Iteration 1: see designs/42/index.html`
   - Human opens the file directly in their browser; redirects via issue comment

### Implications for the v1 work

- Manifest schema gets a new top-level field `requires_tools` (Q-new1)
- Manifest schema gets a new top-level field `iteration_mode: hitl | normal` (Q7)
- Validator (`references/scripts/manifest.py`) gains MCP-availability detection — needs to enumerate the host Claude session's MCP servers (mechanism TBD, dev discretion). Built-in capabilities like `local_html` always pass.
- Wizard gets a tool-selection sub-step for roles with multiple satisfying tools (Q-new3)
- New sub-skill files: `references/sub-skills/designer-tools/figma.md`, `references/sub-skills/designer-tools/stitch.md`, `references/sub-skills/designer-tools/html.md`
- Designer's `references/roles/designer/` template directory needs new structure to support tool-conditional composition
- `config.md` schema gains a `## Tools` section
- New status labels: `status:pending-human-approval` and `status:pending-human-review`
- Existing `status:pending` is renamed → `status:pending-human-approval` (migration in this repo only)
- tracker.py legal-transitions table updated to include both new transitions and remove old `pending` references
- Test plan must cover: tool present (install succeeds), tool missing (install refused with clear message), both tools present (selection prompt), tool removed after install (re-run wizard prompt), HITL designer iterating on a real issue with figma/stitch/html tools, status migration script idempotency

## v1 Role Inventory (final, REVISED)

| Role | Always installed | Presets | iteration_mode | routes_to | requires_tools |
|------|------------------|---------|----------------|-----------|----------------|
| pm | yes | both | normal | [designer, dev, qa, dm] | none |
| dm | yes | both | normal | [] (terminal) | none in v1 (TBD: delivery tools come later) |
| designer | optional in software-dev, required in design | both | **hitl** | [pm, dm] | `any_of: [figma_mcp, google_stitch, local_html]` |
| dev (be/fe/fullstack variants) | required in software-dev only | software-dev | normal | [qa, dm] | none |
| qa | auto-installed when dev is installed | software-dev | normal | [dm] | none |

**Total v1 roles: 5** (no design-review)

**Resolved pipelines:**
- `software-dev` default (with designer): `PM → Designer ↻ → [BE, FE] → QA → DM`
- `software-dev` no designer: `PM → [BE, FE] → QA → DM`
- `software-dev` fullstack: `PM → Designer? ↻ → Dev → QA → DM`
- `design`: `PM → Designer ↻ → DM`
- minimal (any preset, decline all optionals): `PM → DM`

**Note on `↻`**: The `↻` glyph in the pipeline display indicates a HITL role — that role iterates with the human via issue comments before handing off. Hovers / tooltips not in scope for v1; the glyph is documented in README.

## Dev Discretion (skill-lead can choose)

- Manifest YAML field naming details (as long as `schema_version`, `name`, `routes_to`, `setup_questions`, `template_refs` exist)
- Validator implementation (Python in `references/scripts/manifest.py` is the obvious choice)
- Resolver algorithm details (recursion vs iteration, cycle detection mechanism)
- Wizard UX prose (prompts, error messages, hints)
- LLM sub-prompt wording for intent classification
- Where to store the `routes_to` traversal logic (`manifest.py`, new file, or inline in `compose.py`)
- Whether `design-review` reuses parts of QA's CLAUDE.md template or is fully standalone (recommend mostly standalone with shared sub-skills where they apply)

## Side Effect Mitigations (required)

From RESEARCH.md §5:

1. **Removing hardcoded role refs in PM CLAUDE.md** — refactor must preserve all existing PM behavior. Test: run a full PM cycle on the `software-dev` preset and verify all 11 hardcoded sites still work.
2. **`compose.py` dispatch tables** (lines 100-106, 166-167, 201-214) — replace with manifest lookups. Add a unit test that loads each shipped manifest and verifies compose.py can still produce a valid CLAUDE.md for each role.
3. **`config.py` FIELD_MAP** (lines 26-52) and **`sync_agents()`** (line 162) — must stay backward compatible with config.md files written by the new wizard. Document the new config.md schema in CONTEXT.
4. **`statusline.sh` agent loop** — must read installed roles from manifest, not hardcoded list. Test: install design preset and verify status line shows pm/designer/design-review/dm.
5. **Manifest validation at setup time** — malformed YAML must fail loudly with line number and field name. Never silent fallback.
6. **Cycle detection in resolver** — even though no v1 manifest creates cycles, the resolver must detect and reject `routes_to` loops to prevent future bugs.
7. **`design-review` is a brand new role** — boot scripts (`start-role.sh`/`ps1`) must work with it without changes (already parameterized via `[ROLE]`).

## Upgrade Path

**Bounded migration: this repo only.** SquidSquad's own repo is the single install base for v1. Migration tasks:

1. **GH Issue label migration**: Rewrite all open + closed issues currently labeled `status:pending` to `status:pending-human-approval`. Use a one-shot script in `references/scripts/migrate_status_labels.py` (or inline gh CLI commands). Check the count before and after to verify completeness.
2. **Label table update**: Add `status:pending-human-approval` and `status:pending-human-review` to the GH labels list. Remove `status:pending` after migration is complete and verified.
3. **tracker.py legal transitions**: Update the transitions table:
   - Old: `pending → planning | approved`
   - New: `pending-human-approval → planning | approved`
   - New: `in-progress → pending-human-review` (for HITL roles)
   - New: `pending-human-review → in-progress | pending-ship`
4. **Template/text references**: Find and replace `pending` (status context) with `pending-human-approval` across all CLAUDE.md files, sub-skills, SKILL.md, README, and references/scripts/. Be careful not to clobber `pending-test`/`pending-ship` references.
5. **Working-state and iteration log references**: Update format docs but do NOT rewrite existing iter-N.md files (history is preserved as-is).
6. **`/squidsquad-upgrade` flow**: v1 of upgrade does NOT need to learn manifests (manifests are setup-time only, frozen into config.md). But upgrade DOES need to handle the new label namespace if any external install ever exists (none today).

**Migration ordering** (important to avoid breakage):
1. First add the new labels (`pending-human-approval`, `pending-human-review`) — additive, no breakage
2. Update tracker.py to accept both old and new transitions during a transition window
3. Run the issue migration script (rewrites labels)
4. Update templates and CLAUDE.md files
5. Remove `pending` label and the transition-window code in tracker.py
6. Verify with a full PM cycle that nothing references the old label

Future-upgrade consideration: when manifest `schema_version` bumps to 2 (post-v1), `/squidsquad-upgrade` will need to migrate manifests. Out of v1 scope.

## Out of Scope

- User-defined custom roles (future feature)
- Role variation derivatives (PM-marketing, Dev-firmware) — future feature, captured in #328 body
- Custom-builder wizard mode (v2 — see Q6)
- Third preset for `planning-delivery` workflow (v2 — see Q5)
- Migration of any existing installs (no install base)
- Marketing / research / content presets (v2)
- A `modify team` post-setup mode (v2 — captured in Q8)
- LLM intent classifier running outside Claude (only inside-Claude wizard supported)
- `references/scripts/manifest.py add-role` post-setup script (v2 — see Q6)

## Phase 3 — Test Planning

Test plan subagent will read this CONTEXT.md and produce `FEAT-328-TEST-PLAN.md` covering:
- Happy path for both presets (software-dev with be+fe, design with new design-review)
- Variant question coverage (be+fe / fullstack / be only / fe only)
- DM-as-terminal walker resolution for [pm, designer, dm] case
- Re-run setup three-way prompt (abort default, upgrade path, full rebuild)
- LLM intent classifier with three test inputs (software, design, unclear)
- Schema version validation (valid, missing, unknown)
- Malformed manifest YAML → loud failure
- Cycle detection in resolver (synthetic test manifest)
- design-review role end-to-end (pickup design:complete issues, verify against AC, route to DM)
- Regression: existing software-dev workflow still works
- ASCII arrow display rendering on PowerShell + bash

## References

- Research: `.squidsquad/skill/planning/FEAT-328-RESEARCH.md`
- Phase 2 prep: `.squidsquad/skill/planning/FEAT-328-PHASE2-PREP.md`
- Original feature filing: WallyDoodlez/SquidSquad#328
- Current setup flow being replaced: `SKILL.md` Step 1 (Gather Project Details) and Steps 2-6
