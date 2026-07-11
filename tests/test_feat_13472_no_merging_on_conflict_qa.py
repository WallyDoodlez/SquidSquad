"""Independent verifier tests for #13472 — _safe_pull_in_clone must not leave a clone MERGING.

Verifier-filed gap (surfaced during #13456 verification). Derived from the fix
contract: on a genuine committed conflict, deploy-pull must abort the in-progress
merge (no .git/MERGE_HEAD) and report failure — and must NOT regress the #13456
untracked-collision path.
"""
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start):
    for p in [start, *start.parents]:
        if (p / "references" / "scripts" / "harness.py").exists():
            return p
    raise RuntimeError("could not locate repo root")


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


def _is_merging(clone):
    return (Path(clone) / ".git" / "MERGE_HEAD").exists()


@pytest.fixture
def scaffold(tmp_path):
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
    return {"origin": origin, "agent": agent, "upstream": upstream}


def test_committed_conflict_not_left_merging(scaffold):
    """AC (the #13472 fix): committed conflict -> ok=False AND clone NOT left MERGING."""
    agent, upstream = scaffold["agent"], scaffold["upstream"]
    _commit(upstream, P, "BASE\n", "add P base")
    git(upstream, "push", "-q", "origin", "main")
    git(agent, "pull", "-q", "--no-rebase", "origin", "main")
    _commit(upstream, P, "ORIGIN-COMMIT\n", "origin change")
    git(upstream, "push", "-q", "origin", "main")
    _commit(agent, P, "LOCAL-COMMIT\n", "divergent local")
    ok, detail = harness._safe_pull_in_clone(agent)
    assert ok is False, f"genuine conflict must fail: {detail}"
    assert not _is_merging(agent), f"clone STILL left MERGING (fix ineffective); detail={detail}"


def test_untracked_collision_regression_still_works(scaffold):
    """Regression: the #13456 untracked-collision path still survives + pulled wins."""
    agent, upstream, origin = scaffold["agent"], scaffold["upstream"], scaffold["origin"]
    _commit(upstream, P, "ORIGIN\n", "add tracked P")
    git(upstream, "push", "-q", "origin", "main")
    (Path(agent) / P).write_text("LOCAL-UNTRACKED\n")
    ok, detail = harness._safe_pull_in_clone(agent)
    assert ok is True, f"#13456 untracked path regressed: {detail}"
    assert (Path(agent) / P).read_text() == "ORIGIN\n"
    assert not _is_merging(agent)


def test_regression_test_present():
    """Worker ships a real-git regression test for the MERGING case."""
    wt = REPO_ROOT / "tests" / "test_13472_safe_pull_committed_conflict_no_merging.py"
    assert wt.exists(), "worker regression test missing"
    txt = wt.read_text().lower()
    assert "merge_head" in txt or "merging" in txt
