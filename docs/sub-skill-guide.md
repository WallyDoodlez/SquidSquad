# Sub-Skill Developer Guide

This guide explains how to create, test, and contribute sub-skills for SquidSquad.

---

## What is a Sub-Skill?

A sub-skill is a markdown file that defines a specific behavior for SquidSquad agents. Sub-skills are composed together at build time to create complete agent instruction templates.

For example, `pull-latest.md` defines how agents sync with git:

```markdown
### Step 1 — Pull Latest

Print: `[🦑 HH:MM:SS] Pulling latest...`

` ``bash
python references/scripts/git_ops.py pull
` ``

The script handles stash/pop automatically if there are unstaged changes.
```

Sub-skills are plain markdown with optional section markers. No special syntax beyond the `{{include}}` directive (used in entry files, not sub-skills themselves).

---

## Where Sub-Skills Live

Sub-skill fragments live under `references/sub-skills/` and role entry files live under `references/roles/<role>/` (self-contained role directories):

```
references/
├── sub-skills/
│   ├── manifest.md          ← composition reference doc (documents include order)
│   ├── common/              ← shared by multiple roles
│   │   ├── pull-latest.md
│   │   ├── vault-protocol.md
│   │   ├── vault-remember.md
│   │   └── ...
│   ├── roles/               ← role-specific behaviors
│   │   ├── pm/              ← PM-only behaviors
│   │   ├── qa/              ← QA-only behaviors
│   │   ├── dm/              ← DM-only behaviors
│   │   └── dev/             ← Dev-only behaviors
│   ├── capabilities/        ← optional add-on behaviors (figma, google_stitch, local_delivery, local_html, etc.) with {manifest.yaml, setup.md, sub-skill.md}
│   └── project/             ← per-project overrides (shared + per-role instructions/soul-directives)
│
└── roles/                   ← one self-contained directory per role
    ├── dev/
    │   ├── instructions.md  ← entry file with {{include}} directives
    │   ├── SOUL.md          ← personality template (deployed to .squidsquad/<role>/SOUL.md)
    │   └── manifest.yaml
    ├── pm/
    ├── qa/
    └── dm/
```

**Common** sub-skills are shared across multiple agent roles. **Role-specific** sub-skills belong to one role. **SOUL.md** files (one per role, alongside the role's `instructions.md`) define each role's personality.

---

## How Composition Works

### Entry Files

Each agent role has an **entry file** at `references/roles/<role>/instructions.md` that defines the template skeleton using `{{include}}` directives:

```markdown
{{runtime: souls/dev}}

# SquidSquad — [ROLE] Lead

You are the [ROLE] Lead on the SquidSquad autonomous dev team...

---

{{include: common/vault-protocol}}

---

## On Startup
...

{{include: common/pull-latest}}

{{include: common/context-pressure}}
```

### The Include Directive

```
{{include: relative/path}}
```

- Path is relative to `references/sub-skills/`
- `.md` extension is omitted
- Each resolved include is wrapped with section markers: `<!-- sub-skill: name -->`
- Directives must appear on their own line

### The Runtime Directive

```
{{runtime: souls/<role>}}
```

Unlike `{{include:}}` which compiles content into the template at build time, `{{runtime:}}` emits a "read at session start" instruction that tells the agent to load its personality from `.squidsquad/<role>/SOUL.md` at boot. This is used for content that should be editable without redeploying templates — most notably SOUL.md personality files.

- The `souls/<role>` argument is a symbolic marker name (used for section-marker generation); it is not resolved to a file during composition.
- SOUL.md is **assembled** from Layer 1 base (`references/roles/SOUL.md`) + role-specific SOUL (`references/roles/<role>/SOUL.md`) during `compose.py deploy` (only if no local SOUL.md already exists — agent customisations are preserved).
- Changes to `.squidsquad/<role>/SOUL.md` take effect on next agent boot without recomposing.
- Typically used at the top of an entry file: `{{runtime: souls/dev}}`.

### Build Pipeline

```
references/roles/<role>/instructions.md   (entry file with {{include}} directives)
        │
        ▼  compose.py all
references/agent-instructions.md         (all includes resolved, section markers added)
        │
        ▼  compose.py deploy <role>
.squidsquad/<role>/CLAUDE.md             (placeholders substituted with config values)
                                          + .squidsquad/<role>/SOUL.md (assembled from
                                            Layer 1 base + role SOUL.md if missing)
```

Run composition:
```bash
# Compose the dev entry file into agent-instructions.md
python references/scripts/compose.py all

# Deploy a specific role (compose + substitute placeholders + write CLAUDE.md)
python references/scripts/compose.py deploy <role>

# Deploy every configured role at once
python references/scripts/compose.py deploy-all
```

### Section Markers

After composition, each included sub-skill is wrapped with HTML comment markers:

```html
<!-- sub-skill: pull-latest -->
### Step 1 — Pull Latest
...
<!-- /sub-skill: pull-latest -->
```

These markers serve two purposes:
1. The status bar reads the active sub-skill name for display
2. Developers can find where a sub-skill's content appears in the composed output

---

## Placeholders

After includes are resolved, placeholders are substituted with values from `config.md`:

| Placeholder | Used in | Substituted with |
|-------------|---------|-----------------|
| `[ROLE]` | All templates | Role name (e.g. `skill`, `dm`) |
| `[ROLE_UPPER]` | All templates | Uppercase role (e.g. `SKILL`, `DM`) |
| `[ROLE_TEST_CMD]` | Dev templates only | Test command from config |
| `[OTHER_ROLES]` | Dev templates only | Other dev role names |
| `[INTERVAL]` | All templates | Loop interval in minutes |
| `[ACTIVE_AGENTS]` | PM, QA, DM templates | List of active dev agents |
| `[E2E_TEST_CMD]` | PM templates | E2E test command |

**Important**: `[ROLE]` and `[ROLE_UPPER]` are substituted for ALL roles (needed by shared sub-skills like `cycle-runner.md`). `[ROLE_TEST_CMD]` and `[OTHER_ROLES]` are dev-only — PM, QA, and DM do not use them.

---

## The Manifest and Includes

Each role's composition order is defined in `references/roles/<role>/includes.yml` — this is the **source of truth** that `compose.py` reads when building templates. `references/sub-skills/manifest.md` is a reference document that mirrors these include orders for human readability.

When adding a new sub-skill, update the role's `includes.yml` to add it at the right position, and optionally update `manifest.md` to keep the reference doc in sync.

---

## Creating a New Sub-Skill

### Step 1 — Decide the scope

A sub-skill should be a single, focused behavior. Good examples:
- `pull-latest.md` — one step: sync with git
- `vault-remember.md` — one step: end-of-cycle reflection
- `bug-triage.md` — one step: find and fix bugs

Bad examples:
- A sub-skill that does both bug triage AND feature implementation (too broad)
- A sub-skill with one line of text (too narrow — just inline it)

### Step 2 — Choose the location

- **Common** (`references/sub-skills/common/`): If 2+ roles need this behavior
- **Role-specific** (`references/sub-skills/roles/[role]/`): If only one role uses it
- **Soul** (`references/roles/<role>/SOUL.md`): Personality/communication style — edit the role's SOUL.md template directly (not a sub-skill fragment)

### Step 3 — Write the sub-skill

Create a new `.md` file. Follow the style of existing sub-skills:

```markdown
### Step N — Your Step Name

Print: `[🦑 HH:MM:SS] Doing the thing...`

Description of what this step does and why.

` ``bash
# Commands the agent should run
python references/scripts/your_script.py
` ``

Rules:
- Specific constraints or behaviors
- Error handling expectations
```

### Step 4 — Add the include directive

Edit the entry file(s) at `references/roles/<role>/instructions.md` to include your sub-skill at the right position:

```markdown
{{include: common/your-new-skill}}
```

### Step 5 — Update includes.yml

Add your sub-skill to `references/roles/<role>/includes.yml` for each role that should include it. Optionally update `manifest.md` to keep the reference doc in sync.

### Step 6 — Test composition

```bash
# Compose and check for errors
python references/scripts/compose.py all

# Verify section markers appear correctly
grep "sub-skill: your-new-skill" references/agent-instructions.md

# Run composition tests
python tests/run_tests.py
```

### Step 7 — Deploy and verify

```bash
# Deploy to a specific role
python references/scripts/compose.py deploy <role>

# Check the output
cat .squidsquad/<role>/CLAUDE.md
```

---

## Walkthrough: vault-remember

`common/vault-remember.md` is a good example of a well-structured common sub-skill. Here's what it does:

1. **Config gate**: Checks if vault-remember is enabled
2. **Quiet-cycle gate**: Skips if no real work was done this cycle
3. **Reflection prompt**: Reviews the cycle and evaluates 5 categories (decisions, patterns, learnings, human preferences, project context)
4. **Write budget**: Limits vault writes per cycle to prevent noise
5. **Dedup check**: Avoids writing notes that duplicate existing vault content

It's included by dev and PM roles via their `includes.yml`:
```
  - common/vault-remember
```

The sub-skill uses Python scripts for deterministic gates (`vault_remember.py`) rather than relying on the agent to self-regulate. This is a good pattern — use scripts for anything that needs to be reliable.

---

## Contributing Sub-Skills

Sub-skills in this repo are part of SquidSquad's core behavior. To contribute:

1. Fork the repo
2. Create your sub-skill following this guide
3. Run `python tests/run_tests.py` to verify composition
4. Open a PR with a clear description of what the sub-skill does and which roles use it

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full contribution process.

---

## Tips

- **Keep sub-skills atomic** — one behavior per file. If it's doing two things, split it.
- **Use Python scripts for gates** — don't rely on the agent to remember thresholds or limits. Scripts are deterministic.
- **Test with `compose.py all`** — catch include errors before deploying.
- **Check includes.yml** — if your sub-skill isn't in the role's `includes.yml`, it won't be composed. Update `manifest.md` too to keep the reference doc in sync.
- **Use section markers** — they power the status bar and make debugging easier.
- **Mind the dev-only placeholders** — `[ROLE_TEST_CMD]` and `[OTHER_ROLES]` are only substituted in dev templates. Common sub-skills using `[ROLE]` or `[ROLE_UPPER]` work for all roles.
