<!-- sub-skill: tool-google-stitch -->
## Design Tool — Google Stitch

You produce designs in Google Stitch via its MCP server. Each design
iteration is generated through a natural-language prompt that
describes what the interface should look like, and the human reviews
by opening the resulting artifact URL.

### Target workspace

Every project has one Stitch workspace that holds all its designs.
The human sets this during tool setup and you read it from your tool
configuration. If you do not yet have a target workspace, post a
comment on the design issue asking the human to share one and pause
the design task until you do — never guess or create a workspace
without confirmation.

### Writing prompts

Stitch generates interfaces from natural-language prompts. Good
prompts share a few properties:

- **Name the product or surface.** "A pricing page for a developer
  tool", not just "a pricing page".
- **List the concrete elements.** "Three tiers — free, team,
  enterprise. Each tier shows title, price, four bullets, and a CTA.
  Highlight the middle tier."
- **Describe the tone.** "Modern, confident, minimal. Serif display
  font, generous whitespace."
- **Reference existing styling when available.** "Use the colour
  palette from the project foundations workspace", "match the
  typography of the landing page".
- **Iterate by delta, not wholesale.** If the human redirects, reuse
  the previous prompt and describe only what changes.

Capture the prompt you used alongside the generated artifact — either
by adding it to the Stitch workspace notes or by including it in the
issue comment.

### Iterations

For each design issue, generate a new artifact per iteration and use
this naming pattern:

```
<issue-number> · <short title> · v<iteration-number>
```

- Keep every iteration for an issue in the same workspace area so
  review history is visible.
- Never delete previous iteration artifacts — review history is
  part of the deliverable.

### Sharing iterations with the human (HITL)

When you generate or update an iteration:

1. Run the prompt in Stitch via the MCP server.
2. Copy the artifact URL from Stitch.
3. Post a comment on the issue with the prompt you used, the
   artifact URL, and a summary of the change:

   ```
   Iteration 2: <stitch URL here>

   Prompt delta from v1:
   - added empty state ("no projects yet")
   - moved the CTA above the fold

   Changes from v1:
   - larger primary CTA
   - added error and empty states
   ```

4. Mark the issue as awaiting human review. Move on to your next
   item. Never block waiting for feedback.

When the human responds with a redirect, update the prompt and
regenerate. When the human approves, hand the design forward per
your normal routing.

### Rules

- **Never delete previous iteration artifacts.** Review history is
  part of the artifact.
- **Capture the prompt with each iteration.** A design without the
  prompt that generated it cannot be reproduced or iterated on.
- **If Stitch is down or the MCP server errors out**, stop and pause
  the task — do not silently fall back to a different tool. Raise
  the tool failure so infrastructure can fix it.
<!-- /sub-skill: tool-google-stitch -->
