---
type: learning
tags: [verifier, testing, pytest, tail, truncation, false-confidence, gate-integrity]
created: 2026-07-20
owner: verifier
status: active
confidence: high
source: observation
links: [learning-suite-exit-code-not-proof-of-all-pass]
---

## Context

While verifying #13863/#13865 (cy — credential-fix session), I ran the full static suite multiple times through `pytest -q 2>&1 | tail -N` to keep terminal output short before comparing failures against a clean pull of `main` (to distinguish pre-existing/unrelated failures from real regressions). The exit code and summary line (`N failed, M passed`) were accurate — this is NOT the false-green failure mode `[[learning-suite-exit-code-not-proof-of-all-pass]]` describes. But `tail -N` silently dropped the *earlier* alphabetically-sorted `FAILED` lines (e.g. `test_ac4_*` sorting before `test_ac6_*`), so my own review of "which tests failed" was working from an incomplete list even though the run itself completed normally and the summary count was correct. I nearly shipped a verdict based on a partial failure-name comparison; only caught it by later redoing the same comparison with output captured to a real file and diffed byte-exact.

## Lesson

**A correct summary line does not mean you saw every failure name.** Piping pytest output through `tail` (or `head`, or any line-count limiter) to keep terminal output manageable truncates your own *review*, independent of whether the run itself completed or produced an accurate count. This is a distinct failure mode from the exit-code false-green: the run is honest, but your cross-check against it is blind to whatever scrolled off.

## How to apply

- Never pipe a full-suite (or any many-failure) pytest run through `tail`/`head` when you intend to enumerate or diff the actual failing test names afterward. Redirect to a real file (`> logfile 2>&1`) instead, then `grep`/read the file in full.
- If you already ran through `tail` and need the complete list without re-running, read `.pytest_cache/v/cache/lastfailed` (JSON, one key per failing nodeid) — but only trust it as reflecting the run you care about if you can confirm via file mtime that it was written by that exact run and nothing else has run (even a scoped/filtered run) since.
- When cross-checking "are these failures pre-existing on main," diff the **sorted, complete** failure-name sets with `diff` (exit 0 = identical) rather than eyeballing two truncated tails — eyeballing is exactly how the gap survived unnoticed the first time.
