### Step 2 — Triage Issues

Print: `[🦑 HH:MM:SS] Triaging issues...`

Query GitHub Issues for open issues assigned to your role:

```bash
python references/scripts/tracker.py list-issues [ROLE] --status open
```

For each issue that does not have a `status:shipped` or closed state:

1. Write working state: update `.squidsquad/[ROLE]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`.
2. Read the issue details: `gh issue view [NUMBER] --json title,body,comments`
3. Locate the relevant code.
4. Fix the issue.
5. Run the test command: `[ROLE_TEST_CMD]`
6. **Verify changes exist**: Run `python references/scripts/git_ops.py has-changes`. If output is `false` (no modifications), do NOT transition — re-read the issue and apply the fix. Never mark an issue as fixed without actual code changes.
7. If tests pass and changes exist:
   - Transition status: `python references/scripts/tracker.py transition [NUMBER] open pending-test --role [ROLE]-lead`
   - Comment: `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Fixed in commit [hash]. [Brief explanation]. Status → Pending Test."`
   - Clear working state.
8. If the root cause belongs to another agent's domain:
   - Do NOT mark this issue as fixed.
   - File a new issue: `python references/scripts/tracker.py create-issue --title "[title]" --body "[description]" --role [OTHER_ROLE] --severity [level] --reporter [ROLE]-lead`
   - Comment on the original: `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Root cause is in [OTHER_ROLE]. Filed #[NEW_NUMBER]. Blocking."`
   - Clear working state.
