# TEST-PLAN-11140 — Composed CLAUDE.md major H2 sections get orientation prose

- **Issue**: #11140 (type:issue, severity:medium, role:skill) — composed `.squidsquad/<role>/CLAUDE.md` H2 sections drop straight into sub-content with no orientation paragraph; a fresh agent boot has no prior context. No formal AC list — derived from symptom + suggested scope.
- **PR**: #13112, branch `squidsquad/task/11140` @ `eb2bf91fa`. Files: `SOUL.md` (+2), `responsibility.md` (new, +6), `installer-files.txt` (+2/-1). LLM-consumed instruction change → CQ.
- **Derived**: 2026-06-21 01:05.
- **Method**: isolated worktree; `compose.py deploy-all` per-H2 orientation inspection; installer registration/count; fresh-agent CQ; full static gate.

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | Major H2s that drop straight into sub-content get a 2-4 sentence orientation lede (purpose + reader-use) before the first H3. | Composed inspection: Soul + Responsibility now have ledes (were bare); Identity / Vault / Agent Functions already had orientation prose (pre-existing L1) — no redundant edit. |
| AC2 | `project-context` correctly handled (scoped out as L4-exclusive per COMPOSE-ARCHITECTURE §3.3, flagged to PM — not an oversight). | Composed: ## Project Context still bullets; skill flagged the L4-exclusive constraint. |
| AC3 | New L1 `responsibility.md` registered in installer-files.txt; Total bumped + matches. | Diff: Total 250→251, responsibility.md listed, count integrity OK. |
| AC4 | Ledes compose into all 4 role CLAUDE.md. | deploy-all + composed inspection. |
| AC5 | No regression. | `run_tests.py static`. |
| AC-CQ | A fresh agent reading a lede correctly states the section's purpose + when to consult it (the fix's goal: sections self-orient). | `tests/comprehension/11140_spec.json` + fresh sonnet run. |

## DM watch (merge-time, non-blocking)
#11140 (installer-files Total 250→251, +responsibility.md) and the pending-ship #13101 (Total 250→252, +identity.md+vault.md) both edit the `# Total:` line + nearby manifest region → they WILL conflict at merge. DM should reconcile to **Total 253** and union all three new entries (responsibility.md + identity.md + vault.md). #13101's L1-slot completeness test then requires responsibility.md present (it has `slot:` frontmatter) — satisfied by #11140's entry.
