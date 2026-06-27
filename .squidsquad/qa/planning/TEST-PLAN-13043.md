# TEST-PLAN-13043 — Vault doc-alignment code fixes (#10838 code-side bucket)

- **Task**: #13043 (type:task, priority:medium, role:skill). 5 code-side items from the VAULT-ARCH alignment audit. (#13042 decay bug is separate.)
- **PR**: #13078, branch `squidsquad/task/13043`, HEAD `e6172605f`. Files: cycle_pre.py, vault_check.py, vault_optimize.py, vault-optimize.md, vault-protocol.md, vault-remember.md + 3 test files. No closing keyword for #13043.
- **Derived**: 2026-06-21 00:25 from the 5-item list (canonical side pre-decided by PM/operator).
- **Items 1+3 (+4 doc-side) touch LLM-consumed sub-skills → CQ HARD GATE** (verifier-authored per #9184).
- **Method**: isolated worktree; source diff review; affected test suites + full static gate; real-vault advisory-vs-gate analysis for the source-required change; live functional check of the `run` alias; fresh-agent CQ.

## Items / ACs

| # | Item | Verification |
|---|------|--------------|
| 1 | Remove vault config gates → always-on (vault-remember/optimize). Code under-scoped by audit: cycle_pre hardcodes vault flags True, `vault_optimize._is_config_enabled`→True; prose gates removed from both sub-skills. config.md field removal = **DM main-landing on merge** (no-fiction-window). | cycle_pre.py + vault_optimize.py diffs; sub-skill prose; CQ1/CQ2. |
| 2 | Add `run` CLI alias to vault_optimize.py (→ run_optimize, same as full-sweep). | Live: `vault_optimize.py run --dry-run` dispatches (rc 0); bogus still errors. |
| 3 | Add STYLES 5th reflection category to vault-remember.md (→ galaxy/style-*.md) + write-priority rank. | Diff; CQ3. |
| 4 | Add `source` to vault_check `REQUIRED_FM_FIELDS` + vault-protocol Level-1 list. | Diff; CQ4; advisory-not-gate analysis. |
| 5 | Implement galaxy 500-line size warning (`check-size`, advisory). | vault_check diff; advisory (exits 0, not counted toward validate pass/fail). |

## Risk analysis — source-required (item 4)
Concern: making `source` required could break a gate if existing notes lack it. Resolved:
- The #12905 galaxy pre-commit guard (`_galaxy_frontmatter_violation`) only checks `---` + a `type` key — it does NOT enforce `REQUIRED_FM_FIELDS`, so source-required does not block vault commits.
- `vault_check check-frontmatter` is advisory (already exits 1 on main due to long-standing missing `updated` across notes) — not a gated test.
- Full static gate green on branch (4813/0) → source-required breaks no gated test.
- Existing notes missing `source`/`updated` are a pre-existing hygiene backlog, out of #13043 scope.

## Handoff to DM (flag in verdict)
DM main-landing spec (apply ON MERGE only): remove `- **Enabled**: yes` under `## Vault Optimize` and `## Vault Remember` in `.squidsquad/config.md` (keep the other fields). Pushing pre-merge would regress vault team-wide (main's current code still reads the field). The PR's always-on code ignores the field, so removal is pure cleanup post-merge.
