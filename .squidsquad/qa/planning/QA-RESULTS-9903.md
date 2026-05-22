# QA Results — #9903 (cycle_pre.py wedges on Windows — WMI in platform.system())

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 10:01 cycle 728
**Fix commit**: e7a47737 (direct-to-main hotfix; same commit closes #9905)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Cross-reference

This issue is a companion to #9905 (verified pending-ship last cycle, 727). Both root causes — the WMI hang inside `platform.system()` (#9903) and the 26 s `tasklist` shell-out (#9905) — were fixed in the single emergency commit `e7a47737`. I am applying the same verification evidence here, with the #9903-specific reproduction.

## Diagnostic stacktrace from issue body

```
process_utils.py:32 is_process_alive    # platform.system().lower()
Lib/platform.py:922 uname
Lib/platform.py:450 win32_ver
Lib/platform.py:388 _win32_ver
Lib/platform.py:327 _wmi_query           # <-- blocked here
```

Verification: `grep "platform.system()"` across `references/scripts/` returns 6 hits, all inside docstrings/comments explaining why the code now uses `sys.platform` (a compile-time constant). The actual `platform.system()` call shown at the top of the stacktrace no longer exists in the wedge path.

## Reproduction from issue body

`python references/scripts/health_check.py --json` — pre-fix hangs > 8 s, no exit. Post-fix this cycle: **0.078 s, exit 1, valid JSON output**. (Same evidence as #9905 because the same subprocess is the test.)

## Tests

`pytest tests/test_process_utils.py tests/test_thin_launcher.py tests/test_health_check.py tests/test_cycle_pre.py` → **195 passed in 1.00 s** (verified last cycle while clearing #9905; same commit).

## Soft signal

This QA agent successfully completes `cycle_pre.py qa` every 30 minutes — exactly the wedge path described in the issue body. The diagnostic was reproduced by PM-lead with a faulthandler stacktrace; the absence of the wedge is reproduced by every cycle this session.
