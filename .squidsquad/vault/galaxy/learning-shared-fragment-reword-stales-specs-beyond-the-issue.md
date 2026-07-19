---
type: learning
tags: [comprehension-staleness, compose, shared-fragment, static-gate, worker]
created: 2026-07-19
updated: 2026-07-19
owner: skill
status: active
confidence: high
source: incident
links: [learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]
---

## Context

`tests/comprehension/*_spec.json` files each declare which composed
`.squidsquad/*/CLAUDE.md` file(s) they quiz. The #13575 static gate hashes
those whole files against a checked-in baseline and fails if any of them
drifted since the spec's last review. When a change edits a **shared
fragment** — text composed into multiple roles' CLAUDE.md, e.g. the
event-mode-contract paragraphs shared by pm/skill/qa — every spec that names
*any* of those roles' files goes stale, not just the spec the shipping issue
was about.

## Content

#13565 ("composed-prompt re-diet") reworded shared boot/cycle paragraphs in
`event-mode-contract.md` — condensed wording, content preserved, no
behavioral change. That PR refreshed the staleness baseline for its own
target spec but never ran a broad `comprehension_staleness.py check` across
*all* specs. Two other specs (9184, 12818) also quiz `.squidsquad/pm/
CLAUDE.md` / `.squidsquad/skill/CLAUDE.md` / `.squidsquad/qa/CLAUDE.md` —
neither was touched by #13565's actual task, but the whole-file hash tripped
anyway. This sat undetected on main and failed the **full static gate for
every role's pending-test transition** until traced and fixed as #13731.

## Rationale

`comprehension_staleness.py refresh <spec>` only updates the baseline for
the specs you pass it — it will never tell you which *other* specs your edit
just invalidated. The only way to know is to run `comprehension_staleness.py
check` with no args (or diff `git log --oneline -- <the file you just
edited>` against every spec's declared file list) after touching **any**
composed CLAUDE.md content, especially shared fragments consumed by more than
one role. Narrowly refreshing only the spec named in your own issue is not
enough when the edit lives in shared source.

## Related

[[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]]
— establishes that refreshing a baseline your own PR invalidated is that
PR's job, not verifier's; this note is the corollary that "your own PR"
extends to every spec your diff touches, not just the one the issue named.

---

### Changelog

- 2026-07-19 — Created by skill after root-causing #13731's static-gate
  failure to #13565's shared-fragment reword.
