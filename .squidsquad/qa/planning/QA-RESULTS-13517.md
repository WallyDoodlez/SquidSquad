# QA-RESULTS #13517 — ASCII-safe gh --title for create-issue/create-task

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps)
**PR**: #13547 (squidsquad/task/13517)
**Branch verified on**: squidsquad/task/13517, combined with current origin/main (branch predated #13434/#13371 merges — see below)

## AC walk (independent, scope = code-only guard per issue body)

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | transliteration before `--title`, both create_issue/create_task | PR's `TestAsciiizeTitle` + my own probes (em-dash, smart quotes, arrows, bullet) | **PASS** |
| AC2 | ascii-encode backstop, no residual can crash gh | PR's `test_residual_non_ascii_replaced_not_crashed` + my own emoji probe, all `.encode('ascii')`-safe | **PASS** |
| AC3 | forge-adapter path unaffected (Unicode preserved) | **Independent** monkeypatched-adapter probe (not in PR's own suite) — adapter received the RAW em-dash title unchanged | **PASS** |
| AC4 | stderr NOTE on alteration | Source confirms `print("NOTE: title transliterated...", file=sys.stderr)` in both functions | **PASS** |
| AC5 | regression coverage + static gate | 12/12 PR tests pass; full static gate on combined state 5437/0 | **PASS** |

## Test runs

- PR's own tests: `TestAsciiizeTitle` (9) + `TestCreateRoutesAsciiTitle` (3) — 12/12 passed
- My own independent black-box probes (not in the PR's suite): additional real-world phrasings (em-dash, smart quotes, arrows, ellipsis, nbsp, bullet, emoji-residual, None) all matched expected ASCII output; forge-adapter path confirmed to preserve Unicode (the PR's own suite only exercises the gh path)
- Full static gate on **combined state**: 5437 gated, 0 failures, 0 errors

## Branch staleness — combined-state verification

`squidsquad/task/13517` forked at `c161bbd1c` (post-#13323, pre-#13434/#13371
— both merged by me earlier this session). Verified the actual post-merge
state via a local `git merge origin/main --no-edit` (no push) — clean merge,
no conflicts. Full static gate on combined state: 5437/0.

## Notes

- `type:issue` severity:low — auto-approved, no human gate.
- No comprehension spec (code-only change, not agent-consumed instructions).
- My own test-harness aside: printing raw Unicode to this cp1252 Windows
  console during ad hoc probing hit the identical class of encoding error the
  fix addresses — had to `sys.stdout.reconfigure(encoding='utf-8')` in my probe
  script first. Confirms the bug class is real and easy to trip over even in
  a throwaway script, reinforcing the fix's value.
