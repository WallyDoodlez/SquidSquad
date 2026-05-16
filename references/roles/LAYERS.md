# Layered Role Architecture

Role definitions compose from 4 layers. The directory depth IS the layer.

## Directory Structure

```
references/roles/
├── instructions.md              ← Layer 1 (base agent definition)
├── SOUL.md                      ← Layer 1 (base agent identity)
├── dev/                         ← Layer 2 (role definition)
│   ├── instructions.md
│   ├── SOUL.md
│   ├── includes.yml
│   ├── manifest.yaml
│   └── skill/                   ← Layer 3 (domain variant)
│       ├── instructions.md
│       ├── SOUL.md
│       └── includes.yml

.squidsquad/<agent>/             ← Layer 4 (project-specific)
├── CLAUDE.md                       (deployed — L1+L2+L3 assembled)
├── SOUL.md                         (deployed — L1+L2/L3 assembled + Project Adaptation)
└── role-adaptations.md             (project signals detected by soul-shepherd)
```

## The 4 Layers

| Layer | Location | What it defines | Who maintains it |
|-------|----------|-----------------|------------------|
| **L1 — Agent** | `roles/` root | What ANY SquidSquad agent is | SquidSquad core |
| **L2 — Role** | `roles/<role>/` | What a dev/pm/qa/dm IS | SquidSquad core |
| **L3 — Domain** | `roles/<role>/<variant>/` | Domain specialization (iOS, web, skill) | Preset authors |
| **L4 — Project** | `.squidsquad/<agent>/` | Project-specific adaptations | soul-shepherd + human |

## How Layers Compose

**Horizontal scaling**: Add more roles (L2) or domain variants (L3) without touching existing layers.

**Vertical scaling**: Each layer adds depth without modifying layers above or below it.

**SOUL.md**: L1 base + L2/L3 role SOUL → flat file. L4 Project Adaptation section is appended by soul_adaptation.py at runtime.

**instructions.md → CLAUDE.md**: L1 + L2 + L3 assembled, includes resolved → deployed as `.squidsquad/<agent>/CLAUDE.md`.

**Naming**: Agent instance `dev-skill` maps to `roles/dev/skill/`. compose.py splits on hyphen.

## Adding a New Role (Layer 2)

1. Create `references/roles/<name>/instructions.md`, `SOUL.md`, `includes.yml`, `manifest.yaml`
2. Run `compose.py deploy <name>`

## Adding a New Variant (Layer 3)

1. Create `references/roles/<base>/<variant>/` with `instructions.md`, `SOUL.md`, `includes.yml`
2. Create variant sub-skills in `references/sub-skills/roles/<base>/<variant>/`
3. Run `compose.py deploy <base>-<variant>`

## Project Adaptation (Layer 4)

Layer 4 has two channels:

### Automatic: Soul Shepherd (SOUL.md)
As PM's soul-shepherd detects project signals (tech stack, domain vocabulary, quality preferences), it adds them to `role-adaptations.md`. soul_adaptation.py renders these into the `## Project Adaptation` section of deployed SOUL.md. No manual setup needed — L4 grows organically.

### Manual: Project Sub-Skills (CLAUDE.md)
PM can push behavioral sub-skills to ALL agents without a dev cycle:

1. Write sub-skills to `references/sub-skills/project/*.md` (standard sub-skill format with `<!-- sub-skill: name -->` markers)
2. Run `python references/scripts/compose.py deploy-all`
3. Reboot affected agents (`python references/scripts/start_team.py --reboot --all`)

Project sub-skills are auto-included in every agent's CLAUDE.md during assembly — same composition mechanism as all other sub-skills. PM owns this directory directly — no task filing, no QA verification needed. Use for project-wide rules, constraints, or behavioral adjustments that apply to the entire team.
