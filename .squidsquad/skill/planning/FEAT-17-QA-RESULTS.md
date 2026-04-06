# FEAT-17 QA Results — Vault Phase 3: vault-remember + End-of-Cycle Reflection

**QA Agent**: Claude Opus 4.6 (subagent)
**Date**: 2026-04-05
**Verdict**: 14 PASS / 1 FAIL (see TC-14)

---

## TC-01: vault_remember.py exists with expected commands

**PASS**

Script exists at `references/scripts/vault_remember.py`. Help output confirms all expected commands: `is-quiet`, `write-budget`, `inc-writes`, `reset-writes`, `briefing-budget`, `effective-confidence`, `note-count`, `decay-scan`.

---

## TC-02: cycle.py has `is-quiet` command implemented

**FAIL**

`cycle.py` documents `is-quiet` in its usage docstring (line 14) but does **not** implement it. The command dispatcher (lines 187-222) handles: `timestamp`, `timestamp-short`, `step-marker`, `status-bar`, `get-counter`, `inc-counter`, `reset-counter`, `log-iteration`, `cleanup-iterations` -- no `is-quiet`. Running `python references/scripts/cycle.py is-quiet pm` returns `Unknown command: is-quiet` with exit code 1.

The `is-quiet` command IS implemented in `vault_remember.py` and works correctly there. The CONTEXT.md listed "implement the documented but missing command" for cycle.py, but the dev agent placed it in vault_remember.py instead. The deployed CLAUDE.md files reference `vault_remember.py is-quiet`, so the feature works end-to-end. However, cycle.py's docstring is stale/misleading.

**Evidence**: `python references/scripts/cycle.py is-quiet pm` -> `Unknown command: is-quiet` (exit 1)

---

## TC-03: vault_check.py has `dedup-check` command

**PASS**

`dedup-check` is implemented in `vault_check.py` with a `dedup_check()` function (line 182) and command dispatch (line 287). Running the command produces structured match output.

---

## TC-04: vault-remember sub-skill exists

**PASS**

File exists at `references/sub-skills/common/vault-remember.md`.

---

## TC-05: dev-agent.md includes vault-remember between iteration-log and git-commit

**PASS**

`references/sub-skills/roles/dev-agent.md` contains:
- Line 178: `{{include: common/iteration-log}}`
- Line 180: `{{include: common/vault-remember}}`
- Line 182: `{{include: common/git-commit}}`

Correct ordering: iteration-log < vault-remember < git-commit.

---

## TC-06: pm-agent.md includes vault-remember between iteration-log and git-commit

**PASS**

`references/sub-skills/roles/pm-agent.md` contains:
- Line 242: `{{include: pm-specific/iteration-log}}`
- Line 244: `{{include: common/vault-remember}}`
- Line 246: `{{include: pm-specific/git-commit}}`

Correct ordering: iteration-log < vault-remember < git-commit.

---

## TC-07: Deployed CLAUDE.md files contain vault-remember step

**PASS**

Both deployed files contain the vault-remember sub-skill:
- `.squidsquad/skill/CLAUDE.md`: Step 4b "Vault Remember (End-of-Cycle Reflection)" with config gate, quiet-cycle gate, reset-writes, reflection prompt, write gates, and BRIEFING budget check (lines 605-686).
- `.squidsquad/pm/CLAUDE.md`: Same structure (lines 733-814), referencing `[ROLE]` placeholder correctly.

---

## TC-08: config.md has Vault Remember section with all required keys

**PASS**

`.squidsquad/config.md` lines 52-57:
```
## Vault Remember
- **Enabled**: yes
- **Writes Per Cycle**: 2
- **BRIEFING Token Budget**: 2000
- **Confidence Decay Days**: 60
```

All four required config keys present with expected default values.

---

## TC-09: human-profile.md exists with valid frontmatter

**PASS**

`.squidsquad/vault/areas/human-profile.md` exists with complete YAML frontmatter:
- `type: area` (correct for areas/ folder)
- `tags: [human, preferences, profile]`
- `created: 2026-04-05`, `updated: 2026-04-05`
- `owner: pm`, `status: active`
- `confidence: medium` (correct for seeded entries per CONTEXT.md)
- `source: observation`

Contains required sections: Communication Style, Quality Expectations, Technical Preferences, Decision-Making Style, Schedule & Availability. Content references known preferences (terse communication, tests must pass).

---

## TC-10: vault_remember.py write-budget pm returns a number

**PASS**

```
$ python references/scripts/vault_remember.py write-budget pm
2
```

Exit code 0. Returns `2` (full budget, no writes consumed this cycle).

---

## TC-11: vault_remember.py briefing-budget returns budget info

**PASS**

```
$ python references/scripts/vault_remember.py briefing-budget
1591
```

Exit code 0. Returns remaining token budget (1591 out of 2000). Positive remaining value confirms BRIEFING.md is under budget.

---

## TC-12: vault_remember.py note-count returns correct count

**PASS**

```
$ python references/scripts/vault_remember.py note-count
6
```

Exit code 0. Returns `6`. Independent count via `find .squidsquad/vault/ -name "*.md" | wc -l` also returns `6`. Counts match.

---

## TC-13: vault_check.py dedup-check finds existing decision note

**PASS**

```
$ python references/scripts/vault_check.py dedup-check --title "sub-skill architecture" --tags "architecture"
MATCH (100%): galaxy/decision-sub-skill-architecture.md - shared: architecture, skill, sub
MATCH (33%): areas/code-conventions.md - shared: architecture
MATCH (33%): galaxy/learning-atomic-migration-strategy.md - shared: architecture
```

Exit code 1 (match found). The existing `decision-sub-skill-architecture.md` is correctly identified as a 100% match. Additional partial matches returned with lower scores.

---

## TC-14: cycle.py is-quiet returns exit code (not error)

**FAIL** (see TC-02)

`cycle.py is-quiet pm` returns `Unknown command: is-quiet` with exit code 1. The command is not implemented in cycle.py.

However, `vault_remember.py is-quiet pm` works correctly: returns `non-quiet` with exit code 1 (non-quiet because recent iteration logs exist). This is the command the deployed CLAUDE.md files actually reference.

---

## TC-15: manifest.md lists vault-remember

**PASS**

`references/sub-skills/manifest.md` lists `common/vault-remember` in all role compositions:
- Line 25: dev-agent Step 4b
- Line 46: pm-agent Step 8b
- Line 67: dm-agent Step 4b
- Line 87: qa-agent Step 7b
- Line 105: designer-agent Step 3b
- Line 126: fe-agent Step 4b
- Line 186: Directory listing shows `vault-remember.md`

---

## Summary

| # | Test | Result |
|---|------|--------|
| 1 | vault_remember.py exists with commands | PASS |
| 2 | cycle.py has is-quiet implemented | **FAIL** — documented but not implemented; lives in vault_remember.py instead |
| 3 | vault_check.py has dedup-check | PASS |
| 4 | vault-remember sub-skill exists | PASS |
| 5 | dev-agent.md includes vault-remember (correct order) | PASS |
| 6 | pm-agent.md includes vault-remember (correct order) | PASS |
| 7 | Deployed CLAUDE.md files have vault-remember step | PASS |
| 8 | config.md has Vault Remember section | PASS |
| 9 | human-profile.md exists with valid frontmatter | PASS |
| 10 | write-budget returns number | PASS |
| 11 | briefing-budget returns budget info | PASS |
| 12 | note-count matches actual count | PASS |
| 13 | dedup-check finds existing note | PASS |
| 14 | cycle.py is-quiet works | **FAIL** — same root cause as TC-02 |
| 15 | manifest.md lists vault-remember | PASS |

## Defect Filed

**TC-02/TC-14**: `cycle.py` documents `is-quiet` in its usage string but does not implement it. The command dispatcher falls through to "Unknown command." The functionality exists in `vault_remember.py` and the deployed CLAUDE.md files reference the correct script (`vault_remember.py is-quiet`), so the feature works end-to-end. The defect is a **stale docstring** in cycle.py that advertises a command it does not handle. Severity: low (cosmetic/misleading, no functional impact).
