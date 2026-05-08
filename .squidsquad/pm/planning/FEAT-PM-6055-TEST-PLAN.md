# FEAT-PM-6055 Test Plan — Enforce Role Separation PM/QA/DM

## Scope

Verify that all fallback paths where one role absorbs another's duties are removed, that PM/QA/DM are always present as mandatory roles, that setup and upgrade flows enforce this, and that no agent instructions leave room for role boundary violations.

---

## Test Cases

### TC-1: PM testing-and-verification.md has no QA fallback logic

- **Precondition**: `references/sub-skills/roles/pm/testing-and-verification.md` has been updated as part of #6055
- **Steps**:
  1. Read `references/sub-skills/roles/pm/testing-and-verification.md`
  2. Search for any of the following: `qa/` directory check, `QA is not installed`, `PM falls back`, `combined PM/QA duties`, `current-state` liveness check gating Steps 3–6
- **Expected**: None of the above strings are present. The file either contains no Steps 3–6 at all, or the header introduces them as unconditionally QA-owned with no PM takeover clause
- **Verification**: `grep -i "falls back\|combined PM/QA\|QA is not installed\|qa/ does not exist" references/sub-skills/roles/pm/testing-and-verification.md` — must return no matches

---

### TC-2: delivery-fallback.md is removed or gutted

- **Precondition**: #6055 implementation complete
- **Steps**:
  1. Check whether `references/sub-skills/roles/pm/delivery-fallback.md` exists
  2. If it exists, read it and check for the DM presence check clause: `If .squidsquad/dm/ directory does NOT exist`
  3. If it exists, check for any version bump logic, CHANGELOG writing, or `mark Shipped` steps attributed to PM
- **Expected**: Either the file does not exist, or if retained as a stub, it contains no fallback logic — no DM directory check, no PM-performs-delivery steps, no version bump sequence
- **Verification**: File is absent (`test ! -f references/sub-skills/roles/pm/delivery-fallback.md`) OR `grep -i "DM not installed\|dm/ does not exist\|PM takes over delivery\|PM performing delivery" references/sub-skills/roles/pm/delivery-fallback.md` returns no matches

---

### TC-3: PM instructions.md role description no longer mentions QA fallback

- **Precondition**: `references/roles/pm/instructions.md` updated as part of #6055
- **Steps**:
  1. Read line 5 (the PM identity paragraph) of `references/roles/pm/instructions.md`
  2. Check whether the sentence `When QA is absent, you fall back to combined PM/QA duties` or equivalent wording is present
  3. Check Step 6c comment: `If DM is present, it handles version bumps. If DM is absent, PM handles version bumps in Step 6d`
- **Expected**: Line 5 describes PM as coordinator only — no fallback mention. Step 6c either refers unconditionally to DM for version bumps or is removed entirely. No `If DM is absent` conditional appears
- **Verification**: `grep -i "fall back\|DM is absent\|QA is absent\|combined PM" references/roles/pm/instructions.md` — must return no matches

---

### TC-4: PM SOUL.md — "almost half a QA agent" wording removed

- **Precondition**: `references/roles/pm/SOUL.md` updated as part of #6055
- **Steps**:
  1. Read `references/roles/pm/SOUL.md`
  2. Search for the phrase "almost half a QA agent" or any variation implying PM shares QA identity
- **Expected**: The phrase is absent. The soul language reinforces PM as coordinator and pipeline overseer — not as a QA fallback. Acceptable replacement: "PM holds QA accountable for verification quality — but does not replace QA" or equivalent
- **Verification**: `grep -i "half a QA\|half of QA\|combined PM/QA\|acts as QA" references/roles/pm/SOUL.md` — must return no matches

---

### TC-5: PM prohibitions.md includes explicit never-verify, never-deliver rules

- **Precondition**: `references/roles/pm/prohibitions.md` updated as part of #6055
- **Steps**:
  1. Read `references/roles/pm/prohibitions.md`
  2. Confirm at least one prohibition explicitly says PM must never verify its own planned work (or equivalent: verification is QA's job)
  3. Confirm at least one prohibition explicitly says PM must never perform delivery (or equivalent: delivery is DM's job)
- **Expected**: Both prohibitions are present as explicit, unconditional rules. No "unless QA is absent" or "unless DM is absent" qualifier appears alongside them
- **Verification**: `grep -i "never verify\|never deliver\|verification.*QA.*job\|delivery.*DM.*job" references/roles/pm/prohibitions.md` — must return at least two matches, one for each prohibition

---

### TC-6: QA instructions.md no longer assumes PM→DM delivery fallback exists

- **Precondition**: `references/roles/qa/instructions.md` updated as part of #6055
- **Steps**:
  1. Read `references/roles/qa/instructions.md`
  2. Search for any language asserting that PM handles delivery when DM is absent (e.g., "PM's delivery fallback handles it", "PM will deliver if DM is absent")
- **Expected**: No such language exists. QA's instructions treat DM as always present for delivery
- **Verification**: `grep -i "PM.*delivery fallback\|PM.*deliver.*DM.*absent\|delivery fallback handles" references/roles/qa/instructions.md` — must return no matches

---

### TC-7: SKILL.md lists DM as always present (not optional)

- **Precondition**: `SKILL.md` updated as part of #6055
- **Steps**:
  1. Read the roles/agents section of `SKILL.md`
  2. Find where DM is described
  3. Check whether DM is described as "optional", "can be omitted", or given any opt-in language
- **Expected**: DM is described as a mandatory role alongside PM and QA. No opt-in language, no "if installed" qualifier, no "optional for lightweight teams"
- **Verification**: `grep -i "optional\|if installed\|if present\|can be omitted" SKILL.md` in the DM description section — must return no matches for DM specifically

---

### TC-8: Setup wizard always creates PM + QA + DM

- **Precondition**: `references/scripts/wizard.py` (or equivalent setup script) updated as part of #6055
- **Steps**:
  1. Run the setup wizard in a clean temp directory (or read the wizard's role-creation logic directly)
  2. Observe which agent directories are created by default
  3. Attempt to find any "skip QA" or "skip DM" option in the wizard flow
- **Expected**: The wizard creates `.squidsquad/pm/`, `.squidsquad/qa/`, `.squidsquad/dm/`, and at least one dev/worker agent directory unconditionally. No prompt or flag allows skipping QA or DM creation
- **Verification**:
  - `grep -i "skip.*qa\|skip.*dm\|optional.*qa\|optional.*dm\|qa.*optional\|dm.*optional" references/scripts/wizard.py` — must return no matches
  - After wizard run: confirm all four directories exist

---

### TC-9: compose.py fails with clear error if a mandatory role is missing

- **Precondition**: #6055 implementation complete; a test environment without a QA or DM directory
- **Steps**:
  1. Remove `.squidsquad/qa/` from a test clone (or simulate with a dry-run flag if available)
  2. Run `python references/scripts/compose.py deploy-all`
  3. Observe exit code and error message
- **Expected**: `compose.py` exits non-zero and prints a clear, human-readable error naming which mandatory role(s) are missing. It does NOT silently proceed and compose a partial team
- **Verification**: Exit code is non-zero AND stderr/stdout contains text identifying the missing role (e.g., "ERROR: mandatory role 'qa' is missing — cannot compose. Run /squidsquad-setup to add it.")

---

### TC-10: Upgrade detects missing mandatory roles and guides user

- **Precondition**: A simulated pre-#6055 install that has PM and dev but no QA and no DM
- **Steps**:
  1. Run `/squidsquad-upgrade` (or `references/scripts/upgrade.py` if that is the entry point) against the simulated install
  2. Observe whether the upgrade detects that QA and DM are absent
  3. Observe the guidance provided to the user
- **Expected**: The upgrade script detects missing mandatory roles and outputs a clear message telling the user which roles are missing and how to add them (e.g., "QA and DM are now mandatory. Run /squidsquad-setup or manually run compose.py deploy qa && compose.py deploy dm."). It does NOT silently proceed
- **Verification**: Upgrade output contains language identifying both missing roles. The upgrade does not complete without surfacing the gap

---

### TC-11: Old agents with fallback code still work until recompose (backward compatibility)

- **Precondition**: A running PM agent whose CLAUDE.md was composed before #6055 — still contains the old `testing-and-verification.md` fallback logic
- **Steps**:
  1. Confirm the old agent's `.squidsquad/pm/CLAUDE.md` still contains the legacy `QA presence check` block
  2. Run one PM cycle with QA absent
  3. Observe that the agent falls back as per old instructions (no crash, no undefined behavior)
- **Expected**: The old composed agent runs normally using its old instructions. The fallback behavior works as before. This confirms the transition is non-breaking until the user recomposes
- **Verification**: Cycle completes without error. The PM agent log shows the QA fallback path was taken (per old instructions). No crash or error state

---

### TC-12: After recompose, PM no longer has fallback logic in its CLAUDE.md

- **Precondition**: `compose.py deploy pm` run after #6055 templates are in place
- **Steps**:
  1. Run `python references/scripts/compose.py deploy pm`
  2. Read the resulting `.squidsquad/pm/CLAUDE.md`
  3. Search for the legacy QA presence check block and the DM delivery fallback block
- **Expected**: Neither block appears in the composed output. The `{{include: roles/pm/testing-and-verification}}` directive pulls in the updated (fallback-free) sub-skill. The `{{include: roles/pm/delivery-fallback}}` directive either pulls in an empty/removed stub or is itself removed from `instructions.md`
- **Verification**:
  - `grep -i "QA is not installed\|falls back to combined\|DM not installed\|PM performing delivery" .squidsquad/pm/CLAUDE.md` — must return no matches
  - Composed file exists and has nonzero size

---

### TC-13: Pipeline sentinel still runs regardless of QA presence

- **Precondition**: `references/sub-skills/roles/pm/pipeline-sentinel.md` reviewed post-#6055
- **Steps**:
  1. Read the pipeline-sentinel.md header
  2. Confirm the phrase "This step runs every cycle regardless of QA presence" is still present (or equivalent unconditional language)
  3. Confirm there is no conditional gate that skips the sentinel when QA is absent
- **Expected**: Pipeline sentinel is unconditional. Its activation header does not reference QA presence
- **Verification**: The step header in `pipeline-sentinel.md` contains no `if QA present/absent` conditional. The sub-skill is self-contained and does not depend on QA's state

---

### TC-14: PM cycle — pending-ship items are not touched by PM

- **Precondition**: New PM agent composed after #6055; one task at `pending-ship` status
- **Steps**:
  1. Run one PM cycle
  2. Observe PM's behavior toward the `pending-ship` task
- **Expected**: PM does not transition the `pending-ship` item to `shipped`. PM does not write CHANGELOG entries, update README, or perform any delivery work. The item stays at `pending-ship` awaiting DM
- **Verification**: After the cycle, the task remains at `pending-ship`. No `Status → Shipped` Discussion comment from PM appears on the issue. No CHANGELOG or README modification in the cycle's git diff

---

## Smoke Tests

- [ ] `grep -i "falls back\|combined PM/QA\|QA is not installed" references/sub-skills/roles/pm/testing-and-verification.md` returns no matches
- [ ] `grep -i "DM not installed\|PM takes over delivery\|PM performing delivery" references/sub-skills/roles/pm/delivery-fallback.md` returns no matches (or file is absent)
- [ ] `grep -i "almost half a QA" references/roles/pm/SOUL.md` returns no matches
- [ ] `grep -i "fall back\|QA is absent\|DM is absent" references/roles/pm/instructions.md` returns no matches
- [ ] `grep -i "never verify\|never deliver" references/roles/pm/prohibitions.md` returns at least two matches
- [ ] `python references/scripts/compose.py deploy pm` completes without error
- [ ] After compose, `.squidsquad/pm/CLAUDE.md` contains no QA fallback block
- [ ] SKILL.md does not describe DM as optional

---

## Regression Risks

- **Existing solo/minimal installs**: Users running PM-only or PM+dev-only teams will lose the ability to verify or deliver until they add QA and DM. The upgrade flow must surface this clearly — not silently break them
- **cycle_post.py CHANGELOG fallback**: The research identified `cycle_post.py` lines 437–453 as writing CHANGELOG when DM is absent. If this code path is not removed, it will conflict with the template change — PM instructions will say "don't deliver" but the script will still write CHANGELOG
- **compose drift**: If `delivery-fallback.md` is deleted but `{{include: roles/pm/delivery-fallback}}` remains in `instructions.md`, compose will fail or include an empty block. Both the template and the include directive must be updated atomically
- **QA instructions assuming PM→DM fallback**: If QA's instructions still say "PM's delivery fallback handles it," QA agents will have stale expectations. Items at pending-ship may be misrouted

---

## Comprehension Questions

### CQ-1: Can a SquidSquad team run without QA? Why or why not?

- **Files**: `references/sub-skills/roles/pm/testing-and-verification.md`, `references/roles/pm/prohibitions.md`, `SKILL.md`
- **Expected**: No. QA is a mandatory role in every SquidSquad team. PM is explicitly prohibited from verifying its own planned work. There is no opt-in flag or fallback path that allows a team to operate without QA — a missing QA role is an error condition, not a supported configuration

### CQ-2: What happens if PM detects QA directory is missing at cycle start?

- **Files**: `references/sub-skills/roles/pm/testing-and-verification.md`, `references/roles/pm/instructions.md`, `references/scripts/compose.py` (or `wizard.py`)
- **Expected**: PM does not silently absorb QA duties. PM surfaces the gap — either the cycle halts with an error, or compose.py failed earlier preventing deployment without QA. There is no fallback logic that allows PM to proceed with Steps 3–6. The correct response is to add the missing QA role via setup or upgrade

### CQ-3: What does PM do with items at pending-ship?

- **Files**: `references/sub-skills/roles/pm/delivery-fallback.md`, `references/roles/pm/prohibitions.md`, `references/roles/pm/instructions.md`
- **Expected**: Nothing. PM does not transition pending-ship items to shipped, does not write CHANGELOG entries, does not update README, and does not perform version bumps. All delivery work belongs to DM. PM's pipeline sentinel may nudge DM if an item stalls at pending-ship too long, but PM never performs delivery actions itself
