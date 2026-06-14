Now I have a thorough understanding of all the relevant code. Let me produce my findings.

---

### Finding 1

- **File**: D:\Dev\Dev\SquidSquad-2\references\scripts\harness.py
- **Line**: 3261 (and the dedup design at lines 3139–3140, 3257–3262)
- **Severity**: error
- **Issue**: Back-transition starvation — when an issue returns to a previously-emitted status, the `(issue_num, status)` dedup key permanently suppresses a second `assigned-to` event for that status. This is a correctness regression for roles that depend on EAD wake events. The legal transition graph in `tracker.py` explicitly allows cycles, most critically `pending-test → in-progress → pending-test` (lines 124, 137 of tracker.py: `"status:in-progress"` includes `"status:pending-test"` and `"status:pending-test"` includes `"status:in-progress"`). When QA fails verification and returns work (`pending-test → in-progress`), the worker's resubmission (`in-progress → pending-test`) produces no EAD wake because `(N, "status:pending-test")` is already in the dedup set from the first time the issue entered that status. The verifier starves — no wake event for re-verification work.

- **Evidence**: The `_STATUS_ROUTING` map (lines 3125–3130) routes `status:pending-test` to the verifier alias and `status:pending-ship` to dm. The dedup check at line 3261 calls `self.is_emitted(issue_num, status)` which queries a persistent `_emitted_issues` dict keyed by `(issue_num, status)` (line 3152). Once an `(issue_num, status)` tuple is inserted (line 3306), it is never removed except via FIFO eviction at 500 entries (lines 3159–3161). The legal transitions `pending-test → in-progress → pending-test` and `pending-ship → in-progress → pending-ship` (tracker.py lines 199, 137) mean an issue can legitimately re-enter a previously-emitted status. The EAD will not re-emit because dedup is permanent. The test at line 3217 (`test_dedup_per_issue_status_across_transitions`) only validates forward transitions (approved→pending-test), not back-transitions.

- **Suggested fix**: When `_check_for_changes` observes an issue whose current status is NOT in `_STATUS_ROUTING` (e.g. `in-progress`), clear all dedup entries for that `issue_num` — the issue has left the routed state, so a future re-entry should trigger a fresh emission. For example, before the `continue` on line 3278, iterate `_emitted_issues` under lock and delete any key whose first element matches `issue_num`. This correctly handles the gap where the EAD doesn't see the intermediate status (since it only polls current state, not transitions).

---

### Finding 2

- **File**: D:\Dev\Dev\SquidSquad-2\references\scripts\harness.py
- **Line**: 3261–3262 (dedup check) and 3306 (mark emitted)
- **Severity**: error
- **Issue**: Dedup entries for non-routed statuses are never created, but they could prevent a future legitimate emission if the issue later transitions to a routed status without an `updatedAt` bump. Consider: an issue is at `status:in-progress`, `updatedAt=T1`. The EAD polls, finds it unmapped (line 3276-3278, `continue` without `mark_emitted`). Later, the issue transitions to `status:pending-test` but the transition is done via a method that doesn't update `updatedAt` (unlikely with GitHub's API, but possible via direct label edits or some forge adapters). The time filter at line 3270 checks `updatedAt > _last_check_epoch`. If `updatedAt` is still T1 and `_last_check_epoch` has advanced past T1, the issue is permanently invisible to the EAD — no time-filter pass AND no dedup entry to clear.

- **Evidence**: `_last_check_epoch` monotonically advances (line 3308, set every poll). If an issue's `updatedAt` doesn't change between polls (e.g., a label-only edit that doesn't bump the GitHub timestamp, or a forge adapter that handles transitions without updating `updatedAt`), it's filtered out at line 3271-3272. Since the unmapped statuses don't create dedup entries, there's no "already handled" record — the issue is simply never seen again.

- **Suggested fix**: This is a narrow edge case (GitHub bumps `updatedAt` on any label change), but the defensive fix is to call `mark_emitted(issue_num, status)` for UNMAPPED statuses as well — marking them as "seen and intentionally skipped" — so there's a record that the EAD evaluated and deliberately chose not to emit. Alternatively, document that the EAD assumes `updatedAt` always bumps on every status transition.

---

### Finding 3

- **File**: D:\Dev\Dev\SquidSquad-2\references\scripts\harness.py
- **Line**: 3287
- **Severity**: warning
- **Issue**: Only the first sorted `role:*` label is used for worker routing. If an issue legitimately carries multiple `role:*` labels (e.g., cross-cutting work assigned to both `skill` and `dm`), only the alphabetically-first role receives the `assigned-to` wake event. The other assigned roles are silently skipped with no event.

- **Evidence**: Lines 3287-3290: `role_labels = sorted(l for l in labels if l.startswith("role:"))` then `target_alias = role_labels[0].replace("role:", "")`. Only `role_labels[0]` is used. The `continue` on line 3289 fires only when `role_labels` is empty. When multiple role labels exist (e.g. `["role:dm", "role:skill"]`), `role_labels[0]` = `"role:dm"` and `"skill"` gets no wake event. The comment at lines 3284-3286 asserts "the `role:*` label always carries the routed alias" — but this is about the label VALUE being an alias, not about cardinality. It doesn't address multi-role issues.

- **Suggested fix**: Either iterate all `role_labels` and emit one `assigned-to` per role (each with its own `target_alias`), or add explicit documentation that the EAD intentionally wakes only one worker per issue and multi-role assignment is out of scope.

---

### Finding 4

- **File**: D:\Dev\Dev\SquidSquad-2\references\scripts\tracker.py
- **Line**: 1263
- **Severity**: warning
- **Issue**: The emit-role stripping in `transition` uses a different normalization path than the authority check, creating inconsistent behavior during the #6274 dual-aware window. `_canonicalize_role("verifier-lead (tester)")` returns `"qa"` (mapping `verifier` → `qa` via `_DUAL_ROLE_PREFIXES_6274` at line 292), but the emit strip `(role or "unknown").split(" ")[0].replace("-lead", "")` produces `"verifier"`. The event's `role` field is `"verifier"` while the authority check was performed against `"qa"`. The harness HTTP allowlist at harness.py line 2079 uses `_get_all_roles()` which (at line 152 of boot_remote.py) returns `"qa"`, not `"verifier"`. This means status-transition events emitted with `role="verifier"` would be dropped (204) if posted via HTTP. However, `event_bus.emit` may bypass this — depending on whether it POSTs to the harness or calls `_emit_event` internally.

- **Evidence**: `_canonicalize_role` at tracker.py lines 219-273 maps `verifier` → `qa` via the dual table. The emit strip at line 1263 does not. The `comment` function at line 1337 uses the same strip (`role.split(" ")[0].replace("-lead", "")`), so the two emit sites are CONSISTENT with each other — but both diverge from `_canonicalize_role`. During the #6274 dual-aware window, this means events carry `"verifier"` while the authority table uses `"qa"`. The harness allowlist (harness.py line 2079) calls `boot_remote._get_all_roles()` which (boot_remote.py line 152) hardcodes `"qa"` not `"verifier"`. If `event_bus.emit` goes through the HTTP endpoint, the event is dropped.

- **Suggested fix**: Use `_canonicalize_role(role)` (or `_canonicalize_role(role) or "unknown"`) for the emit role in both `transition` and `comment`, so the emitted role matches what the harness allowlist expects during the dual-aware window. After #6274.3 cutover (when `_DUAL_ROLE_PREFIXES_6274` flips), `_canonicalize_role("verifier-lead")` would return `"verifier"` and everything aligns.

---

### Finding 5

- **File**: D:\Dev\Dev\SquidSquad-2\references\scripts\harness.py
- **Line**: 3158–3161 (eviction) and 3261 (dedup check)
- **Severity**: warning
- **Issue**: FIFO eviction of the `_emitted_issues` dict can cause spurious re-emission when an `(issue_num, status)` tuple is evicted and the issue later transitions back to that same status (or, more likely, a comment bumps `updatedAt` while the issue is still in that status). The old single-key `issue_num` design had the same eviction window, but the new tuple-key design increases the number of entries per issue (one per status transition), making eviction more likely in repos with many issues that traverse many statuses. Once an entry is evicted, the time-filter+dedup defense is weakened: a comment bump passes the time filter, and the absent dedup entry allows a duplicate `assigned-to` emission.

- **Evidence**: Lines 3159–3161 evict the oldest-added tuple when `len(_emitted_issues) > 500`. Each issue can produce up to 4 entries (open, approved, pending-test, pending-ship). At 500 entries, ~125 issues can be fully tracked. Beyond that, FIFO eviction removes the oldest entries. If issue #1's `(1, "status:approved")` entry is evicted and someone comments on #1 (bumping `updatedAt`), the EAD re-emits an `assigned-to` for an issue that was already approved long ago. The old per-issue-number dedup was coarser but more compact (500 entries = 500 issues). The new design effectively reduces the tracked-issue capacity by a factor equal to the average number of routed statuses an issue visits.

- **Suggested fix**: Increase the eviction bound (e.g., 2000) to compensate for the tuple-key expansion, or switch to a per-issue eviction strategy where evicting one issue removes all its status entries atomically (e.g., track `(issue_num, last_emitted_statuses_set)` or use an LRU structure keyed by `issue_num` with a nested set of statuses).