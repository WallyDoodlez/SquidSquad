# QA-RESULTS-12271 — Progress-based agent liveness (UMBRELLA, holistic)

**Verdict: PASS — zero gaps.** Umbrella TASK (no umbrella PR — each slice shipped via its own PR; verified holistically against main). Closes on ship.

## Holistic verification — each umbrella AC realized on main via its slice
| Umbrella AC | Slice(s) | Forge | On main (verified) |
|---|---|---|---|
| Liveness/reboot consume progress signals, not PID | #12492 | CLOSED | `_PROGRESS_LIVENESS_AUTHORITATIVE=True` + `progress_liveness()` authoritative in update_health (2 hits) |
| Inert-but-alive zombie (#10855) detected dead within a bounded window | #12460 + #12492 | CLOSED | bounded progress verdict + zombie kill-step (18 hits) |
| Legitimately busy/booting agent NOT falsely rebooted | #12458 (pause-aware) + #12443/#13213 (activity heartbeats incl. UserPromptSubmit) + #13179 (booting-grace) + #13113 (telemetry-freeze FP removed) | all CLOSED | pause-aware (40 hits), heartbeat/UserPromptSubmit (harness 36 + settings.json 7), BOOT_GRACE_SECONDS (3), #13113 (6) |
| SessionEnd reason recorded + used by reboot decision | #12418 | CLOSED | SessionEnd/last_session_end (44 hits) |
| PID retained only for teardown | #12492 | CLOSED | PID demoted to teardown-only; dead-PID stays the instant crash signal (§15.4) |

## Evidence
- All 8 cited slices CLOSED/shipped on both tracker.py and gh.
- All composite behaviors present + realized on main (grep-confirmed above).
- Full `tests/test_harness.py` = **305 passed** (the composite machinery green); each slice carried its own tests as it shipped.
- I personally verified the most recent slices this session: **#13179** (booting-grace bound), **#13213** (UserPromptSubmit activity hook), **#12492** (the cutover) — all PASS with promoted independent tests.

## Scope notes
- Deterministic harness lifecycle → no CQ.
- Follow-ups (separately tracked, NOT blocking this umbrella): #12416 (thin_launcher — the #10101/#10440 Windows PID liveness-path machinery is now *removable*); #12409 (qa slow-boot loop) retest + close; qa→event-mode move (qa already event-mode this session). Flagged, not reblocked.

Status: pending-test → pending-ship.
