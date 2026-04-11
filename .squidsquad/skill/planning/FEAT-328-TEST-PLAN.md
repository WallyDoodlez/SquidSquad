# FEAT-328 Test Plan — Intent-driven setup wizard with role manifest registry

## Scope

Tests cover the full install flow (Steps 0-7), the role and tool manifest registries, the preset manifest registry, the pipeline resolver, the status taxonomy migration (`pending` → `pending-human-approval` + new `pending-human-review` / `pending-human-setup`), PM's runtime tool orchestration (Q-new11/12), and regression safety.

All tests target **this repo only** (no external install base per locked decision 10). Tests execute in a scratch clone unless otherwise noted.

Notation:
- **Fixtures** reference files under `tests/fixtures/feat-328/` (dev creates these).
- **Scratch repo** = a fresh `git clone` + empty `.squidsquad/`.
- "Wizard" means running `/squidsquad-setup` inside a Claude session (the installer agent).

## Test Cases

### Happy-Path Install

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-01 | software-dev + be+fe + designer=yes + QA auto | 1. Scratch repo. 2. Run `/squidsquad-setup`. 3. Step 2: "I want to build a web app". 4. Step 3: confirm software-dev. 5. Step 4 designer.install_optional: `yes`. 6. Step 4 dev.variant: `be+fe`. 7. Step 4 dev.stack: "FastAPI + pytest backend, Next.js + jest frontend". 8. Step 5 interval: `10`. 9. Step 6: [P]roceed. | `config.md` contains `## Agents` with pm, designer (iteration_mode: hitl), be, fe, qa, dm. `## Tools` has `designer.tool: (unset — PM will configure on first use)` and `dm.tool: local_delivery`. Directories `.squidsquad/{pm,designer,be,fe,qa,dm}/` all exist with CLAUDE.md, SOUL.md, working-state.md. `start-pm.sh/ps1`, `start-designer.sh/ps1`, `start-be.sh/ps1`, `start-fe.sh/ps1`, `start-qa.sh/ps1`, `start-dm.sh/ps1` created. Labels seeded. `role:be`, `role:fe`, `role:pm`, `role:designer`, `role:qa`, `role:dm` all exist. Installer prints "SquidSquad ready" and disposes. | integration |
| TC-02 | software-dev + fullstack + designer=no | 1. Scratch. 2. Wizard intent: "build a web app". 3. Preset: software-dev. 4. designer.install_optional: `no`. 5. dev.variant: `fullstack`. 6. dev.stack: "Node + Express + jest". 7. Interval: 10. 8. Proceed. | config.md has pm, dev (variant: fullstack), qa, dm. No `.squidsquad/designer/`. Pipeline summary prints `PM → Dev → QA → DM`. Boot scripts created for pm, dev, qa, dm only. | integration |
| TC-03 | software-dev + be only + designer=no | 1. Scratch. 2. Intent: software. 3. Preset: software-dev. 4. designer.install_optional: `no`. 5. dev.variant: `be`. 6. dev.stack: "Python FastAPI pytest". 7. Proceed. | config.md has pm, be, qa, dm (no fe, no designer). Pipeline: `PM → BE → QA → DM`. | integration |
| TC-04 | software-dev + fe only + designer=yes | 1. Scratch. 2. Preset: software-dev. 3. designer.install_optional: `yes`. 4. dev.variant: `fe`. 5. dev.stack: "Next.js TypeScript jest". 6. Proceed. | config.md has pm, designer, fe, qa, dm. Pipeline: `PM → Designer ↻ → FE → QA → DM`. designer entry has `iteration_mode: hitl`. `.squidsquad/qa/` created (auto with dev). | integration |
| TC-05 | design preset — designer always, no dev variant question | 1. Scratch. 2. Intent: "I need a mobile app UI mockup". 3. Preset: design. 4. No dev.variant question asked. 5. No designer.install_optional question (designer mandatory). 6. Interval: 10. 7. Proceed. | config.md has only pm, designer, dm (no dev, no qa). Pipeline: `PM → Designer ↻ → DM`. Step 4 walker only asks designer's requirements (none in v1 for design preset since `install_optional` is `only_in_presets: [software-dev]`). | integration |
| TC-06 | Happy path — config.md structure validation | Complete TC-01. | `config.md` has these sections in order: `## Project`, `## Preset`, `## Agents`, `## Tools`, `## Loop`, `## Flags`. Each Agent entry matches Q-new17 schema: `- **<id>**: <alias>` with `role:`, optional `iteration_mode:`, optional `setup:` block, optional `variant/stack/test_command`. | unit |
| TC-07 | Happy path — role CLAUDE.md does NOT contain tool sub-skills | Complete TC-01. Read `.squidsquad/designer/CLAUDE.md`. | File contains designer body template but NO figma/stitch/html sub-skill content (tool deferred to runtime per Q-new11). A composition anchor comment exists for PM to fill in later. | unit |
| TC-08 | Happy path — installer disposes cleanly | Complete TC-01. Capture the installer session's final output. | Last message contains "SquidSquad ready" and a hint to run `./start-pm.sh` (or `.ps1` on Windows). Installer does not loop, does not boot PM, does not remain alive. Exit code 0. | integration |
| TC-09 | Happy path — nothing is written before [P]roceed | 1. Scratch. 2. Walk wizard through Step 6. 3. At review screen, pick [A]bort. | No files under `.squidsquad/` were created. No git changes. No labels created. `git status` is clean. | integration |

### Manifest Schema Validation

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-10 | Role manifest missing schema_version → fail loudly | 1. Copy fixture `role-missing-schema-version.yaml` over `references/roles/designer/manifest.yaml`. 2. Run `python references/scripts/manifest.py validate`. | Exit 1. stderr contains `ERROR`, the path, and `schema_version`. | unit |
| TC-11 | Role manifest unknown schema_version → fail loudly | 1. Set `schema_version: 99` in a fixture manifest. 2. Run validator. | Exit 1. Message names the offending version and that the supported versions are `[1]`. | unit |
| TC-12 | Role manifest routes_to references non-existent role | 1. Fixture: designer routes_to `[nonexistent, dm]`. 2. Run validator. | Exit 1. Message identifies `designer.routes_to[0]=nonexistent` as unknown and lists known roles. | unit |
| TC-13 | Role manifest domain-only violation | 1. Fixture: manifest `description` mentions `config.md` or `.squidsquad/`. 2. Run validator. | Exit 1. Message says domain-only rule violated (Q-new14) and quotes the offending text. | unit |
| TC-14 | Tool manifest missing required fields | 1. Fixture `tool-missing-fields.yaml` lacks `id` and `provider`. 2. Run validator. | Exit 1. Both missing fields are named. | unit |
| TC-15 | Preset manifest role_install_order references non-existent role | 1. Fixture: `software-dev` preset with `role_install_order: [designer, ghost, qa]`. 2. Validator. | Exit 1. Message identifies `ghost` as unknown role. | unit |
| TC-16 | Cross-reference: role requires_tools unknown tool ID | 1. Fixture: designer's `requires_tools.any_of: [unicorn]`. 2. Validator. | Exit 1. Message identifies `designer.requires_tools: unicorn` not in tool registry. | unit |
| TC-17 | Cycle detection in resolver | 1. Fixture: role A routes_to [B], role B routes_to [A]. 2. Validator. | Exit 1. Message names cycle: `A → B → A`. | unit |
| TC-18 | Validator passes on shipped v1 manifests | 1. Clean repo. 2. Run validator against `references/roles/` and `references/tools/` and `references/presets/`. | Exit 0. No warnings. All 5 role, 4 tool, 2 preset manifests load. | smoke |
| TC-19 | Role manifest missing display_name / tagline / show_in_roster | 1. Fixture lacking any of the three Q-new15 fields. 2. Validator. | Exit 1. Each missing field is named individually. | unit |
| TC-20 | Every v1 role manifest has setup_requirements (possibly empty) | Load each shipped manifest. | Each manifest has a `setup_requirements` key (empty list allowed). PM/DM/QA have `[]`, designer has `install_optional`, dev has `variant` and `stack`. | unit |

### Step 0 — gh prerequisite

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-21 | gh not installed → abort with clear message | 1. PATH excludes gh. 2. Run wizard. | Wizard exits at Step 0 with message naming `gh` as missing, including install link. No `.squidsquad/` changes. | unit |
| TC-22 | gh installed but not authenticated → abort | 1. `gh auth logout`. 2. Run wizard. | Wizard exits at Step 0 with message instructing user to run `gh auth login` with `repo` scope. | unit |
| TC-23 | gh installed and authenticated → proceed | 1. `gh auth status` succeeds. 2. Run wizard. | Wizard proceeds past Step 0 to Step 0b. | smoke |

### Step 0b — Re-run detection

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-24 | No existing `.squidsquad/` → skip re-run detection | 1. Scratch. 2. Wizard. | Wizard goes directly to Step 1, no three-way prompt shown. | unit |
| TC-25 | Existing `.squidsquad/`, pick Abort (default) | 1. Repo with existing `.squidsquad/`. 2. Wizard. 3. Press Enter at the three-way prompt. | Wizard exits with "no changes made". `.squidsquad/` untouched. | unit |
| TC-26 | Existing `.squidsquad/`, pick Regenerate (option 2) | 1. Existing install. 2. Wizard. 3. Choose option 2. | Wizard delegates to `/squidsquad-upgrade` and exits. Does not proceed with fresh install steps. | integration |
| TC-27 | Existing `.squidsquad/`, pick Full rebuild (option 3) | 1. Existing install. 2. Wizard. 3. Choose option 3. 4. Type confirmation string. | Wizard records full-rebuild intent and proceeds to Step 1. `.squidsquad/` is NOT deleted yet (deferred to Step 7). | integration |
| TC-28 | Full rebuild typed-confirmation required | 1. Choose option 3. 2. Type anything other than the confirmation phrase. | Wizard refuses and re-prompts or returns to the three-way menu. Nothing committed. | unit |

### Step 1 — Project details

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-29 | Auto-fill from `gh repo view` | 1. Scratch clone of WallyDoodlez/SquidSquad. 2. Wizard. 3. Step 1. | Wizard pre-fills project name and repo slug from `gh repo view --json name,nameWithOwner`. User just confirms. | unit |
| TC-30 | Manual entry validation — non-empty | 1. Wizard Step 1. 2. Submit empty project name. | Wizard re-prompts with "Project name cannot be empty". | unit |

### Step 2 — Intent + roster

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-31 | Roster rendered from role manifests | 1. Wizard Step 2. | Roster shows Designer, Dev, QA (three rows). PM and DM NOT shown (show_in_roster=false). Each row uses manifest `display_name` and `tagline`. | unit |
| TC-32 | LLM classifies simple software intent | 1. Step 2. 2. Answer: "I want to build a web app". | Classification returns `software-dev`. Step 3 proposes software-dev preset. | integration |
| TC-33 | LLM classifies design intent | 1. Step 2. 2. Answer: "I need a mobile app UI mockup". | Classification returns `design`. Step 3 proposes design preset. | integration |
| TC-34 | LLM classifies ambiguous intent → unclear → follow-up | 1. Step 2. 2. Answer: "I'm building something cool". | Classification returns `unclear`. Wizard asks a follow-up question (LLM-driven). After follow-up, preset is resolved. | integration |
| TC-35 | Roster hides infrastructure roles | Same as TC-31. | No row labeled "PM" or "DM" exists in the roster output. | unit |

### Step 3 — Confirmation

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-36 | Conversational confirm accepts Y | 1. Step 3 after software-dev proposal. 2. Answer "yes". | Wizard advances to Step 4. | unit |
| TC-37 | `explain` option shows Claude's reasoning | 1. Step 3. 2. Type `explain`. | Wizard prints the LLM's classification rationale then re-prompts. | integration |
| TC-38 | User redirect: "no, I just want backend" | 1. Step 3 (software-dev proposal). 2. Answer: "no, I just want backend". | Wizard re-proposes software-dev + be-only. User confirms. State reflects be-only variant (dev.variant is pre-populated / user still picks in Step 4). | integration |

### Step 4 — Setup requirements walker

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-39 | Walks roles in preset's install order | 1. software-dev preset. 2. Enter Step 4. | Order of questions follows `role_install_order: [designer, dev, qa]`. Designer questions precede dev questions. | unit |
| TC-40 | designer.install_optional skipped in design preset | 1. design preset. 2. Step 4. | Wizard does NOT ask the install_optional question. Designer is installed unconditionally. `only_in_presets: [software-dev]` filter is honored. | unit |
| TC-41 | dev.variant — be+fe | 1. software-dev. 2. At dev.variant prompt, answer indicating be+fe. | Wizard records `dev.variant=be+fe` and schedules two dev agents (be, fe). | unit |
| TC-42 | dev.variant — fullstack | 1. At dev.variant, answer "fullstack". | Single `dev` agent scheduled. | unit |
| TC-43 | dev.stack collected in ONE conversation for per_installed_agent | 1. variant=be+fe. 2. dev.stack prompt. 3. Reply: "Python/FastAPI with pytest for backend, Next.js with Jest for frontend". | Claude parses the reply and stores `be.stack="FastAPI + Python 3.x + pytest"` and `fe.stack="Next.js + TypeScript + jest"` as two separate answers. Only ONE user-facing prompt exchange. | integration |
| TC-44 | dev.stack follow-up when answer is partial | 1. variant=be+fe. 2. stack prompt. 3. Reply: "FastAPI + pytest". | Claude follows up: "Got the backend. What about the frontend?" | integration |
| TC-45 | dev.stack uses repo_hints (reads package.json first) | 1. Scratch repo with `package.json` present. 2. dev.variant=fe. 3. Reach dev.stack. | Wizard reads `package.json` before asking and pre-suggests a stack inferred from it (e.g., "Detected Next.js + TypeScript"). User confirms or overrides. | integration |
| TC-46 | dev.stack with no repo hints → free text | 1. Empty scratch repo. 2. variant=fullstack. 3. dev.stack. | Wizard asks free-text and LLM-classifies the reply. | integration |
| TC-47 | PM / DM / QA have empty setup_requirements | 1. Step 4 for any preset. | Wizard does not ask any question for pm, dm, or qa. | unit |
| TC-48 | Question skipped when only_in_presets excludes current preset | 1. design preset. 2. Step 4. | Every requirement whose `only_in_presets` list doesn't include `design` is skipped silently. | unit |

### Step 5 — Loop interval

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-49 | Accepts integer >= 1 | 1. Step 5. 2. Enter `10`. | Wizard accepts and advances. | unit |
| TC-50 | Rejects 0 | 1. Enter `0`. | Wizard re-prompts with validation message. | unit |
| TC-51 | Rejects negative | 1. Enter `-5`. | Re-prompts. | unit |
| TC-52 | Rejects non-numeric | 1. Enter `abc`. | Re-prompts. | unit |

### Step 6 — Review screen

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-53 | Review shows full summary | 1. Reach Step 6 with TC-01 answers. | Summary contains: Project, Repo, Preset, Pipeline ASCII arrow, Roles installed list with per-role config, Loop interval. Matches Q-new9 template. | unit |
| TC-54 | [V] Preview shows composed role CLAUDE.md without writing | 1. Step 6. 2. Press V. | Preview renders `config.md` content, each role's composed CLAUDE.md, planned GH label diff, file list. Nothing touches disk. `git status` clean. | integration |
| TC-55 | [E] Edit returns to a specific step, preserves other answers | 1. Step 6. 2. Press E. 3. Pick "dev variant". 4. Change be+fe → fullstack. | Wizard jumps to dev.variant, previous answers for project/intent/interval all preserved. After edit, returns to Step 6. dev.stack is re-asked (downstream of variant). | integration |
| TC-56 | [E] Edit changing variant regenerates downstream answers | Continuation of TC-55. | dev.stack answer is reset and re-collected (it's per-agent and depends on variant). Unrelated answers (interval, project) unchanged. | integration |
| TC-57 | [A] Abort exits with no disk changes | 1. Step 6. 2. Press A. | Prints "no changes made". Exit 0. `.squidsquad/` unchanged. Working tree clean. | unit |
| TC-58 | [P] Proceed advances to Step 7 | 1. Step 6. 2. Press P. | Wizard enters Step 7 file-writing phase. | unit |
| TC-59 | Full-rebuild shows DELETION warning on review | 1. TC-27 setup. 2. Reach Step 6. | Review banner contains "WARNING: Existing `.squidsquad/` will be DELETED on proceed". User can still abort. | integration |
| TC-60 | Preview → Edit → Preview → Proceed preserves state | 1. Step 6. 2. V. 3. E, edit interval. 4. V again. 5. P. | All state preserved across the V/E/V/P cycle. Final install reflects edited interval. | integration |

### Step 7 — Write files

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-61 | config.md Agents/Tools sections match Q-new17 schema | Complete TC-01. Read `.squidsquad/config.md`. | Exact section structure: `## Agents` then `## Tools`. Tools section has `designer.tool: (unset — PM will configure on first use)` and `dm.tool: local_delivery`. | unit |
| TC-62 | Role CLAUDE.md files written without tool sub-skills | Complete TC-01. | `.squidsquad/designer/CLAUDE.md` contains no figma/stitch/html sub-skill blocks. Contains composition anchor comment. | unit |
| TC-63 | New labels created | Complete TC-01. Run `gh label list`. | Labels exist: `status:pending-human-approval`, `status:pending-human-review`, `status:pending-human-setup`. | integration |
| TC-64 | Status:pending issues migrated to pending-human-approval | 1. Repo with issues labeled `status:pending`. 2. Run wizard. 3. Proceed. | All previously-pending issues now have `status:pending-human-approval` label. `status:pending` label removed from those issues. | integration |
| TC-65 | status:pending label removed after migration | Same as TC-64. Run `gh label list`. | `status:pending` label no longer exists. | integration |
| TC-66 | tracker.py legal transitions updated | Read `references/scripts/tracker.py` after install. | Transitions table includes: `pending-human-approval → planning | approved`, `in-progress → pending-human-review`, `pending-human-review → in-progress | pending-ship`, `in-progress → pending-human-setup`, `pending-human-setup → in-progress`. No references to bare `pending`. | unit |
| TC-67 | Boot scripts created for all installed roles | Complete TC-01. List `start-*.sh` / `start-*.ps1`. | One pair per installed role. Scripts use the same generic template as today. | unit |
| TC-68 | "SquidSquad ready" message printed and installer disposes | Complete TC-01. | Final output contains "SquidSquad ready" and the command to start PM. Conversation ends (installer exits per Q-new21). | integration |
| TC-69 | Full rebuild actually deletes at Step 7 | 1. TC-27 flow. 2. Proceed at Step 6. | Existing `.squidsquad/` is removed before new files are written. Fresh install produced. Vault / iteration logs from prior install NOT preserved (full rebuild warning was explicit). | integration |

### Pipeline Resolution

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-70 | software-dev all roles | 1. Load installed set `[pm, designer, be, fe, qa, dm]`. 2. Resolve pipeline. | `PM → Designer ↻ → [BE, FE] → QA → DM`. | unit |
| TC-71 | software-dev no designer | `[pm, be, fe, qa, dm]`. | `PM → [BE, FE] → QA → DM`. | unit |
| TC-72 | software-dev fullstack | `[pm, designer, dev, qa, dm]`. | `PM → Designer ↻ → Dev → QA → DM`. | unit |
| TC-73 | software-dev be only | `[pm, be, qa, dm]`. | `PM → BE → QA → DM`. | unit |
| TC-74 | software-dev fe only + designer | `[pm, designer, fe, qa, dm]`. | `PM → Designer ↻ → FE → QA → DM`. | unit |
| TC-75 | design preset | `[pm, designer, dm]`. | `PM → Designer ↻ → DM`. | unit |
| TC-76 | DM-as-terminal walker for [pm, designer, dm] | Synthetic installed set. | Walker reaches DM via designer.routes_to fallback (Q1 — every role's routes_to ends with dm). | unit |
| TC-77 | Minimal [pm, dm] collapse | Synthetic set. | Pipeline `PM → DM`. Wizard also shows the Q5 friendly hint. | unit |
| TC-78 | Cycle detection rejects synthetic loop | Fixture with circular routes_to. Run validator. | Exit 1 naming the cycle. | unit |

### Status Taxonomy Migration

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-79 | Existing status:pending issues relabeled | 1. Repo with N issues having `status:pending`. 2. Run migration. | All N now have `status:pending-human-approval`. | integration |
| TC-80 | Migration is idempotent | 1. Run migration twice. | Second run is a no-op. Label counts identical. No duplicate labels. Exit 0. | integration |
| TC-81 | Legal transition: pending-human-approval → planning | `tracker.py transition <n> pending-human-approval planning`. | Succeeds. | unit |
| TC-82 | Legal transition: pending-human-approval → approved | Same as TC-81 with target `approved`. | Succeeds. | unit |
| TC-83 | Legal transition: in-progress → pending-human-review | `tracker.py transition <n> in-progress pending-human-review`. | Succeeds. | unit |
| TC-84 | Legal transition: pending-human-review → in-progress | `tracker.py transition <n> pending-human-review in-progress`. | Succeeds. | unit |
| TC-85 | Legal transition: pending-human-review → pending-ship | Same with target `pending-ship`. | Succeeds. | unit |
| TC-86 | Legal transition: in-progress → pending-human-setup | `tracker.py transition <n> in-progress pending-human-setup`. | Succeeds. | unit |
| TC-87 | Legal transition: pending-human-setup → in-progress | Same with target `in-progress`. | Succeeds. | unit |
| TC-88 | Illegal: pending-human-review → shipped direct | `tracker.py transition <n> pending-human-review shipped`. | Exit 1 with "illegal transition" error. | unit |
| TC-89 | Illegal: pending-human-approval → shipped | Same for shipped target. | Exit 1. | unit |

### Runtime Tool Orchestration (Q-new11 / Q-new12)

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-90 | PM pre-emptive scan only when queue has unconfigured-tool feature | 1. Approved queue has 1 feature that requires designer + figma, which is unconfigured. 2. Run PM cycle. | PM triage detects gap, surfaces at check-in. | integration |
| TC-91 | Empty approved queue → PM does NOT prompt for tool setup | 1. Empty approved queue. 2. Run PM cycle. | No tool setup prompt. PM idle / continues normally. | integration |
| TC-92 | PM detects unconfigured tool gap and prompts human at check-in | Continuation of TC-90. | At check-in, PM prints "Feature #X needs <role> + <tool>. Configure now?" and waits for human reply. | integration |
| TC-93 | PM runs setup.md walkthrough interactively | 1. Human answers yes. 2. PM walks figma setup.md. | PM reads `references/tools/figma/setup.md`, presents steps. After completion, PM composes `sub-skill.md` into `.squidsquad/designer/CLAUDE.md` at the composition anchor. PM commits the change. | integration |
| TC-94 | Worker reads updated CLAUDE.md next cycle | 1. TC-93 complete. 2. Designer next cycle. | Designer's CLAUDE.md now contains figma sub-skill content. Designer uses the tool naturally. | integration |
| TC-95 | Worker mid-work discovers missing tool → self-pause | 1. Designer in-progress on #42. 2. Realizes Figma-specific capability missing. | Designer transitions `in-progress → pending-human-setup`, comments on #42 describing the gap, moves to next item. Does NOT block cycle. | integration |
| TC-96 | PM detects pending-human-setup in triage | 1. #42 in pending-human-setup. 2. Run PM cycle. | PM's triage sub-check finds the item and surfaces at check-in. | integration |
| TC-97 | PM completes setup and transitions back | 1. Human walks setup with PM. 2. PM succeeds. | PM composes sub-skill, commits, transitions `pending-human-setup → in-progress`. Designer next cycle picks it up. | integration |
| TC-98 | Worker never writes to its own CLAUDE.md | 1. Designer cycle that discovers missing tool. 2. Inspect any file writes. | Designer commits only touch issue comments and working-state, never `.squidsquad/designer/CLAUDE.md`. | unit |
| TC-99 | HITL designer iterations (human ↔ worker direct) | 1. Designer posts pending-human-review on #42. 2. Human comments redirect. 3. Designer next cycle. | Designer picks up #42 from pending-human-review, iterates, re-presents. No PM involvement. | integration |
| TC-100 | Mid-work clarifications (human ↔ worker direct) | 1. Skill in-progress on #50. 2. Human comments asking a question. 3. Skill next cycle. | Skill can read the comment and respond without PM routing. | integration |
| TC-101 | New feature filings direct to worker | 1. Human creates issue with `role:designer` label and `status:pending-human-approval`. 2. PM cycle. | PM triages and approves; designer picks up. No rejection because PM wasn't the filer. | integration |

### Review Screen Preview

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-102 | Preview shows composed config.md in memory | 1. Step 6. 2. Press V. | Preview displays config.md content. `.squidsquad/config.md` does NOT exist on disk. | integration |
| TC-103 | Preview shows each role's CLAUDE.md content | Same as TC-102. | Preview renders each installed role's composed CLAUDE.md body. | integration |
| TC-104 | Preview shows planned GH label changes | Same. | Preview lists labels to be created and (if full rebuild or migration needed) labels to be migrated/removed. | integration |
| TC-105 | Preview shows file list | Same. | Preview lists every file path to be created under `.squidsquad/` plus boot scripts. | unit |
| TC-106 | Preview is read-only, returns to menu | Same. | After scrolling, wizard re-displays Step 6 menu [P/V/E/A]. No state mutation. | unit |
| TC-107 | Preview → Edit → Preview → Proceed no state loss | TC-60 (duplicate coverage category). | See TC-60. | integration |

### Regression

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-108 | Existing software-dev workflow still works post-install | 1. Complete TC-01 on fresh clone of this repo. 2. Boot PM via `start-pm.sh`. 3. Run one cycle. | PM cycle completes normally: pulls, triages bugs, picks feature, etc. No regressions vs pre-#328. | integration |
| TC-109 | Existing planning artifacts preserved | 1. Repo with `.squidsquad/skill/planning/FEAT-*.md` files. 2. Run wizard (NOT full rebuild). | All existing FEAT-*.md files untouched. | integration |
| TC-110 | Existing iteration logs preserved | 1. Repo with `.squidsquad/skill/iterations/iter-N.md`. 2. Wizard (option 2 regenerate). | iter-N.md files untouched. | integration |
| TC-111 | Existing vault content preserved | 1. Repo with `.squidsquad/vault/` populated. 2. Wizard (regenerate). | Vault untouched. | integration |
| TC-112 | GH issues not labeled status:pending untouched by migration | 1. Repo with mixed status issues. 2. Run migration. | Only `status:pending` issues changed. Everything else identical (labels, comments, state). | integration |
| TC-113 | Boot scripts use existing template | 1. Complete TC-01. 2. Compare `start-*.sh` to `references/templates/start-role.sh`. | Only `{{ROLE}}` is substituted. No other changes vs current pattern. | unit |
| TC-114 | `/squidsquad-upgrade` still functions | 1. Run `/squidsquad-upgrade` on an installed repo. | Upgrade completes successfully. Not modified in #328 scope. | integration |
| TC-115 | compose.py produces valid CLAUDE.md for every shipped role | 1. Run `compose.py deploy <role>` for each role. | All 5 roles produce valid CLAUDE.md files. No dispatch failures. | unit |
| TC-116 | statusline.sh reads installed roles from manifest/config | 1. Install design preset. 2. Check statusline output. | Shows pm, designer, dm only (no skill/be/fe/qa). | integration |

### Edge Cases

| TC | Description | Steps | Expected | Type |
|----|-------------|-------|----------|------|
| TC-117 | Install on repo with no commits | 1. `git init` + no commits. 2. Wizard. | Wizard proceeds; project name derived from directory name when gh/`git log` info unavailable. | integration |
| TC-118 | Install on detached HEAD | 1. `git checkout <sha>` detached. 2. Wizard. | Wizard errors with clear message: "Run setup from a named branch". Exit 1. | integration |
| TC-119 | Install with dirty worktree | 1. Uncommitted modifications. 2. Wizard. | Wizard errors or auto-commits seed files (per #321 fix pattern). Clear message either way. | integration |
| TC-120 | Intent free-text empty | 1. Step 2. 2. Submit empty text. | Wizard re-prompts. | unit |
| TC-121 | Intent in non-English | 1. Step 2. 2. Answer in Spanish: "Quiero construir una aplicación web". | LLM classifies correctly as software-dev. Step 3 proposes software-dev. | integration |
| TC-122 | Dev preset + "skip tests" → empty test commands | 1. software-dev + be-only. 2. dev.stack: "no tests". | dev.stack recorded as empty / no test command. config.md has empty test_command for be. Agent skips test step in its cycle. | integration |
| TC-123 | "back" returns to previous step | 1. Any step > 1. 2. Type `back` or equivalent. | Wizard returns to previous step with prior state intact. | integration |
| TC-124 | Network blip during Step 7 push → retry | 1. Induce `git push` failure (network blip). 2. Wizard Step 7. | Wizard retries push. On eventual success, continues. | integration |
| TC-125 | Push fails due to gh permission — clear error | 1. Remove gh write permission for test repo. 2. Wizard Step 7. | Wizard prints clear permission error. Local files still written (not lost). User can fix permission and re-run just the push. | integration |
| TC-126 | Installer crashes mid-Step-7 | 1. Complete Step 6. 2. Force-kill installer during file writes. | On re-run, wizard detects partial `.squidsquad/` (Step 0b), surfaces three-way prompt. Full rebuild cleanly recovers. No orphaned partial files break the second run. | integration |

## Smoke Tests (fast gate before Pending Test — target < 5 min total)

- [ ] **ST-1** All 5 v1 role manifests load without validation errors: `python references/scripts/manifest.py validate references/roles/`
- [ ] **ST-2** All 4 v1 tool manifests load without validation errors: `python references/scripts/manifest.py validate references/tools/`
- [ ] **ST-3** Both preset manifests load without validation errors: `python references/scripts/manifest.py validate references/presets/`
- [ ] **ST-4** Fresh install on a clean scratch repo with software-dev + be+fe + designer=yes completes successfully and disposes (TC-01 abbreviated).
- [ ] **ST-5** Wizard walks Step 4 for both presets without crashing (software-dev collects designer + dev + qa requirements; design collects designer only).
- [ ] **ST-6** Status migration script runs cleanly on a repo with one `status:pending` issue and is idempotent on second run (TC-80 abbreviated).
- [ ] **ST-7** Installer exits cleanly — no hanging process, exit code 0, "SquidSquad ready" message printed.
- [ ] **ST-8** `gh label list` after install shows `status:pending-human-approval`, `status:pending-human-review`, `status:pending-human-setup`, and does NOT show bare `status:pending`.
- [ ] **ST-9** `.squidsquad/designer/CLAUDE.md` exists and does NOT contain any figma/stitch/html sub-skill content.
- [ ] **ST-10** Pipeline resolver unit test suite (TC-70 through TC-77) passes.

## Coverage Matrix (locked decisions → TCs)

| Locked Decision | Covered by |
|-----------------|-----------|
| LD1 Single feature | All TCs (feature ships as one) |
| LD2 PM always installed | TC-01..TC-05 (every happy path) |
| LD3 DM always installed | TC-01..TC-05 |
| LD4 SS-defined roles v1 | TC-18, TC-20 |
| LD5 Two presets | TC-01..TC-05 |
| LD6 YAML sidecar manifests | TC-10..TC-20 |
| LD7 Decentralized routes_to | TC-70..TC-78 |
| LD8 gh mandatory | TC-21..TC-23 |
| LD9 Conditional dev question | TC-05 (no dev question in design) |
| LD10 Install base = this repo | TC-64, TC-65, TC-112 |
| Q1 DM universal terminal | TC-76 |
| Q2 schema_version | TC-10, TC-11 |
| Q3 Dev manifest shape | TC-41, TC-42, TC-43 |
| Q4 be+fe default | TC-01, TC-41 |
| Q5 PM→DM collapse hint | TC-77 |
| Q6 custom-builder deferred | Out of scope (not tested) |
| Q7 HITL designer | TC-99, TC-83, TC-84 |
| Q8 re-run 3-way | TC-24..TC-28 |
| Q9 LLM intent classifier | TC-32..TC-34, TC-121 |
| Q10 ASCII arrow display | TC-70..TC-75, TC-53 |
| Q-new1 requires_tools | TC-16, TC-20 |
| Q-new3 designer tools | TC-93, TC-94 (runtime) |
| Q-new4 status taxonomy | TC-63..TC-66, TC-79..TC-89 |
| Q-new5 tool registry | TC-14, TC-18 |
| Q-new6 setup walkthroughs | TC-93 |
| Q-new7 LLM stack detect | TC-45, TC-46 |
| Q-new11 lazy tool setup | TC-90..TC-97 |
| Q-new12 human↔worker direct | TC-99..TC-101 |
| Q-new13 declarative requirements | TC-39, TC-40, TC-43..TC-48 |
| Q-new14 domain-only manifests | TC-13 |
| Q-new15 roster | TC-31, TC-35 |
| Q-new16 preset manifests | TC-15, TC-39, TC-40 |
| Q-new17 config.md schema | TC-06, TC-61 |
| Q-new18 hardcoded intent prompt | TC-32..TC-34 (behavioral) |
| Q-new19 single-conversation per-agent | TC-43, TC-44 |
| Q-new20 feature-triggered tool scan | TC-90, TC-91 |
| Q-new21 installer ephemeral | TC-08, TC-68 |
| Q-new9 review screen | TC-53..TC-60, TC-102..TC-106 |
| Q-new10 designer before dev | TC-39 |

## Regression Risks

1. **PM CLAUDE.md rewrites** — 11+ hardcoded role references in PM's template must all continue to work. Risk: one of them silently degrades (e.g., "route to dev" logic breaks when only designer installed). Mitigation: TC-108 full cycle test covers PM in a software-dev install; extend with design-preset PM cycle if time permits.
2. **compose.py dispatch table** — switching from hardcoded dict to manifest lookup could break CLAUDE.md generation for a role missing a manifest field. Mitigation: TC-115 smoke test deploys every role.
3. **config.py FIELD_MAP generalization** — existing callers reading `dev-agents` / `alias-*` / `skill-tests` may break if the new API isn't backward compatible. Mitigation: audit all call sites before merging; TC-108 exercises the full agent cycle.
4. **Status label migration** — if migration script fails partway, repo ends up with mixed old/new labels. Mitigation: TC-64, TC-65, TC-79, TC-80 cover the happy path and idempotency. Consider a "dry-run" mode.
5. **statusline.sh** reading roles — if it still hardcodes role list, design preset will show non-existent agents. Mitigation: TC-116.
6. **tracker.py FEEDBACK_ROLES** stays hardcoded — document in manifest schema notes. No test needed (closed set).
7. **Tool sub-skill composition anchor** — CLAUDE.md templates must include the anchor comment for PM to compose into later. If missing, PM's runtime composition breaks. Mitigation: TC-07, TC-62 confirm anchor exists at install time; TC-93, TC-94 confirm PM's runtime composition works.
8. **Full rebuild data loss** — Step 0b option 3 deletes vault, iteration logs, working state. Risk: user picks option 3 without realizing consequences. Mitigation: TC-28 typed confirmation + TC-59 deletion warning on review.
9. **`/squidsquad-upgrade` not modified** — out of scope per TC-114, but if upgrade re-reads the old config.md format, it may break after #328. Mitigation: TC-114 regression smoke.
10. **Mid-install crash partial state** — TC-126 covers recovery. Risk: if the wizard writes some files before Step 7 finishes, next run's Step 0b sees partial install. Relies on Step 0b three-way prompt being robust.

## Out of Scope (NOT tested in this plan)

- User-defined custom role manifests (v2 feature)
- Third preset beyond software-dev / design (v2)
- DM delivery tools beyond `local_delivery` (gmail, slack, google_drive deferred)
- PM/dev/qa tool definitions beyond registry structure (deferred)
- Custom-builder wizard mode (v2)
- Auto-boot of PM after install (handled by #4)
- `/squidsquad-upgrade` internal behavior (not modified by #328)
- External install base migration (no external installs exist)
- LLM intent classifier running outside Claude (not supported)
