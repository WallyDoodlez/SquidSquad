---
slot: instructions
ordinal: 21
roles: [verifier]
---

## Verification — Finding Routing Process (cold path)

Reached from `verification.md` Step 3 whenever a finding (test failure, gap, or defect discovered during verification) needs to be classified, deduped, and filed.

**Step 3a — Classify the finding:**

Determine the finding category using your domain-specific finding categories (defined in your L3 layer). If no domain categories are available, use this generic process:
- Identify which role's **declared responsibilities** (from config.md team composition) the finding falls under.
- If ownership is unclear, escalate to PM — PM is always present and owns coordination.

**Step 3b — Check for duplicates:**

```bash
python references/scripts/tracker.py list-by-labels "type:issue,squidsquad"
```
Search output for keywords matching this finding. If a matching issue exists, comment on it — do not duplicate.

**Step 3c — Document and file:**

Every finding must include structured evidence:

```
**Finding**: [what is wrong — specific and testable]
**Evidence**: [test output, file:line, command that reproduces it]
**Category**: [implementation defect | spec gap | design defect | test infra]
**Routed to**: [role] — [why this role is responsible]
```

- If **objective** (clear pass/fail, crash, error): File immediately with the structured format above.

  → run sub-skill: `tracker-protocol` — use the **Bug fix** one-liner shape with the structured Finding / Evidence / Category / Routed-to body in place of the bug-fix template. Set `--role [target-role]`, `--severity [high|medium|low]`, `--reporter verifier-lead`.

- If **subjective** (coherence issue, style concern, architectural question): Flag for PM/human review. Do NOT file an issue — PM and human decide.
  ```bash
  python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Subjective finding flagged for PM/human review: [structured description]"
  ```
- If **ownership unclear**: Escalate to PM. PM is always present and owns coordination.
- If the finding **spans multiple domains**: File to the primary responsible role, cross-reference others in comments.

**Step 3d — Record on PR (if PR flow enabled):**

If the finding relates to a PR, also post the structured finding as a PR comment for inline review context:
```bash
gh pr comment [PR_NUMBER] --body "## Verifier Finding\n\n[structured finding from 3c]"
```
