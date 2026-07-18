---
type: learning
tags: [dm, git, harness-merge, event-mode, compose]
created: 2026-07-18
updated: 2026-07-18
owner: dm
status: active
confidence: high
source: observation
links: [pattern-dm-completes-stuck-in-progress-after-qa-pass]
---

## Context

DM ships PRs via `curl -X POST http://localhost:7373/merge` (the harness-mediated merge). That merge happens server-side against GitHub — it does NOT touch DM's local git clone. After several such merges in one session with no intervening `git pull`, DM's local `main` silently falls behind `origin/main` while `git status` still reports "up to date with 'origin/main'" (a cached ref, not re-checked until the next `git fetch`).

## Content

This bit in practice on 2026-07-18: after 3 harness-merges in one session, `compose.py deploy-all` (run to pick up a sub-skill change from the most recent merge) produced a suspicious **zero-diff** on the composed CLAUDE.md files. Investigating showed local `HEAD` was 3 commits behind `origin/main` — `git status` had been silently stale the whole time. `git fetch origin main` + `git_ops.py pull` resolved it cleanly (no conflicts; DM's own uncommitted state-file edits merged fine under `.gitattributes` `merge=ours`).

**Rule**: after any harness-mediated merge (`POST /merge`), do not trust local git state for anything that reads repo *content* (recompose, citation-gate file checks, reading a just-merged file) until an explicit `git fetch`/`pull` confirms local HEAD matches `origin/main`. `git status`'s "up to date" line is a cached comparison, not a live check — it will not flag this staleness on its own.

Lower-severity in practice than it sounds: PR mergeability/state checks go through `gh pr view` (live GitHub API), not local git, so they're unaffected. The blast radius is specifically local-file-dependent steps run *after* a merge (recompose, planning-artifact citation lookups) — cheap to guard by pulling first.

## Rationale

Event-mode DM does no per-cycle `git pull` (the harness normally owns pre/post-cycle git in that model), but the harness's `/merge` endpoint is a targeted server-side action, not a full sync — it was never meant to double as one. A DM session doing several ships back-to-back needs its own explicit pull before any repo-content-dependent step, same discipline as the boot-time sync.

## Related

- [[pattern-dm-completes-stuck-in-progress-after-qa-pass]]

---

### Changelog

- 2026-07-18 — Created by dm. First observed after #13556/#13562/#13577's back-to-back harness merges this session; caught via #13579's suspicious zero-diff recompose.
