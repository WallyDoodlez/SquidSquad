# FEAT-SKILL-027 Phase 2 Prep — Designer Agent Role

## Recommended Question Order

Dependencies flow downward — later questions depend on earlier answers. Controversial / highest-human-input questions are last.

| Order | Question | Category | Rationale for Position |
|-------|----------|----------|------------------------|
| 1 | Q4 — Naming convention | Scope | Foundational — affects setup flow, detection logic, every other answer |
| 2 | Q2 — Status vs. tag | Pipeline | Determines the pipeline shape that Q7 and Q3 depend on |
| 3 | Q1 — Own tracker vs. shared | Architecture | Affects directory structure and cross-agent patterns |
| 4 | Q5 — Token ownership scope | Architecture | Affects spec format, dev handoff, and long-term maintenance |
| 5 | Q6 — Design tool auth | Architecture | Isolated concern, no downstream dependencies |
| 6 | Q3 — Autonomous vs. on-demand | Cost / UX | Controversial — cost implications, depends on pipeline shape from Q2 |
| 7 | Q7 — Interactive design session | UX / Pipeline | Most novel question, highest human-input needed, depends on Q2 pipeline shape |

---

## Q4 — Naming Convention

**Category**: Scope / Convention

Should the designer role always be called `designer` (like `pm` and `dm`), or can the user name it freely and select a "Designer template" during setup?

### Option A — Fixed name `designer` (RECOMMENDED)

- **Description**: The role is always called `designer`. Setup auto-detects it by name, like `pm` and `dm`. Directory is always `.squidsquad/designer/`.
- **Pros**: Simple detection logic. Consistent with `pm`/`dm` precedent. No ambiguity in cross-agent references. Boot scripts use a predictable name (`start-designer.sh`).
- **Cons**: Only one designer per project. Cannot have specialized designers (e.g., `ux-designer`, `visual-designer`).

### Option B — User-named with template selector

- **Description**: User names the role anything (e.g., `ux`, `visual`). During setup, they select "Designer template" from a dropdown/prompt. Template type stored in config.md.
- **Pros**: Multiple designers possible. User can use domain-specific naming. Flexible for larger teams.
- **Cons**: Setup flow complexity increases. Cross-agent references need to look up template type, not just role name. PM routing logic must discover "which agents use the designer template" rather than just checking for `designer`. Breaks the simple `pm`/`dm`/`designer` mental model.

### Option C — Fixed name, allow suffixed variants

- **Description**: Primary designer is always `designer`. Additional designers can be `designer-ux`, `designer-visual`, etc. Setup detects the `designer` prefix.
- **Pros**: Primary case is simple. Extensible for multi-designer setups. Prefix-based detection is straightforward.
- **Cons**: Multi-designer is an edge case that adds complexity for little near-term value. Suffix convention needs documentation.

---

## Q2 — Feature Status: `Design` as Status vs. Routing Tag

**Category**: Pipeline

Should `Design` be a dedicated feature status in the lifecycle, or should design routing use a metadata tag while the feature stays at `Approved`?

### Option A — Dedicated `Design` status with round-trip to `Approved`

- **Description**: PM moves feature from `Approved` to `Design`. Designer works it. Designer moves it back to `Approved` when specs are ready. Dev agents see `Approved` as today — no dev template changes.
- **Pros**: Explicit status makes it obvious who owns the feature at any moment. Discussion log disambiguates the two `Approved` visits. Dev templates unchanged.
- **Cons**: `Approved` is visited twice for design-needed features, which is slightly confusing in status history. Agents reading status history must understand the round-trip pattern.

### Option B — Tag-based routing, no new status (RECOMMENDED)

- **Description**: Features stay at `Approved`. A `Design: needed / in-progress / complete / not-needed` metadata field controls routing. Designer looks for `Design: needed`. Dev agents look for `Approved` AND `Design: complete` (or `Design: not-needed`). When designer finishes, it sets `Design: complete`.
- **Pros**: No new status values. No round-trip confusion. Status flow is unchanged. The tag is a clear, queryable signal. Dev agents add one simple check: "if Design field is `needed` or `in-progress`, skip this feature."
- **Cons**: Dev templates need a minor addition (check the Design field). The tag introduces a parallel state dimension. Slightly more complex for agents to reason about (status + tag vs. status alone).

### Option C — Dedicated `Design` and `Design Review` statuses (linear flow)

- **Description**: Full linear flow: `Approved -> Design -> Design Review -> In Progress`. No round-trip. Dev agents look for `Design Review` (approved by PM) or `Approved` (no design needed) to pick up work.
- **Pros**: Clean linear flow. No ambiguity. Each status has one meaning.
- **Cons**: Dev templates must now check TWO statuses (`Approved` OR `Design Review`). Every agent that reads statuses is affected. Most features that skip design still use the old path, creating two parallel flows through the lifecycle.

---

## Q1 — Designer Tracker: Own vs. Shared with FE

**Category**: Architecture

Should the designer have its own bug/feature tracker (`.squidsquad/designer/bugs/`, `.squidsquad/designer/features/`), or share the FE agent's tracker?

### Option A — Own tracker (RECOMMENDED)

- **Description**: Designer gets `.squidsquad/designer/bugs/` and `.squidsquad/designer/features/` like every other agent. Design-specific issues (spec revisions, token conflicts, tool integration bugs) go here. Design specs for dev features are linked via the spec directory, not the tracker.
- **Pros**: Clean separation. PM can file design-specific bugs without polluting the FE tracker. Designer's workload is independently visible. Follows the established one-tracker-per-agent pattern.
- **Cons**: PM must know which tracker to file to. Cross-references between design bugs and FE features add indirection.

### Option B — Shared tracker with FE

- **Description**: Designer reads from and writes to the FE agent's tracker. Design tasks are tagged or prefixed to distinguish them from code tasks.
- **Pros**: Single source of truth for UI features. No cross-tracker references needed. PM files everything to one place.
- **Cons**: Mixes design and code concerns in one tracker. FE agent sees design bugs it cannot fix. Tag-based filtering adds complexity. Breaks the one-agent-one-tracker pattern. Does not scale if designer serves multiple dev agents.

### Option C — No tracker for designer, uses spec directory only

- **Description**: Designer has no bug/feature tracker. It only reads dev features flagged `Design: needed` and produces specs. Design-related bugs are filed to the relevant dev agent with a `design` tag.
- **Pros**: Minimal new infrastructure. Designer is purely reactive — it only acts on dev features.
- **Cons**: No way to track design-specific work (token system updates, design system maintenance). No place for PM to file design improvement requests. Designer cannot self-file bugs about the design system.

---

## Q5 — Design Token Ownership Scope

**Category**: Architecture

Does the designer own design tokens globally (maintaining a canonical design system) or only per-feature (tokens scoped to each spec)?

### Option A — Per-feature only (RECOMMENDED)

- **Description**: Each design spec includes its own `tokens.md` section listing tokens used or introduced by that feature. No global token file. Dev agents consume tokens from the spec.
- **Pros**: Simple. No global state to maintain. No conflicts between features. Tokens are co-located with the design that uses them. Works well for projects without a formal design system.
- **Cons**: Token duplication across specs. No single source of truth for the project's design language. Harder to enforce consistency across features.

### Option B — Global design system ownership

- **Description**: Designer maintains a `.squidsquad/designer/design-system/` directory with canonical token files (colors, spacing, typography, etc.). Feature specs reference these tokens. Designer updates the global system when introducing new tokens.
- **Pros**: Single source of truth. Consistent design language. Dev agents always reference the canonical tokens. Enables design system auditing.
- **Cons**: Global state means merge conflicts. Designer must maintain the system even when not working on features. Adds maintenance burden. Conflicts possible if FE agent also modifies token files in the codebase.

### Option C — Hybrid: per-feature with optional global promotion

- **Description**: Start per-feature. Designer can optionally "promote" tokens from a feature spec into a global `design-system/` directory when they become reusable. Promotion is a deliberate action, not automatic.
- **Pros**: Best of both worlds — simple by default, powerful when needed. Gradual adoption. No upfront maintenance burden.
- **Cons**: Two places to look for tokens. Promotion step can be forgotten, leading to drift. More complex instructions in the template.

---

## Q6 — Design Tool Authentication

**Category**: Architecture / Security

How should the designer handle credentials for external design tools (Figma API keys, etc.)?

### Option A — MCP-only, no credential management (RECOMMENDED)

- **Description**: Designer only connects to design tools via MCP. MCP handles auth through its own connection config (outside SquidSquad's scope). If a tool is not available via MCP, it is not supported — the designer falls back to manual mode.
- **Pros**: Zero credential management in SquidSquad. No secrets in git. MCP is the established pattern for tool connections. Simplest to implement. Security is delegated to the MCP layer.
- **Cons**: Limits tool support to what is available via MCP. If a design tool only has a REST API (no MCP server), it cannot be used.

### Option B — Environment variable pattern

- **Description**: Design tool credentials are stored in environment variables (e.g., `FIGMA_API_TOKEN`). The designer template references these variables. A `.squidsquad/.local-config` (gitignored) documents which env vars are needed.
- **Pros**: Works with any API-based tool. Standard pattern for secrets. `.local-config` provides documentation without storing secrets.
- **Cons**: SquidSquad must manage secret documentation. Users must set up env vars manually. Risk of accidental commit if someone puts secrets in the wrong file. More setup friction.

### Option C — Config-based with encrypted secrets

- **Description**: Secrets are stored encrypted in `.squidsquad/config.md` or a `.squidsquad/secrets.enc` file. A project-specific key (env var) decrypts them at runtime.
- **Pros**: Self-contained — secrets travel with the project. No external env var setup after initial key creation.
- **Cons**: Encryption adds significant complexity. Key management is its own problem. Overkill for this use case. Encrypted blobs in git are an anti-pattern.

---

## Q3 — Autonomous vs. On-Demand Designer

**Category**: Cost / UX

Should the designer agent run autonomously on a loop (like dev and DM), or be spawned on-demand only when design work exists?

### Option A — Autonomous with idle detection (RECOMMENDED)

- **Description**: Designer runs the standard Ralph Loop on a 30-minute interval, like all other agents. If it finds no `Design: needed` features for N consecutive cycles (e.g., 5), it logs a suggestion to stop the agent. Human decides whether to stop it.
- **Pros**: Consistent with all other agent patterns. No PM complexity for spawning. Designer is always ready when design work arrives. Simple to implement — reuses existing Ralph Loop infrastructure.
- **Cons**: Wastes Claude sessions during idle periods. Designer may be idle most of the time for projects with infrequent design work. Cost adds up over time.

### Option B — On-demand, PM spawns when needed

- **Description**: Designer does not run by default. When PM routes a feature to `Design: needed`, PM spawns the designer agent (via a boot script or Discussion command). Designer runs until its queue is empty, then exits.
- **Pros**: Zero cost when no design work exists. Efficient for projects with sporadic design needs. Designer only consumes resources when productive.
- **Cons**: PM template gets more complex (must manage agent lifecycle). Delay between "design needed" and designer starting. New pattern — no other agent works this way. PM must detect when designer has finished and exited.

### Option C — Hybrid: on-demand start, autonomous while active

- **Description**: Designer is started manually (or by PM) when design work first appears. Once started, it runs autonomously on the Ralph Loop. It auto-exits after N idle cycles (not just a suggestion — actually exits).
- **Pros**: No idle cost — designer auto-exits when done. Once started, it behaves like other agents. PM does not need to manage lifecycle beyond the initial trigger.
- **Cons**: Auto-exit is a new pattern that other agents do not use. Risk of exiting prematurely if design feedback arrives one cycle after the designer exits. Must handle restart gracefully.

---

## Q7 — Interactive Design Session Structure

**Category**: UX / Pipeline

**Context**: The designer's core purpose is to be the human's creative collaborator. After PM planning completes, there must be an interactive design session where the human works WITH the designer — iterating on the vision, refining the design, exploring options — before the design is approved and handed to dev. This is analogous to PM's Phase 2 Discussion but for design.

How should this interactive session be structured?

### Option A — Structured multi-round session in Discussion (RECOMMENDED)

- **Description**: When the designer picks up a `Design: needed` feature, it enters a "Design Discussion" phase (analogous to PM Phase 2). The designer produces an initial design proposal (mood, layout concepts, component options) and posts it to the feature's Discussion. The human reviews and responds. The designer iterates — presenting alternatives, refining based on feedback, exploring variations. After N rounds or when the human signals approval, the designer produces the final spec. A structured template guides the conversation:
  1. **Round 1 — Vision**: Designer presents 2-3 high-level design directions with tradeoffs.
  2. **Round 2 — Refinement**: Based on human's pick/feedback, designer elaborates the chosen direction with component details, layout options, interaction patterns.
  3. **Round 3+ — Polish**: Iterate on specifics until human approves.
  4. **Approval signal**: Human posts `> design approved` (or similar keyword) in Discussion. Designer produces final spec.
- **Pros**: Structured but flexible. Human has clear touchpoints. Multiple options prevent the designer from guessing wrong. The approval gate ensures the human is satisfied before dev begins. Reuses the Discussion mechanism (no new infrastructure). Mirrors PM Phase 2 pattern, so humans already understand the interaction model.
- **Cons**: Asynchronous Discussion is slow — each round requires waiting for the human to respond (could be hours/days). Designer may block on human input for multiple cycles. The structured rounds may feel rigid for creative work.

### Option B — Dedicated design session file with live iteration

- **Description**: Designer creates a `.squidsquad/designer/sessions/FEAT-XXX-design-session.md` file that serves as a live collaboration canvas. The file has sections for the designer's proposals and the human's feedback. The human edits the file directly (or responds via Discussion). The designer checks the file each cycle and iterates. The session file has a clear status (`exploring / refining / approved`) so the designer knows where it stands.
- **Pros**: Dedicated artifact for the creative process (not buried in Discussion). Human can edit proposals directly (redlining). Session history is preserved as a standalone document. Status field makes the phase machine-readable.
- **Cons**: New file type and directory. Human must know to edit the session file (not just Discussion). Two places for feedback (session file vs. Discussion) could cause confusion. More infrastructure to build.

### Option C — Real-time interactive mode (designer waits for human input)

- **Description**: When the designer enters the design phase, it does NOT follow the async Ralph Loop pattern. Instead, it enters an interactive mode where it presents options, waits for human input in the same conversation, iterates in real-time, and produces the spec in one session. This is a synchronous creative session — like a human working with a design collaborator at a whiteboard.
- **Pros**: Best creative experience. Rapid iteration. No waiting between cycles. Feels like true collaboration. Human gets immediate responses to "what if we tried X?"
- **Cons**: Breaks the Ralph Loop pattern entirely. Designer cannot be autonomous during design sessions. Requires the human to be present and engaged for the full session. Context window pressure — a long creative session could exhaust the context. Cannot be backgrounded. If the human steps away mid-session, the designer is stuck.

---

## Summary Table

| Q# | Category | Recommended | Key Tradeoff |
|----|----------|-------------|--------------|
| Q4 | Scope | Fixed name `designer` | Simplicity vs. multi-designer flexibility |
| Q2 | Pipeline | Tag-based routing (no new status) | Clean status flow vs. parallel state dimension |
| Q1 | Architecture | Own tracker | Separation of concerns vs. cross-tracker indirection |
| Q5 | Architecture | Per-feature tokens | Simplicity vs. design system consistency |
| Q6 | Architecture | MCP-only auth | Zero credential burden vs. API-only tool support |
| Q3 | Cost/UX | Autonomous with idle detection | Consistency with other agents vs. idle cost |
| Q7 | UX/Pipeline | Structured multi-round Discussion | Reuses existing patterns vs. async latency |
