# DS-fallback review — Iter 32 (G5 close)

## Verdict: PASS-WITH-WARNINGS

## Findings

### F1 — Catalog "used by" columns stale for resume-working-state and interval-sync [WARNING]

`docs/sub-skill-catalog.md` lines 107–108 still list both sub-skills as used by `worker` only:

```
| `resume-working-state` | ... | worker |
| `interval-sync`        | ... | worker |
```

Iter 32 wires both into DM (`references/roles/dm/instructions.md` L26) and verifier (`references/roles/verifier/instructions.md` L22), making the catalog entries factually wrong post-commit. Iter 38 fixed the adjacent `working-state` row (L120, "worker" → "all roles") but did NOT touch these two rows.

A stale "used by" column does not break runtime — agents resolve via name-to-path mapping, not the "used by" column. But it misleads any future author doing blast-radius analysis ("is it safe to change interval-sync? catalog says worker-only…"). Recommend updating both rows to `PM, verifier, DM, worker` in a follow-up.

---

### F2 — interval-sync sub-skill reads config via script; L2 read config.md prose directly [INFO]

The removed L2 block read the interval by parsing `.squidsquad/config.md` prose directly:
> `Read 'Iteration Interval > Minutes' from .squidsquad/config.md`

The replacement sub-skill (`references/sub-skills/common/interval-sync.md` line 9) reads it via:
```bash
python references/scripts/config.py get interval
```

This is strictly better — the script call is the canonical read path and is less brittle than manual prose-parsing. Not a regression; flagged for audit completeness only. No action required.

---

### F3 — Step-cycle ordering preserved across all four composed files [INFO]

Post-strip order in both DM and verifier composed CLAUDE.md:
`context-pressure → resume-working-state → interval-sync → role-specific sub-skills (issue-triage/delivery-packaging for DM; verification for verifier)`

Verified against `.squidsquad/dm/CLAUDE.md` lines 502–514 and `.squidsquad/qa/CLAUDE.md` lines 510–517. Order is correct and consistent with the requirement.

---

### F4 — [ROLE] substitution is now runtime-only; compose-time path is gone [INFO]

`resume-working-state.md` line 10 contains `[ROLE]` (`.squidsquad/[ROLE]/working-state.md`). Because these are now lazy-loaded at runtime via `→ run sub-skill:` markers, compose-time placeholder substitution does NOT fire on them — the agent must substitute `[ROLE]` itself at runtime.

The agent is expected to do this per the "Placeholder substitution inside runtime-loaded fragments" section of the composed CLAUDE.md (which explicitly covers `[ROLE]`). Architecturally correct for v2-path sub-skills. No regression, but the contract is implicit: the removed L2 content was unambiguous after compose (DM got `[DM_ALIAS]`-resolved path, verifier got `verifier`-literal path). The sub-skill shifts that resolution to agent runtime reasoning. Acceptable given the explicit runtime-substitution instruction.

---

### F5 — Behavior preservation: sub-skill content is richer on all substantive dimensions [INFO]

Comparison of removed DM L2 vs sub-skill body:

| Aspect | Removed L2 | Sub-skill |
|---|---|---|
| Print on check | yes | yes |
| Print on resume | no | yes — added `Resuming [TASK_ID]...` |
| Read task ID + completed/remaining steps | implicit ("resume that work") | explicit enumeration |
| Instruction to skip re-analysis of understood code | no | yes ("trust the working state summary") |
| Interval read method | raw prose parse of config.md | `config.py get interval` script call |
| Interval re-schedule steps 1-3 | identical | identical + adds explicit cron form `*/N * * * *` |

Sub-skill bodies are a strict superset of the removed inlining. No behavioral regression on any dimension.
