# FEAT-67 Context — Integration Test Framework

## Locked Decisions

### 1. Two-Layer Testing Architecture
**Decision**: SquidSquad has two separate test layers:
- **Project Tests**: Target project's own tests (Vitest, pytest, Cargo test, etc.) — configured in config.md, run by dev agent on code changes
- **Skill Tests**: SquidSquad self-tests that validate skill infrastructure (labels, references, composition, config) — run by skill-lead on sub-skill/template changes

These are independent. Skill tests ship with SquidSquad and work on any repo.

### 2. Test Framework: pytest
**Decision**: pytest for skill self-tests. Listed in `requirements-dev.txt`.
**Rationale**: pytest is a DEV dependency for developing SquidSquad, not a USER dependency for using it. Users applying SquidSquad to their repo have zero extra dependencies. Developers working on the skill itself need pytest — same as any project needing test tools.

### 3. Phasing
**Decision**:
- **Phase 1 (this feature)**: Static analysis only — reads files, no GH/git side effects, no cleanup needed. Catches ~85% of historical bugs.
- **Phase 2 (after #66 script layer)**: GH Issues integration tests with `[TEST]` prefix + teardown fixtures.

### 4. Test Location
**Decision**: `tests/` at repo root. Ships with the skill.
```
tests/
├── conftest.py              # Shared fixtures (paths, file loaders)
├── test_labels.py           # Label consistency
├── test_references.py       # Stale reference detection
├── test_manifest.py         # Manifest vs filesystem
├── test_composition.py      # agent-instructions.md sync
├── test_config.py           # config.md validation
├── test_roles.py            # Role completeness
├── test_vault.py            # Vault structure
├── integration/             # Phase 2 (after #66)
│   ├── conftest.py          # GH Issues fixtures + cleanup
│   ├── test_gh_issues.py
│   └── test_git_ops.py
└── README.md
```

### 5. Config Update
**Decision**: Two test commands in config.md:
```
- **Project Tests**: [target project command, e.g. npm test]
- **Skill Tests**: python -m pytest tests/ --ignore=tests/integration/ -q
```
Dev agent runs project tests on code changes. Skill-lead runs skill tests on sub-skill/template changes.

### 6. No User-Facing Dependencies
**Decision**: Using SquidSquad adds zero dependencies beyond gh CLI + git. pytest is a dev dependency only (in `requirements-dev.txt`), needed only when developing/testing the skill itself.

### 7. Generic Framework
**Decision**: Skill self-tests validate SquidSquad's own files (sub-skills, labels, composition, config), NOT the target project's code. They work on any repo because they test skill infrastructure. Target project testing uses whatever framework the project already has.

## Side Effects & Mitigations

- **config.md**: Add `Skill Tests` field alongside existing `Project Tests`
- **Dev agent template**: Add "run skill tests before marking Pending Test" step when sub-skill files are modified
- **requirements-dev.txt**: New file at repo root with `pytest`
- **Setup flow**: No changes for users. Dev setup adds `pip install -r requirements-dev.txt`

## Dev Discretion Areas

- Test helper functions and fixture organization
- Exact regex patterns for stale reference detection
- How many assertion messages to include per test
- Whether to use pytest markers for test categories
