# CONTEXT-13566 — scan-history pruning + size-guarded fallback read

**Light mode** (XS, no dependencies, ACs already fully specified at filing time; operator approved as part of "go ahead on all of context trimming", 2026-07-18).

## Scope

`scan_index.py`'s rebuild path gains a retention cap on `scan-history.md` (keep newest ~100 entries, roll the rest into `scan-history.archive.md`), and the documented fallback read path (`improvement-scan.md` / `-slim`) reads only the tail (~50 entries) instead of the whole file. One-time prune applied to all four roles' existing files.

## Locked Decisions (human decided)

- Proceed exactly as scoped in the issue body — no changes to scan cadence/burst config or scan content format (explicit out-of-scope in the issue).

## Worker Discretion (worker agent can choose)

- Exact retention count tuning around the ~100/~50 targets in the issue body, as long as the size problem (currently 137KB/1,902 lines on skill) is durably resolved.
- Archive file naming/rotation scheme beyond the single `scan-history.archive.md` suggested.

## Side Effect Mitigations (required)

- Archived entries must remain findable (not deleted) — same principle as the BRIEFING.md archive precedent (#13563).
- CQ scenario required for the fallback-instruction wording change (per issue AC2).

## Upgrade Path (required)

- One-time prune of existing oversized files across all four roles, via the new code path (not a manual one-off) — so existing installs self-heal on next rebuild rather than needing a separate migration step.

## Out of Scope

- Scan cadence/burst config changes.
- Scan content format changes.
