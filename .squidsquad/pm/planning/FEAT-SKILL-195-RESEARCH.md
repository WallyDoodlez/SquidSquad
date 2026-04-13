# Research: #195 — Extract Ralph Loop Steps as Modular Sub-Skills Per Role

**Date**: 2026-04-11
**Status**: Complete
**Researcher**: PM research agent

---

## Summary

Every SquidSquad role currently gets **all** common sub-skills composed into a monolithic CLAUDE.md at deploy time, regardless of whether the role actually uses them. The PM role is the worst offender at ~18,000 tokens; even the leanest roles (QA, DM) burn ~12,000 tokens. The three biggest token consumers — `vault-protocol` (~3,060 tokens), `tracker-protocol` (~1,900 tokens), and `improvement-scan` (~1,100 tokens) — appear identically in all five roles despite varying relevance.

The composition engine (`compose.py`) has no concept of conditional includes. It resolves `{{include:}}` directives unconditionally. Making the Ralph Loop modular requires (a) a role manifest declaring which sub-skills to include, and (b) compose.py changes to read that manifest and skip excluded sub-skills.

**Expected savings**: 15-25% token reduction per non-PM role (1,800-3,000 tokens each) by removing vault-protocol from read-only roles and trimming improvement-scan/vault-optimize from roles that do not act on their outputs.

---

## 1. Current State Measurements

### 1.1 Composed CLAUDE.md Size Per Role

| Role     | Lines | Chars  | Est. Tokens | Includes (count) |
|----------|-------|--------|-------------|-------------------|
| PM       | 1,444 | 71,927 | ~17,981     | 20                |
| Designer | 1,090 | 51,414 | ~12,853     | 18                |
| Dev      | 1,029 | 49,610 | ~12,402     | 18                |
| QA       | 1,022 | 48,358 | ~12,089     | 16                |
| DM       | 1,013 | 47,216 | ~11,804     | 18                |

PM is ~50% larger than the other roles, mostly due to `task-intake` (3,761 tokens) which is PM-exclusive.

### 1.2 Top Token Consumers (common sub-skills, per role)

| Sub-skill          | Tokens | Present In         | Notes                                   |
|--------------------|--------|--------------------|-----------------------------------------|
| vault-protocol     | ~3,059 | ALL 5 roles        | Full vault read/write protocol           |
| tracker-protocol   | ~1,896 | ALL 5 roles        | GitHub Issues interaction protocol       |
| improvement-scan   | ~1,104 | ALL 5 roles        | Scans for process improvements           |
| vault-remember     | ~830   | ALL 5 roles        | "Remember to vault" reminders            |
| vault-optimize     | ~418   | ALL 5 roles        | Vault deduplication/optimization         |
| boot-remote-agents | ~238   | ALL 5 roles        | Agent boot orchestration                 |
| pull-latest        | ~90    | ALL 5 roles        | git pull step                            |

**Vault-related sub-skills combined**: ~4,307 tokens per role, ~21,535 tokens across all 5 roles.

### 1.3 Top Token Consumers (role-specific)

| Sub-skill       | Role     | Tokens | Notes                           |
|-----------------|----------|--------|---------------------------------|
| task-intake     | PM       | ~3,761 | PM-exclusive, largest single sub-skill |
| verification    | QA       | ~1,822 | QA-exclusive                     |
| design-session  | Designer | ~1,738 | Designer-exclusive               |
| delivery-fallback | PM     | ~818   | PM-exclusive                     |
| delivery-packaging | DM    | ~633   | DM-exclusive                     |
| version-bumps   | DM       | ~456   | DM-exclusive                     |

### 1.4 Inline (Non-Sub-Skill) Content Per Role

| Role     | Inline Tokens | % of Total |
|----------|--------------|------------|
| PM       | ~3,518       | 19.6%      |
| Dev      | ~2,253       | 18.2%      |
| Designer | ~1,469       | 11.4%      |
| QA       | ~1,375       | 11.4%      |
| DM       | ~1,304       | 11.0%      |

PM's inline is large because Steps 1-7 of its Ralph Loop are hardcoded in the role template, not extracted as sub-skills.

---

## 2. Ralph Loop Structure Analysis

### 2.1 Include Directives Per Role

**PM** (20 includes):
- `common/tracker-protocol`, `common/pull-latest`, `common/boot-remote-agents`, `common/improvement-scan`, `common/vault-remember`, `common/vault-optimize`, `common/vault-protocol`
- `pm-specific/pr-flow`, `pm-specific/delivery-fallback`, `pm-specific/github-issues`, `pm-specific/iteration-log`, `pm-specific/git-commit`, `pm-specific/issue-filing`, `pm-specific/task-intake`, `pm-specific/task-approval`, `pm-specific/discussion-protocol`, `pm-specific/file-conventions`, `pm-specific/status-line`, `pm-specific/prohibitions`

**DM** (18 includes):
- `common/tracker-protocol`, `common/capability-check`, `common/pull-latest`, `common/boot-remote-agents`, `common/improvement-scan`, `common/vault-remember`, `common/vault-optimize`, `common/vault-protocol`
- `dm-specific/issue-triage`, `dm-specific/delivery-packaging`, `dm-specific/version-bumps`, `dm-specific/iteration-log`, `dm-specific/git-commit`, `dm-specific/discussion-protocol`, `dm-specific/issue-filing`, `dm-specific/file-conventions`, `dm-specific/status-line`, `dm-specific/prohibitions`

**Dev** (18 includes):
- `common/tracker-protocol`, `common/pull-latest`, `common/context-pressure`, `common/resume-working-state`, `common/interval-sync`, `common/boot-remote-agents`, `common/improvement-scan`, `common/iteration-log`, `common/vault-remember`, `common/vault-optimize`, `common/git-commit`, `common/discussion-protocol`, `common/issue-filing`, `common/working-state`, `common/vault-protocol`, `common/file-conventions`, `common/status-line`, `common/prohibitions`

**QA** (16 includes):
- `common/tracker-protocol`, `common/pull-latest`, `common/boot-remote-agents`, `common/improvement-scan`, `common/vault-remember`, `common/vault-optimize`, `common/vault-protocol`
- `qa-specific/verification`, `qa-specific/iteration-log`, `qa-specific/git-commit`, `qa-specific/issue-filing`, `qa-specific/discussion-protocol`, `qa-specific/file-conventions`, `qa-specific/status-line`, `qa-specific/prohibitions`

**Designer** (18 includes):
- `common/tracker-protocol`, `common/capability-check`, `common/pull-latest`, `common/boot-remote-agents`, `common/improvement-scan`, `common/vault-remember`, `common/vault-optimize`, `common/vault-protocol`
- `designer-specific/design-session`, `designer-specific/iteration-log`, `designer-specific/git-commit`, `designer-specific/discussion-protocol`, `designer-specific/design-capabilities`, `designer-specific/issue-filing`, `designer-specific/file-conventions`, `designer-specific/status-line`, `designer-specific/prohibitions`

### 2.2 Common vs Role-Specific Classification

**Universal (all 5 roles):**
- `tracker-protocol` (1,896 tokens) — all roles interact with GitHub Issues
- `pull-latest` (90 tokens) — all roles pull
- `boot-remote-agents` (238 tokens) — all roles can boot remote agents
- `improvement-scan` (1,104 tokens) — all roles scan
- `vault-remember` (830 tokens) — all roles remember
- `vault-optimize` (418 tokens) — all roles optimize
- `vault-protocol` (3,059 tokens) — all roles get full vault protocol

**Near-universal (4+ roles, slight variants):**
- `git-commit` — all roles, but role-specific versions (pm/dm/qa/designer have tiny overrides, dev has a larger common version)
- `iteration-log` — all roles, role-specific variants
- `discussion-protocol` — all roles, role-specific variants
- `issue-filing` — all roles, role-specific variants
- `file-conventions` — all roles, role-specific variants
- `prohibitions` — all roles, role-specific variants
- `status-line` — all roles, role-specific variants

**Dev-only (not included in PM/DM/QA/Designer):**
- `context-pressure` (271 tokens)
- `resume-working-state` (134 tokens)
- `interval-sync` (134 tokens)
- `working-state` (220 tokens)

**DM/Designer-only:**
- `capability-check` (250 tokens) — DM and Designer only

### 2.3 Candidates for Conditional Inclusion

| Sub-skill | Currently | Should Be | Rationale |
|-----------|-----------|-----------|-----------|
| `vault-protocol` (3,059 tok) | All roles | Only roles that WRITE to vault (Dev, PM) | QA/DM/Designer read vault but rarely write; a slim "vault-read" variant would suffice |
| `vault-optimize` (418 tok) | All roles | Only PM or a dedicated maintenance cycle | QA/DM/Designer never act on optimization findings |
| `improvement-scan` (1,104 tok) | All roles | Only PM and Dev | QA/DM/Designer file improvement findings but rarely act on them; could use a slim "file-improvement" variant |
| `vault-remember` (830 tok) | All roles | Could be trimmed for non-writing roles | DM/QA/Designer rarely create vault-worthy learnings |
| `boot-remote-agents` (238 tok) | All roles | Keep universal | Small footprint, all roles may need to boot agents |

---

## 3. compose.py Analysis

### 3.1 Current Behavior

- `compose.py` reads `references/roles/<role>/CLAUDE.md` as the entry file
- Resolves `{{include: path}}` directives by inlining content from `references/sub-skills/`
- Resolves `{{runtime: path}}` for SOUL.md bootstrapping
- Resolves `{{capability: id}}` for capability sub-skills
- Wraps each include in `<!-- sub-skill: name -->` markers
- Substitutes placeholders (`[ROLE]`, `[INTERVAL]`, etc.)
- **No conditional logic** — every `{{include:}}` is always resolved

### 3.2 What Is Missing

1. **No role manifest / config**: No way to declare "role X needs sub-skills A, B, C but not D"
2. **No conditional include**: No `{{include-if: condition}}` or `{{optional: path}}` syntax
3. **No sub-skill dependency graph**: No way to express "vault-remember requires vault-protocol"
4. **No token budget tracking**: No way to measure or cap token usage per role

### 3.3 Required Changes

**Option A — Manifest-driven composition (recommended)**:
Add a `manifest.yml` (or `includes.yml`) per role directory:

```yaml
# references/roles/qa/includes.yml
common:
  - tracker-protocol       # required
  - pull-latest            # required
  - boot-remote-agents     # required
  - vault-protocol-slim    # read-only variant
  - improvement-scan-slim  # file-only variant
  # vault-optimize: excluded
  # vault-remember: excluded (or slim variant)
role-specific:
  - qa-specific/verification
  - qa-specific/iteration-log
  # ... etc
```

compose.py reads the manifest instead of parsing `{{include:}}` from the entry file.

**Option B — Conditional include syntax**:
Add `{{include-if: role.uses_vault_write}}` guards in the entry file. compose.py resolves against a role config. More flexible but harder to reason about.

**Option C — Hybrid (pragmatic first step)**:
Keep `{{include:}}` in entry files but add `{{exclude:}}` overrides in a per-role config. compose.py skips excluded includes. Minimal change to existing templates.

---

## 4. Modularization Opportunities

### 4.1 Proposed Core Set (every role needs)

| Sub-skill | Tokens | Justification |
|-----------|--------|---------------|
| tracker-protocol | ~1,896 | All roles interact with GitHub Issues |
| pull-latest | ~90 | All roles must sync |
| boot-remote-agents | ~238 | All roles may boot agents |
| git-commit (role variant) | ~57-296 | All roles commit |
| iteration-log (role variant) | ~177-265 | All roles log |
| discussion-protocol (role variant) | ~95-136 | All roles discuss |
| issue-filing (role variant) | ~57-256 | All roles file issues |
| file-conventions (role variant) | ~97-126 | All roles follow conventions |
| status-line (role variant) | ~85-156 | All roles update status |
| prohibitions (role variant) | ~139-246 | All roles have prohibitions |
| **Core total** | **~2,900-3,500** | |

### 4.2 Optional Sub-Skills (conditional per role)

| Sub-skill | Tokens | Who Needs It | Who Can Drop It |
|-----------|--------|-------------|----------------|
| vault-protocol (full) | ~3,059 | Dev, PM | QA, DM, Designer |
| vault-protocol-slim (new) | ~800 est. | QA, DM, Designer | — |
| vault-remember | ~830 | Dev, PM | QA, DM, Designer |
| vault-optimize | ~418 | PM only (or skip entirely) | Dev, QA, DM, Designer |
| improvement-scan | ~1,104 | PM, Dev | QA, DM, Designer |
| improvement-scan-slim (new) | ~300 est. | QA, DM, Designer | — |
| capability-check | ~250 | DM, Designer | PM, Dev, QA |
| context-pressure | ~271 | Dev only | PM, DM, QA, Designer |
| resume-working-state | ~134 | Dev only | PM, DM, QA, Designer |
| interval-sync | ~134 | Dev only | PM, DM, QA, Designer |
| working-state | ~220 | Dev only | PM, DM, QA, Designer |
| task-intake | ~3,761 | PM only | All others |
| task-approval | ~404 | PM only | All others |

### 4.3 Expected Token Reduction

| Role | Current | After Modularization | Savings | % |
|------|---------|---------------------|---------|---|
| PM | ~17,981 | ~16,700 (drop vault-optimize) | ~1,280 | 7% |
| Dev | ~12,402 | ~11,200 (drop vault-optimize, slim vault-protocol) | ~1,200 | 10% |
| QA | ~12,089 | ~9,400 (slim vault-protocol, drop vault-remember, vault-optimize, slim improvement-scan) | ~2,690 | 22% |
| DM | ~11,804 | ~9,200 (slim vault-protocol, drop vault-remember, vault-optimize, slim improvement-scan) | ~2,600 | 22% |
| Designer | ~12,853 | ~10,100 (slim vault-protocol, drop vault-remember, vault-optimize, slim improvement-scan) | ~2,750 | 21% |
| **Total** | **~67,129** | **~56,600** | **~10,530** | **16%** |

---

## 5. Side Effects

1. **Vault behavior changes for read-only roles**: QA/DM/Designer currently can write to vault even if they rarely do. Switching to vault-protocol-slim removes their ability to create new vault entries. If a DM discovers something vault-worthy during delivery, they would need to file it as a suggestion to PM instead.

2. **Improvement scan truncation**: Slim improvement-scan means QA/DM/Designer only file improvement suggestions (one-line), not run the full analysis. PM/Dev still get the full scan. This changes the information flow slightly — fewer detailed improvement proposals from non-core roles.

3. **Manifest file maintenance**: A new `includes.yml` per role is another file to maintain. When a new sub-skill is created, someone must decide which roles get it.

4. **Composed output differs per-role more visibly**: Currently all roles look structurally similar. After modularization, the output diverges more, making debugging harder if you are comparing across roles.

---

## 6. Edge Cases

1. **New roles added by users**: Custom roles (e.g., `be`, `fe`) inherit from the `dev` template. They would also need a manifest, or inherit the dev manifest by default.

2. **Sub-skill dependencies**: `vault-remember` references concepts from `vault-protocol`. If vault-protocol is slimmed, vault-remember must also be updated or excluded. A dependency graph is needed.

3. **Inline Ralph Loop steps reference sub-skills**: PM's Steps 1-7 are inline and reference behavior defined in sub-skills (e.g., "see Tracker Protocol above"). If tracker-protocol is excluded (unlikely but possible), the inline text becomes orphaned.

4. **Capability sub-skills**: The `{{capability:}}` directive is orthogonal to this work. Capabilities are already role-specific and should remain so.

5. **Upgrade path for existing installs**: Existing `.squidsquad/<role>/CLAUDE.md` files are regenerated by `compose.py deploy`. The change is transparent — re-running deploy produces the new, slimmer output.

---

## 7. Integration Risks

1. **Low risk**: compose.py changes are isolated. The output is still a single CLAUDE.md per role — downstream consumers see no structural change.

2. **Medium risk**: Creating `vault-protocol-slim` and `improvement-scan-slim` variants requires careful extraction. The full vault-protocol has read, write, and organizational sections interleaved. Splitting cleanly requires refactoring the sub-skill content, not just the composition engine.

3. **Low risk**: Manifest format (`includes.yml`) is additive. Roles without a manifest can fall back to current behavior (include everything from the entry file).

4. **Medium risk**: Testing. There are no automated tests for "does the composed output contain the right sub-skills?" Adding manifest-driven composition should include a test that verifies each role's output matches its manifest.

---

## 8. Upgrade & Migration

1. **Phase 1 — Manifest creation**: Create `includes.yml` for each role, reflecting current includes (no behavioral change). Add compose.py support to read manifest. Deploy and verify output is identical.

2. **Phase 2 — Slim variants**: Create `vault-protocol-slim.md` (read-only vault instructions, ~800 tokens) and `improvement-scan-slim.md` (file-only, ~300 tokens). Update QA/DM/Designer manifests to use slim variants.

3. **Phase 3 — Drop unused sub-skills**: Update manifests to exclude `vault-optimize` from non-PM roles, `vault-remember` from read-only roles. Re-deploy and verify.

4. **Phase 4 — Extract PM inline steps**: PM's Steps 2-7 contain ~3,500 tokens of inline content. Some (e.g., E2E test running, health check) could be extracted as PM-specific sub-skills for better reuse and token management.

**Rollback**: At any phase, reverting the manifest to "include everything" restores the current behavior. No data loss risk.

---

## 9. Open Questions

1. **Should vault-protocol-slim be a new file or a conditional section within vault-protocol?** A new file is simpler; a conditional section requires compose.py to support section-level gating.

2. **Should the manifest be YAML or stay in Markdown?** YAML is cleaner for machine parsing but adds a dependency. A Markdown table in the role's directory could work too.

3. **Should we extract PM's inline Ralph Loop steps as sub-skills first (higher token savings) or focus on the composition engine first (lower risk)?** PM inline extraction saves ~3,500 tokens but is more invasive.

4. **Do custom dev variants (`be`, `fe`) get their own manifest or inherit from `dev`?** Inheriting is simpler; custom manifests allow project-specific trimming.

5. **Is the 16% total reduction meaningful enough to justify the complexity?** At ~10,500 tokens saved across 5 roles, this is roughly $0.003 per full deployment cycle at current pricing. The real value is in reduced context window pressure per-role, not cost.

---

## 10. Recommendation

**Proceed with a 3-phase approach:**

1. **Phase A (low risk, foundational)**: Add `includes.yml` manifest per role + compose.py manifest reader. No behavioral change — manifests mirror current includes. This unblocks all future modularization.

2. **Phase B (medium impact)**: Create `vault-protocol-slim` and `improvement-scan-slim` variants. Update QA/DM/Designer manifests. Expected savings: ~2,600-2,750 tokens per read-only role (~22% reduction).

3. **Phase C (optimization)**: Extract PM inline steps as sub-skills. Drop `vault-optimize` and `vault-remember` from non-writing roles. Expected additional savings: ~1,300-3,500 tokens.

Total expected savings: ~10,500 tokens across all roles (16% reduction), with the biggest wins for QA (-22%), DM (-22%), and Designer (-21%).

Priority: **Medium**. This is a quality-of-life improvement for context window pressure. It does not unblock any features but makes the system more maintainable and cheaper to run. Recommend scheduling after current v1.0.0 launch work.
