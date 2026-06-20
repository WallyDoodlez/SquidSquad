I now have a complete picture. Let me compile my findings.

---

### Finding 1

- **File**: references/scripts/tracker.py
- **Line**: 612–694 (repair_status_labels function), specifically the keep/remove logic at lines 667–668
- **Severity**: error
- **Issue**: `repair_status_labels` unconditionally strips `status:pending-ship` from every CLOSED issue that lacks `status:shipped`. This destroys the legitimate #9837 "closed-but-undelivered" pattern — where a PR containing `Closes #N` auto-closes the issue before DM performs the `pending-ship → shipped` transition. After `--apply`, those issues lose their only status label and vanish from DM's delivery query (`list_issues` with `state=all` for `pending-ship`), causing permanently missed deliveries.

- **Evidence**: 
  - `list_issues()` at line 560 explicitly widens to `state=all` for `pending-ship` and `shipped` precisely *because* PR auto-close creates closed-but-undelivered issues: line 536–538 docstring: *"The GitHub issue may already be CLOSED because PRs auto-close their linked issues via 'Closes #N' body — the label survives but the issue state flips to closed BEFORE DM gets to transition it off pending-ship."*
  - `repair_status_labels` at line 667: `keep = {shipped_label} if shipped_label in status_now else set()` — when `status:shipped` is absent, `keep` is empty and the orphan label plus any other status labels are all removed (line 668: `remove = sorted(status_now - keep)`).
  - A legitimately auto-closed-but-undelivered issue has exactly `{status:pending-ship}` — no `status:shipped`. The function strips `status:pending-ship`, leaving the issue with zero `status:*` labels. DM's `list_issues` with `--status pending-ship` (which queries `state=all`) can no longer find it.
  - The docstring at lines 618–623 acknowledges the #9837 pattern but the code does not protect against it.

- **Suggested fix**: Two layers of defense are appropriate:
  1. **Heuristic guard**: Before stripping, check whether the issue has ever had `status:shipped` applied (e.g., check the issue timeline/events for a `shipped` label-add event). If it was never shipped, treat it as a genuine closed-but-undelivered case and skip it (or at minimum surface a prominent warning). Alternatively, check for a linked merged PR — if one exists and the issue was closed by it, the issue likely needs shipping.
  2. **Minimum bar**: At the very least, when `status:shipped` is absent, the function should emit a **WARNING** per-issue (not just the dry-run listing) that says *"#{N} is closed with status:pending-ship but no status:shipped — this may be a legitimate undelivered issue (PR auto-close). Verify before applying."* Currently there is no such warning; the `--apply` path silently strips the label.

---

### Finding 2

- **File**: references/scripts/tracker.py
- **Line**: 640–655 (the gathering phase of repair_status_labels)
- **Severity**: warning
- **Issue**: The `gh issue list` query uses `--limit 1000` with no pagination loop. The comment at line 640–641 says *"the set can exceed one page — the pollution is unbounded until repaired, so request a high limit"*, but a single `--limit 1000` call without iterating `--page` silently truncates results above 1000. While the current pollution is ~30 issues, the code's stated intent is to handle an unbounded set.

- **Evidence**:
  - Line 647–649: `["gh", "issue", "list", "--label", ship_label, "--state", "closed", "--json", "number,labels", "--limit", "1000"]` — no `--page` parameter, no loop.
  - Line 643–644: the adapter path has the same single-call pattern: `adapter.list_issues(labels=[ship_label], state="closed", limit=1000)`.
  - The docstring at line 640–641 acknowledges the set *"can exceed one page."*

- **Suggested fix**: Either (a) add a pagination loop (`--page 1`, `--page 2`, ...) until an empty page is returned, or (b) reduce the claim in the comment from *"ALL closed issues"* to *"up to 1000 closed issues"* and document the limit as a known constraint. Given the cleanup is idempotent (each run shrinks the set until it fits in one page), and the durable fix in `transition()` prevents new accumulation, pragmatically the comment adjustment alone may suffice.

---

### Finding 3

- **File**: references/scripts/tracker.py
- **Line**: 667–668 (the keep/remove logic in repair_status_labels)
- **Severity**: warning
- **Issue**: When `status:shipped` is absent, `keep = set()` causes `remove = sorted(status_now)`. If the issue carries multiple stale `status:*` labels (the very multi-label pollution the function is designed to fix — e.g., `status:approved, status:pending-ship`), ALL are removed, leaving the closed issue with **zero** `status:*` labels. A closed issue with no status label is an undefined/invisible state that may cause confusion in future queries or audits.

- **Evidence**:
  - The docstring at line 626–629 says: *"reduce its status labels to a single terminal status: keep status:shipped when present ... otherwise strip the orphan entirely."* The function interprets *"strip the orphan entirely"* as removing ALL `status:*` labels, not just the orphan.
  - The described multi-label issue (line 1394–1395: *"one issue carrying approved+pending-ship+shipped"*) is handled correctly because `shipped` is present. But if the same issue had `approved+pending-ship` without `shipped` (e.g., a closed issue that leaked `approved` before reaching `pending-ship`, then was closed without ever being shipped), BOTH labels are removed. The issue is left label-less in the status dimension.
  - This isn't necessarily wrong (the issue is closed and may not need any status), but it's a more aggressive action than *"strip the orphan"* implies, and it leaves the issue in a state the taxonomy doesn't define.

- **Suggested fix**: Consider keeping the *first* terminal-appearing label in `status_now` rather than stripping everything. For instance, if `status:shipped` is absent but `status:approved` is present, keep `status:approved` (or another non-pending-ship label) as the surviving status rather than blanking the issue. The comment at line 629 *"strip the orphan entirely (closed, no delivery owed)"* should be refined to clarify that ALL status labels are removed, not just the orphan, and that this is intentional.

---

**Summary on the four review questions:**

**(a) transition() unconditional strip-all**: No regression found. The new behavior is a strict superset of the old: identical in the common single-label case, strictly better when stale labels have accumulated. The empty-`{to_label}` case is handled correctly (remove set empty, add is a no-op). The idempotent re-transition case works correctly.

**(b) Empty-live_status fallback to `[from_label]`**: Safe. This is the same fallback the old force-path used. On API failure or a label-less issue, behavior is identical to the old normal path. No worse outcome is possible.

**(c) repair_status_labels vs. #9837**: **NOT inherently safe** — see Finding 1. The closed scope alone does not distinguish between "stale orphan from a leaked label" and "legitimate closed-by-PR, awaiting DM ship." The dry-run default is the only safeguard. Deferring `--apply` to DM is the correct call, but the function should actively warn about ambiguous cases rather than silently stripping them.

**(d) Idempotency, paging, adapter parity**: Idempotency is correct — after a clean pass, no issues match the query. Paging is limited to 1000 (Finding 2). Adapter parity looks correct — `adapter.edit_labels(number, add=[], remove=remove)` uses the same base method as `transition()` does at line 1412, and the `edit_labels` implementation at forge_adapter.py:128–133 handles empty `add`/`remove` lists correctly via falsy checks.