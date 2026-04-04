### Step 1e — Triage Bugs

Print: `[🦑] Triaging bugs...`

Query GitHub Issues for open bugs assigned to your role:

```bash
gh issue list --label "type:bug,role:dm" --state open --json number,title,labels,body --limit 50
```

For each bug that has `status:open`:

1. Write working state: update `.squidsquad/dm/working-state.md` with `Task: #[NUMBER]`, status `in-progress`.
2. Read the bug details: `gh issue view [NUMBER] --json title,body,comments`
3. Locate the relevant file (README, CHANGELOG, docs, delivery artifacts).
4. Fix the bug.
5. If fix is complete:
   - Transition status:
     ```bash
     gh issue edit [NUMBER] --remove-label "status:open" --add-label "status:pending-test"
     gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **dm**: Fixed in commit [hash]. [Brief explanation]. Status → Pending Test."
     ```
   - Clear working state.
6. If the root cause belongs to another agent's domain:
   - Do NOT mark this bug as fixed.
   - File a new bug to the other agent's domain:
     ```bash
     gh issue create --title "BUG: [title]" --body "[description]" --label "type:bug,role:[OTHER_ROLE],squidsquad,status:open"
     ```
   - Comment on the original:
     ```bash
     gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **dm**: Root cause is in [OTHER_ROLE]. Filed #[NEW_NUMBER]. Blocking."
     ```
   - Clear working state.
