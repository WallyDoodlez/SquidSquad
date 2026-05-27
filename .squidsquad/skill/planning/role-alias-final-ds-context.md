# Code review request: aspirational §4.1 + role:* label clarification

## What this commit (61aa5156) does

Closes two open questions from your previous review (DS findings 6, 10) by applying the user's chosen options:

**HARNESS-ARCH.md §4.1 — option (b) aspirational:**

User chose to keep `alias` in the response shapes as a forward-looking contract. To address the "internal inconsistency" you flagged (some rows had `alias`, others didn't), I made the per-agent response shapes consistent — added `alias` to `/health`, `start`, `stop`, `restart` so they match `/agents` and `/agents/{role}`. Then added a status note explicitly calling out that these shapes are aspirational and land with #10358; clients today should read `claude_pid` directly and treat the `role` field value as the alias.

**AGENT-RUNTIME.md §4.4 prose — doc-only convention update:**

User chose to leave the actual GitHub labels alone (high blast-radius — touches every issue + tracker.py + composed agent files), and just clarify in the doc that the label *key* `role:` is legacy code-compat while the *value* is always alias-typed. The prose now notes a key-rename to `alias:` is in #10358's family but currently out of scope on that task.

## What I want you to look for

1. **§4.1 aspirational note clarity:** is the aspirational-vs-current distinction clear enough that a reader writing a new client today wouldn't be confused about which field to use? The risk is someone reads "response includes `alias`" and codes against a field that doesn't exist yet.

2. **Internal consistency of §4.1:** I added `alias` to `/health`, `start`, `stop`, `restart` for consistency. Spot-check the table — are there other rows I missed where a per-agent operation returns a shape and should also have `alias` for consistency? (Not asking about non-agent endpoints like `/status` or `/shutdown`.)

3. **§4.4 (AGENT-RUNTIME.md) label-rename framing:** the prose says the label key rename is "currently out of scope on [#10358] to limit blast radius." Is that framing accurate? Are there other reasons it's out of scope that I missed (e.g. it affects label-search semantics, breaks running cycle scripts, etc.)?

4. **Cross-doc consistency check:** I left `role:*` label references untouched everywhere ELSE in the codebase (composed CLAUDE.md files, sub-skill sources, INDEX docs). Is there any place in `docs/` (the architecture docs only — not composed agent files) where the same `role:*` convention is described and now needs the same legacy-key clarification I added to §4.4? If so, flag it; I'll apply.

5. **Anything else off:** typos, broken cross-refs, lurking issues in the diff.

## What's in the diff file

`role-alias-final-diff.patch` is the diff for commit 61aa5156 (3 files, 18 insertions, 6 deletions). It's small — much smaller than the prior 153-line cleanup commit. Touches:

- `docs/HARNESS-ARCH.md` — §4.1 table rows + new aspirational note paragraph
- `docs/AGENT-RUNTIME.md` — single sentence in §4.4 prose
- `.squidsquad/skill/planning/REVIEW-ROLE-ALIAS-AUDIT.md` — audit-record update marking the open Qs resolved

## Format of response

Same structured-findings format as before: BLOCK / FLAG / NIT with file + line refs and concrete suggested fixes. If clean, say so explicitly.
