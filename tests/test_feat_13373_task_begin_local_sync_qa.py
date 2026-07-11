"""Independent verifier tests for #13373 — git_ops task-begin local-branch stale-tip sync.

Derived from TEST-PLAN-13373.md (AC list), NOT from the worker's test file.
Exercises the REAL _sync_local_branch_to_origin against REAL git repos by
running it in-process via a subprocess whose CWD is a throwaway clone, so the
exit code + stderr are captured exactly as task-begin surfaces them.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "scripts" / "git_ops.py").exists():
            return p
    raise RuntimeError("could not locate repo root (references/scripts/git_ops.py)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCRIPTS = REPO_ROOT / "references" / "scripts"
BRANCH = "squidsquad/task/13373"


def git(cwd, *args, check=True):
    r = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True
    )
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {r.stderr}")
    return r


def _commit(cwd, fname, content, msg):
    (Path(cwd) / fname).write_text(content)
    git(cwd, "add", fname)
    git(cwd, "commit", "-m", msg)
    return git(cwd, "rev-parse", "HEAD").stdout.strip()


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@t.io")
    git(path, "config", "user.name", "t")
    git(path, "config", "commit.gpgsign", "false")
    return path


def _run_sync(repo, branch=BRANCH):
    """Invoke the real git_ops._sync_local_branch_to_origin against `repo`.

    git_ops._run_list pins git to the module-global REPO_ROOT (git_ops.py:142),
    NOT the process CWD — so we override that global to the temp repo before
    calling, exactly reproducing task-begin's behavior in that repo.
    """
    driver = (
        f"import sys; sys.path.insert(0, r'{SCRIPTS}'); "
        f"import git_ops; from pathlib import Path; "
        f"git_ops.REPO_ROOT = Path(r'{repo}'); "
        f"git_ops._sync_local_branch_to_origin(r'{branch}')"
    )
    return subprocess.run(
        [sys.executable, "-c", driver], cwd=str(repo), capture_output=True, text=True
    )


@pytest.fixture
def repos(tmp_path):
    """origin (bare) + local clone, both on BRANCH with a shared base commit."""
    seed = _init_repo(tmp_path / "seed")
    base = _commit(seed, "f.txt", "base\n", "base")
    git(seed, "branch", "-M", BRANCH)
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "--bare", "-q", str(seed), str(origin))
    local = tmp_path / "local"
    git(tmp_path, "clone", "-q", str(origin), str(local))
    git(local, "config", "user.email", "t@t.io")
    git(local, "config", "user.name", "t")
    git(local, "config", "commit.gpgsign", "false")
    git(local, "checkout", "-q", BRANCH)
    return {"origin": origin, "local": local, "base": base}


def test_tc_01_behind_fast_forwards(repos):
    """AC1: local behind origin -> fast-forward to origin head."""
    local, origin = repos["local"], repos["origin"]
    # Advance origin via a second clone, push.
    pusher = local.parent / "pusher"
    git(local.parent, "clone", "-q", str(origin), str(pusher))
    git(pusher, "config", "user.email", "t@t.io")
    git(pusher, "config", "user.name", "t")
    git(pusher, "config", "commit.gpgsign", "false")
    git(pusher, "checkout", "-q", BRANCH)
    o2 = _commit(pusher, "f.txt", "base\nfix\n", "the fix commit")
    git(pusher, "push", "-q", "origin", BRANCH)
    # local is still at base (behind).
    assert git(local, "rev-parse", "HEAD").stdout.strip() == repos["base"]
    r = _run_sync(local)
    assert r.returncode == 0, r.stderr
    assert git(local, "rev-parse", "HEAD").stdout.strip() == o2, "did not FF to origin head"


def test_tc_02_diverged_fails_loudly(repos):
    """AC2: diverged -> non-zero exit, both SHAs + DIVERGED in stderr."""
    local, origin = repos["local"], repos["origin"]
    # origin gets commit O
    pusher = local.parent / "pusher"
    git(local.parent, "clone", "-q", str(origin), str(pusher))
    git(pusher, "config", "user.email", "t@t.io")
    git(pusher, "config", "user.name", "t")
    git(pusher, "config", "commit.gpgsign", "false")
    git(pusher, "checkout", "-q", BRANCH)
    o_sha = _commit(pusher, "o.txt", "origin-side\n", "origin commit")
    git(pusher, "push", "-q", "origin", BRANCH)
    # local gets a DIFFERENT commit L (diverged from origin)
    l_sha = _commit(local, "l.txt", "local-side\n", "local commit")
    r = _run_sync(local)
    assert r.returncode != 0, "diverged case must exit non-zero"
    assert "DIVERGED" in r.stderr
    assert l_sha[:9] in r.stderr, f"local SHA missing from stderr: {r.stderr}"
    assert o_sha[:9] in r.stderr, f"origin SHA missing from stderr: {r.stderr}"


def test_tc_03_ahead_keeps_local(repos):
    """AC3: local ahead of origin -> keep unpushed work, no-op."""
    local = repos["local"]
    l2 = _commit(local, "f.txt", "base\nunpushed\n", "unpushed local work")
    r = _run_sync(local)
    assert r.returncode == 0, r.stderr
    assert git(local, "rev-parse", "HEAD").stdout.strip() == l2, "clobbered unpushed local work"


def test_tc_04_origin_absent_noop(repos, tmp_path):
    """AC4: branch never pushed to origin -> no-op, no error."""
    origin = repos["origin"]
    # Fresh local clone, create a NEW local-only branch absent on origin.
    local2 = tmp_path / "local2"
    git(tmp_path, "clone", "-q", str(origin), str(local2))
    git(local2, "config", "user.email", "t@t.io")
    git(local2, "config", "user.name", "t")
    git(local2, "config", "commit.gpgsign", "false")
    newbranch = "squidsquad/task/99999"
    git(local2, "checkout", "-q", "-b", newbranch)
    head = git(local2, "rev-parse", "HEAD").stdout.strip()
    r = _run_sync(local2, branch=newbranch)
    assert r.returncode == 0, f"origin-absent must be no-op: {r.stderr}"
    assert git(local2, "rev-parse", "HEAD").stdout.strip() == head


def test_tc_05_task_begin_wires_sync():
    """AC1/AC2 gate: task_begin's local path calls the sync helper (not dead code)."""
    src = (SCRIPTS / "git_ops.py").read_text()
    # Locate task_begin body and confirm the sync call appears within the local path.
    assert "def _sync_local_branch_to_origin(branch):" in src
    tb = src.index("def task_begin(")
    body = src[tb: tb + 2000]
    assert "_sync_local_branch_to_origin(branch)" in body, "helper not wired into task_begin"


def test_tc_06_regression_test_present():
    """AC5: worker ships a regression test covering behind + diverged."""
    wt = REPO_ROOT / "tests" / "test_13373_task_begin_local_sync.py"
    assert wt.exists(), "worker regression test missing"
    txt = wt.read_text().lower()
    assert "ff" in txt or "fast" in txt or "behind" in txt, "no behind/FF coverage"
    assert "diverg" in txt, "no divergence coverage"
