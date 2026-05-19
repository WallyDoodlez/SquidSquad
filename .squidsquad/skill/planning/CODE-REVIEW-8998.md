The grep results confirm every claim in the expected answers:

**Q2 — Wake mechanism**: line 207 (`event_poll.py <role> --wait 5 --target`), line 209 (forge is source of truth), line 282 (forge-read via `tracker.py`), line 283 (`work_queue()`), line 271 (one event at a time), line 275 (cursor auto-advance), line 319 (no mechanical pre/post steps).

**Q4 — Processing flow for event**: lines 279–283 (Case B — idle event arrival: forge-read referenced item → `work_queue()` → pick up top item), lines 296–300 (Case D — mid-task events noted, not acted on), lines 314, 380 (event payloads are hints).

**Q6 — DM learns via status-transition**: line 506 ("emits a `status-transition` event"), lines 235, 290–297 (Monitor stream), lines 487, 505 (bare comments don't wake), lines 495–501 (DM Exception in comment-handling), lines 678–751 (full PR-merge wait fragment).

**Completion-API**: All three occurrences in spec.json are negations. No positive references remain.

The three review criteria are satisfied. The spec.json expected answers for Q2/Q4/Q6 are directly derivable from the fixture content, no legacy completion-API references exist, and the Q1/Q3/Q5 answers (which I cannot fully verify without the polling fixture files) are stated as unchanged and contain no completion-API references.

NO_FINDINGS