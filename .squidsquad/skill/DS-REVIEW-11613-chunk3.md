I now have a complete picture. Here are my findings:

---

### Finding 1

- **File**: references/wizard/WIZARD.md
- **Line**: 81-93
- **Severity**: warning
- **Issue**: The re-verify step (step 4) gives an unconditional "**`ok: false`** → exit cleanly with code 0" instruction (line 82-85), but the hard-gate policy paragraph immediately following (lines 87-93) carves out a claude exception: "if it remains missing after re-verify, warn prominently but you MAY proceed past Step 0." The re-verify bullet makes no reference to this exception and is stated as a complete decision rule. An LLM agent following the bullet point literally would exit even when only the non-hard-gated `claude` CLI is missing — violating the stated claude warn-but-proceed policy.
- **Evidence**: The task's acceptance criteria explicitly require "claude warn-but-proceed" — the install must be allowed past Step 0 if only claude is missing. The re-verify `ok: false` bullet reads as an absolute exit rule with no escape hatch. The exception is stated in a separate paragraph that says "the re-verify gate above **must** reach `ok: true` before the install proceeds" (line 89), which actually reinforces the unconditional exit before adding the claude carve-out. An agent reading linearly is instructed to exit before it encounters the exception context.
- **Suggested fix**: Integrate the claude exception into the `ok: false` branch of the re-verify decision tree. For example:

  ```
  - **`ok: false`** → if any hard-gated dep (gh, Python, pip, packages) is still
    missing, show the still-missing items with their `instruct` lines, tell the
    user plainly what to install, and exit cleanly with code 0. If the only
    remaining missing item is `claude`, warn prominently that agent spawn will
    not work without it, then continue to Step 0a.
  ```

---

### Finding 2

- **File**: references/wizard/WIZARD.md
- **Line**: 66-68
- **Severity**: warning
- **Issue**: The decline path tells the agent to "explain that SquidSquad can't install without these deps (the tracker, harness, and agent spawn all depend on them)" — but this blanket statement contradicts the hard-gate policy that claude is optional for install. If the only missing dependency is `claude` (e.g., npm absent, making it a guided item), the user would be told the install cannot proceed when per the hard-gate policy it actually can (with a warning).
- **Evidence**: Lines 90-93 establish that "the `claude` CLI ... the install itself can complete without it; if it remains missing after re-verify, warn prominently but you MAY proceed." But the decline message on line 66-67 treats ALL deps uniformly as blockers, including the "agent spawn" dep (claude). If `claude` is the sole missing guided item, the user might decline based on the agent's claim that install is impossible, when in fact they could say "yes, walk me through claude install" OR even decline and still proceed (with warning) under the claude-exception policy.
- **Evidence**: The wording "SquidSquad can't install without these deps" is objectively false when the missing set is `{claude}` only — SquidSquad CAN install without claude per the project's own hard-gate policy.
- **Suggested fix**: Qualify the decline message to distinguish hard-gated from soft deps. For example:

  ```
  - If the user declines: explain that at minimum `gh`, Python, pip, and the
    harness packages are hard requirements (tracker, comments, audit trail, and
    harness all depend on them), so SquidSquad can't install without those. If
    only soft deps like `claude` are among the missing set, note that the
    install could proceed but agent spawn would be unavailable. Then exit
    cleanly with code 0 and "no changes made".
  ```

---

**Other items checked — no findings:**

- **No-install-before-consent**: Line 61-62 "Install NOTHING before the user answers" is explicit; provision-deps is gated behind approval (line 69).
- **No fail-fast**: Lines 46-47 "Do NOT bail on the first one; the helper already enumerated them all."
- **Re-verify is present**: Step 4 (lines 79-93) mandates it.
- **Hard gates on gh/python/pip/packages**: Lines 87-89 are clear.
- **Phase 0 no repo writes**: Lines 33-36, 83-84 are explicit; decline and re-verify-failure both exit code 0.
- **7.5b reconciliation**: Consistent belt-and-suspenders framing; `pyyaml` addition noted; `pip install -r requirements.txt` intentionally redundant with Phase 0 provisioning.
- **Test changes**: `_WIZARD_COMMANDS` retains `check-gh` as legacy; `test_all_steps_present_in_order` heading updated; `test_critical_helpers_are_mentioned` correctly pivots to `gather-deps`/`provision-deps`; `Step 0a` correctly exists as "Shared filesystem" section (line 97) so both "continue to Step 0a" references are valid.