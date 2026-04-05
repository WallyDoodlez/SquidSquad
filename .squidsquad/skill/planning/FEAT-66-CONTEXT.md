# FEAT-66 Context — Deterministic Script Layer

## Locked Decisions

### 1. Script Location
**Decision**: `references/scripts/` — copied to project repo during setup (like statusline.sh).
**Rationale**: Consistent with existing reference file pattern.

### 2. Language & Version
**Decision**: Python 3.8+, standard library only. Zero external dependencies.
**Rationale**: Cross-platform, readable, no install step beyond Python itself.

### 3. Discussion Comment Timestamps — REMOVED
**Decision**: Do NOT inject timestamps into GH Issue comments. GitHub already timestamps every comment natively. The `> [YYYY-MM-DD HH:MM] **role**: message` format is redundant — simplify to `> **role**: message`.
**Rationale**: Human insight — "GH already creates a timestamp on the comment. The timestamp is really just important for in-chat status messages."
**Impact**: `tracker.py comment` just formats `> **{role}**: {message}`. All Discussion protocol sub-skills simplified. Timestamp generation (`cycle.py timestamp`) only needed for in-chat `[🦑 HH:MM:SS]` step markers.

### 4. CLI Flags
**Decision**: All scripts support `--help` and `--dry-run`. `--dry-run` prints what would execute without doing it.
**Rationale**: Essential for debugging and agent transparency.

### 5. Status Flow Enforcement — Pessimistic
**Decision**: `tracker.py transition` enforces the full valid status flow. Invalid transitions are rejected with an error showing valid next states.
**Valid transitions**:
```
pending → planning → planned → approved → in-progress → pending-test → pending-ship → shipped
                                                    ↑                          |
                                                    └── (QA rejection) ────────┘
pending → approved  (bugs skip planning)
open → approved     (bugs from open)
```
Transition attempts outside this graph return exit code 1 with message: `"Invalid transition: {from} → {to}. Valid next states from {from}: [{list}]"`
**Rationale**: "Pessimistic optimism" — prevent agents from skipping states, which has caused stale label bugs repeatedly.

### 6. Testing Required Before Ship
**Decision**: All scripts must have tests (`scripts/test_scripts.py` using unittest). Tests must pass before the feature ships. No compromise on quality.
**Rationale**: These scripts become the single source of truth for all mechanical operations. A bug in a script affects every agent.

## Migration Phases

### Phase 1: Foundation (config.py + cycle.py + tracker.py)
- Highest value — covers 72 of 98 invocation sites
- `config.py`: read/write config.md values
- `cycle.py`: timestamps, working state, iteration logs, scan history, atomic writes
- `tracker.py`: all GH Issues operations with correct labels, status flow enforcement

### Phase 2: Git Operations (git_ops.py)
- Pull, commit, push, branch, tag, PR creation
- 18 invocation sites

### Phase 3: Vault (vault_check.py)
- Frontmatter validation, wikilink resolution, orphan/stale detection
- 8 invocation sites, lowest frequency

## Side Effects & Mitigations

- **Sub-skill rewrite**: Every sub-skill with mechanical operations gets rewritten to call scripts. Prose stays for reasoning.
- **agent-instructions.md regeneration**: Must be regenerated after sub-skill updates.
- **Discussion protocol change**: All role discussion-protocol sub-skills simplified (no more timestamp in comment body).
- **statusline.sh**: Unaffected — reads the same files scripts write.
- **Python availability**: Setup checks for Python 3. If missing, warns but allows prose-only fallback during transition.

## Dev Discretion Areas

- Internal module structure within each script (classes vs functions)
- Error message wording
- Exact argparse parameter names (as long as interface is clear)
- Whether to use a shared base module or keep scripts independent
