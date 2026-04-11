# FEAT-328 Research — Intent-driven setup wizard with role manifest registry

## Summary

SquidSquad's current setup flow is hardcoded around the dev-shaped team: Step 1 mandates a `Dev agents` field (default `fe, be`) with no opt-out, PM and QA are auto-added as a side effect of dev presence, DM is never auto-installed, and the wizard never asks the user what they actually want SquidSquad to *do*. FEAT-328 replaces this with an intent-first wizard backed by a role manifest registry at `references/roles/<role>/manifest.yaml`. PM and DM become mandatory, other roles are composed from curated presets (`software-dev`, `design`), and each role declares its own downstream routing via `routes_to`.

The codebase impact is concentrated but heavy in three places: (1) the SKILL.md "Setup Instructions" section (roughly lines 263-865) needs extensive rewriting — Steps 1, 2, 3, 4, and 6 all encode role assumptions that the wizard currently hardcodes; (2) `references/scripts/compose.py` hardcodes role → entry-file mapping and the set `{pm, qa, dm, designer}` in several places, and it reads `dev-agents` from config as the exclusive source of truth for "which agents exist"; (3) `config.md` schema and `config.py`'s `FIELD_MAP` bake `Dev Agents`, `alias-*`, and `skill-tests` in as hardcoded fields — we need a more dynamic agent list and test-command map. A smaller but important surface is the PM and skill CLAUDE.md templates, which enumerate role labels and role logic inline in at least a dozen spots; some of these can stay hardcoded (the label taxonomy is a closed set), others must become manifest-driven (e.g. the design-routing question in PM Phase 2, which checks "is `designer` configured?").

The locked decisions do most of the hard architectural work. What remains is mostly mechanical: define a manifest schema, write a resolver, rewrite the wizard steps, and migrate hardcoded role enumerations to manifest lookups. The main risks are (a) behavior drift in PM's design-routing and agent-health-check logic as those stop hardcoding `designer`, (b) coupling between the wizard's "resolved pipeline" display and what the agents actually do at runtime (the routing is advisory — there's no runtime enforcement of `routes_to` today), and (c) the `references/roles/` directory does not exist yet, so we are greenfielding rather than migrating. There is no install base per locked decision 8, so migration concerns collapse to zero.

## 1. Codebase Impact Analysis

### SKILL.md — `D:\Dev\Dev\SquidSquad\SKILL.md`

| Range | Step | Action | Notes |
|-------|------|--------|-------|
| 48-68 | Architecture: Roles + team shapes table | **Replace** | Replace the "Common team shapes" table with preset descriptions. Keep the Roles table but add DM as always-present. |
| 290-340 | Step 1 — Gather Project Details | **Rewrite** | Replace field #3 `Dev agents` with intent question + preset selector. Add conditional Dev variant sub-question. Remove "at least one dev role required" validation. Reorder fields. Flip field #10 (GH Issues ingestion) default to `Y` (per locked decision 7). |
| 312-339 | Step 1 — Import Existing Items | **Keep, refactor** | The heuristics ("items mentioning UI → `fe`") break when there is no dev agent. Make routing manifest-aware: read installed roles from the wizard state, use first installed dev role as ambiguous fallback, or route everything to `pm` if no dev roles. |
| 341-388 | Step 2 — Folder structure | **Rewrite** | Replace per-role hardcoded branches (`if dev or designer present… if designer role defined… always create pm…`) with a loop over the resolved role list from the wizard. DM directory is now always created. Per-role directory structure (planning/, iterations/, specs/) needs to come from the manifest. |
| 390-452 | Step 3 — Generate config.md | **Rewrite** | Replace `Dev Agents` line with a generalized `Agents` list (e.g. `- pm, designer, skill, qa, dm`). Replace fixed `Aliases` block with one alias per installed role. Test Commands section only lists installed dev-variant roles. Add new field: `## Preset` with the selected preset name for future upgrade hints. |
| 454-557 | Step 4 — Templates and bootstrappers | **Refactor** | Today this step has five per-role branches (dev, PM, QA, DM, designer) each with its own template path, placeholders, and CLAUDE.md body. Drive this from the manifest: `template_refs` field points at entry file, SOUL template, and bootstrapper template. `compose.py deploy <role>` already dispatches via `_get_entry_file_for_role` — the dispatch table has to become a manifest lookup. |
| 583-613 | Step 5 — Boot scripts | **No change to template, change to loop** | The `start-role.sh/.ps1` templates are generic (they substitute `{{ROLE}}` only), so they don't care about role identity. But `compose.py boot-all` hardcodes the rule "add DM if `.squidsquad/dm/` exists" — that loop should walk installed roles from the manifest-resolved list. |
| 659-685 | Step 5d — Guided clone setup | **Small change** | The loop "for each agent (dev agents + PM + QA)" must become "for each installed role from the resolved list". DM has no clone loop entry today; needs one. |
| 686-729 | Step 6a — GitHub Labels | **Refactor** | The label seed command hardcodes `role:[role]` per dev agent plus `role:pm`, `role:qa`, `role:dm`, and conditionally `role:designer`. Change to: seed `role:<role>` for every resolved role. The label taxonomy itself (type, priority, status, severity) stays identical. |
| 752-759 | Step 6c — Seed items | **Keep** | Only affected if the import heuristics change (see Step 1). |
| 820-863 | Step 9 — Confirm Setup | **Update** | The final summary "Open [N] terminals" must enumerate the resolved role list rather than `[dev agents] + dm + pm`. Include the resolved pipeline line (e.g. `Pipeline: PM → Designer → Dev → QA → DM`) so the user sees it one last time. |

**Out of scope for SKILL.md rewriting**: Architecture diagram (48-107), Tracker Protocol (115-159), Ralph Loop sections (162-233), Git Protocol (237-260), Upgrade Instructions (868+). These are role-agnostic or use `[role]` as a template variable that's fine as-is.

### PM CLAUDE.md — `D:\Dev\Dev\SquidSquad\.squidsquad\pm\CLAUDE.md`

Generated by `compose.py deploy pm` from sub-skill sources. Hardcoded role references to audit:

| Line | Content | Type of change |
|------|---------|----------------|
| 14 | "bridge between the human and the dev agents" | **Soften** to "bridge between the human and the rest of the squad". PM may be running a design-only team. |
| 16 | "active dev agents on this project are: **skill** (read from `.squidsquad/config.md`)" | **Change** — "active agents on this project" + read from resolved role list, not just `dev-agents` field |
| 79-83 | Role label taxonomy (`role:skill`, `role:pm`, etc.) | **Keep hardcoded** — the label taxonomy is a closed set; roles declared by manifests MUST conform. Document this invariant in the manifest schema. |
| 86-88 | `design:*` labels | **Keep, conditionally seeded** — only seed if designer is installed. Label definitions themselves stay in the doc as reference. |
| 178-187 | "Designer picks up / Designer completes / Dev agents skip…" example | **Keep as example**; annotate as conditional on designer presence. |
| 218 | "Coordinate between all dev agents" | **Change** to "all active agents (from resolved role list)" |
| 495 | "Read `.squidsquad/.local-config` … For each dev agent listed in `config.md`, plus the DM agent (if `.squidsquad/dm/` exists)" | **Change** to iterate over resolved role list from config (all installed agents), including designer, QA, and DM unconditionally (if present) |
| 522-525 | "Route: Determine which dev agent's domain" | **Change** to: route to any installed role whose manifest declares it handles external triage, or PM by default |
| 579-613 | Improvement scan: per-role lens (Dev/QA/Designer/DM/PM) | **Keep** — lens definitions are per-role SOUL concerns. Just gate which lens applies based on installed roles. |
| 941, 956-966 | "Design routing" question — checks `config.md Dev Agents list for designer` | **Change** — check `config.md` Agents list or run `config.py list-agents` to see if designer is installed. Currently checking the `Dev Agents` field is the bug — designer isn't a dev agent semantically. |
| 1047-1049 | Phase 4 Execution routed to "Dev Agent" | **Soften** to "implementing agent (dev or designer)". Already partially handled via design label. |
| 1103 | "Approved: dev/designer agent picks this up" | **Change** to "the agent(s) whose `role:` label is on the issue picks this up"; cleaner because it's already how tracker labels work. |
| 1370 | File conventions line | No change needed. |

The PM template is assembled by `compose.py` from `references/sub-skills/pm-specific/` + `common/` sub-skills. Edits need to happen in those source files, not the generated CLAUDE.md.

### Skill CLAUDE.md template — `D:\Dev\Dev\SquidSquad\.squidsquad\skill\CLAUDE.md`

Generated from `references/sub-skills/roles/dev-agent.md` + common sub-skills. Hardcoded references:

| Line | Content | Type of change |
|------|---------|----------------|
| 14-16 | "You are the skill Lead" / "work in a loop, independently, coordinating with other agents through markdown files" | **Keep** — `[ROLE]` substitution already handles this |
| 21-22 | "Fix bugs assigned to your role (`role:skill` label)" | **Keep** — `[ROLE]` is substituted |
| 79, 83 | Label taxonomy duplicated (role:skill, role:pm, role:qa, role:designer, role:dm) | **Keep hardcoded** — closed set. Same reasoning as PM. |
| 88-96 | design:* labels | **Keep**; gated at seed time |
| 196 | "Dev agents skip issues with `design:needed`" | **Keep** — this is a rule for dev variants; manifests declare `handles_design_gate: true` if we want to generalize |

The dev-agent.md entry has **no** hardcoded role-specific logic beyond `[ROLE]` substitution. It is already manifest-ready in spirit — the only work is making the wizard install it correctly for whichever dev variant the user picks.

### `references/templates/` and `references/scripts/`

Existing files:

- `references/templates/start-role.sh` — generic boot script; uses `{{ROLE}}` only. **No change needed.**
- `references/templates/start-role.ps1` — same. **No change needed.**
- `references/scripts/compose.py` — **needs refactor** (see below).
- `references/scripts/config.py` — **needs refactor**.
- `references/scripts/tracker.py` — grep shows it only uses `role:{role}` as a label string and a fixed `FEEDBACK_ROLES = {"pm", "qa", "human"}` set (line 219). **Keep**: the feedback-role set is a closed oversight-role list, not dynamic.
- `references/scripts/cycle.py` — untouched by roles AFAICT; uses `[ROLE]` as a CLI arg.
- `references/scripts/git_ops.py` — takes role name as arg; no role enumeration.
- `references/scripts/vault_remember.py`, `vault_check.py`, `diagnostics.py` — take role as arg; no role enumeration.

#### `compose.py` changes

The hardcoded dispatch table at lines 100-106:

```python
role_map = {
    "pm": "pm-agent",
    "qa": "qa-agent",
    "dm": "dm-agent",
    "designer": "designer",
}
return role_map.get(role_name, "dev-agent")
```

and the SOUL map at lines 166-167:

```python
soul_map = {"pm": "pm", "dm": "dm", "qa": "qa", "designer": "designer"}
```

and `boot_all()` at lines 201-214 which hardcodes PM + conditional DM:

```python
roles = [r.strip() for r in agents.split(",") if r.strip()]
roles.append("pm")  # PM always present
dm_dir = REPO_ROOT / ".squidsquad" / "dm"
if dm_dir.exists():
    roles.append("dm")
```

All three must read from `references/roles/<role>/manifest.yaml` instead. Proposed new shape:

```python
def _load_manifest(role_name):
    path = REPO_ROOT / "references" / "roles" / role_name / "manifest.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def _get_entry_file_for_role(role_name):
    return _load_manifest(role_name)["templates"]["entry"]

def _get_soul_for_role(role_name):
    return _load_manifest(role_name)["templates"]["soul"]

def _list_installed_roles():
    # Walk .squidsquad/*/CLAUDE.md like config.py sync_agents does
    # but return the full list without special-casing pm/dm
```

This adds a runtime YAML dependency. The skill already uses PyYAML elsewhere? Let me verify — **open question, confirm in implementation**. If not, use a minimal parser (the schema is small and flat) or pull in `pyyaml` with graceful fallback.

#### `config.py` changes

`FIELD_MAP` at lines 26-52 hardcodes `dev-agents`, `alias-skill`, `alias-pm`, `alias-dm`, `alias-designer`, `alias-qa`, and `skill-tests`. This set is role-fragile — adding a new role today requires editing `config.py`.

Changes needed:
- Replace `dev-agents` with a generalized `agents` (or `installed-roles`). Default the wizard to write this as a comma-separated list of resolved roles including PM/DM/QA.
- Replace the five hardcoded alias fields with a loop that resolves aliases dynamically: `get_alias(role)` already walks the `Aliases` section by field name, but the FIELD_MAP entries need to be generated from the installed role set or looked up ad-hoc. Cleanest fix: drop the alias-* entries from FIELD_MAP and make `get_alias()` parse the Aliases section directly (it already does as a fallback).
- Replace `skill-tests` with a `tests` section lookup keyed by role name at runtime, not hardcoded.
- Add a new helper `list_installed_roles()` that parses the Agents section and returns a list of all agent names. This replaces all `_read_config_value("dev-agents").split(",")` calls across the codebase.

`sync_agents()` at line 162 already walks `.squidsquad/*/CLAUDE.md` directories and excludes `pm`/`dm`. It needs to stop excluding and return all installed roles uniformly.

#### `tracker.py` — line 219

```python
FEEDBACK_ROLES = {"pm", "qa", "human"}
```

**Keep hardcoded**. The locked decisions do not make oversight roles dynamic, and PM/QA/human are the conceptual oversight set regardless of team shape. Worth a comment in the manifest schema noting that any future oversight role (beyond PM/QA) requires editing this set.

### Existing role artifact locations today

- **Agent body templates**: `references/sub-skills/roles/*.md` — `pm-agent.md`, `pm-lean.md`, `qa-agent.md`, `dm-agent.md`, `designer.md`, `dev-agent.md`. These are what `compose.py` pulls in.
- **SOUL templates**: `references/sub-skills/souls/*.md` — `pm.md`, `dm.md`, `qa.md`, `designer.md`, `dev.md`.
- **Role-specific sub-skills**: `references/sub-skills/pm-specific/`, `dm-specific/`, `qa-specific/`, `designer-specific/` (each with 7-16 files). Dev-agent uses `common/` only.
- **Common sub-skills**: `references/sub-skills/common/` — shared across all roles.
- **Boot script templates**: `references/templates/start-role.{sh,ps1}` — one per extension, `{{ROLE}}` substituted.
- **Hints pools**: `references/hints-dev.txt`, `references/hints-pm.txt` — used by statusline.
- **Agent instructions master**: `references/agent-instructions.md` — generated by `compose.py all`; primarily a debug artifact today.

There is **no** `references/roles/` directory today. FEAT-328 creates it. Proposed layout:

```
references/roles/
├── pm/
│   └── manifest.yaml
├── dm/
│   └── manifest.yaml
├── qa/
│   └── manifest.yaml
├── designer/
│   └── manifest.yaml
└── dev/
    └── manifest.yaml       ← single manifest with variants: be, fe, fullstack
```

**Alternative** (flagged as open question): one manifest per dev variant (`dev-be/`, `dev-fe/`, `dev-fullstack/`) instead of a single `dev/` manifest with sub-variants. See §4, §10.

## 2. Manifest Schema Design

Proposed YAML schema. Every field is present on every manifest unless marked optional.

```yaml
# required envelope
schema_version: 1                       # int, bump when schema changes
name: <role-name>                        # must match directory name; also the role: label
display_name: <Human Name>               # shown in wizard summaries
description: <one-line description>      # shown in wizard when the role is about to be installed

# templating
templates:
  entry: <path relative to references/sub-skills/roles/>       # e.g. "pm-agent"
  soul: <path relative to references/sub-skills/souls/>         # e.g. "pm"
  claude_bootstrapper: <template key or null>                   # null = auto-generate from entry
  boot_template: start-role                                      # key in references/templates/

# where the agent lives on disk
directory_layout:
  base: .squidsquad/<role>                # resolved at setup
  required_subdirs: [iterations, planning]
  optional_subdirs: [specs, scan-history]
  files:
    - CLAUDE.md                            # generated
    - SOUL.md                              # generated
    - working-state.md                     # generated empty

# pipeline resolution
routes_to: [<role>, <role>, ...]           # decentralized; order = fallback order
is_start_node: false                       # only PM is true in v1
is_terminal: false                         # only DM is true in v1

# preset membership
presets:
  software-dev: required | optional | excluded
  design: required | optional | excluded

# wizard setup questions (role-specific)
setup_questions:
  - id: <question-id>
    prompt: <text>
    options: [<opt1>, <opt2>, ...]         # null = free text
    default: <opt>
    stores: <key-in-config>                # where to persist the answer
    only_if: <optional predicate>

# runtime config keys this role reads from config.md
config_keys:
  - tests
  - alias

# labels this role owns (subset of the global label taxonomy)
labels:
  role: role:<name>                        # the role label for issue routing
  seeds_design_labels: false               # only designer sets this true
  skip_on_labels: []                       # dev skips issues with design:needed|in-progress

# ship-gating invariants
oversight: false                           # if true, comments from this role block transitions (tracker.py FEEDBACK_ROLES)

# manifest metadata
squidsquad_role: true                      # this manifest is SquidSquad-shipped (not user-defined)
```

### Example 1 — `references/roles/pm/manifest.yaml`

```yaml
schema_version: 1
name: pm
display_name: PM
description: Product Manager — the human's entry point; files bugs, runs feature intake, coordinates the squad.

templates:
  entry: pm-agent           # uses pm-lean-agent when qa is installed; resolver picks
  soul: pm
  claude_bootstrapper: null
  boot_template: start-role

directory_layout:
  base: .squidsquad/pm
  required_subdirs: [iterations, planning]
  optional_subdirs: [migrations]
  files: [CLAUDE.md, SOUL.md, working-state.md, enhancements.md]

routes_to: [designer, dev, qa, dm]   # fall-through order: designer > dev > qa > dm (direct to DM if nothing else)
is_start_node: true
is_terminal: false

presets:
  software-dev: required
  design: required

setup_questions: []     # PM has no role-specific questions

config_keys: [alias]

labels:
  role: role:pm
  seeds_design_labels: false
  skip_on_labels: []

oversight: true         # PM comments block dev transitions
squidsquad_role: true
```

### Example 2 — `references/roles/designer/manifest.yaml`

```yaml
schema_version: 1
name: designer
display_name: Designer
description: Produces design specs, tokens, and component specs. Hands off to dev when design is complete.

templates:
  entry: designer
  soul: designer
  claude_bootstrapper: null
  boot_template: start-role

directory_layout:
  base: .squidsquad/designer
  required_subdirs: [iterations, specs, planning]
  optional_subdirs: []
  files: [CLAUDE.md, SOUL.md, working-state.md]

routes_to: [dev, qa]      # falls through to qa if no dev installed
is_start_node: false
is_terminal: false

presets:
  software-dev: optional    # asks at wizard time
  design: required

setup_questions: []

config_keys: [alias]

labels:
  role: role:designer
  seeds_design_labels: true   # designer presence triggers design:* label seeding
  skip_on_labels: []

oversight: false
squidsquad_role: true
```

### Example 3 — `references/roles/dev/manifest.yaml`

```yaml
schema_version: 1
name: dev
display_name: Dev
description: Writes and ships code. Variants — backend, frontend, or fullstack.

templates:
  entry: dev-agent
  soul: dev
  claude_bootstrapper: null
  boot_template: start-role

directory_layout:
  base: .squidsquad/<variant>   # variant substituted at install time (be, fe, skill, etc.)
  required_subdirs: [iterations, planning]
  optional_subdirs: [scan-history]
  files: [CLAUDE.md, SOUL.md, working-state.md]

routes_to: [qa]
is_start_node: false
is_terminal: false

presets:
  software-dev: optional   # dev agents included by default in software-dev, but user picks variant
  design: excluded

setup_questions:
  - id: variant
    prompt: "What kind of dev work does this project involve?"
    options:
      - id: fullstack
        label: "Fullstack (single `dev` agent owning the whole stack)"
        installs:
          - name_template: dev            # resulting dir: .squidsquad/dev/
      - id: be
        label: "Backend only"
        installs:
          - name_template: be
      - id: fe
        label: "Frontend only"
        installs:
          - name_template: fe
      - id: be+fe
        label: "Separate backend and frontend agents"
        installs:
          - name_template: be
          - name_template: fe
    default: be+fe
    stores: dev.variant

config_keys: [tests, alias, framework]

labels:
  role: role:<name>           # resolved at install: role:be, role:fe, role:dev, etc.
  seeds_design_labels: false
  skip_on_labels: [design:needed, design:in-progress]

oversight: false
squidsquad_role: true
```

**Key design choice for dev**: one manifest, one `setup_questions.variant` that expands into 1 or 2 installed agents (for fullstack = 1, for be+fe = 2). The resolver treats each installed instance as a distinct node (`be`, `fe`) with its own `role:<name>` label. This keeps the dev agent's CLAUDE.md template (`dev-agent.md`) unchanged — it still uses `[ROLE]` substitution per instance. This is the same "multi-dev team" model the current code supports; FEAT-328 just gates it behind a wizard question instead of raw text input.

### Schema validation at setup time

The wizard runs `python references/scripts/manifest.py validate` (new script) which:
1. Loads every `.yaml` under `references/roles/*/manifest.yaml`
2. Checks each against the schema (required fields, known enum values for `presets.*`, `routes_to` references a known role name or is empty)
3. Fails loud with `ERROR: Manifest <path> — <reason>` if any validation fails
4. Warns (not fatal) on schema_version mismatches

## 3. Pipeline Resolution Algorithm

```
function resolve_pipeline(installed_roles):
    # installed_roles is a list of role name instances from the wizard
    # (e.g. ["pm", "designer", "be", "fe", "qa", "dm"])

    manifests = {role: load_manifest(role) for role in installed_roles}

    # 1. Find start node — exactly one role with is_start_node: true
    start_candidates = [r for r in installed_roles if manifests[r].is_start_node]
    if len(start_candidates) != 1:
        FAIL "exactly one is_start_node required, found {len}"
    start = start_candidates[0]   # always "pm" in v1

    # 2. Walk routes_to greedily, picking the first route target that is installed
    pipeline = [start]
    visited = {start}
    current = start

    while True:
        routes = manifests[current].routes_to
        next_node = None
        for candidate in routes:
            # Match by family: "dev" in routes_to matches any installed dev variant (be, fe, skill)
            installed_match = find_installed_matching(candidate, installed_roles)
            if installed_match and installed_match not in visited:
                next_node = installed_match
                break

        if next_node is None:
            break   # current is terminal or all routes already visited

        if next_node in visited:
            FAIL "cycle detected: {current} -> {next_node} (already in pipeline)"

        pipeline.append(next_node)
        visited.add(next_node)
        current = next_node

    # 3. Verify the pipeline ends at a terminal node OR DM
    last = pipeline[-1]
    if not manifests[last].is_terminal and last != "dm":
        WARN "pipeline does not end at a terminal node: {pipeline}"

    return pipeline
```

### Handling parallel dev variants (be + fe)

When multiple dev variants are installed, the greedy walk picks the first one and skips the other. To show both in the wizard summary, the display layer renders them as a parallel group:

```
PM → Designer → [ BE, FE ] → QA → DM
```

Implementation note: the resolver returns a linear pipeline for each dev instance, then the display layer collapses consecutive siblings (roles that share the same `routes_to` and are reached from the same predecessor) into a bracket group. This is a display concern only — the runtime doesn't care because issue routing is label-based, not pipeline-walk-based.

### Cycle detection

Cycle = a role appearing twice in the walk. Because we check `visited` before appending, any re-entry fails loud. The only realistic cycle is a misconfigured custom manifest with `PM: routes_to: [dev]` and `dev: routes_to: [pm]`; the shipped manifests have no such cycle.

### Fallback semantics

`routes_to: [dev, qa]` means: prefer dev, fall back to qa if dev not installed. If neither is installed, the role is terminal by default.

### Unresolvable next step

If `routes_to` has entries but none are installed, the walker treats the current node as terminal. This is the `PM → DM` direct case: PM's `routes_to: [designer, dev, qa, dm]` walks past unavailable roles until it lands on DM.

### Worked examples

**Example A — software-dev with all roles installed** (user picked fullstack + designer):
- installed: `[pm, designer, dev, qa, dm]`
- PM routes_to [designer, dev, qa, dm] → designer installed → next = designer
- designer routes_to [dev, qa] → dev installed → next = dev
- dev routes_to [qa] → qa installed → next = qa
- qa routes_to [dm] → dm installed → next = dm
- dm routes_to [] → terminal
- **result**: `PM → Designer → Dev → QA → DM`

**Example B — software-dev no designer, be+fe**:
- installed: `[pm, be, fe, qa, dm]`
- PM routes_to [designer, dev, qa, dm] → designer not installed → dev family? be/fe match → next = be (first match)
- be routes_to [qa] → next = qa
- qa → dm → terminal
- **result (linear)**: `PM → BE → QA → DM`
- **display (with parallel collapse)**: `PM → [ BE, FE ] → QA → DM`

**Example C — design preset**:
- installed: `[pm, designer, qa, dm]`
- PM → designer → (dev not installed, qa installed) → qa → dm → terminal
- **result**: `PM → Designer → QA → DM`

**Example D — PM → DM direct** (pathological but valid):
- installed: `[pm, dm]`
- PM routes_to [designer, dev, qa, dm] → only dm installed → next = dm
- dm terminal
- **result**: `PM → DM`

## 4. Setup Wizard Flow Redesign

New flow, numbered 1-10, mapped to SKILL.md step replacements.

| # | Question | Default | On answer | Replaces / modifies |
|---|----------|---------|-----------|---------------------|
| 1 | Project name + repo URL | git dir + `git remote get-url origin` | Store; no validation beyond non-empty | SKILL.md Step 1 fields 1, 2 — **no change** |
| 2 | Intent: "What do you want SquidSquad to help with?" (free text) | empty → prompt for preset picker | Keywords → suggested preset. No keywords / empty → show preset picker | **NEW** — inserted before old field 3 |
| 3 | Preset confirm: show suggested preset (or list both) and ask to confirm | suggested | Lock preset; load manifests whose `presets.<preset>` != `excluded`. Split into `required` (auto-install) and `optional` (ask later) | **NEW** — replaces SKILL.md Step 1 field 3 entirely |
| 4 | Optional roles prompt — per role with `presets.<preset>: optional`, ask whether to install. For `software-dev` this is Designer. | software-dev: Designer default N | Add accepted roles to the install list | **NEW** |
| 4b | Dev variant sub-question (only if dev is in the install list — true for software-dev preset only) | `be+fe` (matches current default behavior) | Expand the `dev` manifest into one or two installed instances per `setup_questions.variant.installs` | **NEW** — sub-questions driven by manifest |
| 5 | For each installed dev instance: framework / test command / e2e test command | existing defaults | Store per-instance in config.md `## Test Commands` | SKILL.md Step 1 fields 4, 5, 6 — **trimmed to installed dev roles only**; skip entirely for `design` preset |
| 6 | Agent aliases (one per installed role) | bare role name | Store in `## Aliases` | SKILL.md Step 1 field 3b — **generalized** to all installed roles |
| 7 | Loop interval | 10 | Store | SKILL.md Step 1 field 7 — **no change** |
| 8 | PR-based approval flow | N | Store; `gh auth status` check if Y | SKILL.md Step 1 field 9 — **no change** |
| 9 | GitHub Issues ingestion | **Y** (flipped per locked decision 7) | Store; `gh auth status` check if Y | SKILL.md Step 1 field 10 — **default flipped** |
| 10 | Validation summary: show project info, installed roles (including PM/DM), resolved pipeline (ASCII arrow), and all answers. Prompt for "confirm or re-enter field N" | — | On confirm → proceed to Steps 2-9 (folder creation onward) | SKILL.md Step 1 validation at line 339 — **expanded** |

### Intent question parsing (wizard step 2)

For v1, the parser is a local keyword matcher (no LLM call). Proposed rules:

- matches `software|code|app|api|backend|frontend|full.?stack|cli|library|skill` → suggest `software-dev`
- matches `design|ui|ux|brand|visual|spec|prototype` → suggest `design`
- else → show both presets with descriptions and ask the user to pick

The matcher is 30 lines of Python. If none match, the wizard falls back to a menu. **Open question**: should we also support an LLM-based parse for ambiguous inputs? See §10.

### Custom builder mode

**Out of scope for v1** per locked decision 5 (two presets v1). If the user wants a team shape that isn't covered, they say so during intake and the wizard offers a back-and-forth. V2 can add a `--custom` flag. See §10.

### Re-running setup

If `.squidsquad/` already exists, the wizard detects it and prompts:
1. Abort (default)
2. Regenerate templates only (`/squidsquad-upgrade`)
3. Full rebuild (nukes config.md, asks every question again)

This is not strictly in scope per locked decision 8 (no install base), but the test matrix will include "what if the user re-runs setup" because they will. See §10.

## 5. Side Effects

| Side effect | Severity | Mitigation |
|-------------|----------|------------|
| Removing hardcoded role references in PM CLAUDE.md breaks PM logic that depends on knowing about specific roles (e.g. design routing question, agent health check loop) | **H** | Phase rewrites: (1) for the design routing question, replace the `config.md Dev Agents list contains designer` check with a manifest-driven `is_role_installed("designer")` helper. (2) For the agent health check loop, iterate over all installed roles from the resolved list. (3) Keep label taxonomy enumeration hardcoded — the doc is reference material, not logic. |
| Manifest format errors at setup time | **M** | Validation script runs BEFORE folder creation. Schema errors exit with `ERROR: Manifest <path> invalid — <reason>`. No partial install. Test case: malformed YAML, missing required field, unknown preset enum, `routes_to` referencing an unknown role. |
| Preset semantics drift between `software-dev` and `design` | **M** | Presets are enumerated in each manifest's `presets:` section. Drift is detectable by running `manifest.py preset-audit` which prints the role list per preset. Consider a unit test: "snapshot preset `software-dev` returns [pm, designer?, dev, qa, dm]". |
| Scripts that hardcode `role:skill` in label queries — comprehensive list | **L** | grep results (across references/scripts/): `tracker.py` line 123, 180, 202 (`role_label = f"role:{role}"`) — these are dynamic, no change. No hardcoded literal `role:skill` found outside test fixtures and sub-skill docs. |
| Status bar / statusline.sh — assumes agent list from config.md | **M** | `statusline.sh` line 205-208 loops over agents via `$A`. Currently sources agents from `config.md` Dev Agents field. Update to source from the new generalized `Agents` field (or shell out to `config.py list-agents`). Designer and DM currently are NOT counted in the loop; fix it so they are. |
| Health check assumption that designer is a dev agent | **M** | PM's health check at line 495 walks "dev agents plus DM". Update to walk all installed agents uniformly. Designer and QA current-state mtime check already works if they're in the loop. |
| `start-role.sh/.ps1` boot scripts — do they need to be manifest-aware? | **L** | **No.** The boot template only substitutes `{{ROLE}}` and reads `config.py alias`. It already works for arbitrary role names. |
| Existing planning artifacts use `FEAT-SKILL-XXX-*.md` naming pattern — does the new manifest break this? | **L** | No — the naming pattern uses `ROLE_UPPER` as an infix (`FEAT-SKILL-XXX`) and is set by PM at feature-intake time. The manifest only governs setup-time wiring. Existing planning artifacts in `.squidsquad/skill/planning/` are preserved; new ones continue to use the same pattern. |
| Designer+QA independence when no dev is installed | **M** | In the `design` preset, QA verifies designer specs (rather than code). The qa-agent.md template already refers to "dev and designer work" so it has coverage. But QA's current e2e test logic runs `e2e-test` command — in a `design` preset, this command is empty and QA should skip it. Verify the current "if no e2e command, skip" logic works. |
| `compose.py boot-all` and `deploy-all` iterate from `dev-agents` field + hardcoded PM + DM-if-exists | **M** | Refactor to iterate over resolved role list from config.md's new `Agents` field. Backward-compat alias: if only `Dev Agents` exists (pre-FEAT-328 install), synthesize an `Agents` list. Per locked decision 8 (no install base), this backward-compat is not strictly required, but cheap insurance. |

## 6. Edge Cases

- **User picks `design` preset, wizard skips dev questions entirely, user later wants dev** — out of scope per locked decisions. Documented gap: user runs setup again (re-setup path, see §4) and selects `software-dev`. Current flow would clobber `.squidsquad/`. Fix: the re-run flow should offer an "add role" option. Flag as open question.
- **User picks `software-dev` but says no designer** — Designer preset membership is `optional`, wizard asks Y/N, user picks N. Resolver: PM's routes_to walks past designer (not installed) to dev. Works.
- **Dev variant `fullstack` — 1 agent or 2?** — Locked decisions don't specify. Proposed (see §2): `fullstack` installs one `dev` agent named `dev` (single code owner); `be+fe` installs two. This is an **open question** — see §10.
- **PM → DM direct** — `[pm, dm]` installed only. Walker: PM's routes_to [designer, dev, qa, dm] → only dm installed → pipeline = `[pm, dm]`. Works. Verify with a unit test.
- **Malformed manifest YAML** — wizard fails loudly before Step 2 (folder creation). Error message names the file and line. No silent fallback.
- **Two manifests create a cycle** — e.g. if a future custom manifest sets `pm: routes_to: [dev]` and `dev: routes_to: [pm]`, the walker hits `pm` again in visited and fails. Unit test with a deliberately cyclic test fixture.
- **`routes_to` entry references an unknown role name** — validation script catches this before walking. Error: "routes_to entry '<name>' in manifest <file> references unknown role".
- **Designer installed alone (`[pm, designer, dm]`)** — designer routes_to [dev, qa] → neither installed → walker treats designer as terminal. Final pipeline: `[pm, designer]`. But DM is installed and should be reached! **Bug**: the walker doesn't know designer should fall through to dm. Fix options: (a) add `dm` to every role's `routes_to` as a terminal fallback, or (b) the walker has a hardcoded "always fall through to dm if dm is installed" rule. Option (a) is cleaner and keeps decentralization. Recommend: each role's `routes_to` list ends with `dm` as the universal terminal. Update the example manifests in §2 accordingly.
- **Dev variant renaming conflict** — user picks `be+fe`, but a previous aborted setup left a `.squidsquad/be/` directory. Wizard should detect the existing directory and refuse to overwrite without confirmation.
- **All roles excluded from both presets** — impossible given locked decisions (PM/DM required in both), but the validation script checks that every preset has at least `[pm, dm]`.

## 7. Integration Risks

- **`/squidsquad-upgrade` interaction** — Upgrade flow today regenerates templates from `references/sub-skills/` into `.squidsquad/templates/` without touching config.md. Under FEAT-328, upgrade must also revalidate manifests (in case the shipped SquidSquad version added required fields). If validation fails, upgrade aborts with "manifest schema changed; re-run setup". **Risk**: M. **Mitigation**: ship a migration note and ensure the manifest schema is additive for 1.x.
- **npx installer (#269) interaction** — The installer fetches SKILL.md and the setup slash command today. Under FEAT-328, the skill at `references/` must also include the `roles/` subdirectory so the wizard can read manifests. The installer does not fetch role manifests explicitly — it relies on `claude install-skill` cloning the whole skill repo. Confirm this in FEAT-269 follow-up: verify `references/roles/` is included in the installed skill. **Risk**: L (skill install copies the full tree). **Mitigation**: add a post-install verification step that checks for `references/roles/pm/manifest.yaml` existence.
- **statusline script** — reads agent list from config.md `Dev Agents` field (via `config.py get dev-agents`). Under FEAT-328, the agents list is broader. **Mitigation**: update `statusline.sh` to use the new generalized `Agents` field and iterate all installed roles. The script already loops `for A in $AGENTS`, so the change is one line plus a config.py update.
- **PM Agent Health Check walks per-role current-state files** — loop at PM CLAUDE.md line 495. Currently: "each dev agent listed in config.md, plus DM agent if dm dir exists". Under FEAT-328: all installed roles, no special-casing. **Mitigation**: rewrite the loop body to iterate `config.py list-agents` and exclude self (PM doesn't health-check itself) and `human`. Test matrix must include a design-preset health check (designer+qa without dev).
- **Import-existing-items flow (Step 1 sub-section)** — heuristics route "items mentioning UI → fe". In a `design` preset with no fe/be installed, these heuristics should route to designer or PM. **Mitigation**: heuristics become manifest-aware — route to the first installed role whose manifest declares `handles_import: true` for that category. Or simpler: default all imports to PM if no match, PM triages in Step 7b anyway. Recommend the simple fallback: on no match, route to the first installed dev variant, or PM if none.
- **Label seeding (Step 6a)** — currently creates `role:pm/qa/dm/designer` unconditionally and `role:<dev>` per dev agent. Under FEAT-328, only seed `role:<name>` for installed roles. **Risk**: L. **Mitigation**: loop over installed roles in the seed command.

## 8. Upgrade & Migration

**N/A — no install base per locked decision 8. Clean rebuild is acceptable.**

Future-upgrade considerations (file for backlog, not for this feature):
- Manifest `schema_version` field makes future schema bumps detectable (the validator warns on mismatch). Start at v1.
- When we add a new role family in v2 (e.g. research agent), installs from v1 will not have the manifest and `/squidsquad-upgrade` must copy it in.
- When we allow user-defined roles (deferred feature in issue body), we'll need a `references/roles/<name>/manifest.yaml` vs `.squidsquad/roles/<name>/manifest.yaml` override path so user manifests don't get clobbered by upgrade.

## 9. Prior Art

Searched `.squidsquad/skill/planning/` for FEAT-SKILL-* features that touched setup, role registration, or wizard flow.

- **FEAT-269 (npx installer)** — Recent (`0436b57`). Adds an npm bootstrapper that runs before `claude install-skill`. Does not touch the setup wizard itself — it handles prerequisites only. **Relevance to FEAT-328**: the installer package must include `references/roles/` in its shipped tree. Need to coordinate the two features so the installer ships with manifests present.
- **FEAT-SKILL-055 (license / going public)** — Touches README, CONTRIBUTING, and what's in the public repo. Notes that `.squidsquad/` is per-project generated. **Relevance**: confirms presets and role manifests belong in `references/` (shipped with the skill), not `.squidsquad/` (per-project).
- **FEAT-SKILL-043, FEAT-SKILL-059, FEAT-SKILL-063** — unrelated (tracker, vault, and diagnostics work).
- **No prior feature** dealt with presets, intent questions, or manifest-driven role registration. FEAT-328 is greenfield.

Reusable patterns from existing work:
- The `compose.py` dispatch table pattern (lines 100-106) is the current de-facto "role registry". The new manifest layer generalizes it.
- `config.py sync_agents()` at line 162 already walks `.squidsquad/*/CLAUDE.md` to infer installed roles. This is the seed for the new `list_installed_roles()` helper.
- PM's Phase 2 design-routing question uses `AskUserQuestion` — the same UX pattern can drive the new preset-picker and dev-variant sub-question.

## 10. Open Questions for Phase 2 Discussion

- **Q1**: Dev variant `fullstack` — install one combined `dev` agent (owns the whole stack) or two separate `be`+`fe` agents?
  - **Why this matters**: Affects the dev manifest's `setup_questions.variant` structure (§2 Example 3), the default pipeline display (`PM → Dev → QA → DM` vs `PM → [BE, FE] → QA → DM`), and what happens to a feature that spans both halves. One agent = simpler but may thrash between BE and FE work. Two agents = current default behavior.
  - **Recommended**: Ship `be+fe` as the default `software-dev` preset behavior (matches today), and add `fullstack` as a single-dev option for solo projects.

- **Q2**: Where does the "intent" free-text get parsed to suggest a preset? Local keyword matcher, or LLM call at setup time?
  - **Why this matters**: Local matcher is deterministic, offline, fast, and testable. LLM call is smarter but adds a latency spike during setup and a dependency on the caller having a live Claude session. Since setup runs inside Claude already, an LLM call is free.
  - **Recommended**: Use an LLM call since we're already inside Claude. Matcher is a fallback for offline testing.

- **Q3**: Should the wizard show the resolved pipeline as ASCII art (`PM → Designer → Dev → QA → DM`) or as a list?
  - **Why this matters**: Display is user-facing. ASCII arrow is clearer for linear pipelines; breaks for parallel groups like `[BE, FE]`. List is flatter but loses the flow story.
  - **Recommended**: ASCII arrow with bracket notation for parallel groups: `PM → Designer → [ BE, FE ] → QA → DM`.

- **Q4**: Is custom-builder mode (pick roles individually, bypass presets) in v1 scope or future?
  - **Why this matters**: Adds a whole branch to the wizard. Locked decisions say "two presets v1" which implies no custom mode, but a 5-role team with no dev (PM + Designer + QA + DM + fullstack) isn't expressible with just two presets.
  - **Recommended**: Defer to v2. Document the gap in the README so users know they can hand-edit `config.md` if they need a custom shape.

- **Q5**: Do role manifests need versioning so future SquidSquad versions can detect outdated manifest files?
  - **Why this matters**: Upgrade flow will eventually need to detect schema drift. Versioning now is cheap; retrofitting later is painful.
  - **Recommended**: Yes. Add `schema_version: 1` as a required field from day one (already in §2 schema). Validator warns on mismatch.

- **Q6**: Where does the PM → DM "create plan and deliver it" workflow need explicit support — just the routing rule, or a special preset / template?
  - **Why this matters**: Locked decision 6 says "PM routes to DM direct is valid (e.g., 'create a project plan and deliver it')" but doesn't say whether this is a preset, a PM skill, or just a runtime edge case. If it's a preset, we have a 3rd preset to build. If it's runtime, the resolution algorithm already handles it via `routes_to` fallback.
  - **Recommended**: Runtime only — no new preset. The resolver already lands `[pm, dm]` on `PM → DM` when nothing else is installed. PM's intake flow needs a light tweak: when a feature's domain is "create a document and deliver", PM assigns `role:pm` and routes the work to itself for planning, then hands directly to DM.

- **Q7**: What does QA do in a `design` preset where there's no code? (Review specs against design brief? Visual QA?)
  - **Why this matters**: QA's Ralph Loop step 2 runs `e2e-test` which is empty in a design-only project. Step 5 ("verify pending-test items") is still meaningful — QA verifies designer specs against the feature's acceptance criteria and design brief. But the cycle needs a design-aware test lens.
  - **Recommended**: QA's template already handles "no e2e command → skip" gracefully. For design-spec verification, QA reads the feature's Design Brief section and the designer's specs/*.md, checks against acceptance criteria, and transitions pending-test → pending-ship. No new QA sub-skill needed; the existing "verification" sub-skill (`references/sub-skills/qa-specific/verification.md`) should be reviewed and lightly updated to mention design-spec verification as a valid lens.

- **Q8**: When a user runs setup multiple times in the same repo (re-setup), how does the wizard handle existing `.squidsquad/` directories?
  - **Why this matters**: Locked decisions say "no install base" but users WILL re-run. The wizard must do something sensible.
  - **Recommended**: Detect `.squidsquad/` existence. Offer: (1) Abort (default), (2) `/squidsquad-upgrade` (regen templates only), (3) Full rebuild (nukes `.squidsquad/` after confirmation). Option (3) includes "add role to existing team" in a future iteration.

- **Q9**: Should the `dev` manifest expand into one manifest file with variants (current §2 proposal) or separate manifest files per variant (`dev-be/`, `dev-fe/`, `dev-fullstack/`)?
  - **Why this matters**: Affects directory layout under `references/roles/`, validation logic, and whether users can customize a single variant without editing others. Single manifest with `setup_questions.variant` is DRY; separate manifests are easier to reason about and allow different `routes_to` per variant.
  - **Recommended**: Single manifest with variants. No current variant needs different routing — they all route to QA.

- **Q10**: Does the schema need a universal-terminal rule for `routes_to`? (See Edge Case in §6 where `[pm, designer, dm]` walks `pm → designer` and stops because designer's routes_to `[dev, qa]` has no installed match, leaving DM unreached.)
  - **Why this matters**: The walker can't reach DM without either hardcoding a "fall through to DM if installed" rule OR putting `dm` at the end of every role's `routes_to`.
  - **Recommended**: Put `dm` at the end of every role's `routes_to` in the shipped manifests. Keeps decentralization pure. Update §2 examples before implementation.

## 11. Recommendation

**Feasible with caveats.**

The locked decisions do the hard architectural work. What remains is mechanical — define the schema, write the resolver, rewrite the wizard, and migrate hardcoded role enumerations to manifest lookups. The greenfield nature (no `references/roles/` directory exists today, no install base per locked decision 8) makes this much cleaner than a migration.

Caveats:
1. **Terminal fall-through** (Q10, Edge Case in §6) — the walker algorithm needs a clean answer before implementation. Recommend putting `dm` at the end of every shipped manifest's `routes_to`.
2. **PM's hardcoded "designer is a dev agent" check** — the design-routing question at PM CLAUDE.md line 956 is the biggest logic change. Replace with a manifest-driven `is_installed("designer")` helper. This is a behavior-preserving refactor, not a new feature.
3. **Compose.py dispatch tables** — three places (role→entry, role→soul, boot-all loop) need to become manifest lookups. Straightforward but touches hot code; regression tests should cover all five v1 roles (pm, dm, qa, designer, dev).
4. **Dev variant fullstack** (Q1, Q9) — unresolved in locked decisions; needs a Phase 2 answer before writing the dev manifest.
5. **Re-run handling** (Q8) — needed to not break users, even though "no install base" means we don't have to migrate.

Overall scope: roughly 800-1200 lines of SKILL.md rewrite, a new ~150-line `manifest.py` script, ~150 lines of refactor to `compose.py` + `config.py`, five new manifest files (each ~40 lines), and light edits to 4-6 sub-skill source files for the PM template generation. Test plan will need fresh-install coverage for both presets and the `design` QA-no-code path.
