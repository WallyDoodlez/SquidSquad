---
type: learning
tags: [testing, isolation, harness, event-mode, monitor, 11586, 11657, 11601]
created: 2026-06-13
updated: 2026-06-13
owner: skill-lead
status: active
confidence: high
source: observation
links: [learning-resume-git-tree-is-truth, decision-clone-isolation-architecture, learning-test-pollution-real-clone-state]
---

# Tests must not mutate SHARED live runtime state — it sabotages concurrent agents

**Observed (#11586 triage, #11657):** the verifier ran `python tests/run_tests.py` while its own event-mode Monitor was armed. The Monitor died (`exit 2, "harness port not found"`) and the agent session ended. Root cause: `test_event_poll_exits_cleanly_when_harness_unreachable` called `port_file.unlink()` on the **shared** `REPO_ROOT/.squidsquad/.harness-port` mid-test (restoring it in `finally`). During that window, the live `event_poll.py` sidecar read a missing port file and, on pre-#11601 code, exited 2 → Monitor died → session ended.

**Why it matters:** in SquidSquad, tests run inside live agent clones while agents are actively cycling. A test that deletes/edits a shared runtime file (`.harness-port`, `.event-state.json`, `.claude-pid`, `current-state`, lock files) is not isolated — it reaches outside the test and can kill a live agent. "Passes in isolation" hides this; the damage only shows when something else is running concurrently.

**How to apply:**
- A test that needs to simulate "file absent / corrupt" must operate on a **temp copy / `tmp_path` / monkeypatched path**, never the real shared file. If a function reads a hard-coded shared path, inject the path (or patch the module global) rather than mutating the real file.
- Two independent defenses are both correct and belong together: (1) make the *consumer* resilient to the missing file (#11601 — `event_poll._discover_port` defaults to 7373 instead of exiting), AND (2) remove/sandbox the *test* that yanks the shared file (#11657). Source-resilience + test-isolation, not either alone.
- When triaging a "live agent died mid-session" report, check whether a test run touched shared state in that window before opening a new root-cause issue — it may already be covered by source-hardening + test-removal work. See [[learning-resume-git-tree-is-truth]] for the sibling "the failure may already be tracked elsewhere" reflex.

**Sibling failure mode (same root cause, different blast):** [[learning-test-pollution-real-clone-state]] covers the *git-hygiene* facet — tests mutating git-TRACKED clone files (e.g. `config.md` ship-counter) re-stage them into the index, leaking into feature-branch commits. Same anti-pattern (tests touching the real clone instead of `tmp_path`), but the consequence is a polluted commit rather than a killed agent, and the defense is `git checkout HEAD -- <file>` before commit rather than test sandboxing. The two together: tests must isolate from BOTH the clone's runtime-control files (this note) and its git-tracked state files (the sibling).
