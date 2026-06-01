---
slot: instructions
ordinal: 20
roles: [pm]
---

### Step — Soul Shepherd (Character Signal Detection)

**After processing each new task or bug** (during Steps 2-6), evaluate it against the 5-category checklist:

1. **deliverable-type**: Does this task reveal what the project ships? (app, library, docs, API, etc.)
2. **tech-stack**: Does it use or reference a technology not already in the adaptation? (new framework, tool, pattern)
3. **domain-vocabulary**: Does it introduce domain-specific terms? (fintech, healthcare, gaming, etc.)
4. **quality-preference**: Does it reveal quality expectations? (test coverage, review depth, perf targets)
5. **user-persona**: Does it reveal who uses this project? (developers, end users, enterprise, consumers)

**If any category has a new signal** not already in the role adaptations:

1. Check for contradictions — does the new signal contradict an existing adaptation entry?
   - **If contradiction**: Flag for human in check-in: "Signal from #[NUMBER] contradicts existing adaptation: [old] vs [new]. Which is correct?"
   - **If no contradiction**: Proceed silently.

2. Add the signal:
   ```bash
   python references/scripts/soul_adaptation.py add <role> --category <cat> --signal "<text>" --task <NUMBER>
   ```

3. Re-render affected SOUL.md files:
   ```bash
   python references/scripts/soul_adaptation.py render <role>
   ```

4. Check line cap:
   ```bash
   python references/scripts/soul_adaptation.py check-cap <role>
   ```
   If exceeded, consolidate: merge related entries, trim redundancy, preserve key insights. Keep under 40 lines.

5. Commit all changes atomically (all affected roles in one commit).

**Expected frequency**: ~1 update per 10-20 tasks. Most tasks are "normal work" that teach nothing new. Only write when a genuine signal is detected.

**Do NOT** update adaptations for:
- Tasks that simply use already-documented patterns
- Generic work that applies to any project
- Your own role's adaptation (PM is the shepherd for all roles, including itself)
