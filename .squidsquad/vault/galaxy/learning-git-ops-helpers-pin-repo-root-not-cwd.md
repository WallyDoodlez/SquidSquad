---
type: learning
tags: [verification, testing, git_ops, harness]
created: 2026-07-11
source: "#13373 verification"
---

# Testing git_ops.py functions: override REPO_ROOT, not process CWD

`git_ops.py` runs every git subprocess with `cwd=str(REPO_ROOT)` (see `_run` / `_run_list`, git_ops.py ~L120-142), where `REPO_ROOT = SCRIPT_DIR.parent.parent` is resolved from the module file location. It does **not** honor the process's current working directory.

**Consequence for verifiers**: to exercise a git_ops function (e.g. `_sync_local_branch_to_origin`, `task_begin`) against a controlled throwaway git repo, `chdir`-ing into a temp clone does NOTHING — the function still operates on the real repo. On #13373 this produced a FALSE FAIL: the tests appeared to show the fix no-opping (exit 0, empty output) because the function was actually running against the live repo where local == origin.

**Technique**: in a subprocess driver, reassign the module global before calling:
```python
import git_ops
from pathlib import Path
git_ops.REPO_ROOT = Path(temp_repo)   # helpers read this global at call time
git_ops._sync_local_branch_to_origin(branch)
```
Then git runs in your temp repo and the real behavior is observable.

**General rule**: when a live-system test of a script function gives a surprising all-green or all-noop, check whether the function pins its own working directory / config path instead of inheriting the environment. The disagreement between "my harness says X" and "the function did nothing" is the tell. Cross-ref [[feedback_qa_verification_approach]] (verify E2E against the real behavior, not the unit tests).
