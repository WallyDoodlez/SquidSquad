# FEAT-328 Phase 2 Discussion Prep

Prepared from `.squidsquad/skill/planning/FEAT-328-RESEARCH.md` §10. Ten open questions, ordered for interactive discussion.

## How to use this doc

- Walk the questions in the recommended order below. Each question has three concrete options and a recommended answer with a short justification.
- When the human picks an option, mark it in the Phase 2 discussion notes and lock it into `FEAT-328-CONTEXT.md` as a locked decision for the dev agent.
- If the human picks differently from the recommendation, check the Dependencies section before moving on — some answers invalidate options on later questions.
- Q10 is the highest-priority lock: every shipped manifest's `routes_to` list depends on it. Do not leave Phase 2 without an answer.

## Question Order (recommended)

1. **Q10** — Universal-terminal rule for `routes_to` — blocks the resolver design and every shipped manifest; locking this changes the example manifests in §2.
2. **Q5**  — Manifest `schema_version` field — trivial lock, but gates the validator surface and every manifest's envelope.
3. **Q9**  — One dev manifest with variants vs separate manifests — shapes `references/roles/` layout; Q1 depends on this.
4. **Q1**  — Fullstack = one `dev` agent or two `be`+`fe` agents — depends on Q9's manifest shape; drives default pipeline display and config.md shape.
5. **Q6**  — PM → DM direct: runtime path or new preset — decides whether we have 2 or 3 presets; affects Q4.
6. **Q4**  — Custom-builder mode in v1 or v2 — scope-gate for the wizard; depends on Q6.
7. **Q7**  — QA's role in `design` preset (no code) — behavior-level; depends on the preset set from Q6.
8. **Q8**  — Re-running setup with an existing `.squidsquad/` — behavior, isolated but user-facing.
9. **Q2**  — Intent parsing: local matcher or LLM call — UX/implementation preference, not blocking.
10. **Q3**  — Pipeline display: ASCII arrow or list — pure UX preference, last.

## Dependencies

- **Q1 depends on Q9**: The dev manifest shape (single with variants vs multiple) determines what "fullstack" physically means. If Q9 = single manifest, Q1 is a variant-id question. If Q9 = separate manifests, Q1 is a "which manifest file ships" question.
- **Q4 depends on Q6**: If Q6 creates a third preset for PM→DM, custom mode is less urgent. If Q6 says "runtime only, two presets", the pressure for custom mode increases because users with a PM+Designer+QA+DM team (no dev) are not representable.
- **Q7 depends on Q6**: If `design` preset exists (Q6 = two presets), QA behavior in that preset must be defined. If Q6 introduces a third preset, Q7 may need to cover two design-like presets.
- **Q10 affects Q1, Q6, Q9**: The universal-terminal decision changes every shipped manifest's `routes_to`. Lock Q10 first so downstream manifest questions can reference the final shape.
- **Q3 has a weak dependency on Q1**: If Q1 picks "one fullstack dev", there are no parallel dev variants and bracket notation becomes decorative.

## Questions

### Q1 — Fullstack dev: one agent or two?

- **Category**: schema
- **Why this matters**: Affects the `dev` manifest's `setup_questions.variant` structure (§2 Example 3), the default pipeline display (`PM → Dev → QA → DM` vs `PM → [BE, FE] → QA → DM`), and what happens to features that span both halves. One agent = simpler wizard, solo-friendly, may context-thrash on mixed work. Two agents = matches today's default, clearer ownership, heavier setup.
- **Options**:
  - **Option A**: Default `software-dev` to `be+fe` (two agents), offer `fullstack` (one `dev` agent) as a secondary choice. Pipeline default: `PM → [BE, FE] → QA → DM`. Matches current `Dev agents` default of `fe, be`.
    - Pros: Zero behavior change from today's setup default; preserves muscle memory for existing contributors; two agents means parallel work on FE and BE features; clean `role:fe` / `role:be` label routing.
    - Cons: Heavier setup (two boot terminals, two CLAUDE.md files); solo devs on small projects get overkill; feature-intake must decide FE vs BE for every issue.
  - **Option B**: Default to `fullstack` (one `dev` agent named `dev`), offer `be+fe` as opt-in. Pipeline default: `PM → Dev → QA → DM`.
    - Pros: Simpler default, one terminal, one CLAUDE.md, matches the mental model of a solo engineer; no routing ambiguity for mixed-stack features.
    - Cons: Breaks parity with today's default; single agent may thrash context between FE and BE files; no parallelism; renaming of the stored directory (`.squidsquad/dev/` not `.squidsquad/be/`) is a visible break.
  - **Option C**: Ask the user explicitly during the dev variant sub-question with no preset default — `[be+fe | fullstack | be only | fe only]`, forcing a conscious choice every install.
    - Pros: No assumption baked in; covers all four realistic shapes; self-documenting for new users.
    - Cons: One more mandatory question in the happy path; no "just press enter" experience for repeat setups.
- **→ Recommended**: **Option A** — preserves today's default so no regression for existing users, `fullstack` is available for solo projects. Research §10 Q1 already recommends this path and the codebase already supports multi-dev-agent teams.

### Q2 — Intent parser: local matcher or LLM?

- **Category**: ux
- **Why this matters**: Local matcher is deterministic, offline, fast (under 1ms), unit-testable. LLM call is smarter on ambiguous input but adds latency and depends on the caller being inside a live Claude session. Since setup runs inside Claude already, an LLM "call" is just a sub-prompt.
- **Options**:
  - **Option A**: Local keyword matcher only — `software|code|app|api|backend|frontend|full.?stack|cli|library|skill` suggests `software-dev`, `design|ui|ux|brand|visual|spec|prototype` suggests `design`, else show the preset picker. ~30 lines of Python in `manifest.py` or inline in SKILL.md.
    - Pros: Deterministic and testable; offline-capable; no dependency on the host being Claude; easy to mock in tests; cheap to extend.
    - Cons: Fails on ambiguous or non-English input; keyword list will drift from reality over time; "I want to build a SaaS" matches nothing and falls through to menu.
  - **Option B**: LLM sub-prompt only — the wizard asks Claude (the host session) to classify the free-text answer into `software-dev | design | unclear` with a short prompt and confidence score.
    - Pros: Handles ambiguous/natural language; no keyword list to maintain; scales to new presets trivially; setup is already inside Claude so this is free.
    - Cons: Nondeterministic; hard to unit-test without mocking a model; if wizard is ever run outside Claude (future CLI), this breaks; adds a thinking pause in the UX.
  - **Option C**: Hybrid — local matcher runs first, falls through to LLM classification only when the matcher returns no hit. LLM result is then shown as a suggestion (not auto-accepted).
    - Pros: Fast path for obvious cases, smart fallback for ambiguous ones; tests can cover the matcher branch without mocking LLM; degrades gracefully if LLM unavailable.
    - Cons: Two code paths to maintain; branch coverage in tests needs both; minor complexity tax.
- **→ Recommended**: **Option C** — hybrid gives deterministic tests for the common path and smart handling for the "I want to build a SaaS" case. The LLM branch is trivial to implement inside a Claude-hosted wizard and degrades to menu-picker if unavailable.

### Q3 — Pipeline display: ASCII arrow or list?

- **Category**: ux
- **Why this matters**: This is the final wizard summary the user sees before confirming. ASCII arrow tells a flow story but breaks layout for parallel groups. List is flat but loses the sequencing signal.
- **Options**:
  - **Option A**: ASCII arrow with bracket notation for parallel groups: `PM → Designer → [ BE, FE ] → QA → DM`.
    - Pros: One-line output; matches the mental model in the research doc; shows flow direction explicitly; brackets handle parallelism cleanly.
    - Cons: Unicode arrow may render poorly in some PowerShell hosts (low risk with modern terminals); brackets are a learned convention.
  - **Option B**: Numbered list with indent for parallel:
    ```
    1. PM
    2. Designer
    3. BE + FE (parallel)
    4. QA
    5. DM
    ```
    - Pros: Scans vertically; no arrow glyph concerns; self-evident sequence; readable in all terminals.
    - Cons: Five lines instead of one; loses the "flow" visualization; "parallel" parenthetical is wordy.
  - **Option C**: Both — show the one-line arrow as the headline and the numbered list below it for clarity.
    - Pros: Best of both; arrow as the quick-read, list as the detail; final confirmation screen has room for both.
    - Cons: Redundant; six lines instead of one or five; mildly over-engineered for a confirmation screen.
- **→ Recommended**: **Option A** — matches the research doc's own notation, fits on one line for screenshots and docs, and the Unicode arrow rendering concern is trivially mitigated (we already use emoji squids in status lines).

### Q4 — Custom-builder mode in v1 or v2?

- **Category**: scope
- **Why this matters**: Locked decisions say "two presets v1" which implies no custom mode. But a PM+Designer+QA+DM team (no dev) is not expressible with either preset and is a real team shape. Adding custom mode = whole new wizard branch. Deferring = users must hand-edit `config.md`.
- **Options**:
  - **Option A**: Defer entirely to v2. Document the gap in README. If user needs a custom shape, they run setup with the closest preset and hand-edit `config.md` + delete unwanted directories.
    - Pros: Keeps v1 scope tight; locked decisions already say two presets; real user can always escape via manual edit; less test surface.
    - Cons: Users who want custom shapes get a rough edge; "hand-edit config.md" is fragile guidance; README gap admission is a minor wart on public launch.
  - **Option B**: Add `--custom` flag to the wizard for v1. After preset picker, let the user add/remove roles individually from the list of shipped manifests.
    - Pros: Expressive for all realistic team shapes today; no README gap; no hand-editing; aligns with the manifest-driven architecture.
    - Cons: New wizard branch (adds ~150 lines to SKILL.md); test matrix doubles (2 presets × 2 modes); "add/remove roles" UX needs design; scope creep against locked decisions.
  - **Option C**: Defer `--custom` but add a "modify team after setup" flow in v1 — `python references/scripts/manifest.py add-role <name>` that installs an additional role post-setup. No wizard branching.
    - Pros: Addresses the real use case (team evolves over time) without new wizard branches; lower test burden than Option B; gives users an escape hatch beyond hand-editing; aligns with re-run handling (Q8).
    - Cons: Two entry points (wizard for initial, script for additions) is a cognitive split; `add-role` needs its own validation and idempotency logic.
- **→ Recommended**: **Option A** — honors the "two presets v1" locked decision and keeps scope tight. The gap is real but small; document the workaround in README and promote Option B or C to a v2 backlog item. This is the path research §10 Q4 already recommends.

### Q5 — Manifest schema versioning?

- **Category**: compatibility
- **Why this matters**: Future SquidSquad versions may add required fields or rename keys. Without a version field, detecting drift requires heuristics. Adding it now is a single line; retrofitting later means every existing manifest must be touched.
- **Options**:
  - **Option A**: Require `schema_version: 1` as a top-level field in every shipped manifest from day one. Validator warns (not fatal) if version mismatch is detected; errors on unknown version.
    - Pros: Trivial to add (one line per manifest); future-proof; standard practice for YAML schemas; detectable via `grep`; costs nothing.
    - Cons: None of note — it's a freebie.
  - **Option B**: No version field; detect schema drift via presence/absence of fields in the validator.
    - Pros: One less required field in every manifest; no "bump version" step when schema grows.
    - Cons: Heuristic detection is fragile; "is this an old or new manifest with a typo" ambiguity; painful to retrofit.
  - **Option C**: Use a separate `references/roles/SCHEMA_VERSION` file that covers all shipped manifests at once, instead of per-manifest.
    - Pros: Single source of truth; one place to bump.
    - Cons: User-defined manifests (future) can't declare their own version; file is easy to forget to read; non-standard pattern.
- **→ Recommended**: **Option A** — it's a one-line addition to a schema that's already being written from scratch. Research §10 Q5 already recommends this and §2 already includes it. Lock it and move on.

### Q6 — PM → DM direct: runtime path or new preset?

- **Category**: scope
- **Why this matters**: Locked decision 6 says "PM routes to DM direct is valid (e.g., 'create a project plan and deliver it')" but doesn't specify the mechanism. Runtime = resolver already handles `[pm, dm]` via `routes_to` fallback; no new preset. New preset = a third shipped option (e.g. `planning-and-delivery`) with its own wizard path.
- **Options**:
  - **Option A**: Runtime only — no new preset. The resolver already walks `[pm, dm]` to a linear pipeline when nothing else is installed. User picks the `software-dev` or `design` preset and declines all optional roles, leaving PM + DM. Wizard may need a hint when the resolved install list is tiny ("Just PM + DM? That's fine — you'll get a planning + delivery team").
    - Pros: Zero new wizard surface; leverages existing `routes_to` fallback; keeps "two presets v1" honest; fastest path.
    - Cons: Getting to `[pm, dm]` requires picking a preset and saying "no" to everything else, which is clunky; hides a common use case behind a weird opt-out path.
  - **Option B**: Add a third preset `planning-delivery` that installs `[pm, dm]` only. Preset picker shows three options.
    - Pros: First-class support for the plan-and-deliver workflow; discoverable; three presets still small.
    - Cons: Third preset to document and test; "two presets v1" locked decision has to be revisited or stretched; preset-audit test needs a third snapshot; PM may need a lean variant for this preset (skips design routing entirely).
  - **Option C**: Runtime path, but add a wizard shortcut: after the intent question, if the free text matches `plan|deliver|document|spec|proposal`, suggest `[pm, dm]` directly and skip the preset picker.
    - Pros: Discoverable without a third preset; UX matches the use case; keeps manifest layer clean.
    - Cons: Adds a special-case branch to the intent parser; more test cases; blurs the "presets drive install" mental model.
- **→ Recommended**: **Option A** — matches locked decisions and research §10 Q6. The resolver already supports it; the wizard just needs to display a sensible summary when the install list collapses to `[pm, dm]`. If the plan-and-deliver use case gets popular, promote it to a preset in v2.

### Q7 — QA's role in `design` preset?

- **Category**: behavior
- **Why this matters**: QA's Ralph Loop runs `e2e-test` (empty in a design-only project) and "verify pending-test items" (still meaningful — verifying designer specs against acceptance criteria). But the cycle needs a design-aware lens, or QA will noop.
- **Options**:
  - **Option A**: No QA template change. QA's existing "no e2e command → skip" logic handles the empty-test case; the verification sub-skill already reads acceptance criteria and works on any artifact type. Lightly update `references/sub-skills/qa-specific/verification.md` to explicitly mention "design spec verification" as a valid lens.
    - Pros: Minimal change; existing code paths work; single-sentence doc update; no new sub-skill; no new cycle step.
    - Cons: QA agents in design preset may not obviously know they should verify specs (doc nudge only); no dedicated design-verify lens.
  - **Option B**: Add a new QA sub-skill `qa-specific/design-spec-verification.md` that defines the design-verify lens (check spec completeness, token consistency, accessibility, traceability to acceptance criteria). Gate inclusion via manifest: only compose into QA's CLAUDE.md if designer is installed.
    - Pros: Explicit, discoverable lens; manifest-driven gating fits the FEAT-328 architecture; QA in a design preset has clear instructions.
    - Cons: New sub-skill file + gating logic in `compose.py`; more content to maintain; overlap with the existing verification sub-skill.
  - **Option C**: Split QA into two role manifests — `qa-code` and `qa-design`, installed by the respective presets. Each has its own sub-skill composition.
    - Pros: Clean separation; each preset's QA is purpose-built.
    - Cons: Two role manifests for one conceptual role; breaks the closed-set label invariant (`role:qa`); double the maintenance; overkill for v1.
- **→ Recommended**: **Option A** — lowest risk, matches research §10 Q7, and the existing verification sub-skill already covers spec verification if QA reads it. We gain discoverability by adding two sentences to the doc. If design-preset users report QA confusion, promote to Option B in v2.

### Q8 — Re-running setup with existing `.squidsquad/`?

- **Category**: behavior
- **Why this matters**: Locked decisions say "no install base" but users WILL re-run setup (fix a typo, add a role, switch presets). Wizard must do something sensible and safe — clobbering `.squidsquad/` silently loses work.
- **Options**:
  - **Option A**: Three-way prompt when `.squidsquad/` exists: (1) Abort (default, Enter key), (2) Regenerate templates only (delegates to `/squidsquad-upgrade`), (3) Full rebuild (nukes `.squidsquad/` after typed confirmation). Option 3 warns about loss of working state, iteration logs, vault.
    - Pros: Covers the three realistic intents; safe default (abort); reuses existing upgrade flow; typed confirmation for destructive path.
    - Cons: No "add a role without rebuilding" path; users who want to add designer to an existing `software-dev` install must hand-edit or full-rebuild.
  - **Option B**: Detect existing install and route entirely to `/squidsquad-upgrade`. Setup wizard refuses to run twice on the same repo.
    - Pros: Simplest logic; strong "one setup per repo" invariant; prevents accidental clobber completely.
    - Cons: Users who need a full rebuild have to manually `rm -rf .squidsquad/` first, which is the same thing with extra steps; doesn't help the "add a role" case.
  - **Option C**: Three-way prompt from Option A, plus a fourth option: (4) "Modify team" — runs a mini-wizard that lets the user add optional roles (designer, new dev variant) to the existing install without touching current config. Uses `config.py sync_agents()` to update the Agents list.
    - Pros: Covers all realistic re-run intents including the "I forgot designer" case; encourages incremental team growth; leverages existing sync_agents() plumbing.
    - Cons: Fourth option = more code and tests; "modify team" has its own edge cases (remove role? re-run dev variant question?); scope creep.
- **→ Recommended**: **Option A** — matches research §10 Q8 and §4 re-run flow. Covers the three common intents with minimal scope. Promote Option C's "modify team" path to a v2 backlog item tied to the custom-builder work in Q4.

### Q9 — Dev manifest shape: single with variants or multiple files?

- **Category**: schema
- **Why this matters**: Affects `references/roles/` layout, validator logic, and whether users can customize one variant without editing others. Single manifest with `setup_questions.variant` is DRY. Separate manifests are easier to reason about and allow per-variant `routes_to` differences (though none exist today).
- **Options**:
  - **Option A**: Single `references/roles/dev/manifest.yaml` with `setup_questions.variant` that expands into 1 or 2 installed instances per option (matches §2 Example 3).
    - Pros: DRY; one file to edit when dev routing changes; `routes_to: [qa]` lives in one place; resolver knows "dev family" matches any variant; matches research §2 recommendation.
    - Cons: `variant.installs[]` adds a schema field not used by other roles; validator has a dev-specific branch; user wanting to customize "fe only" touches the dev manifest (affects be too).
  - **Option B**: Three separate manifests: `references/roles/dev-be/`, `dev-fe/`, `dev-fullstack/`. Each is a standalone role with its own `routes_to`. Preset asks "which dev variants" and installs the selected files directly.
    - Pros: Each file is standalone and readable; per-variant `routes_to` flexibility; no special `variant.installs[]` schema; validator is uniform across all manifests; user can edit fe without touching be.
    - Cons: Three files to maintain; any shared change (e.g. `routes_to: [qa]`) is a 3-way diff; "dev family" matching in the resolver needs a family tag in frontmatter.
  - **Option C**: Hybrid — one `dev/manifest.yaml` for shared fields (template_refs, routes_to, labels) and per-variant overlay files (`dev/variants/be.yaml`, `fe.yaml`, `fullstack.yaml`) that override only the fields that differ.
    - Pros: DRY shared fields; per-variant customization possible; somewhat standard pattern in config systems.
    - Cons: Two-level schema is complex; validator needs merge logic; overlay YAMLs are rare in SquidSquad codebase so cognitive load is high; over-engineered for v1 needs.
- **→ Recommended**: **Option A** — research §2 already sketches it, all dev variants currently share `routes_to: [qa]`, and the `variant.installs[]` schema field is the smallest special-case. If per-variant routing diverges in v2, promote to Option B. This is also what research §10 Q9 recommends.

### Q10 — Universal-terminal rule for `routes_to`?

- **Category**: schema
- **Why this matters**: Edge case in §6 — `[pm, designer, dm]` walks PM → Designer and stops because designer's `routes_to: [dev, qa]` has no installed match, leaving DM unreached. The walker needs a clean way to fall through to DM.
- **Options**:
  - **Option A**: Put `dm` at the end of every shipped manifest's `routes_to`. E.g. `designer: routes_to: [dev, qa, dm]`, `qa: routes_to: [dm]`, `dev: routes_to: [qa, dm]`. Walker algorithm unchanged — decentralized, greedy.
    - Pros: Pure decentralization; no special case in the walker; every manifest declares its own fall-through; easy to validate; matches research §10 Q10 recommendation; `[pm, designer, dm]` case resolves to `PM → Designer → DM` naturally.
    - Cons: `dm` appears in every manifest's `routes_to`, which is mildly redundant; if DM is not installed, each role's list terminates one entry earlier (still correct).
  - **Option B**: Walker has a hardcoded "always fall through to DM if DM is installed and no other route resolves" rule. Manifests don't mention DM in `routes_to`.
    - Pros: Less redundancy in manifest files; DM's terminal status is expressed in code once; cleaner manifest diffs.
    - Cons: Hardcodes DM's role name in the walker (violates decentralization); "dm-ness" becomes walker state; if user ever replaces DM with a custom terminal role, walker change required; muddles the manifest-driven invariant.
  - **Option C**: Add an `is_terminal_default: true` manifest flag (set only on DM's manifest) that the walker auto-appends to every non-terminal role's `routes_to` at resolve time.
    - Pros: Decentralized via manifest declaration; no literal "dm" in walker code; supports a future custom terminal role.
    - Cons: New schema field; walker mutates the routes list at runtime; more to test; solves a problem that doesn't exist yet (v2 use case).
- **→ Recommended**: **Option A** — research §10 Q10 and §11 caveat 1 already recommend it, it's the simplest fix, and it keeps the walker algorithm unmodified. Update §2 example manifests (pm, designer, dev, qa) to append `dm` to their `routes_to` before implementation. **This is the highest-priority lock for Phase 2** because every shipped manifest depends on it.
