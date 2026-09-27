# Fix plan -- #14183

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

#13515 added `status:blocked` (owned-but-parked) with a `blocked -> in-progress`
transition but no resume trigger. The L1 Soul claimed "a forge event surfaces
the change". But the blocker is usually a different item, so its merge or close
emits events for that item's owner only. `work_queue()` skipped blocked items
entirely, and pipeline-sentinel 2.1 excluded them. Resuming lived only in the
parking agent's conversation context, which a respawn wipes. The live exposure
was #14181, #14133 and #14130, all parked on PR #14182.

## Intended direction

This is deterministic, in `references/scripts/tracker.py`:
- AC1: `transition <n> ... blocked` requires `--blocked-on <N>[,<N>]`
  (fail-closed, exit 2, before any forge write, except under the human
  `--force`). After the label change it posts a marker comment
  `<!-- squidsquad:blocked-on N -->`. The latest marker wins.
- AC2: `blocked_items()` reads each parked item's marker and checks every
  blocker via `gh api repos/:owner/:repo/issues/N`. A blocker is resolved when
  it is closed (a merged or closed PR, or a closed issue) or at `status:shipped`.
  A failed lookup keeps the item parked, and the next read retries.
  `work_queue()` lists resumable parks right after in-progress work (status
  `blocked`, `resumable: true`). Parks with no marker (pre-#14183) are always
  listed, so they resurface to be re-parked rather than strand. It only runs
  when the role has a blocked item, so the common path costs nothing extra.
- AC3: a new `tracker.py blocked-resumable [--role] [--min-age]` command, and
  pipeline-sentinel **4h** runs it with `--min-age 90`. PM's remedy is a
  `work-assign` wake, because only the assignee may resume. The 2.1 exclusion
  is kept for parks whose blocker is still open.
- AC4: the Soul block-and-continue sentence now names the real mechanism. The
  event-mode-contract Case D 2a park step and the sentinel 4g hint carry
  `--blocked-on`.

I rejected a harness/EAD event for the parked item's owner. It needs a
reverse index from blocker to parked items, and the AC allows a work_queue or
sentinel path.

## Impact

Every role's composed CLAUDE.md changes via the L1 Soul. `compose.py
deploy-all` was verified to carry the new sentence into pm/skill/qa/dm and
leave no stale claim. Existing parks without a marker resurface once in
`work_queue()` until re-parked with `--blocked-on`. Callers of
`transition ... blocked` without `--blocked-on` now get exit 2. The only such
callers are agents following the updated docs.

## Vault context consumed

- [[learning-sequential-phase-gates-are-prose-only-not-mechanical]] -- same failure shape (a dependency recorded only in prose/context, invisible to work_queue); fixed here with a machine-readable marker that work_queue reads

## Applicable rules

- None matched (searched: blocked, park, resume, work-queue, pipeline-sentinel)
