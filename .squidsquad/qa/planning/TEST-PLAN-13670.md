# TEST-PLAN-13670

Derived independently from the issue body (`ISSUE: improvement-scan: DM L4 project doc still names deprecated reboot_agent.py CLI`). Filed by dm-lead, fixed inline by PM (own-domain-autofix — `.squidsquad/project/*.md` is PM's domain, direct-to-main commit, no PR).

## ACs derived from the issue

- **AC1**: `.squidsquad/project/dm.md` (both cited locations) and `.squidsquad/project/dm-instructions.md` are repointed from `reboot_agent.py` to the current restart mechanism.
- **AC2**: The replacement text accurately matches `reboot_agent.py`'s own actual deprecation message — not just plausible-sounding wording, the real redirect.
- **AC3**: No regressions — no existing test asserts the old text (nothing to break); full static gate passes.
- **AC4 (comprehension judgment call)**: Not a new-decision-logic change — a factual command-name correction with no interpretive ambiguity for the agent (DM already knows "trigger reboots"; only *which command* changed) — does not independently warrant a new CQ spec under the #9184 comprehension-testing standard, unlike genuine behavioral/logic changes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | `git show e68cc110e` — confirmed both `dm.md` locations (lines ~19, ~68) and `dm-instructions.md:29` updated |
| TC2 | AC2 (live) | Read `references/scripts/reboot_agent.py:145-160` directly — confirmed its actual `stderr` deprecation message reads exactly `POST http://127.0.0.1:7373/agents/<role>/restart` and `squidsquad_cli.py restart <role>`, matching the new doc text verbatim. Also confirmed `reboot_agent.py` now `return 2`s (genuinely broken if invoked per the old instruction) — the old references were a real operational hazard, not just stale prose |
| TC3 | AC3 | `grep -rl reboot_agent tests/*.py` — no test asserts this doc's prose text, nothing to update. `python tests/run_tests.py static` (canonical gate, run against current main since this was a direct commit, no PR) |
| TC4 | AC4 | Checked `comprehension_staleness.py check` — clean; the one spec (`10659_spec.json`) that mentions "dm.md" only uses it as an illustrative filename in unrelated prose, not a tracked content dependency — confirmed via grep, not a real drift |
