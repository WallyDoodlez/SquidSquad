---
slot: instructions
ordinal: 20
roles: [pm]
---

### Step 7b — Triage External Issues

Print: `[🦑 HH:MM:SS] Checking for external issues...`

Since GitHub Issues is the tracker, external contributors may file issues directly. Scan for issues that lack SquidSquad labels (filed by humans or contributors, not by agents):

```bash
python references/scripts/tracker.py list-all-open
```

For each open issue that does NOT have the `squidsquad` label:

1. **Classify**: Read the title and body. Determine if it's an issue or task request.
2. **Route**: Determine which worker agent's domain it belongs to based on content.
3. **Label**: Add appropriate labels:
   ```bash
   python references/scripts/tracker.py add-labels [NUMBER] "squidsquad,type:[issue|task],priority:low,role:[target-role]"
   ```
4. **Comment**: Add a triage comment:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role pm --message "Triaged. Routed to [role]. Priority: Low (human can bump)."
   ```

External issues start as `priority:low` by default. The human can bump priority through the normal check-in flow.

If no external issues are found, skip silently.
