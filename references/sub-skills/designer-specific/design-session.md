### Step 2 — Check Design Requests

Print: `[🦑] Checking design requests...`

Read each dev agent's `features/INDEX.md` (listed in `config.md` under `Dev Agents`). For each feature with status `Approved` or `In Progress`, read its individual file and check for `**Design**: needed`.

If no features need design, this is a **quiet cycle** — increment the quiet cycle counter. After **5 consecutive quiet cycles**, log a suggestion in the iteration log: `"No design requests for 5 cycles — consider stopping the designer agent."` Do NOT auto-stop. Reset the counter when design work is found.

When a design-needed feature is found, pick the highest-priority one. Print: `[🦑] Designing FEAT-[ROLE_UPPER]-XXX...`

1. Write working state with the feature ID, status `in-progress`, and planned design approach.
2. Read the feature's planning artifacts:
   - `FEAT-[ROLE_UPPER]-XXX-CONTEXT.md` — look for the `## Design Brief` section
   - `FEAT-[ROLE_UPPER]-XXX-RESEARCH.md` — understand constraints, side effects
3. **Validate Design Brief completeness**: The Design Brief must contain: user story, target platforms, existing patterns to follow, constraints. If incomplete:
   - Append a Discussion entry requesting PM clarification with specific missing items.
   - Set working state to `blocked`.
   - Move to next feature or idle.
4. Update the feature's `**Design**` field to `in-progress`.
5. Append a Discussion entry:
   ```
   > [YYYY-MM-DD HH:MM] **designer**: Picking up design. Design → in-progress.
   ```

### Step 2b — Feasibility Assessment

Print: `[🦑] Assessing feasibility for FEAT-[ROLE_UPPER]-XXX...`

Before starting the interactive design session, assess technical feasibility:

1. Review the feature's acceptance criteria and RESEARCH.md for complexity signals.
2. Check the Design Brief constraints.
3. If design tools are configured (see Design Tools in `config.md`), query the tool for existing components/patterns.
4. Produce a feasibility rating:
   - **Green**: Straightforward — uses existing patterns, standard components, reasonable effort.
   - **Yellow**: Feasible with caveats — requires custom components, new patterns, or significant effort. Note specific concerns.
   - **Red**: High risk — fundamentally difficult, may require scope reduction or architectural changes. Recommend discussion with PM/human before proceeding.
5. If **Red**: Append a Discussion entry with concerns and recommendation. Use `AskUserQuestion` to confirm whether to proceed, reduce scope, or reject the design work.

### Step 2c — Interactive Design Session

Print: `[🦑] Starting design session for FEAT-[ROLE_UPPER]-XXX...`

Write current state: `echo "designing|🎨 FEAT-[ROLE_UPPER]-XXX design session..." > .squidsquad/designer/current-state.tmp && mv -f .squidsquad/designer/current-state.tmp .squidsquad/designer/current-state`

**Set planning phase flag**: Update `.squidsquad/designer/working-state.md` to include `- **Phase**: designing FEAT-[ROLE_UPPER]-XXX` so cron-triggered cycles are suppressed during this interactive session.

Enter an interactive design session with the human. This blocks the loop — interactive design is inherently collaborative.

**Session flow:**

1. **Present context**: Summarize the feature, design brief, feasibility assessment, and any constraints.
2. **Propose design direction**: Based on the brief, propose 2-3 design approaches with tradeoffs. Use `AskUserQuestion` to let the human choose or discuss.
3. **Iterate**: The human may request changes, ask for alternatives, or refine the direction. Iterate until the human is satisfied. If design tools are connected, use them to fetch design references, tokens, or component specs.
4. **Produce draft spec**: When direction is agreed, produce a draft design spec (see Step 2d).
5. **Human approval gate**: Present the draft spec and use `AskUserQuestion`:
   ```
   question: "Design spec for FEAT-[ROLE_UPPER]-XXX is ready. Review the spec above.\n\nApprove this design for dev handoff?"
   options: ["Approve — hand off to dev", "Needs revision", "Reject design"]
   ```
   - **Approve**: Proceed to Step 2d (finalize and hand off).
   - **Needs revision**: Continue iterating.
   - **Reject**: Set `**Design**` back to `needed`. Append Discussion entry. Clear working state.

**If the human does not respond**: After presenting the design, note "awaiting human approval on design" in working state. On the next cycle, check if the human has responded. Continue iterating or waiting. Do not force approval.

### Step 2d — Produce Design Spec

Print: `[🦑] Writing design spec for FEAT-[ROLE_UPPER]-XXX...`

After human approval, write the design spec to `.squidsquad/designer/specs/FEAT-[ROLE_UPPER]-XXX/design-spec.md`:

```markdown
# Design Spec — FEAT-[ROLE_UPPER]-XXX: [Title]

- **Source**: [manual / Figma / Stitch / etc.]
- **Designer**: designer
- **Approved**: [YYYY-MM-DD HH:MM]
- **Round-trip**: [1 / 2 — number of dev rejection cycles, if any]

## Feasibility Assessment

- **Overall**: [Green / Yellow / Red]
- **Estimated Effort**: [N dev cycles, baseline: [explanation]]
- **Constraints**: [list]
- **Recommendation**: [proceed / proceed with caveats / reduce scope]

## Component Hierarchy

- [Component tree / page structure]

## Layout

- [Layout description, responsive behavior, breakpoints]

## Interactions

- [User interactions, state transitions, animations]

## Visual States

- [Default, hover, active, disabled, error, loading, empty states]

## Design Tokens

- **Colors**: [list with hex values and usage]
- **Typography**: [font families, sizes, weights, line heights]
- **Spacing**: [spacing scale, padding/margin conventions]
- **Borders**: [radius, width, colors]
- **Shadows**: [shadow values and usage]

## Assets

- [Asset references with source URLs — no large binaries committed]
- [Dev agent fetches assets during implementation]

## Notes for Dev

- [Implementation hints, component library references, accessibility requirements]
- [Any feasibility constraints that affect implementation approach]
```

After writing the spec:

1. Update the feature's `**Design**` field to `complete`.
2. Append a Discussion entry:
   ```
   > [YYYY-MM-DD HH:MM] **designer**: Design approved by human. Spec written to specs/FEAT-[ROLE_UPPER]-XXX/. Design → complete.
   ```
3. **Clear planning phase flag** from working-state.md.
4. Clear working state.

### Step 2e — Handle Design Rejection from Dev

If a dev agent sets `**Design**` back to `needed` (via Discussion entry noting specific issues), the designer picks it up again on the next cycle.

Track the **round-trip counter** in the design spec file. If this is the **3rd round-trip** (2 previous rejections):
- Do NOT produce another revision.
- Append a Discussion entry escalating to PM/human:
  ```
  > [YYYY-MM-DD HH:MM] **designer**: Design rejected by dev for the 3rd time. Escalating to PM/human for mediation. See spec revision history.
  ```
- Set working state to `blocked`.
