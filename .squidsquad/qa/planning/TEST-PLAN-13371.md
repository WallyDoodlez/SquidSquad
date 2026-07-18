# TEST-PLAN #13371 — pr_create neutralizes GitHub closing keywords

**Derived from the issue body "Suggested fix" — not the diff.**

Bug class: a PR body carrying a GitHub closing keyword ("Fixes #N") auto-closes
the issue at squash-merge, bypassing the verifier's pending-ship transition and
the DM's ship gate (counter/changelog/verdict record). Observed live twice
(#13335 via PR #13346; #13373 via PR #13458).

## Acceptance Criteria (independent reading — scope = code-only guard in git_ops.py pr_create)

| AC | Contract |
|----|----------|
| AC1 | `pr_create` neutralizes closing keywords (Close/Fix/Resolve + inflections) directly followed by an issue ref to a non-closing form, on **both** the gh-CLI path and the forge-adapter (non-GitHub) path |
| AC2 | Ref forms covered: `#N`, `GH-N`, `owner/repo#N`, full issue URL — each with optional colon separator |
| AC3 | Word-boundary safety: sub-words containing a keyword ("prefix", "hotfixes", "affixes") are never matched |
| AC4 | A keyword NOT immediately followed by a ref is left alone (matches GitHub's own linking rule) |
| AC5 | The ref (and colon) is preserved verbatim — only the verb changes |
| AC6 | Regression test suite covers the rewrite; empty/None body passthrough; full static gate green |

## Verification (branch squidsquad/task/13371, combined with current main — see below)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 (gh path) | `TestPrCreateNeutralizesBody::test_body_neutralized_before_gh` (PR's own test) | **PASS** |
| TC2 | AC1 (forge-adapter path) | **Independent** black-box probe (not in the PR's own suite): monkeypatched `forge_adapter` module, called `pr_create` with provider `gitea`, confirmed the adapter's `create_pr` received `"Addresses #999"` not `"Fixes #999"` | **PASS** |
| TC3 | AC2 | `test_cross_repo_reference`, `test_issue_url_reference`, `test_colon_separator_preserved`, `test_all_keyword_variants_rewritten` (PR's own) + my own probes (`GH-42`, `owner/repo#7` with colon) | **PASS** |
| TC4 | AC3 | `test_subword_keywords_not_matched` (PR's own) + my own probe (`"Prefixes are safe. Suffixed too. Affixes fine."`) | **PASS** |
| TC5 | AC4 | `test_keyword_without_immediate_reference_untouched`, `test_bare_reference_no_space_untouched` (PR's own) + my own probe (`"this closes out the sprint, not an issue"`) | **PASS** |
| TC6 | AC5 | `test_colon_separator_preserved`, `test_cross_repo_reference` (PR's own) | **PASS** |
| TC7 | AC6 | 13/13 PR tests pass; full static gate on combined state 5425/0 | **PASS** |

## Branch-staleness handling

`squidsquad/task/13371` forked from `8b8bf7b82`, before both #13323 (merged
today) and #13434 (merged today) landed on main. Verified combined
post-merge state via local `git merge origin/main --no-edit` (no push,
verifier-only local check) — clean merge, no conflicts (git_ops.py's #13371
region does not overlap the other two merges' files). Full static gate on
combined state: 5425/0.

## Notes

- `type:issue`, severity:low — auto-approved, no human gate.
- No comprehension spec (code-only change, not an LLM-consumed instruction).
- Noted but not a gap: PR #13544's own body contains a self-neutralized
  cosmetic artifact ("auto-Addresses #13335" instead of "auto-closed #13335")
  — confirmed this is the guard correctly firing on prose that itself contains
  a closing-keyword+ref pattern, not a bug. Worker flagged this transparently
  in their pending-test comment.
