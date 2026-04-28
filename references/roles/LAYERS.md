# Layered Role Architecture

Role definitions compose from 3 layers, assembled at deploy time into flat files.

## Layer Stack

```
Layer 1: Base Agent (references/roles/base/)
├── SOUL.md — shared identity (timestamps, atomic writes, quality gate)
│
├── Layer 2: General Role (references/roles/general/<category>/)
│   ├── developer/SOUL.md — code-change protocol, PR conventions
│   ├── coordinator/SOUL.md — pipeline oversight, human check-in
│   ├── verifier/SOUL.md — zero-gap gate, coverage requirements
│   └── delivery/SOUL.md — user-first protocol, delivery quality
│
└── Layer 3: Specific Role (references/roles/<role>/)
    ├── SOUL.md — role personality, boundaries, improvement scan
    ├── CLAUDE.md — entry template with {{include:}} directives
    ├── includes.yml — sub-skill composition manifest
    └── manifest.yaml — role metadata (general_role field maps to L2)
```

## How It Works

- `compose.py deploy <role>` assembles SOUL.md: L1 + L2 + L3 → flat file
- Layer markers (`<!-- layer: base -->`, `<!-- layer: general-role -->`) embedded for upgrade
- `compose.py upgrade-soul <role>` re-renders L1+L2, preserves L3 + Project Adaptation
- Dev variants (skill, be, fe) inherit `general_role` from `dev/manifest.yaml`
- PM has dual L2: `general_role: [coordinator, verifier]`

## Adding a New Role

1. Create `references/roles/<name>/CLAUDE.md`, `SOUL.md`, `includes.yml`, `manifest.yaml`
2. Set `general_role` in manifest.yaml to inherit Layer 2 identity
3. Run `compose.py deploy <name>` — Layer 1 + Layer 2 are injected automatically
