# QA-RESULTS #13579 — working-state.md sub-skill silent on #13562 size discipline

**Verdict: PASS → pending-ship.**

## Summary

PM's own improvement-scan finding: #13562 shipped a runtime size discipline
for `working-state.md` (8KB cycle-input embed cap, tail-truncation marker,
oversized-write warning) but the authoring sub-skill
(`references/sub-skills/common/working-state.md`) agents actually write
against never mentioned it — an agent following the sub-skill verbatim could
still drift into the exact append-only-journal failure #13562 fixed, only
discovering the cap from runtime truncation after the fact. Skill added one
additive bullet documenting the bound, the tail-truncation + marker behavior,
the write-side warning, and that history belongs in git/iteration logs, not
an in-file journal.

## Independent verification

- Read the full updated sub-skill: the new bullet is accurate against
  #13562's actual shipped behavior (verified directly during #13562's own
  QA pass this session) and does not crowd out or contradict the existing
  clear-on-complete guidance.
- **Comprehension gate (#9184, hard gate — this is an LLM-consumed
  instruction-file change)**: spawned a fresh sonnet general-purpose agent,
  given ONLY the modified file's content inline, explicitly instructed to use
  no other file, tool, or prior knowledge. Asked 4 questions covering the
  size bound + consequence, the clear-on-complete rule, the journal-growth
  remediation + where history belongs, and the tail-vs-head truncation
  direction. **4/4 correct, zero must_not violations** — satisfies PM's
  stated AC (fresh agent states the size bound and clear-on-complete
  unprompted). Spec: `tests/comprehension/13579_spec.json`.
- `pytest tests/ -k "working_state or sub_skill"` on combined state: 60
  passed, 1 skipped, 0 failed.
- Full static gate on combined state: 1 failure, 0 errors, 5511 gated —
  confirmed identical to the already-tracked #13582 (`inject-permissions.ps1`),
  not introduced by this PR.

## Records

- `TEST-PLAN-13579.md` — full AC derivation and evidence.
- `tests/comprehension/13579_spec.json` — CQ spec, PASS.
