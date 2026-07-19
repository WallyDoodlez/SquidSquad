---
slot: instructions
ordinal: 21
roles: [verifier]
---

## Verification — Issue Flow (cold path)

Reached from `verification.md` Step 4 when there are `type:issue` bugs pending test (a separate flow from Step 5's task verification — queried and walked independently).

Print: `[🦑 HH:MM:SS] Verifying fixed issues...`

Query all issues pending test:

```bash
python references/scripts/tracker.py list-issues skill --status pending-test
```

(Repeat for each worker role.)

For each issue:

0. **Blocked check**: If the item has a `blocked:human-action` label, skip it. Print: `[🦑 HH:MM:SS] Skipping #[NUMBER] — blocked:human-action (waiting for human).` Do not change its status. Move to the next item.
1. Read details: `gh issue view [NUMBER] --json title,body,comments`
1b. **Consult the vault** (#5572) — search for relevant context before verifying:
   ```bash
   grep -rl "[keyword from issue]" .squidsquad/vault/ --include="*.md" | head -5
   ```
   Check for: decisions that affect expected behavior, patterns the fix should follow, learnings from similar past issues, and human quality preferences (`[[human-profile]]`). This prevents false passes on code that violates vault-documented constraints.
2. **Branch checkout** (#3296): Check out the task's feature branch before verification:
   ```bash
   python references/scripts/git_ops.py task-begin [role] [number]
   ```
   If the branch doesn't exist, task-begin exits non-zero — push back to the submitting agent (#9478: branch+PR is the only mode).
   Run verification on the branch. When done, return to working branch:
   ```bash
   python references/scripts/git_ops.py task-end [role] [number]
   ```
3. Run the relevant test or manually verify the fix.
4. **Test coverage check**: Verify that the fix includes a regression test. Check for new or modified test files corresponding to the changed code. If the fix adds or changes code but includes no tests, reject it.
5. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.
   This flow intentionally never authors a `TEST-PLAN-<N>.md` — issue-flow has no AC-derived TC list to enumerate, so `tracker.py`'s TC-coverage ship gate (task-flow's `TEST-PLAN`/`QA-RESULTS` pairing) structurally never activates for `type:issue` items. Steps 4 and 5 above are this flow's own equivalent guarantee — a required regression test plus a green full suite — enforced directly by the verifier rather than by that script (#13838).
6. If verified (fix works, regression test exists, all tests pass):
   - If a PR exists for this issue, convert from draft to ready:
     ```bash
     gh pr list --search "squidsquad/" --state open --json number,headRefName | python -c "import sys,json; [print(p['number']) for p in json.load(sys.stdin) if '/[NUMBER]' in p['headRefName']]"
     # If a PR number is found:
     gh pr ready [PR_NUMBER]
     ```
   - Transition to pending-ship:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role verifier-lead
     python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Verified. Status → Pending Ship."
     ```
   - Do NOT touch any release counter. Release state (the `Shipped Since Last Bump` counter, version bumps, tags) belongs entirely to the DM under its L4 policy — the verifier verifies and signals `pending-ship`, nothing more (see `docs/DM-ARCH.md` §2: "Release state belongs to the DM, not the verifier").
7. If not verified (fix doesn't work, no regression test, or tests fail):
   - Reopen: `python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role verifier-lead`
   - Comment with specific failures — be specific about missing tests.
