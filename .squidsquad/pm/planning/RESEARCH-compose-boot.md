# Research: compose.py Dual-Mode + L1 Boot Sub-Skill

**Tasks under planning**: #8696 (L1 boot instructions), #8697 (dual-mode compose.py)
**Date**: 2026-05-17
**Researcher**: sub-agent (read-only investigation)

---

## Files Surveyed

| Path | Purpose |
|---|---|
| `references/scripts/compose.py` | Sub-skill composition engine — assembles CLAUDE.md from layers + resolves includes |
| `references/roles/pm/instructions.md` | PM role entry template — contains `{{include:}}` directives |
| `references/roles/pm/includes.yml` | PM manifest — ordered list of sub-skills to compose |
| `references/roles/dev/includes.yml` | Dev/skill manifest |
| `references/roles/qa/includes.yml` | QA manifest |
| `references/roles/dm/includes.yml` | DM manifest |
| `references/roles/instructions.md` | Layer 1 base agent definition (prepended to every agent) |
| `references/sub-skills/common/cycle-runner.md` | Cycle transport sub-skill (Ralph Loop phases) |
| `references/sub-skills/common/context-pressure.md` | Step 1b context pressure check |
| `references/sub-skills/common/resume-working-state.md` | Step 1c resume working state (dev/skill version) |
| `references/sub-skills/common/task-pickup.md` | Task pickup sub-skill (common/task-pickup) |
| `references/sub-skills/common/agent-lifecycle.md` | Agent lifecycle instructions |
| `references/sub-skills/common/event-reactions.md` | Creative-phase event reaction guidance |
| `references/sub-skills/roles/dev/triage-issues.md` | Dev Step 2 — deterministic triage + pickup ordering |
| `references/sub-skills/roles/dm/task-pickup.md` | DM task pickup variant |
| `references/scripts/tracker.py` | Tracker script — `work_queue()` function encodes priority ordering |
| `.squidsquad/pm/CLAUDE.md` | Deployed PM instructions (contains event-driven-workflow block) |
| `.squidsquad/skill/CLAUDE.md` | Deployed skill instructions |
| `.squidsquad/qa/CLAUDE.md` | Deployed QA instructions |
| `.squidsquad/dm/CLAUDE.md` | Deployed DM instructions |
| `.squidsquad/project/pm-instructions.md` | PM-specific L4 project instructions |
| `.squidsquad/project/dev-instructions.md` | Dev-specific L4 project instructions |
| `.squidsquad/project/shared-instructions.md` | Shared L4 project instructions (all agents) |
| `tests/comprehension/1428_spec.json` | Example comprehension test spec |
| `tests/test_comprehension_1428.py` | Example comprehension test runner |
| `references/scripts/run_comprehension_test.py` | CQ pipeline: spawns test + eval agents |

---

## compose.py Architecture

### Layer Stack

compose.py assembles CLAUDE.md via a 4-layer stack:

- **Layer 1** (`references/roles/instructions.md`): Base agent definition, prepended to every role. Source: `compose.py:296`.
- **Layer 2** (`references/roles/<role>/instructions.md`): Role-specific entry template with `{{include:}}` directives. Source: `compose.py:300-303`.
- **Layer 3** (`references/roles/<base>/<variant>/instructions.md`): Variant customization for hyphenated roles (e.g. `dev-skill` → `roles/dev/skill/instructions.md`). Source: `compose.py:305-312`.
- **Layer 4** (`.squidsquad/project/*.md`): Live project instructions injected at deploy time. File naming: `shared-*.md` → all roles, `<role>-*.md` → that role only. Source: `compose.py:318-340`.

### Sub-Skill Fragment Discovery

Sub-skill fragments live in `references/sub-skills/` (line 28: `SUB_SKILLS_DIR = REPO_ROOT / "references" / "sub-skills"`). Two subdirectories:
- `references/sub-skills/common/` — shared sub-skills used by multiple roles
- `references/sub-skills/roles/<role>/` — role-specific sub-skills

Capabilities (optional tools) live in `references/sub-skills/capabilities/<id>/sub-skill.md`.

### Ordering Mechanism: includes.yml

Fragment ordering is controlled by `references/roles/<role>/includes.yml`. This YAML file lists sub-skill paths top-to-bottom. Example for PM (`references/roles/pm/includes.yml`):

```yaml
includes:
  - common/cycle-runner
  - common/event-reactions
  - common/context-pressure
  - common/task-pickup
  - roles/pm/checkin
  ...
```

The manifest is loaded by `_load_manifest()` (line 120) and passed to `_resolve_includes_with_manifest()` (line 209). When a manifest exists, it is authoritative for ordering — includes in the entry template that are absent from the manifest are silently skipped (line 248: "Include is in the template but not in the manifest — skip it. This enables manifest-driven removal in Phase B."). When no manifest exists, `_resolve_includes()` resolves includes in template order.

**Variant inheritance**: Layer 3 variants can use `base_role: <base>` + `additional_includes: [list]` in their `includes.yml` to inherit the base manifest and append entries (lines 163-186).

### CLI Entry Points

```
python references/scripts/compose.py all           # Compose dev role to references/agent-instructions.md
python references/scripts/compose.py deploy <role> # Compose + write to .squidsquad/<role>/CLAUDE.md
python references/scripts/compose.py deploy-all    # Deploy all configured roles
python references/scripts/compose.py upgrade-soul <role>  # Re-render Layer 1 of SOUL.md only
python references/scripts/compose.py <role>        # Print composed output to stdout (no write)
```

`deploy_role()` (line 804) is the full pipeline: assemble template → resolve includes → substitute placeholders (`[ROLE]`, `[INTERVAL]`, etc.) → optional agent-compose polish → write `CLAUDE.md` + assemble `SOUL.md`.

Output path: `.squidsquad/<output_name>/CLAUDE.md` (line 837).

### Fragment Injection Syntax

Three directive types in entry templates:
- `{{include: common/cycle-runner}}` — inline a sub-skill file verbatim
- `{{runtime: souls/pm}}` — emit a "read SOUL.md at boot" instruction
- `{{capability: id}}` — inline a capability sub-skill from `capabilities/<id>/sub-skill.md`

Each included fragment is wrapped in HTML comment markers:
```
<!-- sub-skill: cycle-runner -->
...content...
<!-- /sub-skill: cycle-runner -->
```

Source files that contain their own markers have the outer markers stripped before re-wrapping (to prevent doubling — `_strip_outer_markers()`, line 34).

**Important finding**: The `includes.yml` manifest controls ordering but does NOT today support per-entry metadata (no `mode:`, `when:`, or `event-driven:` fields). The include list is a flat list of strings.

---

## Sub-Skill Fragment Structure

### Has Frontmatter?

**No.** None of the 25+ fragment files inspected contain YAML or TOML frontmatter. Fragments are plain Markdown, optionally wrapped in their own `<!-- sub-skill: name -->` markers. There is no standard frontmatter convention today.

### Conditional Markers?

**No.** None of the fragments contain conditional inclusion markers (`<!-- mode: event-driven -->`, `<!-- if: config.event-driven == yes -->`, etc.). There is no today mechanism for a fragment to declare its own conditions.

### Representative Fragment Survey

**`common/cycle-runner.md`** (`references/sub-skills/common/cycle-runner.md`):
- 93 lines. Wrapped in `<!-- sub-skill: cycle-runner -->` / `<!-- /sub-skill: cycle-runner -->`.
- Describes the 3-phase Ralph Loop. No frontmatter. No conditional markers.
- Assumes /loop + cycle_pre/cycle_post semantics throughout.

**`common/context-pressure.md`** (`references/sub-skills/common/context-pressure.md`):
- 20 lines. No outer markers (compose.py wraps it). Starts at "### Step 1b — Context Pressure Check".
- Pure /loop semantics. No event-driven awareness.

**`common/resume-working-state.md`** (`references/sub-skills/common/resume-working-state.md`):
- 11 lines. Simple: read working-state.md; if in-progress task, resume it; else proceed to Step 2.
- Used by dev/skill role. No frontmatter, no conditions.

**`roles/pm/checkin.md`** (`references/sub-skills/roles/pm/checkin.md`):
- Step 2 check-in with human. Pure /loop semantics. No frontmatter.

**`common/event-reactions.md`** (`references/sub-skills/common/event-reactions.md`):
- 33 lines. Describes how to interpret `recent_events` from cycle-input.json (mechanical layer).
- NOT the event-driven-workflow fragment — this is the creative-phase event guidance for /loop mode. Included in all roles (PM, skill, QA, DM manifests all have `common/event-reactions` as position 2).

---

## Existing Mode-Gate Mechanism (event-driven-workflow)

### Location

The `event-driven-workflow` block is **NOT in any source template or sub-skill file**. It was injected directly into all four deployed CLAUDE.md files in git commit `a3b108f2` ("skill: cycle 1078 state — #7630 review fixes applied, pending-test"). It is not tracked in any `includes.yml`. It is not in `references/sub-skills/` anywhere.

This means the current `event-driven-workflow` block is a **manually injected dead-end** — it exists in the deployed files but will be overwritten on the next `compose.py deploy` run, since no source backs it.

### Block Location in Deployed CLAUDE.md

The block appears immediately after `<!-- /sub-skill: cycle-runner -->` and before `<!-- sub-skill: context-pressure -->`:

```
.squidsquad/pm/CLAUDE.md line 344-425
.squidsquad/skill/CLAUDE.md line ~328-416
.squidsquad/qa/CLAUDE.md line 344-425
.squidsquad/dm/CLAUDE.md line 363-444
```

### The Config Gate

The fragment contains this explicit branch instruction (quoted from `.squidsquad/pm/CLAUDE.md` line 351):

```
This mode is active ONLY when `event-driven: yes` in config.md. If `event-driven: no`, use the standard /loop + cycle_pre/cycle_post flow instead.
```

This is a **runtime gate**: the agent reads config.md at boot and branches based on the flag value. It is NOT a compose-time gate — the fragment is included unconditionally (for all roles), and the agent self-selects the mode at runtime.

### Both Flows in Same Composed File

Confirmed: all four deployed CLAUDE.md files contain BOTH the event-driven-workflow instructions AND the /loop cycle-runner instructions. The cycle-runner sub-skill (lines 251-342 in PM) describes cycle_pre/cycle_post flow. The event-driven-workflow block (lines 344-425 in PM) describes Monitor + event_poll flow. Both are present simultaneously. The agent is responsible for reading the config gate and ignoring the inapplicable set of instructions.

This is the problem #8697 addresses: agents currently see conflicting instructions and must self-sort. The goal is conditional composition so each mode gets clean, unambiguous instructions.

---

## Current Boot Path Per Role

All four deployed roles share the same basic boot sequence. Here is what "On Startup" and early steps look like per role (from deployed CLAUDE.md files):

| Role | On Startup text | Step 1a | Step 1b | Step 1c |
|---|---|---|---|---|
| **PM** | Verify `gh` access → invoke `/loop 30m execute one Ralph Loop cycle` | cycle_pre.py (mechanical) | Context pressure check (read `.squidsquad/pm/context-pressure`) | Resume from working-state.md if in-progress task; else proceed |
| **skill** | Verify `gh` access → invoke `/loop 30m execute one Ralph Loop cycle` | cycle_pre.py (mechanical) | Context pressure check | Resume from working-state.md (sub-skill: resume-working-state) |
| **QA** | Verify `gh` access → read interval from config.md → invoke `/loop 30m` | cycle_pre.py (mechanical) | Context pressure check | Resume from working-state.md; else proceed |
| **DM** | Verify `gh` access + capability-check → read interval → invoke `/loop 30m` | cycle_pre.py (mechanical) | Context pressure check | Resume from working-state.md; else proceed |

**Common pattern** across all roles:
1. `tracker.py check-gh` (auth check)
2. Invoke `/loop` (or Monitor if event-driven)
3. Per-cycle: `cycle_pre.py` → read `cycle-input.json` → creative work → write `cycle-output.json` → `cycle_post.py`
4. Step 1b: context pressure check
5. Step 1c: resume from working-state if active task

**What is missing** (the gap #8696 addresses): None of the roles have a **tracker-driven fallback pickup** at boot. Step 1c only resumes an existing in-progress task — it does not scan the tracker for a top backlog item if working-state.md is empty. After Step 1c, roles go directly to their role-specific work without an explicit "check tracker for first task" step at the /loop boot level. The `triage-issues` and `task-pickup` sub-skills do handle tracker queries, but they are inside the cycle flow (Step 2+), not at boot (pre-loop).

**Where new L1 boot instructions would slot in**: After the current Step 1c but before the first Step 2 action. Or alternatively, as a pre-loop boot step executed once before the first `/loop` invocation (between `check-gh` and `/loop`).

The `event-driven-workflow` block currently says "At boot, invoke the Monitor tool" — so for event-driven mode, the boot action IS the Monitor invocation. The L1 boot for event-driven should replace the Monitor-call-immediately pattern with: check working-state → if in-progress resume → else scan tracker for top item → THEN invoke Monitor and enter event-listening.

---

## Pickup Ordering Rule

### Canonical Citation

The canonical ordering rule lives in two places:

**1. `references/scripts/tracker.py`, function `work_queue()`, lines 437-510:**

```python
def work_queue(role):
    """Return a single prioritized work list for an agent role.

    Priority order (strict):
    1. In-progress items (resume first)
    2. Approved issues — severity:high → medium → low
    3. Approved tasks — priority:high → medium → low
    4. Open issues — severity:high → medium → low
    """
    ...
    type_rank = 0 if item_type == "issue" else 1
    prio = severity if item_type == "issue" else priority
    prio_rank = PRIORITY_ORDER.get(prio, 1)  # default medium
    ...
    queue.sort(key=lambda x: x["_sort"])
```

Sort key is `(status_rank, type_rank, prio_rank)` — status first (in-progress < approved < open), then type (issue < task), then priority/severity rank.

**Items filtered out**: Only `status in ("in-progress", "approved", "open")` are included. Items with `design:needed` or `design:in-progress` labels are not filtered by `work_queue()` itself — the filtering is done by agent instructions in Step 2 ("Design label check" in `task-pickup.md` line 12 and `triage-issues.md` line 41).

**2. `references/sub-skills/roles/dev/triage-issues.md`, lines 29-35:**

```
This returns a unified, priority-sorted list of ALL actionable items (issues AND tasks). Priority order is enforced by the script:
1. In-progress items (resume first)
2. Approved issues — severity:high → medium → low
3. Approved tasks — priority:high → medium → low
4. Open issues — severity:high → medium → low

You MUST pick the first item in the queue. No discretion to skip, reorder, or cherry-pick. The queue is deterministic — the script decides priority, not you.
```

The design-gate rule: `triage-issues.md` line 41: "If the item has a `design:needed` or `design:in-progress` label, skip it and pick the next item in the queue."

**Summary for #8696**: The work-queue ordering is "bugs (issues) first, then tasks, sorted by priority/severity, skip design-gated" — exactly as described in the task spec. This is already implemented in `tracker.py work_queue()`. The L1 boot sub-skill should call `tracker.py work-queue <role>` and apply the same design-gate skip as triage-issues.md.

---

## Comprehension Test Format

### Files

| Path | Purpose |
|---|---|
| `tests/comprehension/1428_spec.json` | CQ spec: issue number, file list, 5 Q&A pairs |
| `tests/test_comprehension_1428.py` | Pytest harness: runs spec, asserts all questions pass |
| `references/scripts/run_comprehension_test.py` | Pipeline: hash-cache check → spawn test agent → spawn eval agent → write results.json |

### Spec Format (`tests/comprehension/1428_spec.json`)

```json
{
  "issue": 1428,
  "title": "Deterministic QA verification framework",
  "files": [
    "references/sub-skills/roles/qa/verification.md",
    "references/prompts/test-plan.md.j2"
  ],
  "questions": [
    {
      "id": "1",
      "question": "When a test case cannot run because an API key is missing...",
      "expected": "It should be marked HUMAN-REQUIRED, not skipped or deferred..."
    },
    ...
  ]
}
```

Key fields:
- `files`: the ONLY files the test agent may read (simulates a fresh agent given only the changed files)
- `questions`: array of `{id, question, expected}` — expected is the correct answer, used by eval agent to score PASS/FAIL
- `issue`: the GitHub issue number being tested

### Pytest Harness (`tests/test_comprehension_1428.py`)

```python
SPEC = REPO / "tests" / "comprehension" / "1428_spec.json"
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"

class TestComprehension1428:
    def test_q1_blocked_not_defer_for_missing_api_key(self, comprehension_results):
        r = _get_result(comprehension_results, "1")
        assert r["pass"], f"Q-1 FAIL: {r.get('reason', 'no reason')}"
```

Each question gets its own test method. All questions must pass — one `assert r["pass"]` per question.

### Pipeline

`run_comprehension_test.py` does:
1. Compute SHA256 hash over spec + listed files (content-hash cache)
2. Skip if cache hit (unchanged since last PASS)
3. Spawn test agent: reads `files`, answers `questions`, writes `answers.md`
4. Spawn eval agent: reads `answers.md` + spec, evaluates against `expected`, writes `results.json`
5. Exit 0 if all pass (update cache), exit 1 if any fail

Cache stored at `tests/comprehension/.cache/<spec-stem>.hash`.

### Minimal Template for New CQ Spec

For tasks #8696 and #8697, a new spec file should be created at `tests/comprehension/8696_spec.json` and `tests/comprehension/8697_spec.json` with a corresponding `tests/test_comprehension_8696.py` / `tests/test_comprehension_8697.py`.

```json
{
  "issue": 8696,
  "title": "L1 boot instructions — tracker-driven failsafe",
  "files": [
    "references/sub-skills/common/l1-boot.md",   (new file)
    "references/roles/dev/includes.yml"
  ],
  "questions": [
    {
      "id": "1",
      "question": "When an agent boots with an empty working-state.md, what does it do?",
      "expected": "It scans the tracker (work-queue) for the top backlog item and picks it up before entering event-listening."
    }
  ]
}
```

---

## Path to Dual-Mode compose.py (#8697)

### Problem Statement

Today:
- `event-driven-workflow` fragment was hand-injected into deployed CLAUDE.md files (commit a3b108f2). It has no source in `references/sub-skills/` and no entry in any `includes.yml`. It will be overwritten on next deploy.
- ALL roles include `cycle-runner` (which is /loop-only) AND the injected `event-driven-workflow` block simultaneously. Agents must read the config gate and self-select. This is fragile.

### What compose.py Needs to Learn

1. **Fragment frontmatter / metadata**: `includes.yml` entries need to optionally carry a `mode:` field (or compose.py needs a separate metadata mechanism). For example:

   ```yaml
   includes:
     - path: common/cycle-runner
       mode: loop          # only include when event-driven: no (or absent)
     - path: common/event-driven-workflow
       mode: event-driven  # only include when event-driven: yes
     - path: common/context-pressure
       mode: both          # always include (default)
   ```

   Two design options:
   - **Option A — Inline YAML**: change includes list from `[string]` to `[{path: string, mode?: string}]`. Backward-compatible if `mode` defaults to `both`.
   - **Option B — Separate metadata YAML** (`includes-meta.yml`): keep includes.yml flat strings for backward compat, add a sidecar file for metadata.

   Option A is simpler and recommended.

2. **Compose-time mode flag**: `compose.py deploy <role>` needs to read `event-driven:` from `.squidsquad/config.md` (already accessible via `_read_config_value("event-driven")`, line 388). At compose time, resolve each include entry: if `mode == event-driven` and config says `no`, skip; if `mode == loop` and config says `yes`, skip; if `mode == both` or absent, always include.

3. **New sub-skill files to create**:
   - `references/sub-skills/common/event-driven-workflow.md` — move the hand-injected content here, tag with `mode: event-driven`
   - `references/sub-skills/common/cycle-runner.md` — already exists, tag with `mode: loop` (or `mode: both` if parts of it are shared, e.g. the Phase 2 creative work description)

4. **Ordering enforcement** (the defined ordering from #8697):
   - L1 boot (`common/l1-boot`) — new, always first
   - Mode selector (either `common/cycle-runner` or `common/event-driven-workflow`) — position 2
   - Mode-specific sub-skills
   - Shared sub-skills

   This ordering is enforced by the manifest — whoever edits `includes.yml` controls order. There is no automatic ordering enforcement in compose.py today. The PM task should define the canonical ordering explicitly in `includes.yml` and add a lint step if desired.

### What Fragment Frontmatter to Add

Minimal approach — add `mode` as an optional string field to each entry in `includes.yml`. New schema for each include entry:

```yaml
# Simple (backward-compatible — mode defaults to 'both'):
- common/cycle-runner

# With mode:
- path: common/cycle-runner
  mode: loop

- path: common/event-driven-workflow
  mode: event-driven

- path: common/l1-boot
  mode: both
```

compose.py `_load_manifest()` needs to handle both string entries (current) and dict entries `{path, mode}`.

compose.py `_resolve_includes_with_manifest()` needs to accept a `config_mode` parameter (`"loop"` or `"event-driven"`) and skip entries where `entry.mode != config_mode and entry.mode != "both"`.

### What the Ordering Enforcement Looks Like

The specification in #8697 says: L1 boot → mode selector → mode-specific → shared. This maps to:

```yaml
# references/roles/pm/includes.yml (after #8697)
includes:
  - path: common/l1-boot          # new — always first
    mode: both
  - path: common/cycle-runner     # /loop mode
    mode: loop
  - path: common/event-driven-workflow  # event mode
    mode: event-driven
  - path: common/event-reactions  # shared — reaction guidance
    mode: both
  - path: common/context-pressure # loop-only (event mode: harness monitors)
    mode: loop
  - path: common/task-pickup      # shared pickup logic
    mode: both
  ... (remaining shared sub-skills)
```

compose.py does not need to enforce the ordering beyond "use manifest order." The PM/template author ensures the order is correct by editing `includes.yml`.

---

## Path to L1 Boot Sub-Skill (#8696)

### New Fragment Name

`common/l1-boot` → `references/sub-skills/common/l1-boot.md`

### Where It Slots

**In includes.yml**: Position 1 (before everything else, including cycle-runner). Mode: `both` (needed for both /loop and event-driven boots).

**In the agent session**: Executes ONCE at boot, before the first `/loop` invocation or Monitor invocation. It is NOT a per-cycle step — it is a session-init step.

### What It Instructs

The fragment should cover three cases:

```
### L1 Boot — Failsafe Startup

On agent boot (before your first cycle or event), execute this sequence once:

Print: `[🦑 HH:MM:SS] L1 Boot — checking resume state...`

**Step 1 — Resume check**:
Read `.squidsquad/[ROLE]/working-state.md`.
If it contains an active task (status `in-progress`):
- Print: `[🦑 HH:MM:SS] L1 Boot — resuming in-progress [TASK_ID].`
- Note the task for pickup in your first cycle.
- Proceed to your mode-specific startup (Step 3).

**Step 2 — Tracker scan (only if no in-progress task)**:
Query the tracker for your top backlog item:

```bash
python references/scripts/tracker.py work-queue [ROLE]
```

The script returns items sorted by: in-progress first, then issues (bugs) by severity, then tasks by priority, design-gated items last. Take the first non-design-gated item:
- If `design:needed` or `design:in-progress` label is present, skip to next.
- If an item is found, note it for pickup in your first cycle.
- If queue is empty, proceed with no pre-queued work.

Print: `[🦑 HH:MM:SS] L1 Boot — queued [NUMBER]: [title] for first cycle.`
(Or: `[🦑 HH:MM:SS] L1 Boot — queue empty, entering normal cycle.`)

**Step 3 — Emit bootup-complete, enter listening**:
Regardless of whether work was found, this step completes the boot sequence. Proceed to your mode-specific startup (invoke /loop for loop-mode, invoke Monitor for event-driven-mode).
```

### Key Design Notes for PM Discussion

- **L1 boot is failsafe, not primary**: If the event bus is operational, the harness dispatches `assigned-to` events and boot-time triage is redundant. L1 boot matters when: (a) agent crashed mid-task, (b) harness is down, (c) fresh agent start with no events pending.
- **The "note for first cycle" mechanism**: The sub-skill should not immediately start working — it notes the item and lets the mode-specific loop pick it up. This keeps boot logic separate from work logic.
- **bootup-complete signal**: #8696 mentions emitting `bootup-complete`. The event catalog should have this event type. PM should verify `event_catalog.py` includes it or file a sub-task to add it.

---

## Open Questions for PM Discussion Phase

1. **Fragment frontmatter schema**: Option A (inline dict in includes.yml) vs Option B (sidecar metadata file)? Option A is simpler but breaks includes.yml backward compat if scripts parse it as pure string lists. Check `_load_manifest()` — it already handles both `includes:` and `base_role:` dict schemas, so adding dict entries per-include is feasible.

2. **Where does event-driven-workflow.md live as a source file?** It was hand-injected and has no source. Before #8697 can close, someone needs to create `references/sub-skills/common/event-driven-workflow.md` as the canonical source. This is a prereq for #8697.

3. **Does `cycle-runner` get split?** The cycle-runner sub-skill mixes Phase 1 (cycle_pre.py), Phase 2 (creative work description), and Phase 3 (cycle_post.py). Phases 1+3 are /loop-only. Phase 2 (read cycle-input.json, examine pipeline state) has partial overlap with event-driven mode's "read the event payload." Should cycle-runner be split into a loop-specific part and a shared creative-work-description part?

4. **L1 boot in event-driven mode**: The `event-driven-workflow` block currently says "At boot, invoke the Monitor tool." After #8696, the boot sequence is: check working-state → scan tracker → emit bootup-complete → THEN invoke Monitor. The `event-driven-workflow` fragment's "How You Wake" section needs to change to reference L1 boot first. This ordering must be explicit in the new fragment.

5. **`common/event-reactions` position**: It's currently position 2 in all manifests (right after cycle-runner). In event-driven mode, `recent_events` from cycle-input.json doesn't exist (no cycle_pre.py). Should `event-reactions` be mode-gated (`mode: loop`) or kept shared? The event-driven path gets events via Monitor, not cycle-input.json.

6. **QA and DM manifests don't have `common/resume-working-state`**: QA and DM have inline Step 1c text (not sub-skill). Skill has the `common/resume-working-state` sub-skill. PM's Step 1c is inline in `references/roles/pm/instructions.md`. After #8696, all four roles should use the `common/l1-boot` sub-skill instead of their individual Step 1c patterns. This requires removing or replacing the existing Step 1c inline text in PM's and QA's and DM's instructions.md files.

7. **`bootup-complete` event type**: #8696 mentions emitting this. Verify it exists in `references/scripts/event_catalog.py` — if not, a sub-task to add it to the catalog and the harness event bus dispatch logic is needed before #8696 can be fully implemented.

8. **Ordering spec for existing manifests**: PM manifest has 31 entries. After adding `l1-boot` at position 1 and mode-gating cycle-runner/event-driven-workflow, the remaining entries need to be classified as `mode: loop`, `mode: event-driven`, or `mode: both`. Who does this classification work? It may need to be a separate sub-task rather than part of #8697.

9. **compose.py `_load_manifest()` backward compat**: Today `includes.yml` entries are strings. After Option A, entries can be strings OR dicts. `_load_manifest()` validates all include paths (lines 195-205). This validation loop needs to handle dict entries `{path: ..., mode: ...}` as well as plain strings.

10. **Testing approach**: CQ specs for #8696 should test that agents read working-state.md first, then call work-queue, then proceed to mode entry. CQ specs for #8697 should test that agents know which mode they're in (event-driven vs loop) and do not invoke /loop when event-driven is active. Both need comprehension specs filed before task execution (per `feedback_comprehension_tests_required.md` memory note).
