# FEAT-PM-5868 Test Plan — Event consumption sub-skill

## Test Cases

### TC-1: Emission catalog classifies event types correctly across all three tiers
- **Precondition**: The hardcoded emission catalog exists in `compose.py` covering all known event types from `tracker.py`, `git_ops.py`, `cycle_pre.py`, and `cycle_post.py`
- **Steps**: Inspect the catalog for `pr-merge`, `status-transition`, `cycle-start`, `cycle-end`, `git-pull`, `git-push`, `git-commit`, `branch-checkout`, `pr-create`, `phase-change`, `verification-failed`, `verification-passed`, `agent-health`
- **Expected**: `pr-merge`, `status-transition`, `cycle-start`, `cycle-end`, `git-pull`, `git-push`, `git-commit`, `branch-checkout`, `pr-create` are classified `emitted`; `verification-failed`, `verification-passed`, `agent-health`, `phase-change` are classified `recognized`; any event type invented by the LLM not present in either list is classified `unknown`
- **Verification**: `python -c "from references.scripts.compose import EVENT_CATALOG; emitted=[k for k,v in EVENT_CATALOG.items() if v['tier']=='emitted']; recognized=[k for k,v in EVENT_CATALOG.items() if v['tier']=='recognized']; assert 'pr-merge' in emitted; assert 'verification-failed' in recognized; print('OK')"`

### TC-2: Catalog entries include human-readable description for process-gap translation
- **Precondition**: Emission catalog is defined in `compose.py`
- **Steps**: For `pr-merge`, `verification-failed`, and `status-transition`, check that each catalog entry has a non-empty `description` field
- **Expected**: Each entry includes a plain-language description (e.g., `pr-merge`: "a pull request was merged", `verification-failed`: "QA verification rejected the implementation")
- **Verification**: `python -c "from references.scripts.compose import EVENT_CATALOG; assert all(v.get('description') for v in EVENT_CATALOG.values()), 'Missing description'; print('OK')"`

### TC-3: Config.md Event Reactions section is written by compose and parsed by config.py
- **Precondition**: `compose.py deploy pm` has been run with the updated derivation logic; `config.py` has new FIELD_MAP entries for event reaction keys
- **Steps**: Run `python references/scripts/compose.py deploy pm` on a project with `agent-compose: yes`; then run `python references/scripts/config.py get pm-emits`
- **Expected**: config.md gains a `## Event Reactions` section with `- **pm emits**: cycle-start, cycle-end, ...` and `- **pm reacts-to**: pr-merge, ...`; `config.py get pm-emits` returns the comma-separated list
- **Verification**: `grep -A 20 "## Event Reactions" .squidsquad/config.md | grep "pm emits"` returns a non-empty line; `python references/scripts/config.py get pm-emits` exits 0 with output

### TC-4: Config.md Event Reactions section is written for all four roles on deploy-all
- **Precondition**: `compose.py deploy-all` is run with `agent-compose: yes`
- **Steps**: Run `python references/scripts/compose.py deploy-all`; inspect config.md
- **Expected**: `## Event Reactions` section contains entries for `pm`, `skill`, `qa`, and `dm` — both `emits` and `reacts-to` lines for each
- **Verification**: `python -c "text=open('.squidsquad/config.md').read(); roles=['pm','skill','qa','dm']; missing=[r for r in roles if f'{r} emits' not in text or f'{r} reacts-to' not in text]; assert not missing, f'Missing: {missing}'; print('OK')"`

### TC-5: Derivation runs on every compose unconditionally
- **Precondition**: Claude CLI is available (always true — SquidSquad = Claude Code)
- **Steps**: Run `compose.py deploy pm`; observe config.md
- **Expected**: Derivation runs; config.md `## Event Reactions` section is populated/updated with pm's emits and reacts-to
- **Verification**: `grep "pm emits" .squidsquad/config.md` returns a match after compose

### TC-6: Cross-agent validation runs after every compose (single-role and deploy-all)
- **Precondition**: A config.md with a complete `## Event Reactions` section for all four roles
- **Steps**: Run `python references/scripts/compose.py deploy skill` (single-role deploy)
- **Expected**: Cross-agent validation executes after the role is composed; it validates `skill`'s contract against all other roles' entries in config.md; output is printed to stdout/stderr
- **Verification**: Stdout/stderr contains validation output (e.g., "Event contract validation: OK" or a process-gap warning); no Python exception raised

### TC-7: Cross-agent validation detects orphaned emit (emit with no consumer)
- **Precondition**: config.md `## Event Reactions` section where `pm emits: foo-event` but no other role has `foo-event` in their `reacts-to`
- **Steps**: Run any `compose.py deploy` command
- **Expected**: Validation output includes a plain-language process-gap message describing the orphan — using the catalog `description` field, not the raw event name `foo-event`
- **Verification**: Stdout/stderr contains a human-readable gap description (e.g., "PM fires a signal that no other agent handles") rather than the raw string `foo-event`

### TC-8: Cross-agent validation detects missing consumer (reacts-to with no emitter)
- **Precondition**: config.md where `skill reacts-to: bar-event` but no role has `bar-event` in their `emits`, and `bar-event` is not in the `recognized` tier of the catalog
- **Steps**: Run any `compose.py deploy` command
- **Expected**: Validation flags `bar-event` as an `unknown` type — presents a process-gap message indicating skill is listening for something that nothing produces
- **Verification**: Stdout/stderr contains a process-gap message; no Python exception; `bar-event` is described in plain language

### TC-9: Cross-agent validation detects hallucinated event type
- **Precondition**: config.md where `pm emits: nonexistent-event-xyz` and `nonexistent-event-xyz` does not appear in the catalog as `emitted` or `recognized`
- **Steps**: Run any `compose.py deploy` command
- **Expected**: Validation flags `nonexistent-event-xyz` as `unknown` tier; presents it as a process-gap error (not just a warning)
- **Verification**: Stdout/stderr contains an error-level process-gap message about the unknown event; compose exits non-zero OR human fix-loop prompt appears

### TC-10: Cross-agent validation presents all failures as process-gap plain language
- **Precondition**: config.md with one orphaned emit and one unknown event type
- **Steps**: Run `compose.py deploy pm`
- **Expected**: Validation output contains zero raw event type strings in error messages — all gaps are described in terms of agent behavior and workflow ("PM fires a signal that no agent handles") not event bus internals
- **Verification**: Check that `pr-merge`, `status-transition`, or any raw event-name string does not appear in the gap-description output lines; only in catalog lookup internals

### TC-11: Fix loop presents failures and asks human; non-interactive mode falls through
- **Precondition**: Validation finds a gap; (a) interactive TTY; (b) `CI=true` or no TTY
- **Steps (a)**: Run compose in a terminal where stdin is a TTY; validation finds a gap
- **Steps (b)**: Run compose with `CI=true` or piped stdin; validation finds a gap
- **Expected (a)**: Human is prompted with plain-language description of the gap and options to fix
- **Expected (b)**: Compose logs warnings and completes without blocking; exit code 0
- **Verification (b)**: `CI=true python references/scripts/compose.py deploy pm` exits 0 even when gaps exist; stderr shows warning lines

### TC-12: cycle_pre.py reads event filters from config.md when Event Reactions section present
- **Precondition**: config.md has a populated `## Event Reactions` section; `cycle_pre.py` updated to read from it
- **Steps**: Run `python references/scripts/cycle_pre.py pm` with a mock harness that emits `pr-merge` and `cycle-start` events; config.md has `pm reacts-to: pr-merge`
- **Expected**: cycle-input.json `recent_events` contains `pr-merge` (listed in config) and filters out events not in pm's `reacts-to` list
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); types={e['event_type'] for e in d.get('recent_events',[])}; assert 'pr-merge' in types; print('OK')"`

### TC-13: cycle_pre.py falls back to hardcoded _ROLE_EVENT_TYPES when Event Reactions section absent
- **Precondition**: config.md does NOT contain a `## Event Reactions` section; cycle_pre.py updated version deployed
- **Steps**: Run `python references/scripts/cycle_pre.py pm` with a mock harness emitting mixed events
- **Expected**: Filtering behavior is identical to current hardcoded `_ROLE_EVENT_TYPES` (pm receives `pr-merge`, `verification-failed`, `verification-passed`, `cycle-start`, `cycle-end`, `status-transition`, `agent-health`); no error or exception
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); print('OK — events:', [e['event_type'] for e in d.get('recent_events',[])])"` — output matches expected pm filter set; no traceback in stderr

### TC-14: Self-event filtering is preserved in config-driven reactions
- **Precondition**: config.md `## Event Reactions` populated; harness emits a `cycle-start` event with `role=pm`
- **Steps**: Run `python references/scripts/cycle_pre.py pm`
- **Expected**: The pm-emitted `cycle-start` event does NOT appear in `mechanical_reactions` or trigger any reaction (self-event filter at line 413 preserved)
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert all(r.get('role') != 'pm' for r in d.get('mechanical_reactions',[])), 'Self-event leaked'; print('OK')"`

### TC-15: Cascade safeguard preserved — pr-merge reaction does not re-trigger itself
- **Precondition**: config.md `## Event Reactions` populated; `pr-merge` event from another role is in the event bus
- **Steps**: Run `python references/scripts/cycle_pre.py pm` twice in sequence (simulating two cycles)
- **Expected**: The `pr-merge` reaction fires on first cycle (event ID consumed via cursor); second cycle does not re-fire the same reaction (cursor-based deduplication preserved)
- **Verification**: Inspect `working-state.md` `Last Processed Event ID` advances between cycles; second cycle's cycle-input.json does not re-list the same event

### TC-16: event-reactions.md sub-skill is included in composed CLAUDE.md for all four roles
- **Precondition**: `references/sub-skills/common/event-reactions.md` exists; all four `references/roles/*/includes.yml` list `common/event-reactions`; `compose.py deploy-all` has been run
- **Steps**: Inspect each role's `.squidsquad/<role>/CLAUDE.md`
- **Expected**: Each composed file contains the content from `event-reactions.md` (detectable by a unique heading or phrase from that sub-skill)
- **Verification**: `for role in pm skill qa dm; do grep -l "event-reactions\|Event Reactions" .squidsquad/$role/CLAUDE.md; done` — all four paths returned

### TC-17: event-reactions.md provides actionable creative-phase guidance for interpreting recent_events
- **Precondition**: `references/sub-skills/common/event-reactions.md` exists and is readable
- **Steps**: Read the file; verify it addresses: (a) what each major event type means for the agent's creative phase work, (b) what to do when `recent_events` is non-empty in cycle-input.json, (c) how to handle `mechanical_reactions` already executed
- **Expected**: The sub-skill covers at least: event type meanings, agent action guidance per event, and the distinction between mechanical (already done) and creative (still to do) reactions
- **Verification**: `grep -c "recent_events\|mechanical_reactions\|creative" references/sub-skills/common/event-reactions.md` returns count > 0 for each term

### TC-18: Graceful degradation — absent Event Reactions section produces identical behavior to today
- **Precondition**: A clean install where config.md has no `## Event Reactions` section; no changes to `_ROLE_EVENT_TYPES` fallback logic
- **Steps**: Run the full test suite `python tests/run_tests.py`
- **Expected**: All existing tests pass without modification; `cycle_pre.py` behavior is bit-for-bit identical to the pre-#5868 version for any role
- **Verification**: `python tests/run_tests.py` exits 0 with no new failures; diff of cycle-input.json output between old and new binary when Event Reactions absent shows no changes

### TC-19: Backward compatibility — existing test_cycle_pre.py tests pass without modification
- **Precondition**: Updated `cycle_pre.py` deployed; `tests/test_cycle_pre.py` not modified
- **Steps**: Run `python -m pytest tests/test_cycle_pre.py -v`
- **Expected**: All tests pass; no new test failures or unexpected skips
- **Verification**: Exit code 0; no FAILED lines in output

### TC-20: Backward compatibility — existing test_compose.py tests pass without modification
- **Precondition**: Updated `compose.py` deployed; `tests/test_compose.py` not modified
- **Steps**: Run `python -m pytest tests/test_compose.py -v`
- **Expected**: All tests pass; no new test failures
- **Verification**: Exit code 0; no FAILED lines in output

### TC-21: New tests for event contract derivation and validation exist and pass
- **Precondition**: `tests/test_compose.py` updated with new test cases; `tests/test_config.py` updated with event reaction parsing tests
- **Steps**: Run `python -m pytest tests/test_compose.py tests/test_config.py -v`
- **Expected**: New tests covering: (a) catalog tier classification, (b) cross-agent validation of valid contracts, (c) validation failure detection, (d) config.py parsing of `pm-emits`/`pm-reacts-to` fields — all pass
- **Verification**: Exit code 0; grep for new test function names (e.g., `test_event_catalog`, `test_cross_agent_validation`, `test_config_event_reactions`) in output

### TC-22: config.py correctly parses all four roles' emits and reacts-to from config.md
- **Precondition**: config.md has a valid `## Event Reactions` section with entries for pm, skill, qa, dm
- **Steps**: Run `python references/scripts/config.py get pm-emits`, `python references/scripts/config.py get pm-reacts-to`, and equivalents for skill, qa, dm
- **Expected**: Returns comma-separated event type lists matching what was written to config.md; exits 0 for all eight queries
- **Verification**: All eight `config.py get <role>-emits` and `config.py get <role>-reacts-to` calls exit 0 and return non-empty strings

### TC-23: deploy-all validate runs against config.md, not individual CLAUDE.md files
- **Precondition**: Only `skill` agent has been recently composed; pm/qa/dm CLAUDE.md files are from a prior compose run; config.md `## Event Reactions` is current
- **Steps**: Run `python references/scripts/compose.py deploy skill` (single-role)
- **Expected**: Cross-agent validation checks `skill`'s new contract against the `## Event Reactions` entries for pm/qa/dm in config.md — NOT against their CLAUDE.md files; no spurious "stale agent" errors
- **Verification**: Validation output does not reference pm/qa/dm CLAUDE.md file paths; uses config.md as the canonical cross-agent registry

---

## Smoke Tests
- [ ] `python references/scripts/compose.py deploy pm` completes without exception when Event Reactions section is absent from config.md
- [ ] `python references/scripts/cycle_pre.py pm` produces valid cycle-input.json with correct event filtering when Event Reactions section is absent
- [ ] `python references/scripts/config.py get pm-emits` exits non-zero gracefully (not a crash) when Event Reactions section is absent
- [ ] `python tests/run_tests.py` passes with zero failures on a clean repo with no Event Reactions section in config.md
- [ ] All four `includes.yml` files contain `common/event-reactions` entry after the feature ships
- [ ] `references/sub-skills/common/event-reactions.md` file exists and is non-empty
- [ ] `grep "Event Reactions" .squidsquad/pm/CLAUDE.md` returns a match after `compose.py deploy pm`

---

## Regression Risks
- **cycle_pre.py self-event filter**: Refactoring to config-driven dispatch could inadvertently remove or skip the `if event.get("role") == role: continue` check at line 413 — verify TC-14 explicitly
- **cycle_pre.py cascade**: Config-driven reactions that trigger tracker transitions emit new events; verify cursor-based deduplication still prevents re-read on the next cycle (TC-15)
- **Hardcoded fallback correctness**: The exact set of events in the fallback `_ROLE_EVENT_TYPES` dict must not change — any accidental removal of `verification-failed`/`verification-passed`/`agent-health` from the recognized tier would silently break pm's filter behavior (TC-13)
- **agent_compose() scope creep**: The LLM polishing step in `agent_compose()` currently rewrites prose coherence only; extending it to also derive event contracts must not cause it to modify or remove behavioral instructions — the code-block and marker preservation checks (lines 610-618) must apply to the extended version
- **config.md bloat**: Adding per-role emits/reacts-to lines for four roles adds ~8-16 lines to config.md; verify total config.md size stays under a practical parsing threshold and does not cause `config.py` to slow down or exceed any line-count checks
- **Validation blocking compose**: If cross-agent validation raises an uncaught exception on malformed config.md content, it could prevent all role composes; the validation step must catch and degrade gracefully rather than crash the pipeline

---

## Comprehension Questions

### CQ-1: How does an agent interpret the Event Reactions section in config.md during the creative phase?
- **Files**: `.squidsquad/<role>/CLAUDE.md` (composed, containing `event-reactions.md` content), `references/sub-skills/common/event-reactions.md`
- **Expected**: A fresh agent reading their composed CLAUDE.md should be able to answer: "The Event Reactions section in config.md is consumed mechanically by `cycle_pre.py` — it is not something the agent parses directly. The agent's creative-phase guidance for events comes from the `event-reactions.md` sub-skill embedded in CLAUDE.md. When `recent_events` is non-empty in cycle-input.json, the agent checks it to understand what has changed in the environment since last cycle. `mechanical_reactions` in cycle-input.json lists what was already acted on automatically — the agent uses this to avoid re-doing mechanical work and focuses creative attention on what the events mean for open tasks."

### CQ-2: What should an agent do when they see non-empty recent_events in cycle-input.json?
- **Files**: `.squidsquad/<role>/CLAUDE.md`, `references/sub-skills/common/event-reactions.md`, `references/sub-skills/common/cycle-runner.md`
- **Expected**: A fresh agent reading only their composed CLAUDE.md should answer: "When `recent_events` is non-empty: (1) Review each event type against the event-reactions sub-skill guidance to understand what it signals about the project state. (2) Check `mechanical_reactions` — these are already-completed automatic responses, no duplicate action needed. (3) Apply creative judgment: e.g., a `pr-merge` event for a tracked issue means PM should check whether the task should transition to pending-ship; a `verification-failed` event means the assigned dev agent needs rework context surfaced. (4) Events are filtered by role — only events relevant to this role appear in `recent_events`, so all listed events are actionable. (5) Do not re-process events already reflected in `mechanical_reactions`."

### CQ-3: What is the difference between emitted, recognized, and unknown event types, and why does it matter for the fix loop?
- **Files**: `references/scripts/compose.py` (emission catalog definition), `references/sub-skills/common/event-reactions.md`
- **Expected**: A fresh dev agent reading compose.py and the event-reactions sub-skill should answer: "`emitted` = a script in the codebase actually fires this event (ground truth, hard constraint). `recognized` = the system references this event type in filters or plans but no script currently emits it — these are planned or expected events, treated as allowed with no error. `unknown` = the LLM invented this event type; it does not appear in either the emitted or recognized catalog — this is an error that triggers the fix loop. The fix loop presents gaps to the human in process-gap language (not raw event names) so they can decide whether to add the event to the catalog, remove the reference, or accept the gap."

### CQ-4: What happens if Claude returns malformed or partial output during derivation?
- **Files**: `references/scripts/compose.py` (derivation function)
- **Expected**: "If Claude CLI returns incomplete output (missing roles, truncated JSON, malformed structure), compose.py must detect the problem and reject the output — it must NOT write partial contracts to config.md. The existing Event Reactions section (if any) is preserved unchanged. Compose reports the derivation failure but does not crash. The system continues to work because cycle_pre.py falls back to hardcoded defaults when the section is absent or stale."

### CQ-5: What happens if config.md Event Reactions section contains corrupt or invalid data at runtime?
- **Files**: `references/scripts/cycle_pre.py` (config reading logic), `references/scripts/config.py`
- **Expected**: "If cycle_pre.py reads a corrupt or invalid Event Reactions section from config.md (malformed lines, missing fields, unparseable format), it must NOT crash or produce broken cycle-input.json. Instead, it falls back to the hardcoded _ROLE_EVENT_TYPES filter and _run_mechanical_reactions() logic — identical behavior to the section being absent. The agent's cycle continues normally. This is the rollback safety guarantee."

### CQ-6: How does cross-agent validation detect reaction cycles, and why are they dangerous?
- **Files**: `references/scripts/compose.py` (validation function)
- **Expected**: "A reaction cycle occurs when Agent A reacts to an event that Agent B emits, AND Agent B reacts to an event that Agent A emits — creating a potential infinite loop where each agent's reaction triggers the other. Validation must detect these by building a directed graph of emit→react edges across all roles and checking for cycles. Cycles are hard errors because at runtime, a mechanical reaction in cycle_pre.py can trigger a tracker transition (which emits a new event), which could re-trigger the other agent's reaction next cycle, cascading indefinitely."

### CQ-7: Why must validation output use process-gap language instead of raw event names?
- **Files**: `references/scripts/compose.py` (validation output formatting), emission catalog (description fields)
- **Expected**: "The human reviewing validation failures should understand them as workflow/process problems, not bus internals. Instead of 'event pr-merge missing from pm reacts-to config', say 'PM should know when a pull request is merged, but nothing notifies PM after a merge.' This uses the catalog's description field to translate event types into human-readable process language. The human can then decide whether the gap is real (fix it) or intentional (accept it) without needing to understand the event bus architecture."

### CQ-8: What guarantees idempotency of the derivation step?
- **Files**: `references/scripts/compose.py` (derivation function)
- **Expected**: "Running compose.py deploy twice with unchanged L1-L4 instructions must produce identical Event Reactions output. This means the derivation prompt must be deterministic (same input text every time), and the output must be normalized (sorted, consistent formatting) before writing to config.md. If the LLM produces semantically equivalent but differently ordered output, the normalization step ensures config.md doesn't show spurious diffs. This prevents git noise and ensures agents don't see phantom config changes."

### CQ-9: Why does cross-agent validation run on single-role deploys, not just deploy-all?
- **Files**: `references/scripts/compose.py` (deploy_role function, validation call site)
- **Expected**: "Changing one role's event contract can break system-wide topology. If PM's reacts-to changes, skill's emit may become orphaned. Single-role compose produces a partial contract view — but validation checks it against the full config.md Event Reactions section (which is the canonical cross-agent registry for ALL roles). This ensures no single-role change silently breaks the event bus contract for other agents."
