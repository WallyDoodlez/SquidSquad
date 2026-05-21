# RESEARCH-9742 — Boot TOCTOU Monitor Hang

**Issue**: #9742
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

When an agent boots in event mode, it probes harness reachability at Step 2 of `boot-bootstrap.md` via `curl -sf --max-time 5`. If the probe succeeds, the agent enters event mode and invokes the Monitor tool wrapping `event_poll.py`. There is a TOCTOU (time-of-check / time-of-use) window between the curl check and the Monitor invocation: the harness can die in that gap.

Once the Monitor tool is active and the harness is gone, two contradictory things are true simultaneously:

1. `event_poll.py` exits with code 2 (`sys.exit(2)`) when `poll()` returns `None` — the script does the right thing.
2. `l1-base.md` is silent about what the **agent** should do when Monitor exits unexpectedly. The agent is left without instruction and may stall waiting for the (now-dead) Monitor to emit another line.

The `l1-base.md` "Harness-Loss Recovery (#9588)" section covers harness loss **after** `bootup-complete` — instructing the agent to NOT pivot to forge-direct work. But it says nothing about what happens if Monitor exits before `bootup-complete` is even emitted, or at any point mid-session when the process simply terminates. The agent is told to wait for Monitor output; Monitor is gone; the session hangs until a human intervenes.

Issue body confirmed this framing: the recommended fix is a doc-only clarification in `l1-base.md` that when Monitor exits (regardless of timing), the agent must exit the session rather than attempting any manual recovery.

---

## 2. File-Grounded Findings

### 2.1 TOCTOU window location

`references/sub-skills/common/boot-bootstrap.md:20-26` — Step 2 performs the curl probe. The probe succeeds, and Step 3 begins: the agent Reads the event fragments (including `l1-base.md`) and then invokes Monitor. The window is everything between the curl returning exit 0 and `event_poll.py` acquiring its first successful connection to the harness.

### 2.2 event_poll.py exit behavior is correct

`references/scripts/event_poll.py:307-311` — The `--wait` loop exits `sys.exit(2)` on `poll()` returning `None`. `poll()` returns `None` on: fatal HTTP error (4xx), cursor write failure (disk/permission), or connection drop. A harness crash causes `urllib.error.URLError`, which returns `(None, True, reason)` from `_fetch()` (line 176-180) — treated as transient, retried with backoff. But if the harness stays down, retries eventually exhaust... wait, actually they do NOT exhaust in the `--wait` loop: `poll()` in `--wait` mode loops forever on transient errors (the `while True` at line 307 only exits on `events is None`, meaning a fatal/non-transient failure). This means: if the harness crashes after boot, `event_poll.py` itself will loop indefinitely retrying the transient connection error — it will NOT exit with code 2.

This is a significant finding: **`event_poll.py` does NOT exit non-zero on sustained harness loss in `--wait` mode**. The `sys.exit(2)` at line 311 is only reached on fatal errors (4xx, cursor write fail), not on transient retried connection failures. The issue body's statement "The poll loop at line 307-310 exits on poll returning None with sys.exit(2) — correct" conflates the single-shot mode with the `--wait` loop mode.

### 2.3 l1-base.md is silent on Monitor tool exit

`references/sub-skills/common-events/l1-base.md:35-47` — The "How You Listen" section instructs the agent to invoke Monitor and treat each stdout line as one event. There is no sentence covering what the agent should do if Monitor terminates (tool exits, stream closes). Without such instruction, the agent has no defined behavior at that exit point.

`references/sub-skills/common-events/l1-base.md:97-101` — "Harness-Loss Recovery (#9588)" covers post-`bootup-complete` harness loss: "do NOT pivot to forge-direct work mid-session. Operator restarts the agent to recover." This correctly blocks a drift to forge-direct mode. But it does not say "exit the session when Monitor exits." An agent following only this instruction may instead wait indefinitely for harness recovery (retrying `bootup-complete` at 5-minute backoff) while Monitor is already gone.

### 2.4 thin_launcher / harness auto-reboot dependency

The issue body's acceptance criterion states: "Agent session exits cleanly when event_poll dies; thin_launcher / harness auto-reboot picks it up." For this to work, the agent must exit with a non-zero code after Monitor exits. `thin_launcher.py` and the harness intent state machine (`running` → auto-reboot on death) are the recovery path — but they require the claude session to exit first. An indefinitely-hung session would never trigger the reboot.

### 2.5 AUDIT-A Risk 4 exact text

`.squidsquad/pm/planning/audits/AUDIT-A-events-architecture.md` (Side Effects, Risk 4) — states the mitigation as: "In `event_poll.py`'s main loop, if the harness becomes unreachable, exit non-zero so thin_launcher/harness auto-reboot catches it." Also: "the l1-base fragment should clarify that if the Monitor tool exits, the agent should not attempt manual recovery but should exit the session."

The audit presents this as a **dual-part mitigation**: (a) `event_poll.py` code change to exit non-zero on sustained harness loss in `--wait` mode, AND (b) `l1-base.md` instruction clarification. The issue body scopes it to doc-only, but finding 2.2 above shows `event_poll.py` does NOT exit non-zero on sustained transient-class failures — which is required for the auto-reboot path to work at all.

### 2.6 Compose pipeline requirement

`references/sub-skills/common-events/l1-base.md` is a source fragment. Per `feedback_l1_l4_only`, any change to it must flow through `compose.py deploy <role>` to regenerate composed CLAUDE.md fixtures. The fragment is in `RUNTIME_READ_FRAGMENTS` (per the AUDIT-A vault candidate noting `compose.py:40-52`), meaning compose does NOT inline it — agents Read it at runtime. Therefore, a change to `l1-base.md` takes effect immediately on next agent boot without a recompose step, though CQ fixture regeneration is still needed to keep test snapshots current.

---

## 3. Options

### Option A — Doc-only: l1-base.md Monitor-exit clause

Add a single explicit clause to `l1-base.md` under "How You Listen" (or "Harness-Loss Recovery") stating: if the Monitor tool exits for any reason (event_poll.py terminates, process crash, tool error), the agent MUST NOT attempt manual recovery — it must exit the session immediately with a non-zero outcome so the harness/thin_launcher can auto-reboot.

**Pros**: Minimal change, no code risk, single file, takes effect immediately on next boot (fragment is runtime-Read not composed-inlined). Satisfies the issue body's explicit scope.

**Cons**: Does NOT fix the underlying `event_poll.py` behavior: if `event_poll.py` hangs in its retry loop on sustained harness loss, Monitor never exits, so the new l1-base clause is never triggered. The doc fix only covers the case where `event_poll.py` has already exited — it does not cause `event_poll.py` to exit. The TOCTOU hang risk is partially mitigated (agent knows what to do WHEN Monitor exits) but the primary failure mode (Monitor never exits) is unaddressed.

**Files**: `references/sub-skills/common-events/l1-base.md` only.

### Option B — Code + doc: event_poll.py retry ceiling + l1-base.md clause

Add a maximum retry count or wall-clock timeout to the `--wait` loop in `event_poll.py` so that sustained harness unavailability causes the script to exit non-zero (code 2). Also add the l1-base.md clause from Option A.

**Pros**: Addresses both the script behavior (Monitor eventually exits on harness loss) and the agent behavior (agent exits cleanly when Monitor exits). Together these make auto-reboot reliable. Matches the full AUDIT-A Risk 4 mitigation. Consistent with `feedback_harness_sole_lifecycle` — the agent exits, the harness performs the restart.

**Cons**: Code change in `event_poll.py` requires QA verification. Need to tune the retry ceiling so transient blips (harness restart taking 15-30 seconds) don't false-positive. Adds a `--max-retries` or `--timeout-seconds` parameter to `event_poll.py` invocation syntax, which means `l1-base.md`'s Monitor invocation example must also be updated. Slightly more surface than a doc-only fix.

**Files**: `references/scripts/event_poll.py`, `references/sub-skills/common-events/l1-base.md`.

### Option C — Code only: event_poll.py retry ceiling, no l1-base update

Add the retry ceiling to `event_poll.py` but rely on the existing "Harness-Loss Recovery" section in `l1-base.md` to cover the agent behavior (operator restarts).

**Pros**: One fewer file changed.

**Cons**: The existing "Harness-Loss Recovery" section does not explicitly say "exit the session when Monitor exits" — it says the operator restarts the agent. Without the explicit exit instruction, an agent may still try to re-invoke Monitor manually or attempt some recovery behavior. The issue body's acceptance criterion ("Agent session exits cleanly when event_poll dies") is not guaranteed by existing prose. This option under-specifies the agent contract.

**Files**: `references/scripts/event_poll.py` only.

---

## 4. Recommended Option

**Option B** (code + doc).

The issue body scopes this as doc-only, and Option A satisfies the stated acceptance criteria narrowly. However, finding 2.2 reveals a substantive gap: without a `event_poll.py` retry ceiling, the Monitor tool never exits on sustained harness loss — making the l1-base.md doc clause a dead letter in the primary failure scenario. The AUDIT-A Risk 4 mitigation explicitly called for both parts.

Option B is the minimal complete fix: a bounded retry ceiling in `event_poll.py` (configurable via `--max-retries` or wall-clock) so Monitor exits when the harness stays down, plus the explicit l1-base.md "exit session on Monitor exit" clause so the agent acts correctly when that exit occurs.

The PM should surface finding 2.2 to the human — the issue body's "doc-only" scope assumption may have been based on the audit's suggestion that `event_poll.py:307-310` "exits on poll returning None with sys.exit(2) — correct," which is accurate only for single-shot mode, not `--wait` mode. This warrants a scope discussion before locking Option A.

---

## 5. Open Questions for PM/Human

1. **Is the event_poll.py `--wait` loop hang confirmed in production?** Finding 2.2 derives this from code reading — a minimal repro (kill the harness process while an agent is in Monitor, observe event_poll.py behavior) would confirm before filing a code change. Per `feedback_minimal_repro_over_symptom_match`, this should be verified rather than assumed.

2. **What retry ceiling is appropriate for event_poll.py?** A harness restart typically takes 5-20 seconds. A ceiling of 10 transient retries at 5s HTTP timeout = ~50s before exit. Does that match operator expectations? Too aggressive risks false positives on slow harness restarts; too lenient delays auto-reboot unnecessarily.

3. **Should the l1-base.md clause distinguish "Monitor exits cleanly (code 0)" vs "Monitor exits with error (code 2)"?** Code 0 would indicate `event_poll.py` exited normally (no events, empty poll in single-shot mode — but in `--wait` mode code 0 is unreachable). Code 2 = fatal error. The clause probably need not distinguish — either case warrants a session exit — but it is worth confirming.

4. **Does the fix require a CQ test update?** `l1-base.md` is a runtime-Read fragment; per `feedback_comprehension_tests_required`, any change to agent instructions must include CQ specs. Who owns the CQ spec: QA writes it per the #9184 workflow when picking up verification. PM should include a comprehension-coverage AC in the issue.

5. **Does the scope include updating the Monitor invocation in l1-base.md to pass `--max-retries`?** If Option B adds a CLI parameter to `event_poll.py`, the example command in `l1-base.md:38-43` needs updating. Confirm this is in scope.

---

## 6. Out of Scope

- Changes to `thin_launcher.py` or the harness intent state machine — the auto-reboot recovery path exists and is correct; this fix just ensures agents exit to trigger it.
- Changes to the curl probe in `boot-bootstrap.md` — the probe is not the problem; the problem is the gap after the probe.
- Addressing other AUDIT-A risks (cursor re-anchor race, in-flight dispatch, DM label-blind wait) — separate issues.
- Adding a code-side pre-check retry before Monitor entry (e.g., second curl probe just before invoking Monitor) — this would only narrow the TOCTOU window, not close it, and adds a third execution path per `feedback_harness_sole_lifecycle`.
- Polling-mode fallback path changes — the polling mode boot flow is unaffected by this issue.
