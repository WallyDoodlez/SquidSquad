Now I have all the information needed. Let me produce the research document.

```markdown
# FEAT-PM-6126 Research — Harness Owns PR Merge + Compose

## Summary
This research analyzes the impact of moving PR merge execution and post-merge recompose from agents (QA, DM, PM) to the harness. Currently, agents call `git_ops.py pr-merge` directly (4 call sites), and PM runs `/squidsquad-compose` after merge detection via `git log --merges` (Step 6e). The proposed change centralizes merge authority in the harness via a new `POST /merge` REST endpoint, makes agents fire a `request-merge` event instead of merging directly, and moves recompose trigger to the harness based on whether merged files touch `references/`. This eliminates 5 agent-side call sites, removes PM's post-merge recompose step entirely, and adds 3 new event types to the catalog.

**Recommendation**: Feasible with caveats. The core architecture is straightforward — harness already has FastAPI endpoints, event bus emission infrastructure, and `git_ops.pr_merge()` is a mature, well-tested function. The primary risk is (a) merge failure handling in the harness (non-interactive context — no agent to resolve conflicts), (b) compose error handling (what if `deploy-all` fails?), and (c) ensuring agent templates properly fire `request-merge` via a REST call instead of a CLI command.

## Vault Context
- **BRIEFING.md priorities**: #5622 EPIC Harness Phase 3: Agent communication bus — agents read events (shipped); #3963 EPIC: Web dashboard — Harness Phase 4 (pending). This task aligns with the Phase 3+ trajectory of moving operational authority to the harness.
- **Related decisions**: [[decision-branch-per-feature-workflow]] — branch workflow enables PR-based merges, which is the path this feature rides on. [[decision-pid-primary-liveness]] — harness's direct PID monitoring philosophy extends naturally to owning merge operations: prefer harness over agent for mechanical ops.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — the merge endpoint should be a deterministic Python function call, not an LLM-involved decision. [[pattern-model-router-architecture]] — not directly applicable, but the event routing pattern (agent → harness → event bus → agents) mirrors the model router's proxy pattern.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — harness directly running `git_ops.pr_merge()` is the mechanical check. "Systems should self-heal: detect stuck states → unstick immediately" — harness detecting `references/` changes and auto-recomposing is self-healing. "PM should not intervene in code or branch management" — removing PM's post-merge recompose aligns with this preference.
- **Related learnings**: [[learning-qa-branch-merge-workaround]] — QA currently handles merge conflicts by merging working branch into feature branch (verification.md lines 259–268). This logic becomes irrelevant if harness merges — harness would need its own conflict strategy, or the merge would need to be rejected back to the agent. [[learning-atomic-migration-strategy]] — the upgrade path must be atomic: agents must not continue calling `pr-merge` CLI after harness takes over, or we get double-merges.

## Impact Analysis
- **Files touched**:
  - `references/scripts/harness.py` — new `POST /merge` endpoint, merge + compose logic, event logging for 3 new types
  - `references/scripts/git_ops.py` — remove `_emit("pr-merge", ...)` from `pr_merge()` (lines 342, 372); function remains as utility
  - `references/scripts/event_catalog.py` — add `request-merge` (recognized), `pr-merged` (emitted), `compose-completed` (emitted)
  - `references/scripts/cycle_pre.py` — update `_ROLE_EVENT_TYPES` (lines 377–382) to include `pr-merged`, `compose-completed`; update `_run_mechanical_reactions` to handle `pr-merged` (same as current `pr-merge` at lines 428–437)
  - `references/sub-skills/roles/qa/verification.md` — replace 3 `git_ops.py pr-merge` calls (lines 230, 256, 268) with `curl -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [N], "branch": "[BRANCH]", "role": "qa"}'`
  - `references/sub-skills/roles/dm/delivery-packaging.md` — replace 1 `pr-merge` call (line 48) with harness `POST /merge`
  - `references/sub-skills/roles/pm/post-merge-recompose.md` — **delete entire file**
  - `references/roles/pm/includes.yml` — remove line 11: `roles/pm/post-merge-recompose`
  - `references/roles/pm/instructions.md` — remove line 109: `{{include: roles/pm/post-merge-recompose}}`
  - `references/sub-skills/common/event-reactions.md` — add `request-merge`, `pr-merged`, `compose-completed` to the event type table
  - `tests/test_event_catalog.py` — update `test_emitted_tier_has_expected_events` (line 38–43) and `test_recognized_tier_has_expected_events` (line 45–49) expected sets
  - `tests/test_feat_1074_auto_merge.py` — adjust for `pr_merge()` no longer emitting events (or keep if backward compat)
  - New tests: `tests/test_feat_6126_harness_merge.py`
  - All composed CLAUDE.md files regenerate on next `compose.py deploy-all` — they pick up template changes

- **Behavior changes**:
  1. Agents no longer call `git_ops.py pr-merge` CLI — they POST to harness `/merge` instead
  2. Harness performs the merge, detects `references/` changes, conditionally runs `compose.py deploy-all`
  3. Harness emits `pr-merged` (with richer payload: pr_number, branch, issue_number, files_changed) instead of `git_ops.py` emitting bare `pr-merge`
  4. Harness emits `compose-completed` if recompose ran
  5. PM Step 6e disappears entirely — no post-merge recompose in PM cycle
  6. The `request-merge` event is recorded in the event stream for audit trail (agent requested merge)
  7. Agents see `pr-merged` and `compose-completed` events in their next cycle's `recent_events`
  8. The mechanical reaction that currently fires on `pr-merge` (cycle_pre.py line 428) must fire on `pr-merged` instead

- **Dependencies**:
  - `git_ops.pr_merge()` — stable, well-tested utility function. No behavior change needed except removing its internal `_emit`.
  - `compose.py deploy-all` (line 1171) — harness calls this as a subprocess. Already exists, already works from CLI.
  - `event_bus.py emit()` — used by harness to emit `pr-merged` and `compose-completed`. Already exists.
  - `gh` CLI or forge adapter — must be available on harness's PATH. Already required for current architecture.
  - `event_validator.py` — will naturally flag `pr-merged` if no role subscribes to it. Both PM and DM must react-to `pr-merged`.

## Side Effects
- **Risk 1: Double-merge race condition** — Severity: **M** — Mitigation: `git_ops.pr_merge()` already handles "already merged" gracefully (returns `True, "already merged"`). If an old-template agent calls `pr-merge` CLI while harness also tries to merge the same PR, the second caller gets "already merged". Harmless, but wasteful. Full mitigation requires upgrade sequencing: recompose agents THEN enable harness merge endpoint.
- **Risk 2: Compose failure during harness merge flow** — Severity: **H** — Mitigation: If `compose.py deploy-all` fails (exit non-zero), harness should still emit `pr-merged` (the merge succeeded) but emit `compose-completed` with `{"success": false, "error": "..."}`. Agents see the compose failure and can take corrective action. Never roll back the merge.
- **Risk 3: Harness merge blocks the event loop** — Severity: **M** — Mitigation: `pr_merge()` runs subprocesses (gh CLI) that can take several seconds. The `/merge` endpoint must run merge + compose in a background thread (pattern already exists in `/shutdown` at line 930 and deferred init at line 447). Return `202 Accepted` immediately with a status endpoint or event-based notification.
- **Risk 4: PM mechanical reaction breaks if pr-merge event stops being emitted** — Severity: **H** — Mitigation: The mechanical reaction in `cycle_pre.py` (lines 428–437) that creates `pr-merge-detected` for PM must be updated to trigger on `pr-merged` instead. If both `pr-merge` and `pr-merged` coexist during transition, handle both to avoid gaps. The `pr-merge-detected` reaction type can be renamed or kept as-is (internal detail).

## Edge Cases
- **Case: Merge conflict detected by `gh pr merge`**: `git_ops.pr_merge()` returns `(False, "merge conflict")`. Harness should emit `pr-merged` with `{"success": false, "error": "merge conflict"}` so the requesting agent can handle it. The agent's cycle will see this and can resolve conflicts (currently QA does `git merge origin/working` into feature branch — verification.md lines 259–268). This conflict resolution logic should remain in QA's template for the "merge failed → resolve → re-request merge" path.
- **Case: PR already merged (human merged manually between cycles)**: `git_ops.pr_merge()` returns `(True, "already merged")`. Harness emits `pr-merged` with `{"already_merged": true}`. No compose needed. Agents see the event and proceed.
- **Case: PR closed without merge**: `pr_merge()` returns `(False, "PR closed without merge")`. Harness emits `pr-merged` with error. Agents treat as skip.
- **Case: No `references/` files changed**: Harness skips compose. Only `pr-merged` event fires. `compose-completed` is never emitted. Agents should handle absence of `compose-completed` gracefully — it's conditional.
- **Case: `compose.py deploy-all` fails due to missing mandatory roles**: Compose exits non-zero (line 1176–1181 in compose.py). Harness captures stderr, emits `compose-completed` with failure details.
- **Case: Agent requests merge for a PR that doesn't exist**: Harness calls `pr_merge()` → `gh pr view` fails. `pr_merge()` currently returns `(False, "merge failed: ...")`. Harness should surface the exact error.

## Integration Risks
- **Risk: `git_ops.pr_merge()` emits its own `pr-merge` event** (lines 342, 372). If harness also emits `pr-merged`, the event stream gets two similar events per merge. Need to either suppress `git_ops`'s internal emit (preferred) or document that `pr-merge` is the raw-merge event and `pr-merged` is the harness-enriched event. Removing from `git_ops` is cleaner and simpler.
- **Risk: `cycle_pre.py` hardcoded role event filters** (lines 378–382) currently include `pr-merge` for PM, QA, skill, DM. These must be updated to `pr-merged` as well. During a mixed-version squad (some agents on old templates, some on new), old agents still see `pr-merge` events if `git_ops` still emits them. Removing the emit from `git_ops` forces all agents to the new path.
- **Risk: Event validator will flag `pr-merged` as orphaned** if no role declares `reacts-to: pr-merged` in config.md Event Reactions. Compose's `derive_and_write_event_contracts()` (compose.py line 649) regenerates these from CLAUDE.md analysis. If the template changes are in place, recompose will fix this automatically. But if a user deploys harness changes before recomposing, validation will fail.
- **Risk: Forge adapter path** — `pr_merge()` has forge adapter paths (lines 325–346). Harness calling `pr_merge()` inherits full forge adapter support for non-GitHub backends (Forgejo). No additional integration work needed.

## Upgrade & Migration
- **New config values**: `auto-compose` — default `yes` — controls whether harness auto-runs `compose.py deploy-all` after merge. Allows disabling if compose is managed externally.
- **New files**: None. Changes are all modifications to existing files.
- **Template changes**:
  - QA `verification.md`: 3 `pr-merge` CLI calls → 3 `POST /merge` REST calls. Merge conflict resolution section (lines 259–277) remains — QA handles failed merges by resolving conflicts and re-requesting.
  - DM `delivery-packaging.md`: 1 `pr-merge` CLI call → 1 `POST /merge` REST call.
  - PM `post-merge-recompose.md`: deleted entirely.
  - PM `instructions.md`: remove include directive.
  - PM `includes.yml`: remove manifest entry.
  - `common/event-reactions.md`: new event types table entries.
- **Upgrade steps**:
  1. Stop agents (`POST /agents/all/stop` or `/shutdown`)
  2. Pull new code
  3. Run `compose.py deploy-all` — regenerates all CLAUDE.md templates with new merge flow
  4. Start harness — now serves `POST /merge` endpoint
  5. Start agents — they now use `curl` to harness instead of `git_ops.py pr-merge`
  6. Old `pr-merge` CLI command remains functional in `git_ops.py` for manual/admin use, but agents no longer call it
- **Graceful degradation**: If an agent on old template calls `git_ops.py pr-merge` directly, the merge still works (git_ops unchanged). But harness doesn't know about it — no `pr-merged` event, no auto-compose. The old PM post-merge recompose would still run if PM is also on old template. This is safe but means the new flow isn't active until all agents are recomposed. No data loss or corruption risk.

## Open Questions
- **Q1**: Should `request-merge` be a dedicated `POST /merge` endpoint, or a generic `POST /events` with `event_type: "request-merge"` that harness intercepts? — **Why**: Dedicated endpoint is cleaner (REST semantics, explicit validation) but duplicative of event infrastructure. If harness intercepts events, it needs to distinguish "this event is a command to harness" from "this event is a notification." **Recommendation**: Dedicated `POST /merge` endpoint. Harness can still emit `request-merge` into the event stream for audit trail.
- **Q2**: What payload does `pr-merged` carry beyond what `pr-merge` carries today? — **Why**: Current `pr-merge` payload is `{"pr_number": "42"}`. The task spec says "PR number, branch, issue number, files changed." `branch` is extractable from `gh pr view --json headRefName` (already done in `pr_merge` line 375). `issue_number` requires parsing branch name (already done at line 384). `files_changed` requires `gh pr view --json files` or `git diff --name-only`. This is new and adds latency.
- **Q3**: Should harness wait for compose to complete before responding to `/merge`? — **Why**: Synchronous wait could mean the HTTP request hangs for 30+ seconds (compose can call Claude API for event contract derivation). Asynchronous (202 Accepted) with event-based notification is more robust but adds complexity for the requesting agent (must poll events or check merge status). **Recommendation**: Async. Return 202 immediately, emit `pr-merged` on merge completion, emit `compose-completed` on compose completion. The requesting agent sees these in its next cycle.
- **Q4**: What happens if harness itself is on an old version (no `/merge` endpoint)? — **Why**: Agent templates would call an endpoint that doesn't exist, getting HTTP 404. The agent's creative phase needs to interpret this and fall back. The upgrade sequence (stop → pull → recompose → start) prevents this, but if someone upgrades agents without upgrading harness, things break.

## Recommendation
**Feasible with caveats.** The architecture is sound — harness already owns agent lifecycle, event bus, and has the FastAPI infrastructure for new endpoints. `git_ops.pr_merge()` is a well-tested utility. The main implementation work is:
1. Harness `POST /merge` endpoint with async merge + compose
2. Removing 4 agent-side `pr-merge` call sites, replacing with REST calls
3. Deleting PM's post-merge-recompose sub-skill
4. Updating event catalog and cycle_pre.py for new event types

The caveats are: (a) merge failure handling shifts from agent creative judgment to harness mechanical logic — the harness must surface failures clearly so agents can resolve them next cycle; (b) compose failure must never block the merge event from being emitted; (c) careful upgrade sequencing is required to avoid double-merge windows.

## Vault Candidates
- **Type**: decision — **Harness owns all mechanical git operations — agents request, never execute** — **Why**: This task establishes a principle that could extend beyond PR merge: future ops like branch deletion, rebase, or issue closure could follow the same "agent requests, harness executes" pattern. A vault decision would lock this in as architecture.
- **Type**: pattern — **Async harness endpoints: 202 Accepted + event-based completion notification** — **Why**: The pattern of returning 202 immediately and emitting completion events is used by `/shutdown` (line 921) and should be formalized for `/merge`. Reusable for any future harness operation that takes >2 seconds.
- **Type**: learning — **Upgrade sequencing for authority migration: stop → compose → restart** — **Why**: When authority moves from agent to harness, all agent templates must be recomposed before the new flow activates. The upgrade sequence (stop agents, recompose, start harness, start agents) prevents dual-authority windows. This is the same sequence used for #4966 (sentinel→intent migration) and should be documented as a reusable pattern.
- **Type**: learning — **Merge conflict resolution should remain in agent templates, not harness** — **Why**: The harness can detect merge conflicts but shouldn't resolve them (requires code understanding). QA's conflict resolution logic (verification.md lines 259–277: merge working branch into feature branch, push, retry) stays in the QA template. Harness just surfaces the failure. This boundary between "mechanical execution" and "judgment-requiring resolution" is worth preserving as a documented learning.
```