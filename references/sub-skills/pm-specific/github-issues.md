### Step 7b — Triage External Issues

Print: `[🦑 HH:MM:SS] Checking for external issues...`

Since GitHub Issues is the tracker, external contributors may file issues directly. Scan for issues that lack SquidSquad labels (filed by humans or contributors, not by agents):

```bash
gh issue list --state open --json number,title,labels,body --limit 50
```

For each open issue that does NOT have the `squidsquad` label:

1. **Classify**: Read the title and body. Determine if it's a bug or feature request.
2. **Route**: Determine which dev agent's domain it belongs to based on content.
3. **Label**: Add appropriate labels:
   ```bash
   gh issue edit [NUMBER] --add-label "squidsquad,[type],[priority:low],[role:[target-role]]"
   ```
4. **Comment**: Add a triage comment:
   ```bash
   gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **pm**: Triaged. Routed to [role]. Priority: Low (human can bump)."
   ```

External issues start as `priority:low` by default. The human can bump priority through the normal check-in flow.

If no external issues are found, skip silently.
