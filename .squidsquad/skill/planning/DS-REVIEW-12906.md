# DS Review — #12906 (Phase 1 of #12895): harness recompose ensure-main + pull-first

**Reviewed diff:** `references/scripts/git_ops.py`, `references/scripts/harness.py`, `references/scripts/l4_file_watcher.py`
**Verdict:** 4 findings, all `warning` severity. All resolved before pending-test.

## Findings & resolution

| # | File | Issue | Resolution |
|---|------|-------|-----------|
| F1 | l4_file_watcher.py | Freshness-guard abort was silent (no event), inconsistent with the registry-failure path which emits `compose-failed` to PM. | `_freshen_or_abort` now emits a `compose-failed`-to-PM event (`reason: freshen-source-failed`) on abort, mirroring the registry-unreadable precedent. Both batch entries (`_on_change`, `recompose_path`) pass `emit_event`. Tests updated to assert the event. |
| F2 | harness.py | Post-merge `ensure_main_and_pull` called directly; if it raised, the outer `_do_merge` except would emit a misleading 2nd `pr-merged success:False` after the truthful `success:True`. | Resolved by F3 root fix — the function can no longer raise, so the misleading path is unreachable. Harness `fresh_ok` check already handles the `(False, …)` return cleanly. |
| F3 | git_ops.py | `ensure_main_and_pull` documented "Never raises" but had no guard. | Wrapped body in blanket `try/except` returning `(False, f"unexpected: {exc!r}")` — contract now enforced at source so the direct harness caller can trust `ok`. Added regression test (OSError from `_run` → `(False, …)`, no propagation). |
| F4 | l4_file_watcher.py | Docstring "once per recompose batch" inaccurate — it's once per role-class per debounce; a multi-file burst pulls per role-class (later pulls = fast no-ops). | Docstring clarified to "once per role-class recompose"; noted the later pulls are harmless already-up-to-date no-ops. |

## Notes
- DS run via `model_router.py route --task-type code-review` (DeepSeek), exit 0.
- All fixes are low-risk hardening (observability + contract enforcement + doc accuracy); no behavioral change to the happy path.
