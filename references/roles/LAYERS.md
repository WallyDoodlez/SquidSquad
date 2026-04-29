# Layered Role Architecture

Role definitions compose from 3 layers, assembled at deploy time into flat files.

## Layer Stack

```
Layer 1: Agent Definition (references/roles/base/)
├── SOUL.md — what any SquidSquad agent IS (professionalism, discipline, quality gate)
│
├── Layer 2: Role Definition (references/roles/<role>/)
│   ├── dev/ — engineering specialist (CLAUDE.md, SOUL.md, includes.yml, manifest.yaml)
│   ├── pm/ — project manager
│   ├── qa/ — verification specialist
│   ├── dm/ — delivery manager
│   └── designer/ — design specialist
│
└── Layer 3: Role Customization (references/roles/<base>-<variant>/)
    ├── dev-skill/, pm-skill/, qa-skill/, dm-skill/ — skill development preset
    ├── dev-ios/, pm-ios/, qa-ios/, dm-ios/ — iOS preset
    ├── dev-web/, pm-web/, qa-web/, dm-web/ — web preset
    ├── dev-android/, pm-android/, qa-android/, dm-android/ — Android preset
    └── dev-fullstack/, pm-fullstack/, qa-fullstack/, dm-fullstack/ — full-stack preset
```

## How It Works

**SOUL.md**: `compose.py deploy <role>` assembles: L1 base/SOUL.md + role SOUL.md → flat file.
For variants, the variant's own SOUL.md replaces the base role's (full file, not overlay).
Layer marker (`<!-- layer: base -->`) enables `upgrade-soul` to re-render L1 without clobbering role content.

**CLAUDE.md**: Assembled from entry template + includes.yml sub-skills.
Layer 3 variants use `includes.yml` with `base_role` + `additional_includes` schema — inherits all base role sub-skills, appends variant-specific ones.

**Naming**: `<base>-<variant>` (e.g., `pm-skill`). `compose.py` strips suffix to find base role.

## Adding a New Role (Layer 2)

1. Create `references/roles/<name>/CLAUDE.md`, `SOUL.md`, `includes.yml`, `manifest.yaml`
2. Run `compose.py deploy <name>` — Layer 1 base is prepended to SOUL.md automatically

## Adding a New Variant (Layer 3)

1. Create `references/roles/<base>-<variant>/` with:
   - `includes.yml` — `base_role: <base>` + `additional_includes: [<variant>-specific/...]`
   - `SOUL.md` — full file (copy base role's SOUL.md, add variant section)
   - `CLAUDE.md` — variant entry file with `{{include:}}` for additional sub-skills
2. Create `references/sub-skills/<base>-<variant>-specific/` with variant sub-skills
3. Run `compose.py deploy <base>-<variant>`
