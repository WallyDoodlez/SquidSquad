Now I have a comprehensive picture. Let me compile the findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 125 (AC1.1) vs line 113 (D10)
- **Severity**: error
- **Issue**: AC1.1 and D10 contradict each other on where the 6274.1 dual-aware test lives. AC1.1 says "Verified by `test_compose.py::test_dual_aware_identities`" — placing the test inside the existing `test_compose.py` file. D10 says "New unit test `test_terminology_dual_aware_6274.py` covering both old and new name resolution" — a separate new file. An implementer reading both would be confused about where to put the test.
- **Evidence**: The two statements specify mutually exclusive locations — one is a function within an existing test module, the other is a brand-new test file. They cannot both be satisfied as written.
- **Suggested fix**: Either (a) change AC1.1 to reference `test_terminology_dual_aware_6274.py::test_dual_aware_identities`, or (b) change D10 to say the new test goes into `test_compose.py` as `test_dual_aware_identities`. Pick one and align both sections.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 130 (AC1.6) vs lines 101-106 (D9)
- **Severity**: error
- **Issue**: AC1.6 requires the vault note `migration-6274-cutover` to be created in sub-phase 6274.1 "with target cutover date (T+30 days from 6274.2 merge)." However, at the time 6274.1 lands, the 6274.2 merge date is unknown — it could be days or weeks later. The note cannot be created with a concrete cutover date that doesn't yet exist. This makes AC1.6 unsatisfiable as a 6274.1 acceptance criterion.
- **Evidence**: D9 states 6274.1 is first in sequence, 6274.2 is second. The 30-day window in D3 "starts when sub-phase 6274.2 merges." At 6274.1 time, the merge date of 6274.2 is unknowable, so the note can't contain the cutover date.
- **Suggested fix**: Split AC1.6: (a) 6274.1 creates the vault note as a placeholder with a `TODO: fill after 6274.2 merge` marker, and (b) add a new AC to 6274.2 or its post-merge checklist to populate the actual cutover date into the note after the 6274.2 PR merges.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 37-42 (D2) vs RESEARCH-6274.md lines 86-88 and actual code at `references/scripts/compose.py` lines 465, 474, 665-693, 703
- **Severity**: error
- **Issue**: D2's implementation specification for the dual-aware shim omits critical functions that RESEARCH §4 identified and that the actual code requires. Specifically: (a) `_get_entry_file_for_role()` (line 665) — the central role-identity resolver that every compose path calls, which contains hardcoded `"dev"` at line 689 and calls `_list_known_role_identities()` and `_resolve_variant()`; (b) `_active_roles_for_roster()` (line 454) — hardcodes `"qa"` at line 465 and `"dev"` at line 474 in the manifest fallback path; (c) `boot_remote.py._get_all_roles()` line 127 — hardcodes `{"pm", "qa", "dm"}` for mandatory roles; D2 only mentions `_parse_dev_agents()` in boot_remote.py but not this function; (d) `compose.py` line 703 — `is_dev = entry_file == "dev"` boolean gate would silently break dev-specific placeholder substitution when `entry_file` becomes `"worker"`.
- **Evidence**: RESEARCH §4 explicitly lists `_get_entry_file_for_role()` as a critical-path function. The actual code at lines 465, 474, 689, 703, and boot_remote.py line 127 all contain hardcoded `"dev"` or `"qa"` strings that must be updated in the dual-aware shim. D2 mentions only `_list_known_role_identities()`, `_resolve_variant()`, `config.py.get_field()`, `_parse_dev_agents()`, and `add_role.py` — missing at least 4 other load-bearing touchpoints.
- **Suggested fix**: Extend D2's implementation list to explicitly include: `_get_entry_file_for_role()` dual-aware logic, `_active_roles_for_roster()` mandatory-set update (`"qa"` → `"verifier"` + `"dev"` → `"worker"`), `boot_remote.py._get_all_roles()` set update, and the `is_dev` comparison at line 703 (should become `entry_file in ("dev", "worker")` during the window).

---

### Finding 4

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 38-39 (D2 path-resolution claim) vs `references/scripts/compose.py` lines 1122-1147, 386-391
- **Severity**: error
- **Issue**: D2 claims "Both `references/roles/dev/skill/` and `references/roles/worker/skill/` paths resolve correctly during the window." It also says `_resolve_variant("dev-skill")` returns `(dev, skill)`. After sub-phase 6274.2 renames `references/roles/dev/` → `references/roles/worker/`, the old directory literal `references/roles/dev/skill/` no longer exists on disk. But the returned tuple `(dev, skill)` is used directly for filesystem path construction (e.g., line 388: `ROLES_DIR / base / variant`). Returning `(dev, skill)` and constructing `ROLES_DIR / "dev" / "skill"` would point to a nonexistent directory. D2 doesn't specify whether `_resolve_variant` should remap the return tuple to the new identity, or whether every call site must add a fallback path lookup. The dual-aware mechanism as specified cannot simultaneously return old identity tuples AND have old paths physically resolve after the rename.
- **Evidence**: `_resolve_variant` at line 1140 constructs `ROLES_DIR / base / variant` and checks `is_dir()`. If `base="dev"` and the directory was renamed to `worker/`, this check fails. The downstream call site at line 388 then constructs the same path and calls `.exists()` — also fails. D2's spec has no mechanism to bridge the gap between returning `(dev, skill)` and locating the file at `worker/skill/`.
- **Suggested fix**: Specify that during the dual-aware window, `_resolve_variant` normalizes old base names to new ones in its return value: both `"dev-skill"` and `"worker-skill"` return `("worker", "skill")`. This makes path construction always use the new directory. For identity-level backward compat (code that checks `base == "dev"`), add a separate `_canonical_role_name()` helper or expand `_get_entry_file_for_role()` to accept both. Alternatively, add a fallback filesystem check at every path-construction call site.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 92 (D7 L4 dual-prefix claim) vs `references/scripts/compose.py` lines 398-410
- **Severity**: error
- **Issue**: D7 claims compose.py's L4 prefix routing "reads both old and new prefixes during the dual-aware window." The actual code at lines 400-410 filters L4 stub files by a single `role_identity` (determined by `_get_entry_file_for_role`) against `known_prefixes`. If `role_identity` is `"dev"`, then `worker-*.md` files are skipped due to the `file_prefix != role_identity` guard at line 409. If `role_identity` is `"worker"`, then `dev-*.md` files are skipped. The current routing architecture has no mechanism to accept BOTH prefixes simultaneously for a single agent. Making this work requires either: (a) changing the filtering logic to accept both `dev` and `worker` as valid prefixes during the window, or (b) renaming all L4 files to the new prefix simultaneously with the directory rename (eliminating the need for dual-read). D7 claims the former but neither mechanism is specified.
- **Evidence**: Line 408: `if file_prefix and file_prefix != "shared" and file_prefix in known_prefixes:` and line 409: `if file_prefix != role_identity: continue`. The `role_identity` is a single string, not a set. A single agent can only match one prefix.
- **Suggested fix**: Either (a) specify that during the dual-aware window, the L4 filtering logic at line 409 becomes `if file_prefix != role_identity and (role_identity not in {"dev", "worker"} or file_prefix not in {"dev", "worker"})` — allowing cross-matching between old and new prefixes, or (b) acknowledge that L4 dual-aware is infeasible with the current routing architecture and instead rename the seed files to new prefixes in 6274.2 (matching the directory rename), keeping only the live `.squidsquad/project/` files as the dual-awareness concern (which the wizard upgrade handles).

---

### Finding 6

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 158 (G2.→3)
- **Severity**: warning
- **Issue**: The G2.→3 gate requires "zero new `role:dev` / `role:qa` labels created in the trailing 7 days (script-verified)" but no script is named, specified, or even sketched in the ACs or locked decisions. The only label-related scripts defined are `migrate_labels_6274.py` (AC1.5, initial dual-labeling of OPEN issues) and `cleanup_labels_6274.py` (AC3.4, final label deletion). Neither of these checks the trailing-7-days condition. QA would need to write an ad-hoc `gh api` query to verify this gate, making it nondeterministic — different QA operators would implement the check differently.
- **Evidence**: D3 says the 30-day window is "Tracked via vault note" with no detection script. AC1.5 and AC3.4 specify scripts for different purposes. The gate's own text says "script-verified" but defines no script.
- **Suggested fix**: Add a concrete AC or specify a named script for the G2.→3 verification. For example: add `AC2.X — Script references/scripts/check_label_migration_readiness_6274.py queries GitHub API for issues labeled role:dev or role:qa created in the last 7 days; exits 0 if zero found, exits 1 with counts otherwise. This script is the gatekeeper for G2.→3.` Or fold the check into `cleanup_labels_6274.py` as a `--verify` flag.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 60-66 (D4)
- **Severity**: warning
- **Issue**: D4 describes 4 sequential mutation operations on a per-install directory (config.md rewrite, two directory renames, harness-state.json update). Only the config.md rewrite is claimed atomic ("Rewrites config.md atomically"). The directory renames have no transaction boundary. On Windows, directory renames can fail with a file lock if an agent is running from that directory. If step 1 succeeds (config.md rewritten to `Workers:`) but step 2 fails (`.squidsquad/dev/` locked), the install is in a broken state: config says `Workers: skill` but the per-install directory is still at `.squidsquad/dev/`. D4's idempotency claim ("re-running detects 'already migrated' and no-ops") would then prevent recovery: detection of "already migrated" almost certainly checks config.md for `Workers:`, finds it, and no-ops, leaving the directory rename permanently undone.
- **Evidence**: D4 lists 4 operations with no rollback or transaction. The only atomicity claim applies to a single operation. Windows file-lock behavior is a known issue (D2 itself calls out "brittle on Windows" for symlinks, acknowledging the platform concern). D2's rollback strategy ("revert the shim code; old paths still work since files haven't moved yet") applies to code-level shims, not to per-install directory mutations.
- **Suggested fix**: (a) Implement the upgrade as a multi-check transaction: verify all directories are renameable before touching config.md, or (b) add a `--fix` mode that detects partial failures (config rewritten but directories not renamed) and completes the migration, or (c) make the idempotency check look at the directories, not config.md — detect "migrated" when `.squidsquad/worker/` exists, and detect "partial" when config has `Workers:` but `.squidsquad/worker/` doesn't exist.

---

### Finding 8

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 89 (D7 file count)
- **Severity**: warning
- **Issue**: D7 claims "4 files: `dev-instructions.md`, `dev-soul-directives.md`, `dev-responsibility.md`, and any future dev-prefixed." The actual filesystem under `references/sub-skills/project/` contains exactly 3 dev-prefixed files (`dev-instructions.md`, `dev-responsibility.md`, `dev-soul-directives.md`). The claim of "4 files" with an enumeration of only 3 named files is inconsistent. The glob `dev-*.md` would correctly catch all existing files regardless, but the count mismatch means the implementer can't verify correctness against the spec.
- **Evidence**: `glob` of `references/sub-skills/project/dev-*.md` returns exactly 3 files. D7 says "4 files" but lists 3.
- **Suggested fix**: Correct the count to "3 files" or explain what the 4th file is if it's expected to exist by the time 6274.2 lands.

---

### Finding 9

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 114 (D10 test list) vs `tests/test_pickup_comment_fidelity_9946.py` lines 30-34
- **Severity**: warning
- **Issue**: The #9946 pickup-comment-fidelity regression test (`tests/test_pickup_comment_fidelity_9946.py`) hardcodes paths to `references/roles/dev/` at lines 30-34 (`DEV_TEMPLATE`, `DEV_POLL_MANIFEST`, `DEV_EVENT_MANIFEST`, `IMPLEMENT_TASKS`, `TRIAGE_ISSUES` — all rooted at `references/roles/dev/`). When sub-phase 6274.2 renames `references/roles/dev/` → `references/roles/worker/`, these tests will break. D10's 6274.2 test update list enumerates `test_compose*.py`, `test_config*.py`, `test_boot_remote*.py`, `test_add_role*.py`, `test_wizard*.py`, `test_agent_boundaries.py` — it does NOT include `test_pickup_comment_fidelity_9946.py`. This test was shipped post-#9946 and is not accounted for in the D10 rename sweep.
- **Evidence**: Lines 30-34 of the test file use `REPO / "references" / "roles" / "dev" / ...` for 5 separate path constants. D10 line 114 lists 6 test files/groups but omits this one. RESEARCH §3 explicitly calls out the #9946 sub-skill as relevant context for this rename task.
- **Suggested fix**: Add `test_pickup_comment_fidelity_9946.py` to the D10 6274.2 test update list, or expand the glob to `test_*.py` to catch all test files that reference role paths. Also verify whether the pickup-comment-fidelity sub-skill's own includes.yml references in `references/roles/dev/includes.yml` and `references/roles/dev/includes-events.yml` (confirmed present via grep) are covered by D2/D5 directory rename.

---

### Finding 10

- **File**: `.squidsquad/pm/planning/CONTEXT-6274.md`
- **Line**: 158 (G2.→3 second condition)
- **Severity**: warning
- **Issue**: The G2.→3 gate's 30-day window condition and the D3 30-day window definition create a subtle timing race. D3 says "30-day window starts when sub-phase 6274.2 merges." G2.→3 says 6274.3 can land when "30-day window elapsed AND zero new `role:dev` / `role:qa` labels created in the trailing 7 days." If an issue is created with `role:dev` on day 29 (the old label being applied by a pre-upgrade install that hasn't run the wizard yet), the trailing-7-days check on day 30 would see it and block 6274.3. The window restarts implicitly — the spec says to wait until zero new old labels for 7 days, but doesn't specify how many times to retry, how long to wait between checks, or whether the 30-day window is a hard floor or a rolling gate.
- **Evidence**: D3 states the window duration (30 days). G2.→3 adds a co-condition (trailing 7 days clean). If the window elapses but the trailing-7-days condition fails, what happens? Is it "wait another 7 days" or "re-check daily"? The spec is silent. Without this, QA can't determine deterministically when G2.→3 is satisfied.
- **Suggested fix**: Specify the retry cadence: "If the 30-day window has elapsed but the trailing-7-days check fails, re-check daily until the condition is met. The gate is satisfied when BOTH conditions are true on the same check." Add this to G2.→3 or to a new risk-mitigation row.

---

These 10 findings cover the review criteria systematically — contradictions (F1, F8), unsatisfiable ACs (F2), gate verifiability gaps (F6, F10), D2/D7 mechanism underspecification (F3, F4, F5), D4 rollback risk (F7), and #9946 interaction (F9).