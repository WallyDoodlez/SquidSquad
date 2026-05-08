# FEAT-PM-5868 Context — Event consumption sub-skill: compose-time reaction config, runtime mechanical execution

## Scope

Add an event reaction system that:
1. Extends compose.py to derive per-role event contracts (emits + reacts-to) from L1-L4 instructions using Claude CLI
2. Writes contracts to config.md `## Event Reactions` section
3. Validates contracts cross-agent after every compose (deterministic)
4. Presents validation failures to human as plain-language process gaps
5. Refactors cycle_pre.py to read event filters/reactions from config.md (hardcoded fallback)
6. Adds `event-reactions.md` sub-skill for creative-phase event interpretation

## Locked Decisions (human decided)

- **Config location**: Event Reactions lives in config.md, not a separate file
- **Config scope**: Mechanical only (terse structured data for cycle_pre.py). Creative-phase guidance in separate `event-reactions.md` sub-skill
- **Coverage**: Both emits AND reacts-to per role
- **Mechanical emissions**: Stay hardcoded in scripts (cycle-start, cycle-end, git-pull, git-push, git-commit, task-transition, tracker-comment, branch-checkout, pr-create, pr-merge, phase-change). These are infrastructure-level, universal across all forges/presets/projects
- **Derivation trigger**: LLM derivation runs on every compose. Claude CLI is always available (SquidSquad = Claude Code). No skip path needed
- **Authority model**: Three-tier emission catalog:
  - `emitted` — scripts emit these (hard ground truth)
  - `recognized` — planned/expected, referenced by filters but not yet emitted (allowed, no error)
  - `unknown` — hallucinated by LLM (error)
- **Validation failures**: Always presented to human in plain process-gap language, not event names. Catalog includes human-readable `description` per event type for translation
- **Validation scope**: Cross-agent validation after every compose (even single-role deploys)
- **Fix loop**: Always ask human. Present as process gaps with options to fix
- **Graceful degradation**: Absent Event Reactions section → hardcoded `_ROLE_EVENT_TYPES` and `_run_mechanical_reactions()` behavior (zero change from today)
- **Compose ownership**: /squidsquad-compose skill owns the pipeline (shipped #5888). Validation lives inside compose.py so all callers get it automatically

## Dev Discretion (dev agent can choose)

- Internal data structures for emission catalog (dict, dataclass, whatever fits)
- Config.md format details (exact field naming, spacing) as long as config.py can parse it
- Prompt engineering for derivation step (dev knows compose.py best)
- Implementation order within the task (catalog → config → cycle_pre → validation → sub-skill → derivation is recommended but not mandated)
- Whether to refactor `_run_mechanical_reactions()` as additive overrides or full replacement (as long as hardcoded fallback is preserved)
- Test structure and naming

## Side Effect Mitigations (required)

- `_ROLE_EVENT_TYPES` currently references 3 event types no script emits (`verification-failed`, `verification-passed`, `agent-health`). These must be in the catalog as `recognized` tier — do not treat as errors
- `phase-change` is handled by harness.py but not emitted by scripts — include as `recognized`
- Self-event filtering (cycle_pre.py line 413) and cursor deduplication must be preserved in config-driven reactions
- Existing `test_cycle_pre.py` and `test_compose.py` tests must pass without modification when Event Reactions section is absent
- Mechanical reactions that trigger tracker transitions (which emit new events) must not create infinite loops — preserve existing cascade safeguards

## Upgrade Path (required)

- Absent Event Reactions section = hardcoded fallback = zero behavior change. Existing installs work without any action
- `/squidsquad-compose` (or `compose.py deploy-all`) populates the section automatically on next compose
- No manual migration needed — compose handles it

## Out of Scope

- Config-driven emission (moving hardcoded emissions to config) — explicitly excluded per prior discussion
- Change detection for derivation ("only re-derive when instructions changed") — deferred, always regenerate for now
- Chat/notification routing from reactions (#3415 comms layer)
- Harness TUI display of custom event types (generic display is acceptable)
- "CI without Claude" scenario — Claude CLI is always available in SquidSquad
