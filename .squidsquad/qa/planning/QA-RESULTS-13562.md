# QA-RESULTS #13562 — working-state.md unbounded embed in cycle-input.json

**Verdict: PASS → pending-ship.**

## Summary

`cycle_pre._read_working_state` used to embed the entire `working-state.md`
verbatim into `cycle-input.json` with no size gate — a drifted append-only
journal (dm: 188KB per the issue) cost every cycle 32-48K dead tokens. PR
#13576 caps the `raw_content` embed at 8KB, keeping the TAIL (journals append;
newest is actionable) behind an explicit `[TRUNCATED (#13562): ...]` marker
that instructs the agent to rewrite the file to spec shape — while structured
field parsing (`task`/`status`/etc.) still runs against the full,
un-truncated file. A symmetric warning fires in `cycle_post` on oversized
writes (warn-only — the write still succeeds; the embed-side cap is what
bounds token cost). A second commit addressed 4 DeepSeek review findings:
shared-import to prevent the two thresholds drifting apart, a line-boundary
edge case (tail's only newline is its last byte → marker-only, no partial-line
leak), multibyte boundary safety across 2/3/4-byte UTF-8 sequences, and a
tightened marker-text assertion.

## Independent verification

- **Own 250KB fixture** (different shape from the PR's own 200KB test):
  structured fields parsed correctly from the full file; embed capped to
  8453 bytes; newest content present, oldest absent; marker text correct.
- **Live-checked against real role state**: ran the actual function against
  my own qa role's live `.squidsquad-state/qa/working-state.md` (231 bytes,
  under cap) — embedded verbatim, byte-identical, no marker (confirms the
  under-cap path organically, not just via synthetic fixtures).
- **Live-checked the write-side warning**: an 11KB synthetic update through
  the real `cycle_post._do_working_state_update` — WARNING fires on stderr
  referencing #13562 and the role, and the file is still written in full
  (warn-only, non-blocking, as specified).
- **Sequencing check**: `git diff origin/main...HEAD -- .squidsquad/config.md`
  is empty and `Threshold` is still 70 in the live config — confirmed the
  70→75 Context Threshold bump was correctly deferred out of this PR, per the
  issue's own stated sequencing.
- **CQ-gate call**: independently concurred with skill's read that the
  runtime-generated marker string is cycle-input **data**, not a
  CLAUDE.md/sub-skill/SOUL.md instruction-file change — no CQ spec required.
- Full `test_cycle_pre.py` + `test_cycle_post.py` on a freshly re-fetched
  branch merged with current `origin/main`: **262/262 PASS**, 0 regressions.
- Full static gate on the combined state: 3 failures — identical to, and
  confirmed disjoint from, the pre-existing #13577 finding surfaced during
  #13556's verify pass. **0 new failures from #13562.**

## Records

- `TEST-PLAN-13562.md` — full AC derivation and evidence.
