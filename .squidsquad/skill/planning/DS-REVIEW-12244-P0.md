After thorough analysis of the code flow in `load_state`, the `update_health` force-kill and auto-reboot paths, and all test assertions, I find the change is functionally correct. The `if/elif/else` chain properly handles all intent combinations. The force-kill safety net only fires for `STOPPING`/`RESTARTING` intents, so the RESTARTING→RUNNING reset prevents the P0 loop, while STOPPING preservation keeps the operator-stop path intact. Dead agents reboot because `RUNNING` is in `should_reboot`.

However, I found one minor issue:

```
### Finding 1

- **File**: tests/test_harness.py
- **Line**: 311
- **Severity**: warning
- **Issue**: The docstring for `test_load_state_preserves_none_for_running_intent` still states "the migration only applies to STOPPING/RESTARTING". After this change, RESTARTING no longer goes through the migration/seeding path — it is intercepted first and reset to RUNNING. The migration (seeding `time.time()` for absent `intent_set_at`) now applies exclusively to STOPPING.
- **Evidence**: Lines 760–777 in `harness.py` show that RESTARTING is handled by the `if` block (reset to RUNNING, intent_set_at cleared), and only STOPPING falls through to the `elif` seeding path. The docstring on line 311 of `test_harness.py` (unchanged by this diff) claims RESTARTING is still a migration target, which is now false and could mislead future maintainers reading only the test to understand the migration scope.
- **Suggested fix**: Update the docstring to say "the migration only applies to STOPPING" or remove the sentence entirely.
```

**Overall assessment**: The fix correctly addresses the P0 issue. The trade-off (losing an in-flight restart across a harness restart) is explicitly documented in both code comments and test docstrings, and is acceptable — an operator can re-issue the restart against the new harness session. All critical paths (live agent left alone, dead agent auto-rebooted, STOPPING preserved, no force-kill escalation regression) are covered.