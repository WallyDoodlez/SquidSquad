<!-- sub-skill: tool-figma -->
## Design Tool — Figma

You produce designs in Figma via the Figma MCP server. Each design
iteration is a Figma frame (or a group of frames) inside the project's
Figma file; the human reviews by opening the frame URL you share.

### Target file

Every project has one Figma file that holds all the designs for that
project. The human sets this during tool setup and you read it from
your tool configuration. If you do not yet have a target file URL,
post a comment on the design issue asking the human to share one and
pause the design task until you do — never guess or create a file
without confirmation.

### Iterations

For each design issue, use this frame-naming pattern:

```
<issue-number> · <short title> · v<iteration-number>
```

Example: `42 · Onboarding redesign · v1`, `42 · Onboarding redesign · v2`.

- Put every iteration as a separate frame so review history is visible.
- Keep the iterations for one issue grouped on the same Figma page.
- Use Figma components and styles (fills, typography, effects) rather
  than one-off values wherever a component or style exists.
- If the project has no design system yet, create a small one — colour
  palette frame, type scale frame, spacing token frame — on a
  dedicated "Foundations" page. Link to it from each issue's iteration
  so the human can see the tokens.

### Sharing iterations with the human (HITL)

When you produce or update an iteration:

1. Update the frame in Figma via the MCP server.
2. Copy the frame URL from Figma (the URL that opens directly to that
   frame — not just the file URL).
3. Post a comment on the issue linking the frame and summarising what
   changed since the previous iteration:

   ```
   Iteration 2: https://www.figma.com/file/ABC123/Project?node-id=42-2

   Changes from v1:
   - larger primary CTA
   - moved secondary nav to the sidebar
   - added error and empty states
   ```

4. Mark the issue as awaiting human review. Move on to your next item.
   Never block waiting for feedback.

When the human responds with a redirect, read the comment, produce a
new frame (bump the version), and post a new comment. When the human
approves, hand the design forward per your normal routing.

### Rules

- **Never delete previous iteration frames.** Review history is part
  of the artifact. The human should be able to scroll back.
- **One Figma file per project, many issues inside it.** Keep issues
  on separate pages when the file grows large.
- **If Figma is down or the MCP server errors out**, stop and pause
  the task — do not silently fall back to a different tool. Raise the
  tool failure so infrastructure can fix it.
<!-- /sub-skill: tool-figma -->
