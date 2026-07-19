---
type: learning
tags: [comprehension-staleness, cli-usage, worker, tooling-footgun]
created: 2026-07-18
updated: 2026-07-18
owner: skill
status: active
confidence: high
source: observation
links: [[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]]
---

## Context

`comprehension_staleness.py refresh <spec>...` takes **full spec filenames**
(`1428_spec.json`), not bare issue numbers (`1428`). Passing the wrong form
does not error loudly.

## Content

Ran `comprehension_staleness.py refresh 1428 13464 10678` (bare numbers) this
session. Output was:

```
WARNING: no such spec 1428
WARNING: no such spec 13464
WARNING: no such spec 10678
baseline refreshed for 3 spec(s) -> .staleness-baseline.json
```
exit code 0.

The summary line and exit code both look like success. In reality
`refresh()` silently skipped all three names (none matched `load_specs()`'s
keys) and wrote **zero** baseline entries — confirmed only by re-running
`check()` and seeing all three specs still flagged stale. Filed as #13710
(the underlying bug: the summary prints the *requested* count, not the
actual refreshed count, and `main()` never surfaces partial/total failure
via exit code).

**Correct invocation**: always pass the full `<issue>_spec.json` filename,
e.g. `comprehension_staleness.py refresh 1428_spec.json`. After any refresh,
re-run `comprehension_staleness.py check` and confirm a clean (exit 0, no
output) result before trusting the refresh — don't trust the refresh
command's own success message.

## Rationale

This tool guards the anti-silent-staleness gate (#13575) — its own docstring
says the point of `refresh` is to make re-review "a conscious act, never an
implicit pass." A CLI usage mistake that itself produces a false "success"
message undermines that guarantee at exactly the moment it matters (a
baseline refresh that silently didn't happen looks identical, on the
surface, to one that did).

## Related

[[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]] — same tool, different failure class (role-boundary discipline vs CLI usage).

---

### Changelog

- 2026-07-18 — Created by skill after hitting this directly during #13565's baseline-refresh follow-up; filed #13709/#13710 for the underlying script bugs.
