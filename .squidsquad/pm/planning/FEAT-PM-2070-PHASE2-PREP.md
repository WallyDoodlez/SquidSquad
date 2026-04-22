# FEAT-PM-2070 Phase 2 Prep — Cycle Runner Script

## Optimal Question Order

Dependencies and foundational decisions first, controversial/preference-based last:

1. **Q3** (Agent bash access) — foundational constraint that shapes all other answers
2. **Q2** (/loop integration) — architectural decision that determines how pre/post are invoked
3. **Q7** (Quiet cycle detection) — depends on Q3 (what the agent can do) and Q2 (where logic lives)
4. **Q1** (E2E test execution) — depends on Q3 (bash access policy) and Q2 (wrapper vs agent-invoked)
5. **Q5** (Pre-fetch detail level) — depends on Q1/Q7 (what cycle_pre already does)
6. **Q4** (Status transition granularity) — independent, low controversy, schema detail
7. **Q6** (Human interaction flow) — PM-specific, least controversial, mostly an acknowledgment

---

## Q3: Should the agent be fully blocked from bash during creative work, or just discouraged?

**Category**: Architecture (foundational constraint)

### Option A: Full bash block — whitelist only
- Agent cannot invoke bash at all during creative phase; only cycle_pre/post run commands
- **Pros**: Maximum token savings; zero risk of boilerplate creep; cleanest separation
- **Cons**: Breaks tests, code reading, subagent spawning, verification commands; requires cycle_pre to pre-run everything the agent might need (infeasible for creative work); PM/QA are especially harmed since verification requires reading code and running checks

### Option B: Discouraged via template instructions (soft policy) [RECOMMENDED]
- Agent retains full bash access but template instructions say "use cycle-input/output for mechanical ops; use bash only for creative work (tests, code reading, subagent spawning, verification)"
- **Pros**: No infrastructure changes to enforce; agents can still do everything they need; boilerplate is eliminated by cycle_pre/post providing the data; simple to implement and iterate
- **Cons**: Agents may drift back to boilerplate bash over time; no enforcement mechanism; relies on template discipline
- **Mitigation**: cycle-input.json already provides all mechanical data, so there is no reason for agents to call git_ops, tracker, or status bar commands — the template simply does not instruct them to

### Option C: Bash access with an allowlist filter
- Agent can invoke bash, but a wrapper intercepts and blocks specific commands (git, gh, tracker.py, status bar writes)
- **Pros**: Enforced separation without breaking creative bash needs; agents can still read code, run tests, spawn subagents
- **Cons**: Complex to implement (bash interception layer); fragile (new commands slip through); overhead of maintaining the allowlist; may interfere with legitimate edge cases
- **Mitigation**: Could start with Option B and add the filter later if drift is observed

---

## Q2: How does the `/loop` command integrate with cycle_pre/post?

**Category**: Architecture (integration design)

### Option A: Wrapper script — /loop invokes a wrapper that runs pre → agent → post [RECOMMENDED]
- `/loop` calls a new `cycle_wrapper.py` (or shell script) that: (1) runs `cycle_pre.py`, (2) invokes the agent's creative phase, (3) runs `cycle_post.py`
- **Pros**: Agent template is clean — no mention of pre/post scripts; pre/post always run even if agent crashes (post can have a finally block); single integration point; agent never forgets to call pre/post
- **Cons**: Requires changes to `/loop` infrastructure; the "agent creative phase" invocation from a wrapper is architecturally tricky — the wrapper must somehow trigger the agent and wait for it; may require rethinking how `/loop` works
- **Mitigation**: The wrapper could write cycle-input.json and set a flag, then the agent (already running in the loop) reads it and writes cycle-output.json, then the wrapper detects the output and runs post. This is event-driven rather than subprocess-based.

### Option B: Agent-invoked — agent calls cycle_pre at start, cycle_post at end
- The agent template instructs the agent to run `python references/scripts/cycle_pre.py` as Step 1 and `python references/scripts/cycle_post.py` as the final step. Two bash calls per cycle.
- **Pros**: Simplest to implement; no changes to /loop infrastructure; agent is in full control; easy to debug; works today with existing architecture
- **Cons**: Agent still makes 2 bash calls per cycle (though much fewer than 10-20+); agent could forget or skip the calls; if agent crashes mid-cycle, cycle_post never runs; still some template complexity
- **Mitigation**: 2 bash calls is a massive reduction from 10-20+; crash recovery is already handled by working-state.md

### Option C: Hybrid — /loop runs pre, agent runs normally, /loop runs post
- `/loop` has pre-hook and post-hook support. Configure `cycle_pre.py` as the pre-hook and `cycle_post.py` as the post-hook.
- **Pros**: Clean separation; agent never calls pre/post; hooks are a natural extension of /loop; post-hook can run in a finally block for crash safety
- **Cons**: Requires /loop to support hooks (new feature); the hook output (cycle-input.json) must be available to the agent in the right location; adds complexity to /loop which is currently simple
- **Mitigation**: /loop hook support is a small, well-scoped feature and could be useful beyond this task

---

## Q7: Should quiet cycle detection happen in cycle_pre or remain agent-side?

**Category**: Behavior (decision boundary)

### Option A: cycle_pre detects quiet and sets a flag [RECOMMENDED]
- cycle_pre checks all work queues. If all are empty and no pending verifications exist, it sets `quiet: true` in cycle-input.json. The agent sees the flag and either skips creative work or runs improvement scanning.
- **Pros**: Deterministic — empty queues are a mechanical check; saves the agent from making tracker queries; consistent across all roles; agent can still override (e.g., human input makes it non-quiet)
- **Cons**: Skill agent's quiet counter is more nuanced (was real work done? — depends on agent judgment); cycle_pre cannot know if the agent will do creative work this cycle
- **Mitigation**: cycle_pre sets a `suggested_quiet: true` flag. The agent makes the final determination. cycle_post receives the agent's `cycle_type: "quiet" | "active"` declaration.

### Option B: Agent-side only — agent decides quiet status
- cycle_pre provides all queue data. The agent inspects it and decides if this is a quiet cycle.
- **Pros**: Agent has full context including human input, working state nuances, and judgment; handles the skill agent's quiet counter naturally; no false-quiet risk
- **Cons**: Agent burns tokens analyzing queues that are obviously empty; duplicates logic across all role templates; inconsistent quiet detection across roles

### Option C: Split — cycle_pre for simple roles, agent for skill
- QA and DM get `quiet: true` from cycle_pre (their detection is trivial). Skill agent decides its own quiet status because the counter logic requires judgment about "real work."
- **Pros**: Best of both worlds — mechanical where possible, creative where needed
- **Cons**: Inconsistent behavior across roles; more complex cycle-input schema (some roles have quiet flag, others don't); harder to reason about
- **Mitigation**: Use the same `suggested_quiet` field for all roles but document that skill agent may override it

---

## Q1: Should cycle_pre run E2E tests, or should the agent still run them during creative work?

**Category**: Behavior (execution boundary)

### Option A: cycle_pre runs tests, agent gets results in cycle-input [RECOMMENDED]
- cycle_pre executes the test command and captures output (pass/fail, test count, failure names). Results are provided in cycle-input.json under `e2e_test_result`.
- **Pros**: Eliminates a bash call from the agent; test execution is purely mechanical (run command, capture output); agent focuses on interpreting failures (creative work); consistent — all mechanical work is in cycle_pre
- **Cons**: Adds latency to cycle_pre (tests may take minutes); if tests are flaky, agent cannot immediately re-run; agent loses real-time test output streaming
- **Mitigation**: cycle_pre can set a timeout and report `"result": "timeout"` if tests hang; agent can still run targeted tests during creative work for deeper investigation

### Option B: Agent runs tests during creative phase
- cycle_pre skips tests. The agent runs them via bash during creative work, sees output in real-time, and can react immediately.
- **Pros**: Agent sees full test output; can re-run specific tests; can abort early if obviously broken; real-time feedback loop
- **Cons**: Burns 300-500 tokens on the bash call; test execution is mechanical, not creative; every role template must include test-running instructions
- **Mitigation**: The token cost is relatively small compared to overall savings

### Option C: cycle_pre runs tests in background, agent gets results mid-cycle
- cycle_pre kicks off tests asynchronously. The agent starts creative work immediately. When tests finish, results are written to a file the agent can check.
- **Pros**: No latency added to cycle_pre; agent can work while tests run; best of both worlds for time
- **Cons**: Complex to implement (async coordination); agent must poll or be notified; race condition if agent finishes before tests; adds infrastructure complexity
- **Mitigation**: Could use a simple file-watch pattern, but the complexity is not justified for 30-minute cycles

---

## Q5: Should cycle_pre pre-fetch full issue details (body, comments) for queued items, or just list numbers and titles?

**Category**: Performance (data fetching boundary)

### Option A: List only — numbers, titles, labels, status
- cycle_pre returns a compact list. Agent calls `gh issue view` for items it actually works on.
- **Pros**: Fast cycle_pre execution; no wasted API calls for items not worked this cycle; agent fetches exactly what it needs
- **Cons**: Agent makes 1-3 additional bash calls per active item; some token overhead for those calls

### Option B: Pre-fetch top N items with full details [RECOMMENDED]
- cycle_pre fetches full details (body, comments, branch info) for the top 3-5 items in each queue (prioritized by triage order). Remaining items are list-only.
- **Pros**: Agent has immediate context for likely work items; zero additional bash calls for the common case (working on the top item); bounded API cost (max 5 fetches); good balance of latency vs completeness
- **Cons**: May fetch details for items not worked on; slightly longer cycle_pre; schema is larger
- **Mitigation**: 3-5 items is a small bound; the extra API calls during cycle_pre are cheap compared to agent token savings

### Option C: Pre-fetch everything — full details for all queued items
- cycle_pre fetches body, comments, and branch info for every item in every queue.
- **Pros**: Agent never needs to call gh; maximum token savings during creative phase
- **Cons**: Potentially very slow cycle_pre if queues are large; wasted API calls and bandwidth; cycle-input.json becomes huge; most items won't be worked on this cycle

---

## Q4: How granular should cycle-output.json status transitions be? Should the agent specify `from` and `to` states, or just the target state?

**Category**: Compatibility (API contract design)

### Option A: Both `from` and `to` states [RECOMMENDED]
- Agent specifies `{"number": 123, "from": "pending-test", "to": "pending-ship"}`.
- **Pros**: cycle_post can validate the transition without an API call (it knows the expected current state); catches stale-state bugs (if another agent changed the status between cycle_pre and cycle_post); matches tracker.py's existing `transition` API which requires both from and to; explicit is better than implicit
- **Cons**: Agent must track current state (but cycle-input already provides it); slightly more verbose output
- **Mitigation**: cycle-input.json already contains current statuses for all items, so the agent has the `from` state readily available

### Option B: Target state only
- Agent specifies `{"number": 123, "to": "pending-ship"}`. cycle_post looks up current state and constructs the transition.
- **Pros**: Simpler agent output; agent doesn't need to track from-state; less room for agent to specify wrong from-state
- **Cons**: cycle_post needs an extra API call per transition to get current state; cannot detect stale-state conflicts; diverges from tracker.py's API (which requires both)

### Option C: Target state with optional `from` for validation
- Agent can specify `from` optionally. If provided, cycle_post validates. If omitted, cycle_post looks it up.
- **Pros**: Flexible — agents that track state can provide it, others don't have to; backwards compatible as features evolve
- **Cons**: Inconsistent behavior; "optional validation" means sometimes bugs are caught and sometimes not; two code paths in cycle_post

---

## Q6: How does the human interaction flow (PM Step 2) work with cycle-input?

**Category**: Scope (PM-specific boundary)

### Option A: Acknowledge PM is hybrid — cycle-input handles tracker/git, conversation context handles human input [RECOMMENDED]
- cycle_pre provides all mechanical data (tracker state, health, git). Human input comes from the conversation context as it does today. PM template documents this explicitly: "cycle-input.json provides your operational state; human messages arrive via conversation history."
- **Pros**: Honest about the limitation; no unnecessary abstraction; PM already works this way; other roles are not affected; simple to document and implement
- **Cons**: PM is explicitly different from other roles — slight template inconsistency; future "agent-as-subprocess" architectures may want to capture human input too
- **Mitigation**: This is inherent to how LLM conversations work — cycle_pre cannot intercept human chat. The inconsistency is real and should be documented rather than papered over.

### Option B: cycle_pre captures pending human messages via a queue file
- Human writes to a `.squidsquad/pm/human-input-queue.md` file (or a tool writes to it). cycle_pre reads this file and includes messages in cycle-input.json.
- **Pros**: All input channels go through cycle-input; clean architecture; could support async human input (messages left between cycles)
- **Cons**: Requires a new input mechanism; humans don't naturally write to queue files; breaks the conversational flow that makes PM effective; over-engineering for a non-problem
- **Mitigation**: Could be useful for async workflows (human leaves a note overnight), but adds complexity now for uncertain future value

### Option C: PM skips cycle_pre for human-related steps
- PM's creative phase includes a "check conversation for human input" step that is outside the cycle-input contract. cycle_pre handles everything else.
- **Pros**: Explicit carve-out; PM template is clear about what comes from where
- **Cons**: Identical to Option A in practice; the "skip" framing is misleading since PM doesn't skip cycle_pre — it just has an additional input source
- **Mitigation**: Option A's framing is more accurate

---

## Summary Table

| Question | Category | Recommended | Key Rationale |
|----------|----------|-------------|---------------|
| Q3 | Architecture | **B — Soft policy (discouraged)** | Full block breaks creative work; template discipline is sufficient |
| Q2 | Architecture | **A — Wrapper script** | Cleanest separation; crash-safe; but B is viable if wrapper is too complex |
| Q7 | Behavior | **A — cycle_pre detects with `suggested_quiet` flag** | Mechanical check saves tokens; agent retains override authority |
| Q1 | Behavior | **A — cycle_pre runs tests** | Test execution is mechanical; agent interprets results (creative) |
| Q5 | Performance | **B — Pre-fetch top N items** | Bounded cost; covers the common case; avoids agent bash calls |
| Q4 | Compatibility | **A — Both `from` and `to` states** | Matches tracker.py API; enables validation without extra API calls |
| Q6 | Scope | **A — Acknowledge PM is hybrid** | Honest about the limitation; no over-engineering |
