# RESEARCH-9725 — /loop directive not executed on fresh boot

**Issue**: #9725
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-20 (cycle 1537)

---

## 1. Question

Why do freshly-spawned SquidSquad agents fail to invoke `/loop` reliably, even when their CLAUDE.md contains a correct boot directive? Observed reproducibly across 4+ skill reboots + QA + DM in the 2026-05-19/20 session: agents read CLAUDE.md, run AT MOST one cycle, then sit idle for hours without /loop firing again.

---

## 2. The Actual Mechanism (Grounded in Code)

### 2.1 The spawn invocation

`references/scripts/thin_launcher.py:155-164` builds the claude command line:

```python
cmd = [claude_exe, "--strict-mcp-config"]
if mcp_config.exists():
    cmd.extend(["--mcp-config", str(mcp_config)])
cmd.extend([
    "--append-system-prompt", f"SQUIDSQUAD_ROLE={role}",
    "--name", f"squidsquad-{role}",
    "--effort", effort,
    "--dangerously-skip-permissions",
    "Boot. Begin your first Ralph Loop cycle now.",   # ← positional arg = user prompt
])
```

The trailing string `"Boot. Begin your first Ralph Loop cycle now."` is passed as **the initial user prompt** for the session. Per `claude --help`:

> Arguments:
>   prompt    Your prompt

This is the FIRST USER MESSAGE the agent receives in its session.

### 2.2 What the agent then does

The agent's session opens. Two things happen approximately simultaneously:

1. CLAUDE.md is auto-discovered + loaded into the system prompt.
2. The initial user prompt arrives: `"Boot. Begin your first Ralph Loop cycle now."`

The agent processes that user prompt. CLAUDE.md's "On Startup" section (lines 206-212 in PM/DM CLAUDE.md, similarly placed elsewhere) says:

> When you first receive these instructions, first verify GitHub Issues access (see Tracker Protocol above). Then read the interval from `.squidsquad/config.md` (under `Iteration Interval > Minutes`) and invoke the `/loop` command to schedule repeating cycles:
> 
> ```
> /loop 30m execute one Ralph Loop cycle
> ```

But the user prompt says "Begin your first cycle now" — an explicit instruction to run a cycle, not to set up /loop. **The user prompt takes precedence over CLAUDE.md guidance** (which is closer to "instructions/preferences" than to imperatives in the model's prompt hierarchy).

The agent does literally what the user prompt asks: runs one cycle. Then the session waits for the next user message — which never comes, because there's no scheduler to send it.

### 2.3 Why this isn't obvious from logs

- The first cycle DOES complete (cycle_pre → work → cycle_post → iter log written). So agent looks "healthy" right after boot.
- `current-state` gets written to `idle|` at cycle end. So the status bar correctly shows idle.
- claude.exe stays alive (interactive session, waiting for input). Health check sees the PID and reports "healthy."
- Only the *cycle counter* and *iter log* failing to advance over time reveals the stall — and even then, intermittent /loop fires (when the agent is given another user prompt for some reason) can mask the pattern.

### 2.4 Cross-check against the other proposed root causes from the issue body

The issue body proposed 4 candidate mechanisms. Status of each after this investigation:

| Candidate | Status |
|-----------|--------|
| (1) Prompt-following failure (LLM exits cleanly without invoking tail-end imperative) | **Partially right** — the LLM IS following the explicit user prompt (run cycle now), and the CLAUDE.md /loop directive is tail-end vs an explicit user instruction. So the symptom is real, but the mechanism is "user prompt overrides system prompt directive," not pure prompt-following failure. |
| (2) Slash command not registered in non-interactive session | **Wrong.** Headless mode is `--print/-p`. Thin launcher does NOT use --print — it's interactive. Slash commands ARE available. The agent just doesn't invoke /loop because it wasn't asked to. |
| (3) MCP config interaction | **No evidence.** `--strict-mcp-config` + `--mcp-config <mcp-agents.json>` look correct; no error logs related to MCP at startup. |
| (4) CLAUDE.md /loop directive wording (descriptive vs imperative) | **Contributes but secondary.** Even with hyper-imperative wording, an explicit user prompt saying "begin your first cycle now" still trumps it. The wording rewrite is a defense-in-depth improvement, not the fix. |

The actual root cause was a 5th option not in the original list: **the spawn prompt explicitly directs the agent to run a cycle, not to set up scheduling.**

---

## 3. Why This Worked Before (Or Did It?)

Quick git-blame on thin_launcher.py:163:

This pattern (passing a prompt arg to claude) has been the design for a while. The "Boot. Begin your first Ralph Loop cycle now." string has been there since the thin_launcher was introduced (#4966). So when did /loop start firing reliably, and when did it stop?

Observation: the iter logs in `.squidsquad-state/<role>/iterations/` show recent cycles, BUT the recurring stall pattern across this session (4 skill reboots, QA + DM) suggests /loop has been unreliable for a while. Maybe it never fired reliably and the symptom only became visible when we started rebooting agents more often during the harness-debugging session.

Hypothesis: in normal operation, agents respawn rarely. The first cycle from `thin_launcher`'s spawn prompt covers most boot scenarios. Subsequent cycles fire because the agent itself uses `ScheduleWakeup` or similar internal tool to register polling — NOT because `/loop` is set up at boot. The `/loop` directive in CLAUDE.md might be vestigial.

Need to verify: does any agent currently invoke `ScheduleWakeup` in its cycle_post flow? If yes, that's the actual scheduling mechanism, and the CLAUDE.md `/loop` directive is misleading documentation.

---

## 4. Options Surveyed

### Option A — Change the spawn prompt to invoke /loop directly

Replace `"Boot. Begin your first Ralph Loop cycle now."` in `thin_launcher.py:163` with the literal /loop invocation:

```python
"/loop 30m execute one Ralph Loop cycle",
```

The agent's first turn becomes a /loop registration. /loop then schedules cycle 1 + subsequent cycles. The CLAUDE.md "On Startup" directive becomes informational rather than load-bearing.

**Pros**: minimal change (1 line). Self-documenting (the spawn command IS the /loop registration). Fixes the bug at its source.
**Cons**: hardcodes the interval (`30m`). Doesn't respect `config.md` `Iteration Interval > Minutes`. (Mitigation: read config in thin_launcher and substitute.)

### Option B — Two-prompt boot

Send `/loop 30m execute one Ralph Loop cycle` first, then a follow-up prompt `Begin your first cycle now`. Requires either two-message spawn (not supported by single-shot CLI invocation) or a wrapper script.

**Pros**: explicit setup + first cycle.
**Cons**: Claude CLI doesn't natively support multi-prompt batches. Would need stream-json input or a shell wrapper. More moving parts.

### Option C — Rely on ScheduleWakeup, drop /loop entirely

If agents already use ScheduleWakeup at cycle_post end (need to verify), the /loop layer is redundant. Remove the /loop directive from CLAUDE.md; let each cycle's ScheduleWakeup self-schedule the next.

**Pros**: simpler. Removes the dual-mechanism (ScheduleWakeup + /loop both ostensibly scheduling cycles).
**Cons**: requires verifying ScheduleWakeup is actually being called by all agents. Confirm by audit of recent cycle_post logs.

### Option D — Strengthen the spawn prompt with both instructions

Replace the spawn prompt with: `"First invoke /loop 30m execute one Ralph Loop cycle. Then begin your first cycle."`

**Pros**: explicit dual directive. No script changes needed beyond the prompt text.
**Cons**: relies on the LLM correctly sequencing two imperatives in one user message. Risks the second part getting lost (the same prompt-following failure mode that #9574 surfaced for the CQ runner's tail-end Write).

### Recommendation

**Option C if verified, else Option A.**

Verification needed: read the actual cycle_post.py + skill/PM working CLAUDE.md content to determine whether agents use `ScheduleWakeup` for self-scheduling today. If yes → Option C (delete /loop directive entirely). If no → Option A (one-line thin_launcher fix).

---

## 5. Open Questions for CONTEXT (Phase 2)

1. **Does any agent today actually use `ScheduleWakeup`?** Audit cycle_post.py + the role CLAUDE.md content. If yes, /loop is redundant and Option C applies. If no, Option A is correct.

2. **If Option A: should the interval be hardcoded in thin_launcher.py or read from config.md?** Hardcoded `30m` is simple but breaks if operator changes the interval. Reading config at spawn time adds 1 line of code and is cleaner.

3. **What about the CLAUDE.md /loop directive — keep, remove, or rewrite?** If Option A ships, the spawn handles /loop registration and CLAUDE.md's "On Startup" directive is unnecessary. Removing it shrinks CLAUDE.md and removes a known prompt-following failure point.

4. **Does #9588's lazy-load bootstrap affect this?** The bootstrap directs the agent to Read fragments at runtime, including `ralph-loop-overview.md` which itself contains the /loop directive. Same issue applies — the spawn prompt would still need to handle /loop registration regardless of how the supporting documentation is composed.

5. **Per-agent override**: should the spawn prompt vary by role? PM might want a different interval than DM. Today's design treats all agents uniformly. Status-quo unless reason to change.

6. **Backward-compat with existing live agents**: any agent currently running (PID-alive but stalled in idle) will need a reboot to pick up the new spawn prompt. Acceptable since reboot is the standard recovery path.

7. **Regression test**: how to verify the fix? An integration test that spawns an agent via thin_launcher, waits for it to make 2+ cycles within 60 minutes (cycle counter advanced 2+, iter logs 2+), and asserts both happen. Requires running thin_launcher in a test fixture.

---

## 6. Dependencies

- `references/scripts/thin_launcher.py:155-164` — primary fix site for Option A.
- `references/sub-skills/roles/<role>/ralph-loop-overview.md` — CLAUDE.md /loop directive source. Possibly modified or deleted for Option C.
- `references/scripts/cycle_post.py` — need to audit for ScheduleWakeup usage.
- `tests/test_thin_launcher.py` (if exists) — regression tests.

## 7. Non-Goals

- Switching to event-mode wakes (separate path, covered by harness work).
- Changing the actual cycle interval default (30m stays).
- Refactoring thin_launcher more broadly (focused fix).
- Fixing the orphan-claude-from-subagents pattern (#9688, separate).

## 8. Risks

1. **Hardcoding /loop interval in thin_launcher breaks config-driven cadence** — mitigate by reading config at spawn time.
2. **Removing CLAUDE.md /loop directive loses documentation of the scheduling mechanism** — mitigate by adding a one-line note in CLAUDE.md pointing at the actual scheduler (thin_launcher or ScheduleWakeup).
3. **Some unknown code path may depend on the existing spawn prompt text** — mitigate by greping for `"Boot. Begin your first"` literal before changing. (Verified: only used in thin_launcher.py.)
4. **Live agents need a reboot to pick up the fix** — acceptable; document in ship comment.

## 9. Next Step

Need ONE more audit before CONTEXT: check if `ScheduleWakeup` is actually called by agents in cycle_post (Q1). If yes, Option C is the cleaner fix. If no, Option A. Then write CONTEXT-9725.md locking the chosen option + answers to Q2-Q7.
