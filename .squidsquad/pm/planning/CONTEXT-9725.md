# CONTEXT-9725 — /loop directive not executed on fresh boot

**Issue**: #9725
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-20 (cycle 1537)
**Status**: open → ready-for-pickup (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9725 + this CONTEXT-9725.md combined are the contract for skill at pickup. The body describes the symptom; this file locks the fix mechanism.

---

## 1. Locked Root Cause

**The spawn prompt in `thin_launcher.py:163` directs the agent to run a cycle immediately, not to register /loop scheduling.** Result: agent runs at most one cycle then sits idle waiting for input that never comes.

Specifically the prompt `"Boot. Begin your first Ralph Loop cycle now."` is passed as the initial user message. The agent prioritizes this explicit instruction over the CLAUDE.md "On Startup" directive (which says "invoke /loop"). After the one cycle completes, no scheduler is set up; no further cycles fire.

This is not a prompt-following bug per se — the agent is following the explicit user prompt correctly. The bug is in the prompt itself.

## 2. Locked Fix — Option A from RESEARCH §4

Change `thin_launcher.py:163` from:

```python
"Boot. Begin your first Ralph Loop cycle now.",
```

To:

```python
f"/loop {interval}m execute one Ralph Loop cycle",
```

Where `interval` is read from `.squidsquad/config.md` field `Iteration Interval > Minutes` at spawn time (default `30` if absent or unreadable).

### Locked semantics

- The spawn prompt IS the /loop registration. Agent's first turn registers the schedule.
- /loop's mechanism then handles cycle 1 + cycle 2 + ... at the configured cadence.
- CLAUDE.md "On Startup" directive becomes informational documentation; the spawn handles the actual registration.
- No change to CLAUDE.md required (existing inline `/loop 30m` text + #9588's bootstrap-referenced `ralph-loop-overview.md` both stay).

## 3. Why not Option C (ScheduleWakeup)

Audit confirms: ScheduleWakeup is **NOT used anywhere** in `references/scripts/` or `references/sub-skills/`. Zero hits. Skill, QA, DM have no ScheduleWakeup wiring. Only PM has been using it tactically in this session as an agent-runtime tool, not as part of the scheduling architecture.

Migrating to ScheduleWakeup would require adding self-scheduling calls to every agent's cycle_post equivalent — substantially more work than the one-line spawn-prompt fix. Defer that refactor unless it becomes its own priority.

## 4. Why not Option D (dual-imperative spawn)

`"First invoke /loop... Then begin your first cycle"` is fragile — relies on the LLM correctly sequencing two imperatives in one prompt. Same prompt-following failure mode that produced #9574 (CQ runner skipped Write). Option A is simpler and removes the sequencing risk: /loop's own mechanism handles cycle 1.

## 5. Grounded File References

### 5.1 Primary fix site

- `references/scripts/thin_launcher.py:155-164` — `cmd.extend([...])` block. Line 163 has the literal spawn prompt to change.

### 5.2 Config-read helper

- `references/scripts/config.py:get_field` — used at module top of `thin_launcher.py` already (line 31, `_get_effort_level`). Add a similar `_get_interval()` helper that reads `iteration-minutes` (or whatever the canonical key is) and defaults to `"30"`.

Check the actual field name first:

```bash
python references/scripts/config.py get iteration-minutes 2>/dev/null
```

If that returns nothing, try the v1 key path. Audit during implementation.

### 5.3 Files NOT modified

- `references/sub-skills/roles/<role>/ralph-loop-overview.md` — CLAUDE.md /loop directive stays. Becomes informational rather than load-bearing, but no harm in keeping.
- `references/sub-skills/common/boot-bootstrap.md` (#9588) — bootstrap stays. Independent change.

## 6. Relationship to #9588

`#9588` and `#9725` are **independent fixes that both ship**:

- `#9588` makes mode-specific instructions lazy-loaded.
- `#9725` makes `/loop` registration happen at spawn time.

Both can land in either order. No conflict between them.

**Caveat**: `#9588`'s runtime-Read pattern surfaces a separate bug — `[INTERVAL]` placeholder in `ralph-loop-overview.md` is not substituted at runtime Read. That's tracked as a blocker on #9588 itself (commented there), separate from #9725. Once `#9725` ships, the `[INTERVAL]` bug becomes lower-stakes because the SPAWN prompt handles /loop registration, not the in-session fragment Read.

## 7. Acceptance

- `thin_launcher.py:163` rewritten to invoke `/loop {interval}m execute one Ralph Loop cycle` as the spawn prompt, with `interval` read from `config.md`.
- A freshly rebooted agent (skill, qa, dm, or pm) executes the /loop registration on its first turn. Cycles fire reliably every `interval` minutes thereafter.
- Stress test: reboot all four agents simultaneously via `boot_remote.py --all`. Verify within 65 minutes (2 cycles + slack):
  - `.squidsquad-state/<role>/cycle-input.json` mtime updated 2+ times.
  - `.squidsquad-state/<role>/iterations/` contains 2+ new iter-N.md files per role.
  - `.squidsquad/<role>/current-state` file updates cycle through phases (not stuck at `idle|`).
- Regression test in `tests/test_thin_launcher.py` (if exists) or new test:
  - Assert `thin_launcher.py:main` builds a command whose final positional arg starts with `/loop`.
  - Assert the interval value comes from config (mock config.md, verify substitution).

## 8. Out of Scope

- Removing or rewriting CLAUDE.md "On Startup" /loop directive — stays as documentation.
- Migrating to ScheduleWakeup — separate refactor, not now.
- Fixing the `[INTERVAL]` placeholder in `ralph-loop-overview.md` for #9588's runtime-Read pattern — tracked on #9588.
- Changing the cycle interval default (30m stays).
- Per-agent custom intervals — uniform `iteration-minutes` for all roles.

## 9. Open Questions Resolved (from RESEARCH-9725 §5)

1. **ScheduleWakeup usage?** No — zero usage outside PM's tactical use this session. Option C not viable.
2. **Hardcode interval or read from config?** Read from config.md at spawn time. Default to `30` if absent.
3. **Keep, remove, or rewrite CLAUDE.md /loop directive?** Keep as informational documentation. Spawn handles the actual registration.
4. **Affected by #9588?** No, independent. (Side note on `[INTERVAL]` substitution bug under #9588 — handled on #9588's thread.)
5. **Per-agent override?** No. Uniform `iteration-minutes` per role.
6. **Backward-compat?** None needed — existing stalled agents will pick up the new spawn prompt on next reboot.
7. **Regression test approach?** Unit test on `thin_launcher.py:main` command construction + integration test reboot-and-watch.

## 10. Sequencing

- Ship independently. No ordering constraint vs #9588.
- Once shipped: reboot all four agents (PM, skill, qa, dm) to pick up the new spawn prompt. Verify cycles fire on cadence.
- Watch for ~2 hours post-ship to confirm reliability across multiple cycles.

## 11. Risk Notes (for skill at pickup)

1. **`config.get_field` returns None on missing key** (per existing usage at thin_launcher.py:31). Handle that path — default to `"30"` when None.
2. **Interval value type**: config might store it as int or string. Pass to /loop as a string with `m` suffix appended.
3. **`/loop` syntax**: verify the agent in this Claude Code version actually understands `/loop <duration>m <prompt>` as the registration command. Per the skill memory `/loop` is a skill registered slash command — should work, but smoke-test the spawned agent's first turn output.
4. **Test environment**: don't accidentally spawn against a live agent that has work in progress. Use a separate test clone or stop affected agents first.

## 12. Next Step

PM presents this CONTEXT-9725.md to the human for approval. On approval: PM comments "ready for pickup" on #9725. Skill picks up (autonomously since it's role:skill + status:open + bug type per `feedback_auto_approve_bugs`). Implementation should be small (one file changed, one helper added, regression test).
