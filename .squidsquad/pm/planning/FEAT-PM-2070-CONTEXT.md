# FEAT-PM-2070 Context — Cycle Runner Script

## Scope

Separate mechanical shell operations (git, tracker, status bar, commits) from agent creative work via two Python scripts (`cycle_pre.py` and `cycle_post.py`). Agents call these at cycle start/end instead of 15+ individual bash calls. The agent's role template and SOUL.md continue to govern what the agent does — scripts only handle transport.

## Locked Decisions (human decided)

- **Soft bash policy**: Boilerplate bash removed from templates; agents keep bash access for creative work (tests, code reading, subagent spawning, verification commands). No hard block or allowlist.
- **Agent calls pre/post**: Keep current `/loop` mechanism unchanged. Agent template says "Step 1: run cycle_pre.py, read cycle-input.json" and "Final step: write cycle-output.json, run cycle_post.py". Two bash calls per cycle instead of 15+.
- **Hybrid quiet detection**: cycle_pre sets `likely_quiet: true` based on empty tracker queues. Agent can override if human input arrived via conversation context or other work is needed. ~100 token overhead for the override check.
- **Agent runs tests**: cycle_pre/post is the transport layer. What the agent does (including running tests, deciding work order, choosing what to verify) is governed by its role template and SOUL.md. Scripts never encode workflow decisions.
- **Titles only in queue**: cycle_pre lists queue items with numbers, titles, labels, and priority. Agent decides what to read in depth via `gh issue view`. Keeps agent in control of its own workflow.
- **Both from/to in transitions**: cycle-output.json status transitions specify both `from` and `to` states. cycle_post validates without needing an API call.
- **PM is a hybrid model**: cycle_pre handles transport for PM like all roles, but PM's creative phase always includes reading conversation context for human input. This is inherent to PM's role and documented explicitly in the template.
- **Transport vs Behavior principle**: cycle_pre/post = transport layer (deterministic infrastructure). Role template + SOUL.md = behavior layer (agent reasoning and workflow). This is a first-class architectural concept (#2108 filed for architecture doc).

## Dev Discretion (dev agent can choose)

- JSON schema structure details (field names, nesting) — as long as the contract is clear and documented
- Error handling specifics in cycle_pre/post (retry counts, timeout values)
- File location for cycle-input/output JSON (suggested: `.squidsquad/[role]/cycle-input.json`)
- Whether to add JSON schema validation files (nice to have, not required for v1)
- Internal code organization of cycle_pre.py and cycle_post.py (single file vs module)

## Side Effect Mitigations (required)

- **Branch switching correctness**: cycle_pre MUST ensure the agent is on the correct branch before the agent starts. cycle_post MUST commit to the correct branch. Agent never touches git checkout/branch commands. This fixes #2064 and related branch-switching bugs.
- **cycle-output validation**: cycle_post MUST validate cycle-output.json structure before acting on it. Invalid JSON or unknown fields → clear error, no partial execution.
- **Graceful degradation**: If cycle_pre fails (network down, git conflict), it MUST still write a degraded cycle-input.json with error flags so the agent can log the issue and skip tracker-dependent work. cycle_post still commits local state.
- **Agent crash recovery**: If the agent crashes mid-cycle (no cycle-output.json written), next cycle's cycle_pre detects the missing output and loads working-state.md for recovery.
- **Push conflict handling**: cycle_post inherits git_ops.py's pull-before-push logic. If push is rejected, pull --rebase and retry (up to 3 times).

## Upgrade Path (required)

- **Feature flag**: `Cycle Runner: yes|no` in config.md (default: `no` for existing installs). Agents with `no` use existing Ralph Loop unchanged.
- **New files**: `references/scripts/cycle_pre.py`, `references/scripts/cycle_post.py`. Runtime files (`cycle-input.json`, `cycle-output.json`) are gitignored.
- **Template changes**: All 4 role CLAUDE.md files restructured — mechanical steps replaced with cycle_pre/post calls. Sub-skills that encode mechanical steps are simplified or removed.
- **Rollout**: Incremental — start with skill agent (simplest cycle), then QA, DM, PM (most complex). Feature flag enables per-install opt-in.
- **Upgrade command**: `/squidsquad-upgrade` deploys new scripts and regenerates templates via compose.py.
- **Graceful degradation**: If `Cycle Runner: no` or scripts are missing, agents fall back to existing behavior. No breakage for non-upgraded installs.

## Out of Scope

- Changing how `/loop` works (keep current mechanism)
- Removing bash access from agents (soft policy, not hard block)
- Pre-fetching full issue details in cycle_pre (agent decides what to read)
- Running E2E tests in cycle_pre (tests are behavior, not transport)
- Multi-item-per-cycle QA verification with branch switching (one item per cycle is sufficient)
- Wrapper/boot script approach for cycle isolation (agent calls pre/post explicitly)
