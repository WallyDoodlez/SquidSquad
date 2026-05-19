I've completed a thorough review of both changed files against all acceptance criteria, comprehension tests, and regression risks. Here is my analysis.

---

## Per-Axis Confirmation

### AC-1: Fragment edit replaces old step 2 — **PASS**

- `the planning artifact is the authoritative scope` appears exactly once — at `implement-tasks.md:21`. ✅
- No residual "old phrasing" exists outside the new step. The new heading at line 13 contains "Read planning artifacts" but this is the new step's own heading (permitted by AC-1's "matches only inside the new step"). All other `planning artifact` occurrences (lines 15, 21, 24, 25, 27) are part of the new authoritative-artifact content. ✅
- Fallback location `.squidsquad/[ROLE]/planning/` is preserved at line 19 with "same file patterns" directive. ✅

### AC-2: §9c passes full planning files as additional `--input-files` — **PASS**

- §9c code (lines 60-73) passes `$ARTIFACTS` (discovered via glob `*[NUMBER]*`) appended to `$CHANGED_FILES` via `--input-files`. The glob matches `CONTEXT-<NUMBER>.md`, `TEST-PLAN-<NUMBER>.md`, and legacy `FEAT-PM-<NUMBER>-*` files with full paths. ✅
- The `--context` string at line 73 mentions "architectural locks" and directs the review to "verify the diff conforms to the architectural locks documented there — not only code quality." ✅
- Task context confirms this was previously satisfied by PR #9131 (#8950 Gate #2); no additional edit required. The Scope's "bundle or per-task" language uses "or" — the per-task path is covered. ✅

### AC-3: Non-dev roles byte-identical — **PASS** (structural verification)

- `roles/dev/implement-tasks` is included ONLY in dev manifests: `references/roles/dev/includes.yml:12` and `references/roles/dev/includes-events.yml:26`. ✅
- PM (`references/roles/pm/includes.yml`, `includes-events.yml`), QA (`references/roles/qa/includes.yml`, `includes-events.yml`), and DM (`references/roles/dm/includes.yml`, `includes-events.yml`) do NOT reference `roles/dev/implement-tasks`. ✅
- Therefore, changing `implement-tasks.md` cannot affect PM/QA/DM composed output — their CLAUDE.md files remain byte-identical. ✅

### AC-4: Skill clone receives updated fragment — **PASS** (structural verification)

- `roles/dev/implement-tasks` is in both dev manifests (polling + events), so `compose.py deploy-all` will include the new step 2 in `.squidsquad/skill/CLAUDE.md`. ✅

### CQ-1 through CQ-4 — **PASS**

- **CQ-1** (divergence): Lines 24-25 — planning artifact wins, flag in PR description. ✅
- **CQ-2** (file locations): Lines 15-19 — all 3 patterns + fallback listed. ✅
- **CQ-3** (§9c invocation): Lines 60-73 — `$CHANGED_FILES` + artifacts, "architectural locks" direction. ✅
- **CQ-4** (non-divergence no-flag): Lines 23-24 — "Do not add a planning-artifact note." ✅

### Regression Risks R1/R2/R3 — **MITIGATED**

- **R1**: Confirmed dev CLAUDE.md changes in both modes (both includes files reference `implement-tasks`). Non-dev roles structurally isolated. ✅
- **R2**: PR description noise prevented by conditional phrasing on lines 23-24 ("If ... agree, proceed normally. Do not add..."). Only flags on divergence. ✅
- **R3**: No-op for missing artifacts via line 27's guard: "If no planning artifact exists (bug fix or trivial task), proceed to step 2c." The "If a planning artifact exists" at line 21 is load-bearing. ✅

---

## Detailed Checks

| Check | Location | Result |
|---|---|---|
| Authority phrase count | `implement-tasks.md:21` | 1 occurrence ✅ |
| Fallback `.squidsquad/[ROLE]/planning/` | `implement-tasks.md:19` | Present ✅ |
| Divergence: planning-artifact-wins | `implement-tasks.md:25` | Explicit ✅ |
| Non-divergence: no note in PR | `implement-tasks.md:23-24` | Explicit ✅ |
| Push-back for missing referenced artifacts | `implement-tasks.md:27` | Present ✅ |
| `### 5.X #<NUMBER>` format matches actual CONTEXT.md | `implement-tasks.md:16` vs `.squidsquad/pm/planning/CONTEXT.md:331` (`### 5.1 #8694 — …`) | Matches ✅ |
| §9c context mentions "architectural locks" | `implement-tasks.md:73` | Present ✅ |
| Dev includes.yml references implement-tasks | `references/roles/dev/includes.yml:12` | Present ✅ |
| Dev includes-events.yml references implement-tasks | `references/roles/dev/includes-events.yml:26` | Present ✅ |
| PM includes (both modes) lack dev/implement-tasks | Confirmed | ✅ |
| QA includes (both modes) lack dev/implement-tasks | Confirmed | ✅ |
| DM includes (both modes) lack dev/implement-tasks | Confirmed | ✅ |

---

NO_FINDINGS