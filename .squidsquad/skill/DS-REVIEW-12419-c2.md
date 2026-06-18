Now I have full context from both the WIZARD.md runbook and the INSTALLER-ARCH §10. Let me compile my findings.

---

### Finding 1

- **File**: `references/wizard/WIZARD.md`
- **Line**: 172–174 vs 193–194 (contradiction) + 189–192 (missing mechanism)
- **Severity**: error
- **Issue**: The three-gate sequence is internally contradictory about when writes land on disk. Line 172–174 says "apply its `path` markdown **to the on-disk state** under all three gates" (implying writes happen during the gate walk). But line 193–194 says "All three gates pass → **apply this file's changes to disk** (atomically)" (implying writes happen only after all gates). An agent cannot determine which is correct. Worse, Gate 3 (line 189–190) runs `compose.py deploy-all --check`, which reads from the filesystem — if changes aren't on disk yet (per the "apply after all gates" reading), the check validates pre-migration state and is useless; if changes ARE on disk (per "apply to on-disk state under gates"), the check is meaningful but "clean" abort requires the agent to revert, which the instructions never tell it to do.
- **Evidence**: INSTALLER-ARCH §10 line 489 resolves this with "`compose.py deploy-all --check` validates the migrated content composes cleanly **before any write**" — confirming the intent is no-write-before-Gate-3. But the ARCH provides no mechanism either. The WIZARD text then adds "to the on-disk state" phrasing (line 172–174) that directly contradicts the ARCH's "before any write" contract. The agent has no instruction for how a compose dry-run validates unwritten content.
- **Suggested fix**: Remove "to the on-disk state" from line 173. Add explicit instruction that the agent writes changes to a temporary/staging location before Gate 3, runs `deploy-all --check` against that staging area, and only copies to the real filesystem after Gate 3 passes. Or, if the compose dry-run supports a `--against` flag or similar preview mechanism, document it here.

---

### Finding 2

- **File**: `references/wizard/WIZARD.md`
- **Line**: 212–216 ("Continue" paragraph)
- **Severity**: error
- **Issue**: The "Continue" section uses step/phase numbering that doesn't exist in the WIZARD runbook the agent is following:
  - **"Step 6 (Phase 6) recompose"** (line 212–213): In the WIZARD runbook, Step 6 is the "Review screen" (line 653). Compose happens inline during Step 7.3 scaffold (line 736–743). In the ARCH, there is no Phase 6 either — compose was folded into Phase 5 (per ARCH §4.9).
  - **"Step 8 commits"** (line 215): There is no Step 8 in the WIZARD runbook. The commit step is Step 7.5 (line 776–784).
  - **"Step 7.6 handles the harness restart"** (line 215–216): In the current WIZARD, Step 7.6 is "Print the 'ready' message and exit" (line 810–821). Harness restart is not implemented there; it's tracked as a separate target (#12420) in ARCH §10.3, which places restart *after* Phase 8 commit and *before* Phase 9 exit — not at WIZARD Step 7.6.
- **Evidence**: An agent reads the runbook linearly by step number. It would look for "Step 6 recompose" and find the Review Screen instead; it would look for "Step 8" and find nothing. This directly violates the runbook's own rule: "Never invent behaviour the helpers already implement — call the helper and act on its JSON output" (line 10–12). Mixing ARCH phase numbers into WIZARD step descriptions creates false references.
- **Suggested fix**: Rewrite the paragraph using WIZARD-consistent numbering. E.g.: "Step 7.3 scaffold recomposes every `.squidsquad/<alias>/CLAUDE.md` inline from the now-current source + migrated L4; Step 7.5 commits; the harness restart (post-commit, pre-exit — #12420) will be handled separately. Existing vault / `working-state.md` / `iterations/` are never touched."

---

### Finding 3

- **File**: `references/wizard/WIZARD.md`
- **Line**: 846 ("What NOT to do") vs. 193–194 and 203–209 (migration walk writes)
- **Severity**: error
- **Issue**: The "What NOT to do" invariant at line 846 states "Do not write to disk before Step 7." The new migration walk (Step 0b.1) explicitly writes to disk: migration file changes are applied atomically (line 193–194) and the version stamp is written to `config.md` (lines 203–209). These writes occur at Step 0b.1 — well before Step 7. This creates a direct contradiction: an agent that follows Step 0b.1's instructions to apply migration changes and stamp the version is simultaneously violating the runbook's own red-line rule.
- **Evidence**: The old Step 0b "regenerate" path preserved this invariant by delegating to Step 7 (`overwrite_existing=True` — skip Steps 1–6, all writes still happen at Step 7). The new Upgrade path is the first codepath that writes before Step 7. The "What NOT to do" section was not updated to carve out the migration walk as a permitted exception. An agent instructed to both "stamp the version now" and "never write before Step 7" faces a contradiction that could cause it to skip the stamp or halt.
- **Suggested fix**: Amend line 846 to: "Do not write to disk before Step 7 (the Step 0b.1 migration walk — applying gated migration changes and stamping the version — is the only exception)." Or add a new bullet acknowledging the migration walk as a pre-Step-7 write path that is explicitly permitted.

---

### Finding 4

- **File**: `references/wizard/WIZARD.md`
- **Line**: 196–201 (abort mid-walk) and 201 ("resumes at step _k_")
- **Severity**: warning
- **Issue**: The instruction says "the next installer re-run resumes at step _k_" (line 201) after a mid-walk abort. But the version stamp is explicitly NOT advanced (lines 197–198: "do **not** advance the version stamp"). On the next re-run, `migration-plan` (line 158) computes the chain from the version stamp in `config.md`, which still reflects the pre-walk version. It will return the full chain including files 1..k−1 that were already applied. The fresh agent has no mechanism to detect which files have already been applied and skip to step _k_ — it will re-walk the entire chain from the beginning, re-running all three gates for already-applied files.
- **Evidence**: INSTALLER-ARCH §10.4 line 565 contains the same statement ("The next installer run picks up at step k") with the same gap. The migrations themselves may be idempotent in practice (renaming an already-renamed field is a no-op), but the textual instruction promises "resume at step _k_" and delivers "re-walk from step 1." An agent told it will "resume" may skip the first _k_−1 files without re-verifying them — which is also wrong if the operator manually reverted something. Either `migration-plan` needs to support a partial-walk-resume mechanism (e.g., detecting which migration files are already applied by comparing their content to on-disk state), or the WIZARD text must describe a deterministic skip rule the agent can execute.
- **Suggested fix**: Either (a) specify how `migration-plan` detects already-applied migrations (e.g., via file-content comparison or a checkpoint file) so it can return only the remaining `chain[k:]`, or (b) change line 201 to acknowledge re-walking: "the next installer re-run will re-walk the chain from the beginning; already-applied migrations are idempotent and will pass through the gates as no-ops."