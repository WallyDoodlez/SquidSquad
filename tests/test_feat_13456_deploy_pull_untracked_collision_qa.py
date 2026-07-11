"""Independent verifier tests for #13456 — harness deploy-pull survives untracked-file collision.

Derived from TEST-PLAN-13456.md (AC list), NOT the worker's test file.
Calls the REAL harness._safe_pull_in_clone against REAL temp git clones
(the helper runs git with cwd=clone_path, harness.py:4971).
"""
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "scripts" / "harness.py").exists():
            return p
    raise RuntimeError("could not locate repo root (references/scripts/harness.py)")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import harness  # noqa: E402

P = "squad.txt"


def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {r.stderr}")
    return r


def _cfg(repo):
    git(repo, "config", "user.email", "t@t.io")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "commit.gpgsign", "false")


def _commit(repo, fname, content, msg):
    (Path(repo) / fname).write_text(content)
    git(repo, "add", fname)
    git(repo, "commit", "-m", msg)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def scaffold(tmp_path):
    """seed -> bare origin -> agent clone + upstream clone, all on main."""
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q")
    _cfg(seed)
    _commit(seed, "README", "base\n", "base")
    git(seed, "branch", "-M", "main")
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "--bare", "-q", str(seed), str(origin))
    agent = tmp_path / "agent"
    git(tmp_path, "clone", "-q", str(origin), str(agent))
    _cfg(agent)
    upstream = tmp_path / "upstream"
    git(tmp_path, "clone", "-q", str(origin), str(upstream))
    _cfg(upstream)
    return {"origin": origin, "agent": agent, "upstream": upstream, "tmp": tmp_path}


def _origin_head(origin):
    return git(origin, "rev-parse", "main").stdout.strip()


def _is_merging(clone):
    return (Path(clone) / ".git" / "MERGE_HEAD").exists()


def test_tc_01_untracked_collision_survives_pulled_wins(scaffold):
    """AC1: untracked local file at now-tracked path -> survive, pulled wins."""
    agent, upstream, origin = scaffold["agent"], scaffold["upstream"], scaffold["origin"]
    # origin advances: P becomes a TRACKED file.
    _commit(upstream, P, "ORIGIN\n", "add tracked P")
    git(upstream, "push", "-q", "origin", "main")
    # agent has an UNTRACKED file at the same path.
    (Path(agent) / P).write_text("LOCAL-UNTRACKED\n")
    ok, detail = harness._safe_pull_in_clone(agent)
    assert ok is True, f"should survive untracked collision: {detail}"
    assert git(agent, "rev-parse", "HEAD").stdout.strip() == _origin_head(origin)
    assert (Path(agent) / P).read_text() == "ORIGIN\n", "pulled/tracked content must win"
    assert not _is_merging(agent), "clone left in MERGING state"


def test_tc_02_dirty_tracked_regression_13215(scaffold):
    """AC2: dirty TRACKED file (#13215) still survives, pulled wins."""
    agent, upstream, origin = scaffold["agent"], scaffold["upstream"], scaffold["origin"]
    # P is tracked from base on both.
    _commit(upstream, P, "BASE\n", "add P base")
    git(upstream, "push", "-q", "origin", "main")
    git(agent, "pull", "-q", "--no-rebase", "origin", "main")
    # origin advances P; agent dirties P (uncommitted, tracked).
    _commit(upstream, P, "ORIGIN2\n", "advance P")
    git(upstream, "push", "-q", "origin", "main")
    (Path(agent) / P).write_text("LOCAL-DIRTY\n")
    ok, detail = harness._safe_pull_in_clone(agent)
    assert ok is True, f"dirty-tracked regression must survive: {detail}"
    assert git(agent, "rev-parse", "HEAD").stdout.strip() == _origin_head(origin)
    assert (Path(agent) / P).read_text() == "ORIGIN2\n", "pulled content must win"
    assert not _is_merging(agent)


def _setup_committed_conflict(scaffold):
    agent, upstream = scaffold["agent"], scaffold["upstream"]
    _commit(upstream, P, "BASE\n", "add P base")
    git(upstream, "push", "-q", "origin", "main")
    git(agent, "pull", "-q", "--no-rebase", "origin", "main")
    _commit(upstream, P, "ORIGIN-COMMIT\n", "origin change")
    git(upstream, "push", "-q", "origin", "main")
    local_head = _commit(agent, P, "LOCAL-COMMIT\n", "local divergent change")
    return local_head


def test_tc_03_genuine_conflict_reported_as_failure(scaffold):
    """AC3 (in #13456 scope): committed divergence -> ok=False (routes to
    recovery), origin NOT falsely synced. The fix must not report success on a
    genuine conflict."""
    agent = scaffold["agent"]
    local_head = _setup_committed_conflict(scaffold)
    ok, detail = harness._safe_pull_in_clone(agent)
    assert ok is False, f"genuine conflict must fail: {detail}"
    assert git(agent, "rev-parse", "HEAD").stdout.strip() == local_head, "origin not synced on fail"


@pytest.mark.xfail(
    reason="PRE-EXISTING gap (NOT introduced by #13456, outside its untracked-collision "
    "scope): a genuine committed conflict leaves the first pull MERGING; git stash then "
    "fails on the unmerged index and _safe_pull_in_clone returns 'stash-failed' BEFORE the "
    "retry-branch 'git merge --abort' runs, so .git/MERGE_HEAD lingers -- contradicting the "
    "docstring's no-lingering-MERGE_HEAD claim. Filed separately.",
    strict=False,
)
def test_tc_03b_committed_conflict_leaves_merging_PREEXISTING_GAP(scaffold):
    """Documents the pre-existing gap surfaced during #13456 verification."""
    agent = scaffold["agent"]
    _setup_committed_conflict(scaffold)
    harness._safe_pull_in_clone(agent)
    assert not _is_merging(agent), "clone left in MERGING state after committed conflict"


def test_tc_04_regression_test_present():
    """AC4: worker ships a real-git regression test (untracked + #13215)."""
    wt = REPO_ROOT / "tests" / "test_feat_13456_deploy_pull_untracked_collision.py"
    assert wt.exists(), "worker regression test missing"
    txt = wt.read_text().lower()
    assert "untracked" in txt, "no untracked coverage"
    assert "13215" in txt, "no #13215 regression coverage"


def test_tc_05_clean_pull_noop_no_stash(scaffold):
    """Guard: up-to-date clean pull is a safe no-op, no stash left behind."""
    agent = scaffold["agent"]
    ok, detail = harness._safe_pull_in_clone(agent)
    assert ok is True, detail
    assert git(agent, "stash", "list").stdout.strip() == "", "leaked a stash on clean pull"
    assert not _is_merging(agent)
