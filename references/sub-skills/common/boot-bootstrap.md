<!-- sub-skill: boot-bootstrap -->
## Boot — Mode Detection (#9588)

**This block is the FIRST instruction in your composed CLAUDE.md. Execute it BEFORE any other section, BEFORE invoking any tool, BEFORE responding to the human.** Steps 1–4 below are mandatory and must run in order on every fresh session start.

### Step 1 — Determine wake mode from config

Read `.squidsquad/config.md` and find the active wake mode:

- **If `.squidsquad/config.md` does not exist or cannot be read** (Read tool error, file absent, empty file) → **POLLING mode confirmed**, skip Step 2 and jump to Step 4. Defaulting to polling here mirrors the compose-time `_get_wake_mode` guard (`references/scripts/compose.py:_get_wake_mode`) and honors CONTEXT-9588 D3: the safe fallback for any uncertainty is polling.
- Else if `event-driven-[ROLE]: yes` is present (per-role override) → event-mode candidate.
- Else if `event-driven: yes` is present (global default) → event-mode candidate.
- Else (field absent, set to `no`, or unparseable) → **POLLING mode confirmed**, skip Step 2 and jump to Step 4 (polling branch).

### Step 2 — Check harness reachability (event-mode candidate only)

The harness must be reachable for event-mode to be used. Probe in this order:

1. **Read the port file** at `.squidsquad/.harness-port` (relative to repo root). If the file is absent OR unreadable OR empty OR its content is not a valid integer, default port to `7373` (the harness default — see `cycle_post.py:_discover_harness_port`).
2. **HTTP-probe the harness** with a 5-second timeout against the resolved port. Run via the Bash tool:
   ```bash
   curl -sf --max-time 5 http://127.0.0.1:<port>/status
   ```
   The `-s` flag silences progress output and `-f` makes curl exit non-zero on any HTTP error response — no shell redirect is needed (older versions of this instruction used `> /dev/null`, which fails on native Windows shells and would force a permanent polling fallback). Inspect the exit code only: 0 = harness reachable; any non-zero exit (curl error, connection refused, timeout, HTTP non-2xx, curl missing from PATH) = **harness unreachable**.

If the probe succeeds → **EVENT mode confirmed**, proceed to Step 3.
If the probe fails (for any reason — non-zero exit, network error, missing curl) → **fall through to polling** (jump to Step 4 polling branch). This fallback is intentional per #9580/#9588: until the harness is proven stable across all failure modes, agents fall back to `/loop` polling rather than the bespoke event-mode degraded path.

### Step 3 — EVENT mode: Read event fragments and follow them

Use the Read tool to read each of the following files **in order** and treat their concatenated content as your active wake-mode contract for this session:

1. `references/sub-skills/common-events/event-driven-workflow.md`
2. `references/sub-skills/common-events/l1-base.md`
3. `references/sub-skills/common-events/cursor-management.md`
4. `references/sub-skills/common-events/forge-read-pattern.md`
5. `references/sub-skills/common-events/idle-cooldown-loop.md`
6. `references/sub-skills/common-events/comment-handling.md`

**Role-specific extras** — if your role is `dm`, ALSO Read `references/sub-skills/roles/dm/events/pr-merge-wait.md` as a seventh file. If your role is not `dm`, skip this extra file (no other roles currently have events extras).

After reading, the boot sequence and event-listening loop described in those fragments take effect immediately. Do not proceed to Step 4 (polling branch is unreachable once Step 3 executes).

### Step 4 — POLLING mode: Read the polling fragment and follow it

Use the Read tool to read this single file:

- `[POLLING_FRAGMENT_PATH]`

Treat its content as your active wake-mode contract. Follow its instructions exactly — including invoking `/loop 30m execute one Ralph Loop cycle` (or the cadence specified by `config.md`'s `interval` field) to schedule cycles.

### Loaded mode is sticky

Once Steps 3 or 4 complete, your wake-mode contract is fixed for this session. Do **not** re-check mode mid-session. Mode flips (`config.md` `event-driven:` value changed by an operator) take effect on the next agent restart — not mid-cycle.

### Why polling is the harness-down fallback

The bespoke "degraded mode" in `common-events/l1-base.md` (sleep 60s + retry `work_queue()`) is removed in favor of polling fallback. The `/loop` mechanism is battle-tested across continuous operation including multiple harness outages; degraded mode added a third execution path that complicated the contract without proving more reliable. Operator restarts the agent to re-enter event-mode after the harness recovers.

<!-- /sub-skill: boot-bootstrap -->
