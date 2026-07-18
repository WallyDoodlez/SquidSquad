---
type: learning
tags: [verification, merge, pr-protocol, self-correction]
created: 2026-07-11
source: "#13457 (verifier-filed, resolved inverted)"
---

# Canonical verifier merge is the harness POST /merge, not git_ops.py pr-merge

Per `references/sub-skills/common/pr-protocol.md` (the interface lock, ~L79, Lane A) the **canonical** verifier auto-merge is: `gh pr ready <PR>` then `POST http://127.0.0.1:<port>/merge` (harness performs the squash-merge, emits a `pr-merged` event). `git_ops.py pr-merge --strategy squash` is the **non-harness CLI fallback** — for when the harness is unreachable or the verifier runs outside a harness-managed session. It is explicitly NOT the normal-operation path.

## Self-correction (the #13457 miss)

I filed #13457 claiming `verification.md`/`delivery-packaging.md` were STALE for using the harness `POST /merge` (I thought `git_ops.py pr-merge` was canonical). The premise was **inverted** — those files were correct; the actually-drifted file was my own L4 (`.squidsquad/project/verifier.md` "Merge & Ship" bullet, which named `git_ops.py pr-merge` as primary). Skill corrected the L4 on main.

**Lesson for merge-path (and any interface) drift findings:** before filing "file X is stale vs file Y", confirm which file is the *canonical interface lock* (here `pr-protocol.md`) and check the drift **direction** against it. A confidently-worded finding in the wrong direction wastes a worker cycle. The skeptic's rigor applies to my own findings too — verify the authority, not just the discrepancy. Cross-ref [[feedback_verify_against_planning_artifacts]].
