I now have all the evidence needed. Here are my findings:

---

### Finding 1

- **File**: `references/sub-skills/common/pr-protocol.md`
- **Line**: 78 (in context with `references/sub-skills/roles/verifier/verification.md` lines 318–325, 345)
- **Severity**: error
- **Issue**: `pr-protocol.md` Lane A establishes `git_ops.py pr-merge <PR_NUMBER> --strategy squash` as the verifier's canonical merge command (line 78) and the quick-reference table (line 129) repeats it. However, `verification.md` uses a completely different merge mechanism — `curl -s -X POST http://localhost:7373/merge` (lines 319, 347 of the prompt version) — and has **zero references** to `pr-protocol.md` or `git_ops.py pr-merge`. The two files disagree on which tool performs the merge.
- **Evidence**: D-Lock 1 requires "pr-protocol's two-lane merge protocol matches roles/verifier/verification.md + roles/dm/delivery-packaging.md (the role-side procedures it cross-refs)." A grep of `verification.md` for `git_ops.py pr-merge` and `pr-protocol` returns zero matches. A grep of `pr-protocol.md` for `curl.*7373|localhost:7373` returns zero matches. The verifier's merge flow in `verification.md` is also gated on `auto-merge` config and `PR Flow` yes/no branching — gates that `pr-protocol.md` never mentions in Lane A (lines 73–82). The two documents describe different merge procedures with different tools and different gating logic.
- **Suggested fix**: Either (a) update `verification.md` to delegate merge mechanics to `pr-protocol.md` via `→ run sub-skill: pr-protocol` and replace its `curl` harness calls with `git_ops.py pr-merge --strategy squash` per the canonical lock, or (b) update `pr-protocol.md` to acknowledge the harness as the underlying merge mechanism that `git_ops.py pr-merge` wraps, and ensure the gating logic (auto-merge config, PR Flow branching) is accurately represented. Option (a) is more consistent with D1's intent that pr-protocol is canonical.

---

### Finding 2

- **File**: `references/sub-skills/roles/dm/issue-triage.md`
- **Line**: 27 and 38
- **Severity**: warning
- **Issue**: The `--role` flag on `tracker.py comment` commands uses bare alias `dm` (e.g., `--role dm`), while `tracker-protocol.md`'s canonical form for comments is `--role [ROLE]-lead` (with the `-lead` suffix). The transition commands in the same file (lines 26, 27 in the prompt) correctly use `--role dm-lead`.
- **Evidence**: Line 27: `python references/scripts/tracker.py comment [NUMBER] --role dm --message "Fixed in commit..."`. Line 38: `python references/scripts/tracker.py comment [NUMBER] --role dm --message "Root cause is in..."`. `tracker-protocol.md` Discussion Entries section shows the canonical form as `--role [ROLE]-lead --message`.
- **Suggested fix**: Change `--role dm` to `--role dm-lead` on both comment lines so the file is internally consistent and matches the canonical form in `tracker-protocol.md`.

---

### Additional verification results (no findings)

- **(a) No remaining bare `gh pr create` / `git rebase` recommendations**: All `gh pr create` occurrences in the changed files are normative statements saying NOT to use it (e.g., `pr-protocol.md:17`, `task-intake.md:329`). All `git rebase` occurrences say "NOT git rebase" or are in the non-canonical exclusion statement (`pr-protocol.md:115,136`). ✓
- **(b) No remaining inline `tracker.py create-*` blocks duplicating canonical content**: All 10 inline blocks (from the original inventory) have been replaced with `→ run sub-skill: tracker-protocol` references. ✓
- **(c) No remaining `--reporter` bare-alias deviations**: All three deviations from D3 are fixed in the changed versions: `dm/issue-triage.md` → `--reporter dm-lead`, `verifier/verification.md` → `--reporter verifier-lead`, `improvement-scan-slim.md` → `--reporter [ROLE]-lead`. ✓
- **(d) No remaining `create-bug` or `list-bugs` legacy aliases**: These only appear in `tracker-protocol.md`'s legacy-aliases-retired table (lines 167–168) as documentation of what not to use. No changed file uses them as commands. ✓
- **(e) tracker-protocol internal consistency**: Reporter lock (lines 80–91) and legacy-aliases-retired subsection (lines 164–175) are internally consistent — they address different concerns (flag convention vs subcommand naming). Per-finding-kind one-liners all conform to `--reporter [ROLE]-lead`. ✓
- **(g) worker/instructions.md retirement note consistent**: The note correctly states `common/issue-filing.md` was retired in #11334 and body templates absorbed into `tracker-protocol.md`, and the file indeed contains the absorbed body templates (Bug fix, Feature task, Improvement-scan, Cross-role shapes). ✓