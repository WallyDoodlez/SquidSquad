I have completed a thorough R2 verification of all changed files. Here is my assessment:

---

## R2 Verification Results

### (a) F1 — Fully Resolved ✓

`pr-protocol.md` Lane A (lines 73–86) now correctly describes the harness merge endpoint as canonical:

- **Line 79**: `POST http://127.0.0.1:<harness-port>/merge` with `pr_number` / `branch` / `role` — matching `verification.md`'s actual `curl` invocation.
- **Line 80**: `git_ops.py pr-merge` is repositioned as the **non-harness fallback** — "a thin `gh pr merge --squash` wrapper for direct CLI use when the harness is unreachable."
- **Lines 135–136**: Quick-reference table split into two rows — harness canonical row and CLI fallback row.
- **Line 86**: "canonical interface lock vs runtime mechanics" bridging sentence present, establishing `verification.md` as source of truth for implementation details.
- **Lines 79, 84**: Cross-references to `verification.md` for exact curl invocation and event-handling branches.

No remaining merge-tool disagreement between the two files.

### (b) F2 — Fully Resolved ✓

Zero remaining `--role` bare-alias matches in both target files:

| File | Lines Fixed | Status |
|---|---|---|
| `dm/issue-triage.md` | 27, 38 (`--role dm` → `--role dm-lead`) | ✓ |
| `verification.md` | 64, 119, 286, 291, 325, 333, 366, 374, 389 (`--role verifier` → `--role verifier-lead`) | ✓ |

Confirmed via negative-lookahead grep: `--role dm\b(?!-lead)` and `--role verifier\b(?!-lead)` both return zero matches.

### (c) No New Findings ✓

- No bare `gh pr create` commands — all 6 occurrences are normative "do NOT use" statements or cross-references saying "not bare."
- No bare `git rebase` — sole match is `# NOT git rebase` in `pr-protocol.md:119`.
- No bare `gh pr merge` — only in "do NOT appear in this table" exclusion (`pr-protocol.md:141`) and wrapper description (`pr-protocol.md:80`).
- No `--reporter` bare-alias deviations — all use `-lead` suffix.
- `--reporter [ROLE]-lead` (uppercase) confirmed in `improvement-scan-slim.md:10` (was lowercase `[role]`).
- All `→ run sub-skill: tracker-protocol` and `→ run sub-skill: pr-protocol` references consistently formatted.

### (d) D-Lock Invariants — All Hold ✓

| Invariant | Check | Result |
|---|---|---|
| No bare `gh pr create`/`git rebase` | All occurrences normative/negated | ✓ |
| No inline `tracker.py create-*` blocks | All replaced with `→ run sub-skill: tracker-protocol` | ✓ |
| No `create-bug`/`list-bugs` survivors | Only in `tracker-protocol.md:167-170` legacy table | ✓ |
| D-Lock 3 `--reporter` fixes | `dm-lead`, `verifier-lead`, `[ROLE]-lead` all correct | ✓ |
| D-Lock 4 `list-bugs→list-issues` | `dm/issue-triage.md:14` = `list-issues dm` | ✓ |
| tracker-protocol internal consistency | Reporter lock (`-lead` convention) + legacy table (subcommand naming) address distinct concerns | ✓ |
| worker/instructions.md retirement note | Line 68: body templates confirmed absorbed (`tracker-protocol.md:96,112,132,143`) | ✓ |
| Body shapes in tracker-protocol | Bug fix (L96), Feature task (L112), Improvement-scan (L132), Cross-role (L143) all present | ✓ |

---

## Verdict

```
NO_FINDINGS
```