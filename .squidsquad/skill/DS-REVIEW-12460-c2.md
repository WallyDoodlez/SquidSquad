After thorough analysis of all five review criteria against the changed code:

**1. Behavior change?** No. Lines 584-593 only compute `progress_liveness()` and conditionally log. `alive` is never reassigned, no agent state is mutated, and no decision variable (reboot, status, intent) is touched.

**2. Under `self._lock`?** Yes. `with self._lock:` is entered at line 523, before the `for role in all_roles:` loop at line 524. The divergence logging at lines 584-593 sits at 16-space indent — inside both the lock and the loop. The lock is not released until after line 934.

**3. Exception safety?** `progress_liveness()` (lines 333-380) and `active_pause()` (lines 291-317) perform only attribute access, `is None` checks, and arithmetic on floats. No I/O, no external calls. The only theoretical risk is corrupted state-file data (e.g., a string smuggled into `last_dispatch_at` via manual JSON editing) causing `TypeError` on `now - self.last_dispatch_at`. This risk is identical to the existing unprotected `agent.active_pause(now)` call at line 744 and `agent.stopfailure_backoff_due(now)` at line 778 — the codebase consistently leaves pure in-memory method calls unwrapped while wrapping I/O calls (lines 525-528, 557-568, 634-640). The new call follows the established pattern.

**4. Log volume?** A persistent zombie would log one line per 5-second poll (~720 lines/hour). This is by design for a temporary shadow/observational phase explicitly gated on "showing no false positives/negatives over a real window" before the cutover. The commit message frames this as data collection, not a permanent logging statement.

**5. Placement correctness?** `alive` is finalized by line 564 (three-stage PID → file-PID → legacy-health check). It is never reassigned between line 564 and the force-kill block at line 595. The divergence log at 584 reads `alive` in its final state. Logging *before* the force-kill at 595 is also correct — the force-kill may terminate the process, which would make a post-kill divergence log inaccurate.

```
NO_FINDINGS
```