---
slot: instructions
ordinal: 20
roles: [dm]
---

### Step 1e — Triage Bugs

Print: `[🦑 HH:MM:SS] Triaging bugs...`

Query GitHub Issues for open bugs assigned to your role:

```bash
python references/scripts/tracker.py list-issues dm
```

For each bug that has `status:open`:

1. Write working state: update `.squidsquad/[DM_ALIAS]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`.
2. Read the bug details: `gh issue view [NUMBER] --json title,body,comments`
3. Locate the relevant file (README, CHANGELOG, docs, delivery artifacts).
4. Fix the bug.
5. If fix is complete:
   - Transition status:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] in-progress pending-ship --role dm-lead
     python references/scripts/tracker.py comment [NUMBER] --role dm --message "Fixed in commit [hash]. [Brief explanation]. Status → Pending Ship."
     ```
   - Clear working state.
6. If the root cause belongs to another agent's domain:
   - Do NOT mark this bug as fixed.
   - File a new bug to the other agent's domain.

     → run sub-skill: `tracker-protocol` — use the **Cross-role issue** one-liner shape (Description / Steps / Expected / Actual / Cross-filed-from body). Set `--role [OTHER_ROLE]`, `--severity [level]`, `--reporter dm-lead`.

   - Comment on the original:
     ```bash
     python references/scripts/tracker.py comment [NUMBER] --role dm --message "Root cause is in [OTHER_ROLE]. Filed #[NEW_NUMBER]. Blocking."
     ```
   - Clear working state.
