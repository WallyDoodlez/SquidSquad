# TEST-PLAN-12823 — config.md merge=ours silently drops concurrent non-counter changes

Bug (type:issue/medium, auto-approved), filed by dm. PR #12982, branch
`squidsquad/task/12823`, role:skill. No explicit AC list → ACs derived from the
evidenced root-cause + remediation (option 1 chosen: split counter). config/gitattributes
infra → **no CQ**. Verified in isolated worktree `D:\Dev\Dev\sq-12823-verify`.

## Derived ACs
- **AC1 (root fix — no silent drop):** config.md no longer carries `merge=ours`; a
  concurrent non-counter config edit by another agent SURVIVES a 3-way merge
  (non-overlapping → merges cleanly; overlapping → surfaces as a conflict). Neither
  silently dropped (the original bug).
- **AC2 (counter still protected):** the DM ship counter retains ours-wins protection in
  its own `.squidsquad/.ship-counter` file (a stale sibling clone's push can't regress a bump).
- **AC3 (storage redirect + migration):** config.py `get_field`/`set_field` for the counter
  redirect to `.ship-counter`; `_read_ship_counter` falls back to the legacy config.md field
  for in-place upgrades; default 0 when neither present; first write migrates.
- **AC4 (git_ops staging):** `.ship-counter` is in the role-owned commit patterns so the
  writing role (DM bump/reset) can stage it.
- **AC5 (regression test):** locks the storage redirect + the .gitattributes split.
- **(Doc)** the git_ops KNOWN-LIMITATION (#9474) comment updated to RESOLVED (#12823).

## Test cases / evidence
- **TC1 (AC1 LIVE — the core proof):** isolated temp git repo using the branch's
  `.gitattributes`: (a) far-apart edits (DM Name + skill Flag) → auto-merge CLEAN, both
  preserved, no conflict; (b) adjacent edits → CONFLICT but BOTH preserved (no silent drop).
  Both confirm the bug is fixed (old merge=ours would silently drop one side).
- **TC2 (AC1 .gitattributes):** config.md `merge=ours` removed; `.squidsquad/.ship-counter merge=ours` added.
- **TC3 (AC2/AC3)** — test_12823_ship_counter_split.py (storage read/write/migration/default + gitattributes split).
- **TC4 (AC4)** — git_ops `_role_owned_patterns` common list includes `.squidsquad/.ship-counter`.
- **TC5 (no-reg)** — test_12823 + test_config_functions + test_git_ops → 246 passed; full static gate (pending — see QA-RESULTS).
