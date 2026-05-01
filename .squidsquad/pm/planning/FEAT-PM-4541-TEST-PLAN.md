# FEAT-PM-4541 Test Plan — Agent-Driven Composition

## Overview

Tests cover the full agent-driven composition pipeline: deterministic compose baseline,
coherence agent polish, CQ verification (pass/fail/retry/flag), trigger rules, fallbacks,
dynamic CQ generation, reboot side effect, and regression coverage.

---

## Test Cases

### TC-1: Deterministic compose produces valid baseline output

- **Area**: Deterministic compose — baseline unchanged
- **Precondition**: `Agent Compose: no` in config.md (feature disabled). Layer sources L1–L4 present with known content.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Inspect the written `instructions.md` and `SOUL.md` for the target role.
- **Expected**: Output matches the deterministic concatenation of layer sources (markers preserved, code blocks intact, no prose changes). No coherence agent is called.
- **Verification**: Diff the output against a known-good deterministic render. Zero unexpected changes.

---

### TC-2: Coherence agent polishes prose for natural flow

- **Area**: Coherence agent produces polished output
- **Precondition**: `Agent Compose: yes` in config.md. Layer sources contain repetitive/contradictory prose sections (inject a deliberate duplicate paragraph across L2 and L3).
- **Steps**:
  1. Trigger compose for the affected role (L4 change or forced compose call).
  2. Capture the coherence agent's output before CQ verification.
- **Expected**:
  - Duplicate paragraph appears only once in polished output.
  - Prose flows naturally (no abrupt topic jumps at layer boundaries).
  - Behavioral meaning of all instructions is preserved.
  - Output is not identical to the raw deterministic draft (polish occurred).
- **Verification**: Manual review of polished output vs. deterministic draft. Confirm deduplication by searching for the injected duplicate string — it should appear exactly once.

---

### TC-3: Code blocks, markers, and commands preserved verbatim after polish

- **Area**: Exact-match content never rewritten
- **Precondition**: `Agent Compose: yes`. Layer sources contain:
  - A fenced code block with a bash command (`python references/scripts/cycle.py timestamp-short`).
  - A marker line (`<!-- SQUIDSQUAD:SECTION:soul -->`).
  - A file path reference (`references/roles/skill/CLAUDE.md`).
  - A placeholder (`{{ROLE_NAME}}`).
- **Steps**:
  1. Run compose with coherence agent enabled.
  2. Extract all code blocks, marker lines, commands, and placeholders from the output.
- **Expected**: Every code block, marker, command string, file path, and placeholder is byte-for-byte identical to the source layer content. None are paraphrased, reformatted, or moved inside prose.
- **Verification**: Automated string comparison of extracted code/marker/command regions against source. Zero diffs.

---

### TC-4: CQ verification passes on well-formed compose output

- **Area**: CQ verification passes on good output
- **Precondition**: `Agent Compose: yes`. Layer sources produce a complete, coherent polished output. CQs are dynamically generated from layer headings.
- **Steps**:
  1. Run compose for a role with known good layer sources.
  2. Allow CQ verification sub-agent to quiz the polished output.
  3. Observe verification result.
- **Expected**: CQ sub-agent answers all generated CQs correctly from the output alone (fresh context). Verification returns `pass`. Output is deployed to `instructions.md` and `SOUL.md`.
- **Verification**: Check that `instructions.md` and `SOUL.md` are written (mtime updated). CQ verification log shows `pass` with all CQs answered.

---

### TC-5: CQ verification fails on incomplete output — triggers retry

- **Area**: CQ verification fails on deliberately incomplete output
- **Precondition**: `Agent Compose: yes`. Inject a stub coherence agent that returns output with a section deliberately omitted (simulate a partial polish that drops an L4 directive). CQs include a question covering the omitted directive.
- **Steps**:
  1. Run compose with the stub coherence agent.
  2. CQ sub-agent quizzes the incomplete output.
  3. Observe system response to the failure.
- **Expected**:
  - CQ sub-agent returns `fail` with specific gap feedback identifying the missing directive.
  - System re-prompts the coherence agent with the gap feedback (retry 1 begins).
  - Output is NOT deployed on the first failure.
- **Verification**: Log shows `fail` on first attempt. Retry prompt includes the specific gap identified. `instructions.md` mtime is unchanged (no premature deploy).

---

### TC-6: Two retries then flag human — never silent deploy

- **Area**: Self-correct 2x then flag human
- **Precondition**: `Agent Compose: yes`. Stub coherence agent always returns incomplete output (fails CQ every time, simulating a persistent quality gap).
- **Steps**:
  1. Run compose with the always-failing stub.
  2. Let the system attempt up to 2 retries.
  3. Observe behavior after retry 2 fails.
- **Expected**:
  - Exactly 2 retries attempted (total 3 attempts: original + retry 1 + retry 2).
  - After retry 2 fails: system flags human (via tracker issue, PM comment, or file sentinel — per dev discretion).
  - Output is NOT deployed at any point.
  - Human flag message identifies which CQs failed.
- **Verification**: Log shows 3 attempts total, then `flag-human`. `instructions.md` is unchanged. Human flag artifact (issue/comment/sentinel) exists and names the failing CQs.

---

### TC-7: Fallback — config disabled = deterministic only, no agent call

- **Area**: Fallback: config flag off
- **Precondition**: `Agent Compose: no` in config.md. All API credentials present and valid.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Monitor outbound API calls during execution.
- **Expected**: No coherence agent API call is made. Output is the raw deterministic concatenation. Compose completes successfully.
- **Verification**: Network log / mock shows zero API calls to the model. Output identical to TC-1 baseline.

---

### TC-8: Fallback — API unavailable = deterministic output deployed

- **Area**: Fallback: API unavailable
- **Precondition**: `Agent Compose: yes` in config.md. API endpoint made unreachable (network block or invalid key injected for test).
- **Steps**:
  1. Trigger compose (L4 change).
  2. Coherence agent API call fails.
- **Expected**: System falls back to the deterministic compose output. `instructions.md` and `SOUL.md` are deployed with the deterministic content. No exception propagates to crash compose. No human flag is raised (API failure is a handled fallback, not a retry scenario).
- **Verification**: `instructions.md` and `SOUL.md` written with deterministic content. Compose exits cleanly (exit code 0). Log notes the fallback reason.

---

### TC-9: L4 trigger — L4 file change fires compose at end of cycle + reboot

- **Area**: L4 trigger rule
- **Precondition**: `Agent Compose: yes`. A role agent is running (heartbeat active). L1–L3 unchanged.
- **Steps**:
  1. Make an L4 change (PM directive edit to a role's layer-4 source file).
  2. Let the PM cycle complete.
- **Expected**:
  - Compose fires for the affected role at end of that cycle.
  - Affected agent is rebooted after compose (`.stop-after-cycle` written or `start_team.py --reboot` invoked for that role).
  - No compose fires for unaffected roles.
- **Verification**: Compose log shows compose triggered. Agent health heartbeat resets (new PID or restart timestamp). Unaffected roles' `instructions.md` mtimes are unchanged.

---

### TC-10: L1–L3 trigger — fires on upgrade/install only, not on random file edits

- **Area**: L1–L3 trigger rule
- **Precondition**: `Agent Compose: yes`. L1–L3 source files are modified (simulate a repo-owner layer update).
- **Steps**:
  1. Edit an L2 source file.
  2. Let a normal PM cycle run (no upgrade, no fresh install).
  3. Then run `squidsquad-upgrade` (simulating an upgrade event).
- **Expected**:
  - Step 2: Compose does NOT fire. `instructions.md` mtime unchanged.
  - Step 3: Compose fires during upgrade, producing updated output.
- **Verification**: `instructions.md` mtime is unchanged after step 2. After step 3, mtime is updated. Compose log confirms trigger source was `upgrade`.

---

### TC-11: Dynamic CQ generation from layer sources

- **Area**: Dynamic CQ generation
- **Precondition**: `Agent Compose: yes`. A new directive is added to an L4 source file (e.g., a new heading `### Stall Detection` with a novel instruction). No manual CQ update performed.
- **Steps**:
  1. Add the new L4 directive.
  2. Trigger compose.
  3. Inspect the CQs presented to the CQ verification sub-agent.
- **Expected**: At least one new CQ covers the newly added directive (e.g., "What does the agent do when a task is stalled?"). CQ was generated automatically from the source heading/content — no manual edit.
- **Verification**: CQ list includes a question referencing the new directive's topic. Old CQs for existing directives are still present (no regression in CQ coverage).

---

### TC-12: Reboot after compose — affected agent restarts with new instructions

- **Area**: Reboot after compose
- **Precondition**: `Agent Compose: yes`. Target agent is running (PID file present, heartbeat active). L4 change triggers compose.
- **Steps**:
  1. Record the agent's current PID and `instructions.md` content hash.
  2. Trigger L4 compose.
  3. Wait for compose + reboot sequence to complete.
  4. Check agent state.
- **Expected**:
  - Agent PID changes (or wrapper restart detected via heartbeat gap).
  - Agent re-reads the new `instructions.md` on boot (confirmed by agent's first cycle output referencing new directive or via comprehension test).
  - Agent does not continue running with stale instructions.
- **Verification**: PID before ≠ PID after (or heartbeat gap detected). New `instructions.md` hash differs from pre-compose hash. Agent health recovers to green within 2 cycle intervals.

---

### TC-13: Full suite regression

- **Area**: Regression
- **Precondition**: `Agent Compose: no` (baseline). All existing tests passing before feature merge.
- **Steps**:
  1. Run `python tests/run_tests.py`.
  2. Enable `Agent Compose: yes`.
  3. Re-run `python tests/run_tests.py`.
- **Expected**: All pre-existing tests pass in both configurations. No regressions in compose, upgrade, health-check, or tracker scripts.
- **Verification**: Exit code 0 for full suite in both runs. No new failures.

---

## Smoke Tests

- [ ] `python references/scripts/compose.py deploy-all` completes without error when `Agent Compose: no`.
- [ ] `python references/scripts/compose.py deploy-all` completes without error when `Agent Compose: yes` and API is available.
- [ ] `instructions.md` and `SOUL.md` for a test role are written to disk after a successful compose run.
- [ ] Compose exits cleanly (exit code 0) when the API is unreachable and `Agent Compose: yes`.
- [ ] No compose fires on a normal PM cycle with only L1–L3 changes and no upgrade.
- [ ] Affected agent's heartbeat shows a restart after L4 compose.

---

## Regression Risks

- **compose.py deploy-all broken for users without feature enabled**: If the code path is not properly gated behind the config flag, users with `Agent Compose: no` (or no config entry) may hit import errors or unexpected API calls.
- **Code block corruption**: The coherence agent prompt must explicitly forbid rewriting fenced code blocks. Any loosening of that prompt risks corrupting bash commands or file paths that agents rely on.
- **CQ generation misses new directives**: If CQ extraction relies only on headings and a new directive is added as body text without a heading, it will never be tested by verification. Risk: silent gap in coverage.
- **Reboot loop**: If compose fires every cycle for an L4 change that is never "consumed" as a trigger, the agent may be rebooted every cycle. Trigger detection must be edge-triggered (once per change), not level-triggered.
- **Race condition on deploy**: If compose writes `instructions.md` while an agent is mid-read on startup, the agent may load a torn file. Atomic write (temp file + rename) must be used for deploy.
- **Retry count not persisted**: If the retry counter is in-memory only and the process crashes between retries, the counter resets and the system may loop silently past the 2-retry limit.
- **SOUL.md and instructions.md composed separately**: If these are two separate agent calls, a failure between them leaves one stale and one fresh — inconsistent state. Both must succeed or neither deploys.

---

## Comprehension Questions

### CQ-1: What does the compose system do when the API is unavailable?

- **Files**: `.squidsquad/<role>/CLAUDE.md` or the composed instructions for the role implementing compose
- **Expected**: The system falls back to the deterministic compose output and deploys it. It does NOT raise an error to the user, does NOT retry with the API, and does NOT flag a human. The fallback is silent and automatic.

### CQ-2: How many times will the coherence agent be re-prompted before a human is flagged?

- **Files**: Composed instructions for the compose-owning role
- **Expected**: Exactly 2 retries (3 total attempts: initial + retry 1 + retry 2). After the third failure the system flags a human and stops. It never deploys broken output silently.

### CQ-3: Which types of content must the coherence agent never modify?

- **Files**: Composed instructions for the compose-owning role
- **Expected**: Code blocks (fenced with backticks or tildes), bash commands, file paths, markers/sentinel comments (e.g., `<!-- SQUIDSQUAD:* -->`), and placeholders (e.g., `{{ROLE_NAME}}`). All must be preserved verbatim — byte-for-byte identical to the deterministic draft.

### CQ-4: When does compose fire for an L1–L3 layer change vs. an L4 change?

- **Files**: Composed instructions for the compose-owning role
- **Expected**: L4 changes (PM directive, human edit) trigger compose immediately at the end of the current cycle, followed by a reboot of the affected agent. L1–L3 changes (repo-owner layers) only trigger compose during a `squidsquad-upgrade` or fresh install — never on normal cycles or random file edits.
