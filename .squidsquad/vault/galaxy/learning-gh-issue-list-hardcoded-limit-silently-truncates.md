---
type: learning
tags: [gh-cli, tracker, harness, truncation, silent-failure, pagination, scale]
created: 2026-07-18
owner: pm
status: active
confidence: high
source: observation
links: []
---

## Context

As the repo's open-issue count grew past 150, four independent `gh issue list ... --limit 50` call
sites were found silently dropping issues, all discovered within days of each other:
- #13555 — `harness.py`'s `ExternalActivityDetector._check_for_changes` (155 open, 105 invisible)
- #13602 — `pipeline-sentinel.md`'s two queries (halt-detection sweep + double-pickup check)
- #13660 — `tracker.py`'s `list_all_open()` (150 open, 100 invisible; also flagged sibling
  `list_issues()`/`list_by_labels()`, same cap, lower risk only because current in-progress/approved
  counts stay small)
- #13661 — `cycle_pre.py`'s own `gh issue list` fetch (same class, filed same day as #13660)

`gh issue list` defaults/callers frequently hard-code `--limit 50` because that was a safe assumption
early in the project when open-issue counts were small. It stopped being safe once the backlog grew,
and every instance failed the same way: **silently**. Nothing logged when the cap was hit, so each
caller's result set looked complete right up until someone cross-checked it against a direct `gh`
query with a much higher limit.

## Lesson

**A hard-coded `--limit N` on `gh issue list` (or any paginated forge query) is a latent silent-truncation
bug the moment real volume exceeds N — and it will recur at every call site independently, because each
one was written in isolation without knowledge of the others.** `gh issue list` returns newest-first, so
truncation silently drops the *oldest* open items — exactly the ones most likely to be a stale/starved
handoff or backlog item, which is the worst place for it to bite.

This directly degraded a PM check-in this session: `tracker.py list-all-open` reported 17 pending tasks
when the real count (verified via direct `gh issue list --limit 500`) was 141 — an 88% undercount that
would have gone unnoticed without an independent cross-check.

## How to apply

- **When scanning or auditing any script/sub-skill that shells out to `gh issue list` (or similar
  paginated `gh`/API calls), grep for `--limit` and sanity-check the literal against current real
  volume** (`gh issue list --state open --json number --jq length` or equivalent) — don't assume a
  fix in one call site covers siblings elsewhere in the same file or a different file.
- **Prefer detecting truncation over just raising the cap**: raising `--limit` to 500 is a cheap fix
  today but re-introduces the same bug at a higher volume later with zero warning. The better fix
  (per #13555's precedent) is to check `returned_count == limit` and log/print a WARNING — that turns
  a silent failure into a visible one, buying time to do a real fix (pagination or narrower filtering)
  before it silently bites again.
- **When reporting pipeline/backlog numbers to the human, don't trust a single script's output at
  face value if the count looks suspiciously round or suspiciously low relative to known project
  activity** — cross-check with a direct, differently-scoped query before presenting numbers as fact
  (this is the same discipline as [[feedback_trust_script_output]], but the corollary: trust script
  output over *conversation memory*, but still cross-check *scripts against each other* when a number
  seems off).
- If you find one instance of this bug, grep the whole repo for the pattern before filing — it's
  cheaper to report 2-3 sibling call sites in one issue (as #13602 and this session's #13660 did) than
  to have four separate near-identical issues filed across a week.
