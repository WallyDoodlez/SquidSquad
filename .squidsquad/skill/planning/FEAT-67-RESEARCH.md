# FEAT-67 Research — Integration Test Framework

## Summary

SquidSquad currently has ZERO automated tests. The skill-lead's test command is literally `echo "Skill repo — no automated tests. Validate SKILL.md manually."` All quality verification is performed by QA agents reading markdown files and manually checking consistency. This has resulted in 40+ bugs filed across iterations 60-97, with recurring patterns of stale references, wrong labels, inconsistent cross-references, and drift between source sub-skills and composed output.

This research catalogs the bug patterns, defines what needs testing, designs a minimal framework, and identifies quick wins that would catch the majority of recent bugs with static analysis alone (no GH/git needed).

**Recommendation**: Start with static analysis tests (pytest, ~8 test files). These require no GitHub API calls, no git operations, no cleanup. They would have caught approximately 80% of bugs #25-#65. Add integration tests (GH Issues, git ops) in Phase 2 after the script layer (#66) lands.

**Key finding**: The dominant bug class is "stale references after a migration or refactor" — the same string appears in N places, gets updated in some but not all. This is a textbook grep-based linting problem.

---

## 1. Bug Catalog — Top 5 Categories

### Methodology

Read all iteration logs (iter-60 through iter-97) and all 40+ GitHub Issues (type:bug). Categorized each bug by root cause.

### Category 1: Stale References After Migration (18 bugs, ~45%)

The single largest bug class. When a system-wide change occurs (e.g., GH Issues migration #68, QA separation #43), references in some files get updated but others are missed. The same stale string survives in less-visited files.

| Bug # | Stale Reference | Files Affected |
|-------|----------------|----------------|
| #25 | `agent-instructions.md` refs local markdown tracker | agent-instructions.md |
| #26 | SKILL.md architecture still shows local tracker dirs | SKILL.md |
| #27 | README folder structure missing DM, showing QA dir | README.md |
| #33 | SKILL.md Ralph Loop refs old markdown tracker | SKILL.md |
| #37 | SKILL.md says "PM/QA" (16 refs) after separation | SKILL.md, sub-skills |
| #42 | SKILL.md Step 2 creates obsolete tracker directories | SKILL.md |
| #47 | Vault project note has stale version/tracker refs | vault/projects/ |
| #48 | Live PM and skill CLAUDE.md still ref PM/QA | .squidsquad/pm/CLAUDE.md, .squidsquad/skill/CLAUDE.md |
| #49 | README Quick Start missing DM agent | README.md |
| #50 | README bug filing table uses bare labels | README.md |
| #53 | BRIEFING.md wrong version, old tracker refs | vault/BRIEFING.md |
| #55 | delivery-packaging.md refs markdown tracker | dm-specific/delivery-packaging.md |
| #58 | delivery-fallback.md uses pm/qa alias | pm-specific/delivery-fallback.md |
| #59 | Vault project note stale version/focus items | vault/projects/ |
| #61 | design-session.md refs features/INDEX.md | designer-specific/design-session.md |
| #62 | Vault code-conventions.md old tracker format | vault/areas/ |
| #63 | DM delivery-packaging.md refs features/INDEX.md | dm-specific/delivery-packaging.md |
| #64 | dev-agent.md uses bare `bug`/`feature` labels | roles/dev-agent.md |

**Automated test**: Grep all sub-skill files and composed output for known-stale patterns. A single test file with ~20 patterns would have caught all 18 bugs.

### Category 2: Wrong Label Names / Status Values (6 bugs, ~15%)

Labels are specified as string literals in sub-skill markdown. When the label taxonomy changes, some command examples retain the old format.

| Bug # | Wrong Label | Correct Label |
|-------|-------------|---------------|
| #32 | Non-existent status labels in Bug Flow | Correct status:* labels |
| #39 | Wrong label names in taxonomy | type:bug, type:feature |
| #40 | Missing status:planned in Feature Flow | Added planned state |
| #50 | Bare `bug`/`feature` in README | `type:bug`/`type:feature` |
| #57 | Closed issues still carry status:pending-ship | status:shipped |
| #64 | Bare `bug`/`feature` in dev-agent triage | `type:bug`/`type:feature` |

**Automated test**: Grep for bare `"bug"` or `"feature"` in `--label` arguments (must be `"type:bug"` or `"type:feature"`). Grep for `status:` values against the canonical taxonomy. Verify every `gh issue edit --remove-label/--add-label` uses valid label names.

### Category 3: Template/Composition Drift (5 bugs, ~12%)

The composed `agent-instructions.md` or live `.squidsquad/*/CLAUDE.md` files diverge from their source sub-skills. This happens when sub-skills are edited but not recomposed.

| Bug # | Description |
|-------|-------------|
| #46 | statusline.sh shows PM/QA, lacks QA branch |
| #48 | Live CLAUDE.md files have stale refs |
| #51 | DM template missing bug triage step |
| #55 | delivery-packaging.md not updated in composed output |
| #65 | Timestamp instructions inconsistent across files |

**Automated test**: Verify `agent-instructions.md` contains all sub-skill markers listed in `manifest.md`. Compare section counts. Verify all role templates reference the same label taxonomy.

### Category 4: Missing Content After Role Addition (5 bugs, ~12%)

When new roles (QA, Designer, DM) are added, existing documentation, config templates, and architecture descriptions miss the new role.

| Bug # | Missing Role |
|-------|-------------|
| #38 | Architecture diagram missing DM/Designer |
| #41 | Config template wrong version, missing fields |
| #43 | Setup doesn't handle Designer/QA creation |
| #49 | README missing DM in Quick Start |
| #54 | README Agents table missing DM |

**Automated test**: Extract role list from config.md, verify all roles appear in architecture descriptions, setup instructions, boot script references, and README sections.

### Category 5: Stale Vault / Documentation Content (6 bugs, ~15%)

Vault notes, BRIEFING.md, README, and CHANGELOG fall behind the current state.

| Bug # | Description |
|-------|-------------|
| #47 | Vault project note stale version |
| #53 | BRIEFING.md extensively stale |
| #54 | README missing DM role |
| #56 | CHANGELOG missing 6 shipped items |
| #59 | Vault project note stale version again |
| #60 | README status line refs old FEAT-XXX format |

**Automated test**: Compare version in vault notes and BRIEFING.md against config.md. Verify CHANGELOG has entries for all shipped items. Verify no FEAT-SKILL-NNN format in user-facing docs (should be #N).

---

## 2. Test Scope — What Needs Testing

### 2a. Static Analysis (no GH/git — highest ROI)

These tests read local files only. No API calls, no cleanup needed.

| Test Area | What to Check | Bug Classes Caught |
|-----------|--------------|-------------------|
| **Label consistency** | All `--label` args use `type:bug`/`type:feature` prefixes, not bare `bug`/`feature` | #32, #39, #50, #64 |
| **Stale features/INDEX.md refs** | No sub-skill references `features/INDEX.md` (replaced by `gh issue list`) | #55, #61, #63 |
| **PM/QA stale refs** | Sub-skills for separate PM use `pm` not `pm/qa` (except pm-agent.md which IS the combined template) | #37, #48, #58 |
| **Label taxonomy completeness** | All status values in sub-skills match the canonical list in tracker-protocol.md | #32, #39, #40 |
| **Agent-instructions.md sync** | Sub-skill markers in agent-instructions.md match manifest.md entries | #46, #48, #51, #55 |
| **Role completeness** | All active roles from config appear in architecture docs, README, setup | #38, #43, #49, #54 |
| **Version consistency** | Version in config.md matches vault notes, BRIEFING.md | #47, #53, #59 |
| **No FEAT-SKILL-NNN in user docs** | README, CHANGELOG use #N format, not old FEAT-SKILL-NNN | #60 |
| **Discussion alias consistency** | Each role-specific discussion-protocol.md uses correct alias | #58 |
| **Timestamp instructions** | All role templates reference `date` command for timestamps | #65 |
| **Manifest vs file system** | Every file listed in manifest.md exists on disk | Structure integrity |
| **Include directive resolution** | Every `{{include: path}}` in role entry files points to existing sub-skill | Structure integrity |

### 2b. GitHub Issues Integration Tests (Phase 2)

These require `gh` CLI and create real artifacts that must be cleaned up.

| Test Area | What to Check |
|-----------|--------------|
| **Label CRUD** | Create issue with all label types, verify labels applied |
| **Status transitions** | Walk an issue through the full lifecycle (open -> approved -> in-progress -> pending-test -> pending-ship -> shipped -> closed) |
| **Discussion comments** | Add timestamped comment, verify format matches protocol |
| **Query filters** | `gh issue list --label` with compound filters returns correct results |
| **Startup permission check** | `gh issue list --limit 1` succeeds |

### 2c. Git Operations Integration Tests (Phase 2)

These require git operations and branch cleanup.

| Test Area | What to Check |
|-----------|--------------|
| **Commit message format** | `[role]: [description]` format |
| **Branch naming** | `squidsquad/feat-skill-NNN` or `squidsquad/bug-skill-NNN` |
| **PR creation** | PR title and body format |
| **Atomic writes** | `.tmp` + `mv` pattern for current-state |

### 2d. Config File Tests (Static)

| Test Area | What to Check |
|-----------|--------------|
| **Required fields** | All expected config fields present |
| **Counter arithmetic** | Shipped Since Last Bump is a valid integer |
| **Version format** | Semver-valid version string |
| **Agent list** | Dev Agents field is non-empty, role names are valid |

---

## 3. Framework Design

### Language: Python

Aligned with #66 (script layer). Python stdlib is sufficient for static analysis. pytest is available on all systems with Python.

### Test Runner: pytest

Rationale:
- **Simpler than unittest**: No boilerplate class definitions, just functions
- **Better output**: Color-coded, shows failing line, diffs
- **Fixtures**: `@pytest.fixture` for setup/teardown (critical for GH Issues cleanup)
- **Parameterize**: `@pytest.mark.parametrize` for running the same test across all sub-skill files
- **stdlib fallback**: If pytest not installed, tests can be written to also run with `python -m pytest` after `pip install pytest`, or fall back to unittest discovery
- **Industry standard**: Most Python projects use pytest

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures (paths, file loaders, GH cleanup)
├── test_labels.py           # Label consistency across all sub-skills
├── test_references.py       # Stale reference detection (INDEX.md, PM/QA, FEAT-SKILL-NNN)
├── test_manifest.py         # Manifest vs filesystem, include resolution
├── test_composition.py      # agent-instructions.md sync with sub-skill sources
├── test_config.py           # config.md field validation, counter arithmetic
├── test_roles.py            # Role completeness in docs, setup, architecture
├── test_vault.py            # Vault note structure, version consistency
├── integration/
│   ├── conftest.py          # GH Issues fixtures with [TEST] prefix + cleanup
│   ├── test_gh_issues.py    # GitHub Issues CRUD, label transitions
│   └── test_git_ops.py      # Git operations, branch naming, commit format
└── README.md                # How to run tests, what they cover
```

### Key Design Decisions

**1. Static tests are pure file reads — no side effects.**
Every static test reads files from `references/sub-skills/`, `references/agent-instructions.md`, `.squidsquad/config.md`, etc. They never write, create, or modify anything.

**2. Integration tests use [TEST] prefix and cleanup fixtures.**
```python
@pytest.fixture
def test_issue(cleanup_issues):
    """Create a test issue, register for cleanup."""
    result = subprocess.run(
        ["gh", "issue", "create", "--title", "[TEST] Label validation",
         "--body", "Automated test — will be deleted",
         "--label", "type:bug,role:skill,squidsquad"],
        capture_output=True, text=True
    )
    number = extract_issue_number(result.stdout)
    cleanup_issues.append(number)
    return number

@pytest.fixture
def cleanup_issues():
    """Track and delete all test issues, even on failure."""
    issues = []
    yield issues
    for num in issues:
        subprocess.run(["gh", "issue", "delete", str(num), "--yes"],
                       capture_output=True)
```

**3. Integration tests are opt-in.**
```bash
# Static tests only (default, safe, fast)
pytest tests/ --ignore=tests/integration/

# All tests including integration
pytest tests/ --run-integration
```

**4. Paths are relative to repo root.**
`conftest.py` discovers the repo root via `git rev-parse --show-toplevel` and provides it as a fixture.

---

## 4. Static Analysis Tests — Detailed Specifications

### test_labels.py

```python
# Canonical label taxonomy (extracted from common/tracker-protocol.md)
VALID_TYPES = {"type:bug", "type:feature"}
VALID_PRIORITIES = {"priority:high", "priority:medium", "priority:low"}
VALID_STATUSES = {
    "status:open", "status:pending", "status:planning", "status:planned",
    "status:approved", "status:in-progress", "status:pending-test",
    "status:pending-ship", "status:shipped"
}
VALID_ROLES = {"role:skill", "role:pm", "role:qa", "role:designer", "role:dm"}
VALID_DESIGN = {"design:needed", "design:in-progress", "design:complete"}
VALID_SEVERITY = {"severity:high", "severity:medium", "severity:low"}
SPECIAL = {"squidsquad", "improvement-scan"}

def test_no_bare_bug_feature_labels():
    """All --label args use type:bug/type:feature, never bare bug/feature."""
    # Grep all .md files under references/sub-skills/ and references/agent-instructions.md
    # for patterns like --label "bug" or --label "feature" (without type: prefix)
    # Regex: --label\s+"[^"]*\bbug\b  where bug is not preceded by type:

def test_all_status_labels_valid():
    """Every status:* label in sub-skills matches the canonical taxonomy."""

def test_all_gh_issue_commands_use_prefixed_labels():
    """Every `gh issue list --label` and `gh issue edit --add-label/--remove-label`
    uses only labels from the canonical taxonomy."""
```

### test_references.py

```python
STALE_PATTERNS = [
    # (pattern, description, exceptions)
    (r"features/INDEX\.md", "Old INDEX.md reference (replaced by gh issue list)",
     ["features/INDEX.md"]),  # The file itself is OK
    (r"bugs/INDEX\.md", "Old bugs INDEX.md reference", []),
    (r"FEAT-SKILL-\d{3}", "Old FEAT-SKILL-NNN format in user-facing docs",
     ["features/FEAT-SKILL-*.md", "planning/"]),  # Planning artifacts exempt
    (r"BUG-SKILL-\d{3}", "Old BUG-SKILL-NNN format", ["planning/"]),
    (r"\.squidsquad/\w+/bugs/", "Old markdown bugs/ directory reference", []),
    (r"\.squidsquad/\w+/features/", "Old markdown features/ directory reference",
     [".squidsquad/skill/features/"]),  # Skill features dir still exists (local planning)
]

def test_no_stale_references_in_sub_skills():
    """Scan all sub-skill .md files for known stale patterns."""

def test_no_stale_references_in_agent_instructions():
    """Scan agent-instructions.md for known stale patterns."""

def test_no_stale_references_in_readme():
    """Scan README.md for known stale patterns."""
```

### test_manifest.py

```python
def test_all_manifest_files_exist():
    """Every file listed in manifest.md's inventory exists on disk."""

def test_all_include_directives_resolve():
    """Every {{include: path}} in role entry files points to an existing .md file."""

def test_manifest_composition_order_matches_markers():
    """Sub-skill markers in agent-instructions.md appear in the order
    specified by manifest.md for each role template."""

def test_no_orphan_sub_skills():
    """Every .md file in sub-skills/ (excluding manifest.md) is referenced
    by at least one role entry file or manifest.md."""
```

### test_composition.py

```python
def test_agent_instructions_has_all_sub_skill_markers():
    """agent-instructions.md has <!-- sub-skill: X --> markers for
    every sub-skill listed in manifest.md."""

def test_sub_skill_content_matches_source():
    """For each sub-skill marker in agent-instructions.md, the content
    between <!-- sub-skill: X --> and <!-- /sub-skill: X --> matches
    the source file's content (after stripping the marker lines)."""
    # This is the definitive sync check

def test_no_raw_include_directives_in_composed():
    """agent-instructions.md contains no unresolved {{include: ...}} directives."""
```

### test_config.py

```python
def test_required_config_fields():
    """config.md has all required fields."""

def test_version_is_semver():
    """SquidSquad Version field is valid semver."""

def test_ship_counter_is_integer():
    """Shipped Since Last Bump is a non-negative integer."""

def test_ship_threshold_is_integer():
    """Ship Threshold is a positive integer."""

def test_dev_agents_non_empty():
    """Dev Agents field lists at least one role."""

def test_iteration_interval_valid():
    """Minutes field is a positive integer."""
```

### test_roles.py

```python
def test_all_roles_in_readme_agents_table():
    """README.md Agents table lists all 5 roles (skill, pm, qa, designer, dm)."""

def test_all_roles_in_setup_instructions():
    """SKILL.md setup mentions all role types."""

def test_all_roles_have_soul():
    """Every role in manifest.md has a corresponding souls/*.md file."""

def test_all_roles_have_entry_file():
    """Every role in manifest.md has a corresponding roles/*.md entry file."""

def test_discussion_aliases_correct():
    """Each role-specific discussion-protocol uses the correct alias
    (pm for pm-lean, pm/qa for pm-agent, qa for qa-agent, etc.)."""
```

### test_vault.py

```python
def test_vault_version_matches_config():
    """Version referenced in vault/projects/squidsquad.md matches config.md."""

def test_briefing_not_stale():
    """BRIEFING.md references current version from config.md."""

def test_vault_templates_exist():
    """All template files referenced by vault-protocol sub-skill exist."""
```

---

## 5. Integration with Ralph Loop

### Recommended: Option D — All of the above

**A. Standalone command (primary)**:
```bash
# From repo root
python -m pytest tests/ --ignore=tests/integration/ -v

# Full suite with integration
python -m pytest tests/ --run-integration -v
```

This is what developers and CI run. Fast feedback, clear output.

**B. QA agent verification step**:
The QA agent's verification sub-skill (`qa-specific/verification.md`) currently does manual checks. Add a step:
```
Run `python -m pytest tests/ --ignore=tests/integration/ -q` as part of health check.
If any tests fail, file bugs for each failure category.
```

This turns QA's manual checking into automated checking for the categories that tests cover, freeing QA to focus on semantic/behavioral verification.

**C. Pre-commit hook** (optional, not recommended initially):
Static tests run in <5 seconds. Could add to pre-commit. But SquidSquad agents commit frequently and hooks add friction. Defer to Phase 2.

**D. Skill-lead test command**:
Update config.md:
```markdown
- **skill Tests**: python -m pytest tests/ --ignore=tests/integration/ -q
```

This means every bug fix and feature implementation automatically runs static analysis before marking Pending Test.

### Phase 1 (this feature): Options A + D
### Phase 2 (after #66 script layer): Add B + C

---

## 6. Teardown Protocol

### Static Tests: No Teardown Needed

Static tests read files only. Zero cleanup.

### GH Issues Integration Tests

```python
@pytest.fixture(scope="function")
def gh_cleanup():
    """Tracks test artifacts for cleanup."""
    created = {"issues": [], "branches": [], "files": []}
    yield created
    # Always runs, even on test failure
    for issue_num in created["issues"]:
        subprocess.run(
            ["gh", "issue", "delete", str(issue_num), "--yes"],
            capture_output=True, timeout=10
        )
    for branch in created["branches"]:
        subprocess.run(
            ["git", "branch", "-D", branch],
            capture_output=True, timeout=10
        )
        subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            capture_output=True, timeout=10
        )
    for filepath in created["files"]:
        if os.path.exists(filepath):
            os.remove(filepath)
```

### Naming Conventions for Test Artifacts

| Artifact Type | Naming Convention | Purpose |
|--------------|-------------------|---------|
| GH Issues | Title starts with `[TEST]` | Easy to identify and mass-delete |
| Git branches | Prefix `test/` | Easy to filter, never conflicts with `squidsquad/` |
| Temp files | In `tests/tmp/` or via `tempfile` | Contained, easy to clean |

### Stale Artifact Recovery

If cleanup fails (network error, crash), stale test artifacts may remain. Add a recovery command:

```bash
# Find and delete stale test issues
gh issue list --search "[TEST]" --state all --json number | \
  jq -r '.[].number' | xargs -I{} gh issue delete {} --yes

# Find and delete stale test branches
git branch -a | grep 'test/' | xargs git branch -D
```

This could be a `tests/cleanup.py` script.

---

## 7. Quick Wins — Ship Immediately

These static analysis tests require no GH/git integration, no cleanup, and would catch ~80% of the bugs seen in iterations 60-97.

### Priority 1: Stale Reference Scanner (catches 18/40 bugs = 45%)

A single test that greps all sub-skill files for known-bad patterns:
- `features/INDEX.md` (should be `gh issue list`)
- Bare `bug`/`feature` in `--label` (should be `type:bug`/`type:feature`)
- `PM/QA` in files that should say `PM` or `QA` separately (with exceptions for pm-agent.md which IS the combined template)
- `BUG-SKILL-NNN` / `FEAT-SKILL-NNN` format in non-planning files
- `.squidsquad/*/bugs/` or `.squidsquad/*/features/` directory references (old tracker)

**Implementation time**: ~2 hours. One file, ~100 lines of Python.

### Priority 2: Label Taxonomy Validator (catches 6/40 bugs = 15%)

Parse `common/tracker-protocol.md` to extract canonical labels. Then grep all sub-skills for `--label`, `--add-label`, `--remove-label` arguments and verify every label token is in the canonical set.

**Implementation time**: ~1 hour. One file, ~80 lines.

### Priority 3: Manifest Integrity Checker (catches 5/40 bugs = 12%)

Verify every file in the manifest inventory exists. Verify every `{{include:}}` directive resolves. Verify every sub-skill file is referenced.

**Implementation time**: ~1 hour. One file, ~60 lines.

### Priority 4: Composition Sync Checker (catches 5/40 bugs = 12%)

Verify `agent-instructions.md` has markers for all sub-skills. Verify content between markers matches source files.

**Implementation time**: ~2 hours. One file, ~120 lines.

### Total: 4 test files, ~360 lines, ~6 hours, catches ~85% of historical bugs.

---

## 8. Currently Known Stale References (Still Present)

During this research, the following stale references were identified in the **source** sub-skill files (not just composed output):

### PM/QA References Still in Sub-skills

These exist in sub-skill source files and will propagate to any new composition:

| File | Stale Reference |
|------|----------------|
| `roles/pm-agent.md` line 3 | `# SquidSquad — PM/QA` (intentional — this IS the combined template) |
| `roles/pm-agent.md` line 5 | `You are the PM/QA on the SquidSquad` (intentional) |
| `roles/pm-agent.md` lines 134, 146, 194-196, 222 | `**pm/qa**:` Discussion alias (intentional for combined mode) |
| `roles/dev-agent.md` line 16 | `Keep the PM/QA informed` (BUG: should say "Keep PM informed") |
| `common/bug-filing.md` line 3 | `Do not wait for PM/QA` (BUG: should say "Do not wait for PM") |
| `pm-specific/discussion-protocol.md` line 6 | `**pm/qa**:` (intentional for pm-agent variant) |
| `pm-specific/iteration-log.md` line 10 | `PM/QA Iteration N` (intentional for pm-agent variant) |
| `pm-specific/status-line.md` line 6 | `PM/QA role label` (intentional for pm-agent variant) |
| `pm-specific/file-conventions.md` line 3 | `qa-log.md` ref (BUG: may be stale) |

### features/INDEX.md References

| File | Line |
|------|------|
| `roles/pm-agent.md` line 190 | `read their features/INDEX.md` |
| `references/agent-instructions.md` line 1387 | Same (composed from above) |

These are active bugs that the test framework would catch on first run.

---

## 9. Relationship to #66 (Script Layer)

Feature #66 proposes a Python script layer (`scripts/tracker.py`, `scripts/config.py`, etc.) that replaces inline CLI commands in sub-skills with deterministic Python calls. The test framework complements #66:

- **Tests validate the sub-skill content** (labels, references, structure) — this is orthogonal to whether operations are CLI or Python
- **Tests can validate script behavior** once #66 ships (import and call Python functions)
- **Shared conftest.py** infrastructure (repo root discovery, file loading)
- **Tests should be in `tests/`**, scripts in `scripts/` — separate concerns

The test framework does NOT depend on #66 and should ship first. It provides immediate regression detection for the current markdown-based system.

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Python not available | Tests can't run | Check `python3 --version` in conftest.py, skip gracefully |
| pytest not installed | Tests can't run | Provide `requirements-dev.txt` with `pytest>=7.0`; tests can also run with `python -m unittest discover` as fallback |
| Tests become stale | False sense of safety | Each test documents which bug class it catches; when new bug classes appear, add tests |
| Integration test cleanup fails | Stale GH Issues, branches | `[TEST]` prefix, `test/` branch prefix, `cleanup.py` recovery script |
| Test suite slows down agents | Longer cycle time | Static tests run in <5s; integration tests opt-in only |
| Agents ignore test failures | Bugs still ship | Config.md test command means agents MUST run tests before Pending Test |

---

## 11. Implementation Recommendation

### Phase 1 (This Feature — #67)

1. Create `tests/` directory with `conftest.py`
2. Implement 4 quick-win test files (labels, references, manifest, composition)
3. Add `test_config.py`, `test_roles.py`, `test_vault.py`
4. Update `config.md` test command to run pytest
5. Run tests, fix any bugs they find (expect 2-5 existing bugs)
6. Mark feature Pending Test

### Phase 2 (After #66 ships)

1. Add `tests/integration/` with GH Issues tests
2. Add git operations tests
3. Add QA agent integration (verification step runs static tests)
4. Add pre-commit hook (optional)

### Estimated LOC

| File | Lines | Complexity |
|------|-------|-----------|
| conftest.py | ~80 | Low — path helpers, file loaders |
| test_labels.py | ~100 | Medium — regex parsing of label args |
| test_references.py | ~120 | Low — pattern matching |
| test_manifest.py | ~80 | Low — file existence checks |
| test_composition.py | ~150 | Medium — content comparison |
| test_config.py | ~60 | Low — field validation |
| test_roles.py | ~80 | Low — presence checks |
| test_vault.py | ~50 | Low — version comparison |
| **Total** | **~720** | |

Plus `requirements-dev.txt` (1 line: `pytest>=7.0`).
