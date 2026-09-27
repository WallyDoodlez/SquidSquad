# Fix plan -- #14162

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

Issues are auto-approved and skip PM task intake, and the filing shapes in
`common/tracker-protocol.md` (Bug fix, Improvement-scan finding, Cross-role)
and `roles/pm/issue-filing.md` asked for no acceptance criteria. An issue whose
fix changes LLM-consumed instructions therefore reached pickup with no CQ
requirement: #14114, #14147 and #14137 were all backfilled by hand today.

## Intended direction

Mechanism: the filing shapes carry ACs, with a deterministic backstop (not PM
routing).

- Every issue shape ends with `## Acceptance criteria`. A rule block says to
  add a CQ line (spec path plus 2-3 scenarios) when the fix touches
  instructions; a pure code fix gets ACs without it. The three scan filing
  steps and PM issue-filing point at it.
- `tracker.py create-issue`: if the body names an instruction surface
  (references/sub-skills|roles, .squidsquad/project, CLAUDE.md, SOUL.md) and
  has no CQ mention, it appends a CQ criterion (as a line in a trailing AC
  section, else as a new section) and notes it on stderr.
- Worker `triage-issues` pickup guard (AC2): for a legacy instruction-changing
  issue without ACs/CQ, add a one-line PM request to the pickup comment and
  continue. Non-blocking.

## Impact

- `tracker.py` (every issue filed from now on); `tracker-protocol.md` (shared,
  every role); improvement-scan x3; PM issue-filing; worker triage-issues.
- Instruction changes reach agents on recompose / next read.

## Vault context consumed

- [[learning-shared-fragment-reword-stales-specs-beyond-the-issue]] -- tracker-protocol is shared by every role, so expect CQ staleness flags on specs beyond this issue; re-review each before refreshing
- [[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]] -- the staleness refresh is done in this PR by the author after re-review, not left to the verifier

## Applicable rules

- None matched (searched rules lane: tracker, issue-filing, comprehension)
