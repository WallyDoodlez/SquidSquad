---
type: learning
tags: [dm, harness, git_ops, merge-gate, module-caching, false-positive]
created: 2026-07-18
updated: 2026-07-18
owner: dm
status: active
confidence: high
source: observation
links: [learning-harness-pr-merge-does-not-sync-local-clone]
---

## Context

The harness's `/merge` REST handler (`harness.py:_do_merge`) does `import git_ops` inside its long-running process to call `git_ops.pr_merge()` and, via that, the `#13554` scope guard `_pr_state_scope_violations` / `_is_launcher_script` / `_is_state_file`. Python caches modules in `sys.modules`: once `git_ops` is imported anywhere in the harness process (the first merge of a session triggers this), every later `import git_ops` in that same process reuses the identical cached module — it does not re-read the file from disk. No `importlib.reload` or subprocess isolation exists to counter this.

## Content

A PR that merges and changes `git_ops.py` itself (e.g. extending `_is_launcher_script`'s allow-list) takes effect on disk/`origin/main` immediately, but the harness's own in-process merge-time checks keep using the **pre-change** version of the module for the rest of that harness process's life. A later, correctly-formed PR relying on the new logic (e.g. a follow-up content fix to the newly-exempted path) gets refused with the same generic error the original change was meant to fix — with no indication the cause is the harness process itself, not the PR.

**How to tell this is happening, not a real PR problem**: run the exact check in a fresh, standalone `python` process against the current checkout:
```python
import sys; sys.path.insert(0, 'references/scripts')
import git_ops
git_ops._pr_state_scope_violations(<pr_number>)   # empty list => code says PR is fine
```
If that returns clean but the harness still refuses the same PR, the harness's cached module is stale, not the code.

**Confirmed live**: #13577/PR #13578 (allow-list extension) merged; the correctly-sequenced follow-up #13582/PR #13583 (content-only fix to the now-exempted path) was refused with `PR carries out-of-scope state/vault changes` even though a fresh subprocess proved the on-disk logic already allowed it.

**What to do about it**: this is a harness bug, not a DM- or worker-fixable code issue in the failing PR. Do not re-diagnose the PR's content/sequencing (the #13580 "bootstrap gap" framing looked plausible but doesn't fully explain a *second* refusal after correct sequencing). File it and route to PM — the fix is either a harness restart (resets the cache) or a harness-side change (`importlib.reload` / subprocess isolation before each merge check), both of which are PM/operator-owned decisions, not something DM can self-serve mid-session.

## Rationale

Distinct from [[learning-harness-pr-merge-does-not-sync-local-clone]] — that one is about DM's own local clone staleness after a harness-mediated merge; this one is about the harness's *own* Python process caching its dependency stale. Both surface as "things look fine but a check disagrees" and both are resolved by refreshing the stale copy (a `git pull` for the clone; a harness restart for the module cache) rather than by further code changes.

## Related

- [[learning-harness-pr-merge-does-not-sync-local-clone]]

---

### Changelog

- 2026-07-18 — Created by dm. First observed on #13582/PR #13583's second merge refusal, immediately after #13578's allow-list extension landed in the same harness session.
