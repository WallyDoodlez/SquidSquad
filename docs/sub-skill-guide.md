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

```
references/sub-skills/
├── manifest.md          ← composition rules (which sub-skills each role gets)
├── common/              ← shared by multiple roles
│   ├── pull-latest.md
│   ├── tracker-protocol.md
│   ├── vault-protocol.md
│   ├── vault-remember.md
│   └── ...
├── roles/               ← entry files (one per agent type)
│   ├── dev-agent.md
│   ├── pm-agent.md
│   ├── qa-agent.md
│   ├── dm-agent.md
│   └── designer.md
├── souls/               ← agent personalities
│   ├── dev.md
│   ├── pm.md
│   └── ...
├── pm-specific/         ← PM-only behaviors
├── qa-specific/         ← QA-only behaviors
├── dm-specific/         ← DM-only behaviors
└── designer-specific/   ← Designer-only behaviors
```

**Common** sub-skills are shared across multiple agent roles. **Role-specific** sub-skills belong to one role. **Souls** define each role's personality.

---

## How Composition Works

### Entry Files

Each agent role has an **entry file** in `roles/` that defines the template skeleton using `{{include}}` directives:

```markdown
{{runtime: souls/dev}}

# SquidSquad — [ROLE] Lead

You are the [ROLE] Lead on the SquidSquad autonomous dev team...

---

{{include: common/tracker-protocol}}

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
{{runtime: relative/path}}
```

Unlike `{{include:}}` which compiles content into the template at build time, `{{runtime:}}` copies the file to `.squidsquad/[role]/` for loading at session start. This is used for content that should be editable without redeploying templates — most notably SOUL.md personality files.

- Path is relative to `references/sub-skills/`
- The file is copied to `.squidsquad/[role]/SOUL.md` during `compose.py deploy`
- Changes to the runtime file take effect on next agent boot without recomposing
- Typically used at the top of an entry file: `{{runtime: souls/dev}}`

### Build Pipeline

```
references/sub-skills/roles/dev-agent.md     (entry file with {{include}} directives)
        │
        ▼  compose.py compose
references/agent-instructions.md             (all includes resolved, section markers added)
        │
        ▼  compose.py deploy <role>
.squidsquad/<role>/CLAUDE.md                 (placeholders substituted with config values)
```

Run composition:
```bash
# Compose all entry files into agent-instructions.md
python references/scripts/compose.py compose

# Deploy a specific role (compose + substitute placeholders + write CLAUDE.md)
python references/scripts/compose.py deploy <role>
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
| `[ROLE]` | Dev templates only | Role name (e.g. `skill`, `fe`) |
| `[ROLE_UPPER]` | Dev templates only | Uppercase role (e.g. `SKILL`) |
| `[ROLE_TEST_CMD]` | Dev templates only | Test command from config |
| `[OTHER_ROLES]` | Dev templates only | Other dev role names |
| `[INTERVAL]` | All templates | Loop interval in minutes |
| `[ACTIVE_AGENTS]` | PM, DM templates | List of active dev agents |
| `[E2E_TEST_CMD]` | PM templates | E2E test command |

**Important**: In PM and DM templates, `[ROLE]` is NOT substituted — it's used as a variable meaning "any dev agent's role." This is why some common sub-skills (like `context-pressure.md`) are only shared with dev agents. PM and DM inline those behaviors with hardcoded paths.

---

## The Manifest

`references/sub-skills/manifest.md` documents the composition order for every role. When adding a new sub-skill, update the manifest to show where it appears in each role's include chain.

The manifest is the source of truth for what each agent template contains.

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

- **Common** (`common/`): If 2+ roles need this behavior
- **Role-specific** (`[role]-specific/`): If only one role uses it
- **Soul** (`souls/`): If it defines personality/communication style

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

Edit the entry file(s) in `roles/` to include your sub-skill at the right position:

```markdown
{{include: common/your-new-skill}}
```

### Step 5 — Update the manifest

Add your sub-skill to the composition order in `manifest.md` for each role that includes it.

### Step 6 — Test composition

```bash
# Compose and check for errors
python references/scripts/compose.py compose

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

It's included by every role via the manifest:
```
7b. `common/vault-remember` — Step 4b: end-of-cycle vault reflection
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
- **Test with `compose.py compose`** — catch include errors before deploying.
- **Check the manifest** — if your sub-skill isn't in the manifest, it won't be composed.
- **Use section markers** — they power the status bar and make debugging easier.
- **Mind the `[ROLE]` ambiguity** — common sub-skills that reference `[ROLE]` paths only work in dev templates. PM and DM must inline those sections.
