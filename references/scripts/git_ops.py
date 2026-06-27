#!/usr/bin/env python3
"""SquidSquad git operations — deterministic git workflow commands.

Single source of truth for git operations used by agents.

Usage:
    python scripts/git_ops.py pull                      # git pull (merge)
    python scripts/git_ops.py ensure-main-and-pull [role]  # on-main + pull before a recompose (#12906)
    python scripts/git_ops.py add-all                   # git add -A
    python scripts/git_ops.py commit <role> <message>    # git commit with role prefix
    python scripts/git_ops.py push                      # git push
    python scripts/git_ops.py commit-push <role> <msg>   # add + commit + push
    python scripts/git_ops.py commit-code <role> <branch> <msg>  # code files → branch
    python scripts/git_ops.py commit-state <role> <msg>  # .squidsquad/ files → main
    python scripts/git_ops.py branch-create <name>       # create + checkout branch
    python scripts/git_ops.py branch-switch <name>       # checkout existing branch
    python scripts/git_ops.py branch-exists <name>       # check if branch exists
    python scripts/git_ops.py branch-delete <name>       # delete local + remote branch
    python scripts/git_ops.py current-branch             # print current branch name
    python scripts/git_ops.py pr-create <title> <body>   # create PR via gh
    python scripts/git_ops.py pr-merge <number> [--strategy squash]  # merge PR via gh
    python scripts/git_ops.py task-begin <role> <number>  # checkout task's feature branch
    python scripts/git_ops.py task-end <role> <number>    # return to working branch
    python scripts/git_ops.py has-changes               # check if working tree dirty
    python scripts/git_ops.py last-hash                 # print last commit hash (short)
    python scripts/git_ops.py check-real-conflict <base> <head>  # real conflict? exit 0=clean/1=conflict/2=err
    python scripts/git_ops.py guard-staged-state         # pre-commit hook: unstage state files on a feature branch (fail-open)
    python scripts/git_ops.py guard-galaxy-frontmatter   # pre-commit hook: block a staged galaxy note missing YAML frontmatter (fail-closed on violation, fail-open on error)
    python scripts/git_ops.py install-hooks              # activate the pre-commit state guard (core.hooksPath)
    python scripts/git_ops.py --help
"""

import io
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

# #13211 — serialize ensure_main_and_pull across ALL in-process callers (the
# L4 watcher's per-role-class freshen bursts AND the post-merge deploy-all path,
# both in the harness process). Concurrent main-checkout + pull on the SAME
# clone collide on .git/index.lock (#13197 fixed this for the watcher-only case
# via a watcher-local lock; the deploy path called ensure_main_and_pull outside
# it). Hoisting the lock here covers every caller from one place. ensure_main_
# and_pull never re-enters itself (it calls _run/pull only), so a plain
# non-reentrant Lock cannot self-deadlock. Threading-scoped (not cross-process):
# the racing callers are threads in the one harness process; the CLI caller is a
# separate process not part of that race.
_ENSURE_MAIN_LOCK = threading.Lock()

# Ensure stdout/stderr can handle UTF-8 on Windows (cp1252 consoles choke on em dashes etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _get_working_branch():
    """Get the configured working branch name. Falls back to 'main'."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        branch = get_field("working-branch")
        return branch if branch else "main"
    except Exception:
        return "main"


# #13262 — every git_ops subprocess gets a timeout so a hung `git` (network
# stall, stuck index.lock, a credential-helper wedge — cf. the documented
# `credential.helper=manager` silent hang) fails fast into the callers' existing
# failure paths instead of blocking the thread (and, since #13211, the whole
# in-process recompose surface behind `_ENSURE_MAIN_LOCK`) indefinitely. The
# default is generous (git ops are normally sub-second; a slow network fetch/push
# of a large pack is the worst legitimate case) so it fail-fasts a true hang
# without false-tripping. Overridable per-call and fleet-wide via the
# `SQUIDSQUAD_GIT_TIMEOUT` env var (no config-schema change → existing installs
# keep the default).
DEFAULT_GIT_TIMEOUT = 300


def _git_timeout():
    """Resolve the git subprocess timeout (seconds): ``SQUIDSQUAD_GIT_TIMEOUT``
    env override if a positive int, else ``DEFAULT_GIT_TIMEOUT``.

    Installs on very high-latency links or with very large packs (a `git pull`/
    `git fetch` that legitimately runs minutes) can raise the cap via
    ``SQUIDSQUAD_GIT_TIMEOUT=600`` without a code or config-schema change."""
    import os
    raw = os.environ.get("SQUIDSQUAD_GIT_TIMEOUT")
    if raw:
        try:
            val = int(raw)
            if val > 0:
                return val
        except (TypeError, ValueError):
            pass
    return DEFAULT_GIT_TIMEOUT


def _timeout_failure(cmd, check, timeout):
    """Translate a ``subprocess.TimeoutExpired`` into the failure shape the
    caller already handles (#13262): raise ``CalledProcessError`` when
    ``check=True`` (mirroring subprocess's own check-failure contract), else
    return a synthetic non-zero ``CompletedProcess`` (rc=124, the conventional
    timeout code) so ``check=False`` callers fall into their existing
    ``returncode != 0`` / ``(False, ...)`` recovery."""
    msg = f"git command timed out after {timeout}s: {cmd}"
    print(f"WARNING: {msg}", file=sys.stderr)
    if check:
        raise subprocess.CalledProcessError(124, cmd, output=None, stderr=msg)
    return subprocess.CompletedProcess(cmd, 124, stdout="", stderr=msg)


def _run(cmd, check=True, timeout=None):
    """Run a shell command from repo root (only for static commands)."""
    if timeout is None:
        timeout = _git_timeout()
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            check=check, cwd=str(REPO_ROOT), timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _timeout_failure(cmd, check, timeout)


def _run_list(cmd_list, check=True, timeout=None):
    """Run a command from repo root using list form (safe for variable args)."""
    if timeout is None:
        timeout = _git_timeout()
    try:
        return subprocess.run(
            cmd_list, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            check=check, cwd=str(REPO_ROOT), timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _timeout_failure(cmd_list, check, timeout)


_GH_AVAILABLE_CACHE = None


def _gh_credential_helper_available():
    """Whether `gh` is on PATH and authenticated, so it can serve as the git
    credential helper. Cached for the process lifetime.

    #9890: on Windows the default `credential.helper=manager` (Git Credential
    Manager) can wedge silently in agent sessions waiting on an interactive
    auth dialog. When `gh` is available, routing credentials through it
    sidesteps the dialog.
    """
    global _GH_AVAILABLE_CACHE
    if _GH_AVAILABLE_CACHE is not None:
        return _GH_AVAILABLE_CACHE
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        _GH_AVAILABLE_CACHE = (result.returncode == 0)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        _GH_AVAILABLE_CACHE = False
    return _GH_AVAILABLE_CACHE


def _git_push(push_args, timeout=60):
    """Run `git push <push_args...>` with anti-wedge defenses (#9890).

    Two defenses against the silent-wedge mode observed in cycle 1244:

    1. **Credential helper override**: when `gh` is available and authenticated
       (cached via `_gh_credential_helper_available()`), prepend
       `-c credential.helper=` + `-c credential.helper=!gh auth git-credential`
       so the push routes through the `gh` token rather than the inherited
       helper (which on Windows defaults to GCM and can wedge on agent sessions).
    2. **Timeout**: subprocess.run is called with a `timeout` so a wedge fails
       fast with a synthetic non-zero CompletedProcess (returncode 124, matching
       GNU `timeout` convention) rather than accumulating zombie git processes.

    Args:
        push_args: list of args following `git push` (e.g., ["-u", "origin", "br"]).
                   Pass `[]` for bare `git push`.
        timeout: seconds before the push is killed. Default 60.

    Returns:
        subprocess.CompletedProcess. On timeout, returncode is 124 and stderr
        carries a defense-noted message so existing `if push_result.returncode != 0`
        callers continue to work without changes.
    """
    cmd = ["git"]
    if _gh_credential_helper_available():
        cmd.extend([
            "-c", "credential.helper=",
            "-c", "credential.helper=!gh auth git-credential",
        ])
    cmd.append("push")
    cmd.extend(push_args)
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            check=False, cwd=str(REPO_ROOT),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd, returncode=124, stdout="",
            stderr=f"git push timed out after {timeout}s (wedge defense per #9890)",
        )


def _log_diagnostic(severity, message):
    """Log a diagnostic entry (silently fails if diagnostics.py unavailable)."""
    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "diagnostics.py"), "log", severity, "git_ops", message],
            capture_output=True, check=False, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT),
        )
    except Exception:
        pass


def _emit(event_type, payload=None, cycle_number=None, role=None):
    """Fire-and-forget event emission (#4709). Role from arg or sys.argv.

    #9242: never emit with role=\"unknown\". The previous fallback (when
    argv inference failed) leaked \"unknown\" events onto the bus, which
    the harness persisted into ``.event-state.json`` and (worse) created
    a ghost ``unknown`` agent entry in ``.harness-state.json`` that
    contributed to the HTTP-wedge cascade. When the role cannot be
    determined, emit nothing — better than emitting a poisoned event.
    The matching boundary rejection in the harness (POST /events
    validates role against the configured agent set) is defense in
    depth so a regression here cannot re-corrupt state.
    """
    try:
        from event_bus import emit
        # Use explicit role if provided, otherwise determine from sys.argv
        if role is None:
            args = sys.argv[1:]
            role = None
            # For commands like: commit-code <role> <branch> <msg>
            # or: task-begin <role> <number>
            if len(args) >= 2 and args[1] in ("pm", "skill", "qa", "dm"):
                role = args[1]
            elif len(args) >= 2 and args[0] in ("commit-code", "commit-state", "commit-push",
                                                 "commit", "task-begin", "task-end"):
                role = args[1]
            if role is None:
                # Cannot infer — silent no-op rather than emit "unknown".
                return
        emit(event_type, role, payload=payload, cycle_number=cycle_number)
    except (ImportError, Exception):
        pass


def _stash_top_ref():
    """SHA of the top stash entry (``refs/stash``), or ``""`` if no stash exists.

    Used to detect whether a ``git stash`` actually created a NEW entry: on a
    CLEAN working tree ``git stash`` is a no-op that still exits 0, so a
    subsequent pop would apply a PRE-EXISTING (possibly ancient) stash —
    splattering ``<<<<<<<`` conflict markers tree-wide and breaking compose
    (#13167). Callers compare this before/after their stash and only pop when
    the ref changed (i.e. they created the stash they are about to pop).
    """
    r = _run("git rev-parse --quiet --verify refs/stash", check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def _safe_stash_pop():
    """Pop the most recent stash, leaving NO conflict markers behind (#13045).

    A plain ``git stash pop`` that conflicts writes ``<<<<<<< / ======= /
    >>>>>>>`` merge markers into the unmerged working-tree files and KEEPS the
    stash. The old recovery only ran ``git stash drop`` — which removes the
    stash entry but NOT the markers already written, so a state file like
    ``config.md`` was left corrupt → ``compose.py`` failed on every recompose →
    a fleet-wide compose-failed loop.

    On conflict we instead restore every conflicted (unmerged) path to the
    pulled ``HEAD`` version — the just-pulled/checked-out state is authoritative
    for the state files clone-sync touches (e.g. config.md's ship counter, whose
    live value lives on main) — then drop the now-applied stash. This discards
    the stashed local version of the conflicting paths, which is exactly the
    stale local change that caused the conflict.

    Returns True if the pop applied cleanly, False if it conflicted and was
    force-resolved to HEAD.
    """
    pop = _run("git stash pop", check=False)
    if pop.returncode == 0:
        return True
    conflicted = _run("git diff --name-only --diff-filter=U", check=False)
    unmerged = [p.strip() for p in conflicted.stdout.splitlines() if p.strip()]
    if not unmerged:
        # Pop failed for a NON-conflict reason (no stash entry, or an unrelated
        # git error) — the stash, if any, was NOT applied. Do NOT drop it: that
        # would discard un-applied stashed work. Leave it intact and report the
        # pop did not succeed.
        return False
    for path in unmerged:
        _run_list(["git", "checkout", "HEAD", "--", path], check=False)
    # A real conflict: git applied the stash WITH markers and kept it. Now that
    # the conflicted paths are restored to HEAD, drop the retained stash.
    _run("git stash drop", check=False)
    return False


def pull(role=None):
    """Pull with merge (#5378, #5445).

    Returns True on success, False on failure. Never crashes.
    """
    # #13267: pin to a MERGE pull (never rebase). Under a clone-local or global
    # `pull.rebase=true` a bare `git pull` would REBASE; a first-pull rebase
    # conflict leaves a REBASE-in-progress state that the subsequent `git stash`
    # cannot work over and that the #13261 recovery (`git merge --abort`) cannot
    # clear. `--no-rebase` keeps the first pull consistent with the pinned retry
    # below and with the project's always-merge-never-rebase rule.
    result = _run("git pull --no-rebase", check=False)
    if result.returncode == 0:
        print("Pulled")
        _emit("git-pull", {"result": "ok"}, role=role)
        return True

    # Check if the failure is "already up to date" or branch divergence
    combined = (result.stdout + result.stderr).lower()
    if "already up to date" in combined or "up to date" in combined:
        print("Pulled (already up to date)")
        _emit("git-pull", {"result": "ok"}, role=role)
        return True

    # Try stash + pull + pop. #13167: guard against `git stash` being a no-op
    # on a clean tree (exits 0 but creates nothing) — popping then would apply a
    # PRE-EXISTING ancient stash and write conflict markers tree-wide, breaking
    # compose. Only pop when our stash actually created a new entry.
    pre_stash_ref = _stash_top_ref()
    stash_result = _run("git stash", check=False)
    if stash_result.returncode != 0:
        print("WARNING: git stash failed -- skipping pull", file=sys.stderr)
        return False
    stashed = _stash_top_ref() != pre_stash_ref

    # #13261: pin the retry to a MERGE pull (never rebase). The recovery below
    # cleans up a failed retry with `git merge --abort`, which only clears a
    # MERGING state — under a clone-local `pull.rebase=true` the retry would
    # rebase and leave a REBASE state the abort cannot clear. `--no-rebase`
    # guarantees the abort verb matches what a failed retry leaves behind, and
    # matches the project's "always merge, never rebase" rule.
    retry = _run("git pull --no-rebase", check=False)
    if retry.returncode != 0:
        # #13261: the retry pull may have STARTED a merge and hit a
        # committed-divergence conflict, leaving the clone MERGING (MERGE_HEAD +
        # conflict markers). Abort that merge FIRST — otherwise (a) the markers
        # break the next compose, (b) _safe_stash_pop below misreads the merge's
        # unmerged paths as a stash-pop conflict and DROPS our stash, and (c) a
        # lingering MERGE_HEAD makes the next op needing a clean tree fail. The
        # abort is a harmless no-op (non-zero, ignored) when no merge is in
        # progress (the pull failed before merging). Mirrors the same fix in the
        # deploy path's _safe_pull_in_clone (#13215). The pull still FAILED →
        # report failure after restoring our stash.
        _run("git merge --abort", check=False)
        # Restore OUR stashed changes (only if we actually created one) and
        # report failure. Use the marker-safe pop (#13045), never a raw pop.
        if stashed:
            _safe_stash_pop()
        print(f"WARNING: git pull failed after stash -- {retry.stderr.strip()}",
              file=sys.stderr)
        return False

    if not stashed:
        # Clean tree — `git stash` stashed nothing, so there is nothing of ours
        # to pop. Do NOT pop a pre-existing stash (#13167).
        print("Pulled (no local changes to stash)")
    elif _safe_stash_pop():
        print("Pulled (stashed and popped)")
    else:
        # #13045: a conflicted pop is resolved to the pulled HEAD (markers
        # removed) and the stash dropped (#4829 leak-prevention preserved),
        # so config.md is never left with `<<<<<<<` markers that break compose.
        _log_diagnostic("warning",
                        "stash pop conflict during pull — restored conflicted "
                        "paths to pulled HEAD and dropped stash (#13045)")
        print("WARNING: stash pop conflict -- conflicts resolved to pulled "
              "state, stash dropped.", file=sys.stderr)
        print("Pulled (stash pop conflict -- resolved to pulled state)")
    _emit("git-pull", {"result": "stash"}, role=role)
    return True


def ensure_main_and_pull(role=None):
    """Put the clone on ``main`` and pull origin before a recompose/deploy.

    #12906 (Phase 1 of #12895): every harness-side recompose path
    (`compose.py deploy*` driven by the L4 file-watcher and the
    post-merge deploy-all) MUST run against *current* source. A clone
    that is on a feature branch or behind origin would otherwise
    regenerate composed ``CLAUDE.md`` from stale source and push that
    revert fleet-wide. This guard closes the root condition: ensure
    main, then merge-pull origin.

    Returns ``(ok: bool, detail: str)``. Never raises — the contract is
    enforced here (a blanket ``try/except``) so every caller, including
    the harness merge path that calls this directly, can trust ``ok`` and
    abort the recompose on ``ok=False`` rather than wrap defensively. On
    ``ok=False`` the agents keep their last-known-good composed output
    until a later recompose succeeds.
    """
    try:
        # #13211 — single-flight the checkout+pull across every in-process
        # caller (watcher freshen bursts + post-merge deploy-all) so concurrent
        # git on the shared clone can't collide on .git/index.lock. Held across
        # the subprocess git calls below — exactly the serialization #13197
        # established (it just lived in the watcher before, missing the deploy
        # path). Inside the try so the "Never raises" contract still holds.
        with _ENSURE_MAIN_LOCK:
            result = _run("git branch --show-current", check=False)
            branch = result.stdout.strip() if result.returncode == 0 else ""
            if branch != "main":
                sw = _run_list(["git", "checkout", "main"], check=False)
                if sw.returncode != 0:
                    detail = (sw.stderr or sw.stdout or "").strip()[:200]
                    print(
                        f"WARNING: ensure_main_and_pull could not switch to main "
                        f"from {branch!r}: {detail}",
                        file=sys.stderr,
                    )
                    return False, f"checkout-main-failed (on {branch!r})"
            if not pull(role=role):
                return False, "pull-failed"
            return True, "on-main-synced"
    except Exception as exc:  # noqa: BLE001 — "Never raises" is the contract
        print(
            f"WARNING: ensure_main_and_pull raised unexpectedly: {exc!r}",
            file=sys.stderr,
        )
        return False, f"unexpected: {exc!r}"


def add_all():
    """Stage all changes."""
    _run("git add -A")
    print("Staged all changes")


def _get_alias(role):
    """Get agent alias for Co-Authored-By trailer."""
    try:
        from config import get_alias
        return get_alias(role)
    except Exception:
        return role


def commit(role, message):
    """Commit with role prefix and Co-Authored-By trailer."""
    alias = _get_alias(role)
    full_msg = f"{role}: {message}\n\nCo-Authored-By: {alias} <noreply@squidsquad>"
    # #13262: route through _run_list so the commit (and a hung pre-commit hook
    # holding _ENSURE_MAIN_LOCK) is timeout-protected like every other git op.
    result = _run_list(["git", "commit", "-m", full_msg], check=False)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit")
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return False
    print(f"Committed: {full_msg}")
    return True


def push(role=None):
    """Push to remote."""
    result = _git_push([])
    if result.returncode != 0:
        _log_diagnostic("error", f"push failed: {result.stderr.strip()[:200]}")
        print(f"ERROR: push failed: {result.stderr}", file=sys.stderr)
        return False
    # Determine branch for event payload
    branch_result = _run("git branch --show-current", check=False)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    _emit("git-push", {"branch": branch}, role=role)
    print("Pushed")
    return True


def commit_push(role, message):
    """Add all, commit, push — the standard agent workflow."""
    add_all()
    if commit(role, message):
        return push()
    return False


def branch_create(name):
    """Create and checkout a new branch."""
    _run_list(["git", "checkout", "-b", name])
    print(f"Created branch: {name}")


def branch_switch(name):
    """Switch to an existing branch."""
    _run_list(["git", "checkout", name])
    print(f"Switched to: {name}")


def branch_exists(name):
    """Check if a branch exists (local or remote). Prints 'true' or 'false'."""
    result = _run_list(["git", "rev-parse", "--verify", name], check=False)
    exists = result.returncode == 0
    if not exists:
        # Check remote
        result = _run_list(["git", "rev-parse", "--verify", f"origin/{name}"], check=False)
        exists = result.returncode == 0
    print("true" if exists else "false")
    return exists


def branch_delete(name):
    """Delete a local branch (and its remote tracking branch)."""
    # Delete local
    result = _run_list(["git", "branch", "-d", name], check=False)
    if result.returncode != 0:
        # Force delete if not fully merged
        result = _run_list(["git", "branch", "-D", name], check=False)
        if result.returncode != 0:
            print(f"ERROR: could not delete local branch {name}: {result.stderr}", file=sys.stderr)
            return False
    # Delete remote tracking
    _git_push(["origin", "--delete", name])
    print(f"Deleted branch: {name}")
    return True


def current_branch():
    """Print the name of the current branch."""
    result = _run("git branch --show-current")
    name = result.stdout.strip()
    print(name)
    return name


def pr_create(title, body):
    """Create a draft PR. Uses forge adapter for non-GitHub backends,
    gh CLI for GitHub. PRs start as drafts — QA converts to ready."""
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            adapter = get_adapter(config)
            # Need current branch as head
            branch_result = _run_list(["git", "branch", "--show-current"], check=False)
            head = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
            result = adapter.create_pr(title, body, head=head, draft=True)
            if result:
                print(f"PR created: {result.get('url', '')}")
                return result.get("url", "")
            print("ERROR: PR creation failed via forge adapter", file=sys.stderr)
            return None
    except ImportError:
        pass

    # Default: gh CLI — target the configured working branch
    base_branch = _get_working_branch()
    cmd = ["gh", "pr", "create", "--draft", "--title", title, "--body", body]
    if base_branch != "main":
        cmd.extend(["--base", base_branch])
    result = _run_list(cmd, check=False)
    if result.returncode != 0:
        print(f"ERROR: PR creation failed: {result.stderr}", file=sys.stderr)
        return None
    url = result.stdout.strip()
    # Extract PR number from URL (e.g. https://github.com/.../pull/123)
    pr_num = url.rstrip("/").rsplit("/", 1)[-1] if url else ""
    branch_result = _run("git branch --show-current", check=False)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    _emit("pr-create", {"pr_number": pr_num, "title": title[:80], "branch": branch})
    print(f"PR created: {url}")
    return url


def pr_ready(pr_number):
    """Convert a draft PR to ready (#4991 GAP-5). Uses forge adapter pattern."""
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            adapter = get_adapter(config)
            adapter.pr_ready(pr_number)
            print(f"PR #{pr_number} converted to ready (via adapter)")
            return True
    except (ImportError, AttributeError, Exception):
        pass

    # Default: gh CLI
    result = _run_list(
        ["gh", "pr", "ready", str(pr_number)], check=False)
    if result.returncode != 0:
        print(f"ERROR: Failed to convert PR #{pr_number} to ready: {result.stderr}",
              file=sys.stderr)
        return False
    print(f"PR #{pr_number} converted to ready")
    return True


# #13271 (SEV-1 prevention): the GitHub server-side squash of a PR branch that is
# far behind its base can record a STALE tree — mass-reverting/deleting shipped
# fleet work the behind branch never had locally (the #13263 behind-clone
# mechanism; it hit 194 files / ~155 commits at 154-behind). A clone merging
# `origin/main` before push is NOT sufficient (the anomaly fired anyway), so the
# guard lives at the MERGE step. This pre-merge behind-count check is the
# fail-SAFE interim defense (it can only refuse — never mutate main); the robust
# net is a post-merge scope audit + auto-revert (follow-up). The threshold sits
# well above the #10540 batch-ship drain so it never false-blocks the normal
# behind-by-a-few race; tune via SQUIDSQUAD_MERGE_MAX_BEHIND.
# Default 50: comfortably above any realistic sequential batch-ship drain depth
# (a queue of N PRs leaves the last ~N-1 behind), well below the 154-commit
# SEV-1 event (#13271) — so it catches the catastrophe class without tripping
# normal shipping.
MERGE_MAX_BEHIND_DEFAULT = 50


def _merge_max_behind():
    """Resolve the max-behind merge threshold: ``SQUIDSQUAD_MERGE_MAX_BEHIND`` env
    override if a non-negative int, else ``MERGE_MAX_BEHIND_DEFAULT`` (#13271)."""
    import os
    raw = os.environ.get("SQUIDSQUAD_MERGE_MAX_BEHIND")
    if raw:
        try:
            v = int(raw)
            if v >= 0:
                return v
        except (TypeError, ValueError):
            pass
    return MERGE_MAX_BEHIND_DEFAULT


def _pr_behind_by(pr_number):
    """Return how many commits the PR's base branch is AHEAD of the PR head (the
    branch's 'behind' count), or ``None`` if it can't be determined (#13271).

    Uses the GitHub compare API's ``behind_by`` field — authoritative about the
    real divergence regardless of how GitHub later computes the squash. ``None``
    on any gh/API/parse failure so the caller can fail-OPEN (a guard hiccup must
    not wedge all shipping; the post-merge audit is the reliable net)."""
    refs = _run_list(
        ["gh", "pr", "view", str(pr_number),
         "--json", "baseRefName,headRefName"], check=False)
    if refs.returncode != 0:
        return None
    try:
        data = json.loads(refs.stdout.strip())
        base, head = data["baseRefName"], data["headRefName"]
    except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
        return None
    cmp = _run_list(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/compare/{base}...{head}",
         "--jq", ".behind_by"], check=False)
    if cmp.returncode != 0:
        return None
    try:
        return int(cmp.stdout.strip())
    except (TypeError, ValueError):
        return None


def pr_merge(pr_number, strategy="squash", _max_base_retries=3, _base_retry_delay=2.0):
    """Merge a PR. Uses forge adapter for non-GitHub backends,
    gh CLI for GitHub. Returns (success, message).

    Checks PR state first — if already merged, returns success.
    On merge conflict or unexpected failure, returns failure with details.

    #10540: "Base branch was modified" is a TRANSIENT batch-ship race (not a
    real conflict) — when DM drains a deep ship queue, each successful merge
    moves main's SHA, so PRs dispatched against the old base are rejected until
    GitHub recomputes mergeability; the same PR retried alone succeeds. The
    gh-CLI path retries that specific error up to ``_max_base_retries`` times
    (``_base_retry_delay`` seconds apart, to let GitHub settle), while a real
    ``merge conflict`` stays terminal (routed back to in-progress for rebase,
    never retried). The retry knobs are parameters for deterministic testing.
    """
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            adapter = get_adapter(config)
            # Check state first via adapter
            pr_data = adapter.view_pr(pr_number)
            if pr_data:
                state = pr_data.get("state", "")
                if state == "MERGED":
                    print(f"PR #{pr_number} already merged")
                    return True, "already merged"
                if state == "CLOSED":
                    print(f"PR #{pr_number} closed without merge", file=sys.stderr)
                    return False, "PR closed without merge"
            success, msg = adapter.merge_pr(pr_number, strategy)
            if success:
                # pr-merge event removed (#6126) — harness emits pr-merged instead
                print(f"PR #{pr_number} merged ({strategy})")
            else:
                print(f"ERROR: PR #{pr_number} merge failed: {msg}", file=sys.stderr)
            return success, msg
    except ImportError:
        pass

    # Default: gh CLI
    # Check PR state first
    state_result = _run_list(
        ["gh", "pr", "view", str(pr_number), "--json", "state"],
        check=False,
    )
    if state_result.returncode == 0:
        try:
            state = json.loads(state_result.stdout.strip()).get("state", "")
            if state == "MERGED":
                print(f"PR #{pr_number} already merged")
                return True, "already merged"
            if state == "CLOSED":
                print(f"PR #{pr_number} closed without merge", file=sys.stderr)
                return False, "PR closed without merge"
        except (json.JSONDecodeError, AttributeError):
            pass

    # #13271 (SEV-1 prevention): refuse to squash-merge a branch that is FAR
    # behind base — a stale-tree squash from a deeply-behind clone mass-reverts
    # shipped fleet work (194 files at 154-behind). Fail-SAFE: refuse (never
    # mutate main) and route back to re-sync (merge base into the branch) before
    # retry. Fail-OPEN when the count is undeterminable (don't wedge shipping on
    # a gh/API hiccup). Only applies to the squash strategy (the stale-tree risk
    # is squash-specific; a real merge commit preserves base's history).
    # Fail-open scope (returns None → proceed): gh absent/unauthenticated, a
    # non-GitHub/unresolved remote where `gh api {owner}/{repo}` can't infer the
    # repo (e.g. a CI runner without `gh auth`), a rate-limited compare API, or a
    # malformed response. Those are accepted for this INTERIM guard — the robust
    # net is the planned post-merge scope-audit + auto-revert (#13271 follow-up).
    if strategy == "squash":
        behind = _pr_behind_by(pr_number)
        max_behind = _merge_max_behind()
        if behind is not None and behind > max_behind:
            msg = (f"PR #{pr_number} branch is {behind} commits behind base "
                   f"(> {max_behind}) - refusing the squash to avoid a "
                   f"stale-tree mass-revert (#13271). Merge base into the branch "
                   f"and retry.")
            print(f"ERROR: {msg}", file=sys.stderr)
            return False, "branch too far behind base"

    # Attempt merge, retrying ONLY the transient "Base branch was modified"
    # batch-ship race (#10540). A real merge conflict is terminal.
    merge_args = ["gh", "pr", "merge", str(pr_number), f"--{strategy}", "--delete-branch"]
    for attempt in range(_max_base_retries + 1):
        result = _run_list(merge_args, check=False)
        if result.returncode == 0:
            # pr-merge event removed (#6126) — harness emits pr-merged instead
            print(f"PR #{pr_number} merged ({strategy})")
            # Extract linked issue number from branch name
            branch_result = _run_list(
                ["gh", "pr", "view", str(pr_number), "--json", "headRefName"],
                check=False,
            )
            if branch_result.returncode == 0:
                try:
                    branch_name = json.loads(branch_result.stdout.strip()).get("headRefName", "")
                    # Branch format: squidsquad/role/NUMBER
                    parts = branch_name.split("/")
                    if len(parts) >= 2 and parts[0] == "squidsquad" and parts[-1].isdigit():
                        issue_num = parts[-1]
                        print(f"PR linked to #{issue_num} -- GitHub auto-close will handle issue state")
                except (json.JSONDecodeError, AttributeError, IndexError):
                    pass
            return True, "merged"

        error = result.stderr.strip()
        error_lower = error.lower()
        # Real conflict — terminal, never retried (routes back for rebase).
        if "merge conflict" in error_lower or "not mergeable" in error_lower:
            print(f"PR #{pr_number} has merge conflicts", file=sys.stderr)
            return False, "merge conflict"
        # Transient batch-ship race — an earlier merge moved main's SHA. Retry
        # after a short settle so GitHub recomputes mergeability against the new
        # base (#10540). Checked AFTER the conflict guard so a real conflict
        # never masquerades as the race.
        if "base branch was modified" in error_lower and attempt < _max_base_retries:
            print(
                f"PR #{pr_number}: base branch moved (batch-ship race) — "
                f"retry {attempt + 1}/{_max_base_retries} after {_base_retry_delay}s",
                file=sys.stderr,
            )
            time.sleep(_base_retry_delay)
            continue
        print(f"ERROR: PR #{pr_number} merge failed: {error}", file=sys.stderr)
        return False, f"merge failed: {error}"


def _is_state_file(path):
    """Check if a path is a state/ephemeral file that should not appear in feature PRs."""
    STATE_PREFIXES = (".squidsquad/", ".claude/")
    return any(path.startswith(p) for p in STATE_PREFIXES)


def _is_plan_body(path):
    """Plan-in-PR (#12750): task plan bodies belong ON the task branch, not stripped to main.

    A plan body lives at ``.squidsquad/<role>/planning/<n>-body.md`` where ``<n>``
    is the issue number. PM commits it as commit 1 of the task branch (which opens
    the draft PR); on merge it lands on the working branch co-located with the code
    that fulfilled it (#12750). These are versioned deliverables, not transient
    state, so the pre-commit state guard must NOT strip them from a feature branch.

    Kept deliberately narrow — only the ``<n>-body.md`` plan, never
    ``working-state.md`` / ``iterations/`` / vault notes — so it cannot reintroduce
    the #11511 merge-spiral (those siblings are rewritten every cycle and overlap
    across branches; a one-shot per-issue plan body does not). git always reports
    forward-slash paths in ``diff --cached``, so a plain ``/`` split is sufficient.
    """
    parts = path.split("/")
    if len(parts) != 4:
        return False
    if parts[0] != ".squidsquad" or parts[2] != "planning":
        return False
    name = parts[3]
    if not name.endswith("-body.md"):
        return False
    stem = name[: -len("-body.md")]
    return stem.isdigit()


def _auto_resolve_state_conflicts():
    """Auto-resolve unmerged state files (#8653).

    cycle_pre's pull can leave unresolved conflicts in ephemeral state files
    (e.g. .squidsquad/.backlog-cache, .squidsquad/.event-state.json). Those
    files are runtime state — the next cycle rewrites them — so picking either
    side is safe. We use --theirs (the incoming branch's version) so the
    resolution matches what's already on the remote.

    Code files outside .squidsquad/ and .claude/ are left untouched and
    reported as unresolved so the caller can fail fast.

    Returns (resolved_paths, unresolved_paths).
    """
    result = _run_list(["git", "ls-files", "--unmerged"], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return [], []
    paths = set()
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        paths.add(line.split("\t", 1)[1].strip())
    resolved = []
    unresolved = []
    for path in sorted(paths):
        if _is_state_file(path):
            r1 = _run_list(["git", "checkout", "--theirs", "--", path], check=False)
            r2 = _run_list(["git", "add", "--", path], check=False)
            if r1.returncode == 0 and r2.returncode == 0:
                resolved.append(path)
            else:
                unresolved.append(path)
        else:
            unresolved.append(path)
    return resolved, unresolved


def _safe_checkout(target_branch):
    """Switch to target branch, stashing unstaged changes if needed.

    Handles the case where hooks/linters modify files after a commit,
    which would cause a bare `git checkout` to fail.
    """
    current = _run("git branch --show-current", check=False).stdout.strip()
    if current == target_branch:
        return True
    # Try direct checkout first
    result = _run_list(["git", "checkout", target_branch], check=False)
    if result.returncode == 0:
        return True
    # Checkout failed (commonly unstaged changes, but possibly a non-dirty
    # reason e.g. branch-not-found) — stash anything present and retry. #13167:
    # guard the stash so a no-op stash (clean tree / non-dirty failure) never
    # leads to popping a PRE-EXISTING ancient stash. Only pop what we stashed.
    pre_stash_ref = _stash_top_ref()
    _run("git stash -q", check=False)
    stashed = _stash_top_ref() != pre_stash_ref
    result = _run_list(["git", "checkout", target_branch], check=False)
    if result.returncode != 0:
        # Checkout failed — restore original branch state. Use the conflict-safe
        # pop so a conflict here never leaves `<<<<<<<` markers either (#13045).
        if stashed:
            _safe_stash_pop()
        print(f"ERROR: could not switch to {target_branch}: {result.stderr}", file=sys.stderr)
        return False
    # Checkout succeeded — pop OUR stash on the target branch (conflict-safe,
    # #13045) only if we created one (#13167).
    if stashed:
        _safe_stash_pop()
    return True


def commit_code(role, branch, message):
    """Stage and commit only code files to a feature branch.

    Switches to the feature branch, stages everything EXCEPT state/ephemeral
    files (.squidsquad/, .claude/), commits, pushes the branch, then switches
    back to the configured working branch.
    """
    result = _run("git status --porcelain", check=False)
    if not result.stdout.strip():
        print("Nothing to commit (no changes)")
        return False

    # Get list of changed files
    # Don't strip() the full output — it removes the leading space from
    # the first line's XY status indicator (e.g. " M file.py").
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    code_files = []
    state_files = []
    for line in lines:
        # git status --porcelain format: XY<space>filename (3-char prefix)
        path = line[3:].strip().strip('"')
        # Handle renames: "old -> new"
        if " -> " in path:
            path = path.split(" -> ")[1]
        if _is_state_file(path):
            state_files.append(path)
        else:
            code_files.append(path)

    if not code_files:
        print("No code changes to commit (only state/ephemeral changes)")
        return False

    working = _get_working_branch()

    # Switch to feature branch
    current = _run("git branch --show-current").stdout.strip()
    if current != branch:
        # Check if branch exists
        check = _run_list(["git", "rev-parse", "--verify", branch], check=False)
        if check.returncode == 0:
            _run_list(["git", "checkout", branch])
        else:
            _run_list(["git", "checkout", "-b", branch])

    # Stage only code files
    for f in code_files:
        _run_list(["git", "add", f], check=False)

    # Safety: unstage config.md if it was staged by compose or other tools (#7491).
    # compose.py deploy writes event contracts to config.md, contaminating feature
    # branches. Explicitly revert it to the working branch version.
    _run_list(["git", "checkout", _get_working_branch(), "--",
               ".squidsquad/config.md"], check=False)

    # Commit
    alias = _get_alias(role)
    full_msg = f"{role}: {message}\n\nCo-Authored-By: {alias} <noreply@squidsquad>"
    # #13262: route through _run_list so the commit (and a hung pre-commit hook
    # holding _ENSURE_MAIN_LOCK) is timeout-protected like every other git op.
    result = _run_list(["git", "commit", "-m", full_msg], check=False)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit on branch")
            _safe_checkout(working)
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        _safe_checkout(working)
        return False

    # Push branch — failure is fatal for branch workflow (#5444)
    push_result = _git_push(["-u", "origin", branch])
    if push_result.returncode != 0:
        _log_diagnostic("error", f"branch push failed: {push_result.stderr.strip()[:200]}")
        print(f"ERROR: branch push failed: {push_result.stderr}", file=sys.stderr)
        _safe_checkout(working)
        return False

    # Emit git-commit (code) and git-push events (#4709)
    _emit("git-commit", {"message": message[:80], "branch": branch,
                         "files_changed": len(code_files), "commit_type": "code"})
    _emit("git-push", {"branch": branch})

    print(f"Committed code to {branch}: {message}")

    # Switch back to working branch
    _safe_checkout(working)
    return True


def _role_owned_patterns(role):
    """Path patterns this role is allowed to stage in its cycle commit (#8691).

    Patterns ending in '/' match by prefix; bare paths match exactly. The
    skill role is intentionally absent — skill's code/tests go through the
    branch+PR workflow via commit_code, and its state files go through
    commit_state (which is broader, allowing cross-role CLAUDE.md updates
    from compose.py deploy).
    """
    common = [
        f".squidsquad/{role}/",
        # ``.squidsquad/.backlog-cache`` removed 2026-06-05 (#11065): the
        # file is gitignored (`.gitignore:13-14`) so it has no business
        # in the state-commit allowlist. Leaving it here caused every
        # cycle to re-stage the tracked file and 3-way conflict against
        # any open PR that ``git rm --cached``d it (see #11042's two
        # route-backs on PR #11048 for the symptom). The file still
        # gets written locally for whatever in-cycle scripts read it,
        # but it never enters the index again.
        ".squidsquad/.event-state.json",
        # #12823 — the ship counter lives in its own file now (split out of
        # config.md so config.md can merge 3-way). It's DM-written but listed in
        # common so whatever role's cycle writes it (DM bump/reset, the #9772
        # reconcile) can also stage it via the role-scoped commit path.
        ".squidsquad/.ship-counter",
        ".squidsquad/vault/",
    ]
    role_specific = {
        "pm": [".squidsquad/config.md", ".squidsquad/project/"],
        # DM also legitimately writes SKILL.md (doc-improvement-loop
        # rotation scanning + line-level corrections) and
        # .squidsquad/config.md (Shipped Since Last Bump counter
        # increments, feature-flag toggles post-delivery). Before #9474
        # those edits were treated as foreign and left dirty in the
        # working tree — they either rotted for cycles or got
        # overwritten when a sibling commit re-staged the same file
        # from a stale base. Co-ownership of config.md with PM is
        # intentional: both roles legitimately mutate different fields
        # (PM: own-domain housekeeping; DM: ship counter + flags).
        #
        # RESOLVED (#12823): config.md previously had `merge=ours`, which
        # silently dropped any other agent's concurrent edit (the all-or-nothing
        # ours driver). The ship counter — the ONLY field that needed ours-wins
        # protection — was split into its own `.squidsquad/.ship-counter` file
        # (still merge=ours), so config.md now merges 3-way: real same-field
        # conflicts surface, non-overlapping edits (PM flag + DM flag) merge
        # cleanly. PM and DM co-ownership of config.md is now safe.
        "dm": [
            "README.md",
            "CHANGELOG.md",
            "docs/",
            "SKILL.md",
            ".squidsquad/config.md",
        ],
        # qa (verifier) authors comprehension specs under tests/comprehension/
        # (#9184 — the verifier derives CQ specs; skill never self-authors them).
        # These are permanent regression assets that MUST land in the repo, but
        # tests/comprehension/ is outside .squidsquad/ so it matched no pattern
        # and commit_role_scoped classified every new spec as "foreign" — leaving
        # it untracked until a manual "recover N-behind" rescue commit (#13212).
        # Adding it here lets the verifier's normal post-cycle commit stage its
        # own specs. Scoped to qa only: no other role authors comprehension specs.
        "qa": ["tests/comprehension/"],
    }
    return common + role_specific.get(role, [])


def _path_matches(path, patterns):
    """True if `path` matches any pattern. '/' suffix → prefix match; else exact."""
    for pat in patterns:
        if pat.endswith("/"):
            if path.startswith(pat):
                return True
        elif path == pat:
            return True
    return False


def commit_role_scoped(role, message):
    """Stage and commit only files in the role's commit domain (#8691).

    A single clone can have multiple agents and parallel processes writing
    files. A naive `git add -A` (the old commit_push path) bundles whatever
    happens to be uncommitted into the role's commit — even foreign code
    files or other roles' state. This pollutes the audit trail.

    This function uses an explicit per-role allowlist (see
    `_role_owned_patterns`). Foreign files are left in the working tree and
    surfaced as a stderr warning so the investigator can route them.

    #11083: refuses to stage when the current branch is not the configured
    working branch. Role-state commits belong on `main` (or whatever
    `working-branch` resolves to), not on a feature branch — landing them
    on a sibling agent's feature branch was the root cause of PR #11080's
    `BRIEFING.md` merge-spiral (PM's cycle hit a task-begin/task-end race
    while skill held the checkout). On a non-working branch, write-on-disk
    cycle behavior is unchanged; the staged commit is skipped and the
    files wait for the next cycle that lands on the working branch.

    Returns True if a commit (and push) succeeded, False otherwise.
    """
    working = _get_working_branch()
    current = _run("git branch --show-current").stdout.strip()
    if current != working:
        print(
            f"WARNING: cycle commit skipped — current branch '{current}' "
            f"is not the configured working branch '{working}'. Role-state "
            f"files stay on disk; the next cycle on '{working}' will commit "
            f"them. (#11083)",
            file=sys.stderr,
        )
        return False

    result = _run("git status --porcelain", check=False)
    if not result.stdout.strip():
        print("Nothing to commit")
        return False

    lines = [l for l in result.stdout.splitlines() if l.strip()]
    own_files = []
    foreign_files = []
    patterns = _role_owned_patterns(role)
    for line in lines:
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[1]
        if _path_matches(path, patterns):
            own_files.append(path)
        else:
            foreign_files.append(path)

    if foreign_files:
        print(
            f"WARNING: cycle commit skipped {len(foreign_files)} file(s) outside "
            f"'{role}' domain (left in working tree for the owning role to handle):",
            file=sys.stderr,
        )
        for f in foreign_files[:20]:
            print(f"  {f}", file=sys.stderr)
        if len(foreign_files) > 20:
            print(f"  ... and {len(foreign_files) - 20} more", file=sys.stderr)

    if not own_files:
        print("No role-domain changes to commit")
        return False

    for f in own_files:
        _run_list(["git", "add", "--", f], check=False)

    if not commit(role, message):
        return False
    return push(role=role)


def commit_state(role, message):
    """Stage and commit only .squidsquad/ files to the working branch.

    Only stages files under .squidsquad/. Commits and pushes to the
    configured working branch.
    """
    result = _run("git status --porcelain", check=False)
    if not result.stdout.strip():
        print("Nothing to commit")
        return False

    lines = [l for l in result.stdout.splitlines() if l.strip()]
    state_files = []
    for line in lines:
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[1]
        if path.startswith(".squidsquad/"):
            state_files.append(path)

    if not state_files:
        print("No state changes to commit")
        return False

    # Must be on working branch — state changes always go there
    working = _get_working_branch()
    current = _run("git branch --show-current").stdout.strip()
    if current != working:
        print(f"ERROR: commit-state requires {working} branch (currently on {current})", file=sys.stderr)
        return False

    # Stage only .squidsquad/ files
    for f in state_files:
        _run_list(["git", "add", f], check=False)

    # Commit
    alias = _get_alias(role)
    full_msg = f"{role}: {message}\n\nCo-Authored-By: {alias} <noreply@squidsquad>"
    # #13262: route through _run_list so the commit (and a hung pre-commit hook
    # holding _ENSURE_MAIN_LOCK) is timeout-protected like every other git op.
    result = _run_list(["git", "commit", "-m", full_msg], check=False)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit")
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return False

    # Emit git-commit (state) event (#4709)
    _emit("git-commit", {"message": message[:80], "branch": working,
                         "files_changed": len(state_files), "commit_type": "state"})

    # Push main — failure logged but state is committed locally (#5444)
    push_result = _git_push([])
    if push_result.returncode != 0:
        _log_diagnostic("error", f"state push failed: {push_result.stderr.strip()[:200]}")
        print(f"WARNING: state push failed: {push_result.stderr}", file=sys.stderr)
        # State push failure is non-fatal — state is committed locally,
        # next cycle's pull will sync. Return True since commit succeeded.
    else:
        _emit("git-push", {"branch": working})

    print(f"Committed state to main: {message}")
    return True


def get_branch_name(role, number):
    """Get the branch name for a task (#5040).

    Reads branch-pattern from config. Default: squidsquad/task/{number} (#6526).
    Pattern supports {role} and {number} placeholders.
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        pattern = get_field("branch-pattern") or ""
    except (SystemExit, Exception):
        pattern = ""
    if not pattern:
        pattern = "squidsquad/task/{number}"
    return pattern.format(role=role, number=number)


def task_begin(role, number):
    """Check out the task's feature branch (#3296, #9478).

    Uses configured branch pattern (#5040). Prints branch name to stdout
    so callers can capture it. Branch+PR is the only mode (#9478 D7) —
    no toggle, no early-return.
    """
    # Auto-resolve unmerged state files from pull conflicts (#8653). Code
    # conflicts still require manual resolution — fail fast in that case so
    # the agent surfaces the real problem instead of an opaque checkout error.
    resolved, unresolved = _auto_resolve_state_conflicts()
    if resolved:
        print(f"task-begin: auto-resolved state file conflict(s): {', '.join(resolved)}")
    if unresolved:
        print(
            "ERROR: task-begin found unresolved conflicts in non-state files:\n  "
            + "\n  ".join(unresolved),
            file=sys.stderr,
        )
        print("Resolve manually (e.g. `git checkout --ours/theirs <file> && git add <file>`) before retrying task-begin.", file=sys.stderr)
        sys.exit(1)

    branch = get_branch_name(role, number)
    working = _get_working_branch()

    # Check local
    local = _run_list(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], check=False)
    if local.returncode == 0:
        if not _safe_checkout(branch):
            print(f"ERROR: task-begin failed to checkout {branch}", file=sys.stderr)
            sys.exit(1)
        _emit("branch-checkout", {"branch": branch, "task_number": str(number)})
        print(branch)
        return

    # Fetch before checking remote — stale refs cause false negatives in
    # clone isolation (#5013)
    _run_list(["git", "fetch", "origin", branch], check=False)

    # Check remote
    remote = _run_list(["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"], check=False)
    if remote.returncode == 0:
        result = _run_list(["git", "checkout", "-b", branch, f"origin/{branch}"], check=False)
        if result.returncode == 0:
            _emit("branch-checkout", {"branch": branch, "task_number": str(number)})
            print(branch)
            return
        print(f"ERROR: task-begin failed to checkout {branch} from origin: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Branch not found — create from origin/<working> to avoid contamination (#5444)
    _run_list(["git", "fetch", "origin", working], check=False)
    origin_ref = f"origin/{working}"
    ref_check = _run_list(["git", "rev-parse", "--verify", origin_ref], check=False)
    if ref_check.returncode == 0:
        result = _run_list(["git", "checkout", "-b", branch, origin_ref], check=False)
    else:
        # Fallback: create from current HEAD if origin unreachable
        result = _run_list(["git", "checkout", "-b", branch], check=False)
    if result.returncode == 0:
        _emit("branch-checkout", {"branch": branch, "task_number": str(number)})
        print(branch)
        return
    print(f"ERROR: task-begin failed to create {branch}: {result.stderr}",
          file=sys.stderr)
    sys.exit(1)


def task_end(role, number):
    """Return to the working branch after task work (#3296, #9478).

    Branch+PR is the only mode (#9478 D7) — no toggle, no early-return.
    Warns if uncommitted changes remain on the feature branch.
    """
    working = _get_working_branch()

    # Safety: revert config.md to working branch version before leaving (#7491).
    # compose.py deploy may have contaminated config.md with event contract diffs.
    _run_list(["git", "checkout", working, "--",
               ".squidsquad/config.md"], check=False)

    # Warn about uncommitted changes
    status = _run("git status --porcelain", check=False)
    if status.stdout.strip():
        print(f"WARNING: uncommitted changes on current branch. "
              f"Commit via commit-code before calling task-end.", file=sys.stderr)

    if not _safe_checkout(working):
        # Fallback to main if working branch checkout fails
        _safe_checkout("main")

    _emit("branch-checkout", {"branch": working, "task_number": str(number)})


def has_changes():
    """Check if working tree has uncommitted changes."""
    result = _run("git status --porcelain")
    dirty = bool(result.stdout.strip())
    print("true" if dirty else "false")
    return dirty


def last_hash():
    """Print short hash of last commit."""
    result = _run("git rev-parse --short HEAD")
    h = result.stdout.strip()
    print(h)
    return h


def check_real_conflict(base, head):
    """Report whether merging <head> into <base> has a REAL content conflict.

    GitHub flags a PR ``CONFLICTING`` whenever transient files (e.g.
    ``working-state.md``) differ across branch and base — even when there is no
    real conflict — because GitHub honors NO user ``.gitattributes`` merge
    driver server-side (community discussion #9288; see
    [[learning-pr-conflicting-flag-can-be-cosmetic]]). This helper is the
    deterministic ground truth so agents/DM treat GitHub's flag as ADVISORY and
    stop burning cycles hand-nudging cosmetic flaps (#11511).

    Runs ``git merge-tree --write-tree`` (a non-destructive, in-memory three-way
    merge) in BOTH directions; a real conflict in either is a real conflict.
    Refs should be ``origin/*`` so the comparison matches what GitHub evaluates
    — callers should ``git fetch`` first.

    Returns True (clean), False (real conflict), or None (a ref won't resolve).
    main() maps these to exit 0 / 1 / 2.
    """
    for ref in (base, head):
        rc = _run_list(["git", "rev-parse", "--verify", "--quiet", ref], check=False)
        if rc.returncode != 0:
            print(f"ERROR: cannot resolve ref '{ref}' -- fetch first "
                  f"(e.g. `git fetch origin`)?", file=sys.stderr)
            return None

    conflict_lines = []
    real_conflict = False
    for a, b in ((base, head), (head, base)):
        result = _run_list(["git", "merge-tree", "--write-tree", a, b], check=False)
        if result.returncode != 0:
            real_conflict = True
            conflict_lines += [l for l in result.stdout.splitlines()
                               if "CONFLICT" in l or l.startswith("Conflict")]

    if not real_conflict:
        print(f"CLEAN: no real conflict merging {head} into {base} "
              f"(any GitHub CONFLICTING flag is cosmetic -- merge on content)")
        return True

    print(f"CONFLICT: real merge conflict merging {head} into {base}")
    for l in dict.fromkeys(conflict_lines):  # de-dup, preserve order
        print(f"  {l}")
    return False


# Path to the tracked git-hooks directory, repo-relative (the value we set
# core.hooksPath to). Tracked in-repo so the hook is version-controlled and
# ships via installer-files.txt — no copy-into-.git/hooks step needed.
_HOOKS_DIR_REL = "references/git-hooks"


def guard_staged_state():
    """Unstage transient state/ephemeral files when committing to a feature branch (#11511).

    git_ops' own commit paths already route state correctly: ``commit_code``
    stages code only, ``commit_role_scoped`` refuses off the working branch
    (#11083), ``commit_state`` errors off it. The remaining leak is a RAW
    ``git add -A && git commit`` (POLLING mode / branch races) that bypasses
    git_ops and sweeps ``.squidsquad/<role>/working-state.md`` (and siblings)
    onto a feature branch. That is what flaps PR mergeability to CONFLICTING
    (the file differs across the branch and main on overlapping lines, and
    GitHub honors no user .gitattributes merge driver server-side — see
    [[learning-pr-conflicting-flag-can-be-cosmetic]]).

    Installed as a ``pre-commit`` hook, this guard fires on every commit:

    - On the configured working branch (or a detached/unknown HEAD): no-op.
    - On any other (feature) branch: unstage every staged file classified as
      state/ephemeral by ``_is_state_file`` (the same classifier ``commit_code``
      uses), **except plan bodies** — ``_is_plan_body`` paths
      (``.squidsquad/<role>/planning/<n>-body.md``) are exempted so a task's
      committed plan rides the feature branch into the PR (plan-in-PR, #12750).
      That carve-out is guard-local: ``commit_code`` / ``commit_state`` /
      ``_auto_resolve_state_conflicts`` still treat plan bodies as state. The
      stripped files stay in the working tree for the next working-branch cycle
      to commit: ``.squidsquad/`` files via ``commit_state``; ``.claude/`` files
      via the working branch's normal state-commit path (``commit_state`` stages
      only ``.squidsquad/``).

    FAIL-OPEN: always returns normally (exit 0 at the call site). A pre-commit
    hook that aborts could wedge every agent's cycle, so this guard only ever
    *narrows* a commit, never blocks one.

    Returns the list of paths it unstaged (empty when it was a no-op).
    """
    working = _get_working_branch()
    # check=False: a failing `git branch --show-current` (corrupt HEAD, perms)
    # must not raise mid-commit -- empty `current` falls through to fail-open.
    current = _run("git branch --show-current", check=False).stdout.strip()
    # Empty current = detached HEAD or no branch -> can't classify; stay out of
    # the way (fail-open). On the working branch, state belongs here -> no-op.
    if not current or current == working:
        return []

    staged = _run_list(["git", "diff", "--cached", "--name-only"], check=False)
    if staged.returncode != 0:
        return []
    # Plan bodies (#12750) are versioned deliverables that ride the task branch
    # into the PR — exempt them from the strip even though they live under
    # .squidsquad/. Everything else under .squidsquad/ / .claude/ is still state.
    state_staged = []
    for raw in staged.stdout.splitlines():
        p = raw.strip().strip('"')
        if not p:
            continue
        if _is_state_file(p) and not _is_plan_body(p):
            state_staged.append(p)
    if not state_staged:
        return []

    # Unstage (reset, not restore --staged: works on older git and leaves the
    # working-tree copy untouched). Per-path so one bad path can't drop the lot.
    for p in state_staged:
        _run_list(["git", "reset", "-q", "HEAD", "--", p], check=False)

    print(
        f"WARNING: pre-commit guard unstaged {len(state_staged)} transient "
        f"state file(s) from feature branch '{current}' (state belongs on "
        f"'{working}', not in a PR -- #11511):",
        file=sys.stderr,
    )
    for p in state_staged[:20]:
        print(f"  {p}", file=sys.stderr)
    if len(state_staged) > 20:
        print(f"  ... and {len(state_staged) - 20} more", file=sys.stderr)
    return state_staged


def _galaxy_frontmatter_violation(content):
    """Return a one-line reason string if CONTENT fails the galaxy-frontmatter
    contract, else None. Mirrors ``tests/test_vault.py::TestGalaxyNotes::
    test_galaxy_notes_have_frontmatter`` EXACTLY so the guard never rejects a
    note the static gate would accept (no false positives)."""
    if not content.startswith("---"):
        return "missing YAML frontmatter (must start with '---')"
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "malformed frontmatter ('---' block not closed)"
    fm_keys = set()
    for line in parts[1].strip().splitlines():
        if ":" in line:
            fm_keys.add(line.split(":", 1)[0].strip())
    if not fm_keys:
        return "empty frontmatter (no keys)"
    if "type" not in fm_keys:
        return "missing required 'type' key in frontmatter"
    return None


def guard_galaxy_frontmatter():
    """Pre-commit guard: reject staged ``vault/galaxy/*.md`` notes that lack a
    valid YAML frontmatter block (#12905).

    Galaxy notes committed without frontmatter red the shared
    ``tests/test_vault.py::TestGalaxyNotes`` static gate for the WHOLE fleet
    (every agent's static run hits it) until someone notices and hand-fixes the
    note — a recurring, cross-role hygiene drain with a stash/merge-race risk.
    The root gap is no write-time enforcement; this is the deterministic
    backstop, independent of which agent/sub-skill wrote the note.

    Validates the STAGED blob (``git show :<path>``) — exactly what the commit
    will record — against the test contract via ``_galaxy_frontmatter_violation``.
    Returns the list of ``(path, reason)`` violations (empty = OK).

    FAIL-CLOSED on a real violation: the CLI wrapper exits 1 so the commit is
    blocked, stopping the bad note at the source. FAIL-OPEN on any guard-internal
    error (the CLI wrapper catches and exits 0), so a guard bug can NEVER wedge
    the fleet's commits — the static gate remains the safety net in that case.
    """
    staged = _run_list(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        check=False,
    )
    if staged.returncode != 0:
        return []
    violations = []
    for raw in staged.stdout.splitlines():
        p = raw.strip().strip('"')
        if not p:
            continue
        norm = p.replace("\\", "/")
        # Only galaxy notes under the ACTUAL vault location, *.md. Anchored to
        # .squidsquad/vault/galaxy/ so an unrelated path that merely contains
        # 'vault/galaxy' elsewhere (e.g. docs/vault/galaxy/architecture.md) is
        # never wrongly blocked — the static gate only ever checks
        # .squidsquad/vault/galaxy/ (DS-12905 Finding 2).
        if ".squidsquad/vault/galaxy/" not in norm or not norm.endswith(".md"):
            continue
        name = norm.rsplit("/", 1)[-1]
        # Exclude templates (scaffolding). .gitkeep is already filtered by the
        # .md check above, so no separate name-list is needed (DS-12905 F3).
        if name.endswith("-template.md"):
            continue
        blob = _run_list(["git", "show", f":{p}"], check=False)
        if blob.returncode != 0:
            # Unreadable staged blob — fail-open for this path; the static gate
            # still catches a malformed note.
            continue
        reason = _galaxy_frontmatter_violation(blob.stdout)
        if reason:
            violations.append((p, reason))
    if violations:
        print(
            f"ERROR: pre-commit guard BLOCKED commit — {len(violations)} galaxy "
            f"note(s) lack valid YAML frontmatter (#12905; a frontmatter-less "
            f"note reds tests/test_vault.py for the whole fleet):",
            file=sys.stderr,
        )
        for p, reason in violations:
            print(f"  {p}: {reason}", file=sys.stderr)
        print(
            "  Fix: prepend a '---' frontmatter block with at least a 'type:' "
            "key (see references/vault-templates/galaxy-template.md), then "
            "re-stage and commit.",
            file=sys.stderr,
        )
    return violations


def install_hooks():
    """Activate the tracked pre-commit guard by pointing core.hooksPath at it (#11511).

    Idempotent. Sets ``core.hooksPath`` to the in-repo ``references/git-hooks``
    directory (tracked, version-controlled) and makes the ``pre-commit`` shim
    executable. Because the hooks live in-repo, there is nothing to copy into
    ``.git/hooks`` and the activation survives a fresh clone the moment this
    runs.

    Safety: if ``core.hooksPath`` is already set to a DIFFERENT (foreign,
    non-SquidSquad) value, leave it alone and warn — we never clobber a user's
    own hooks configuration.

    Returns True if the guard is active after the call, False on a skip/error.
    """
    hook = REPO_ROOT / _HOOKS_DIR_REL / "pre-commit"
    if not hook.exists():
        print(f"WARNING: hook not found at {hook}; skipping install-hooks",
              file=sys.stderr)
        return False

    current = _run("git config --get core.hooksPath", check=False).stdout.strip()
    if current and current != _HOOKS_DIR_REL:
        print(
            f"WARNING: core.hooksPath already set to '{current}' (not "
            f"'{_HOOKS_DIR_REL}') -- leaving it; SquidSquad state guard not "
            f"activated. Set it manually if intended.",
            file=sys.stderr,
        )
        return False

    if current != _HOOKS_DIR_REL:
        rc = _run_list(["git", "config", "core.hooksPath", _HOOKS_DIR_REL], check=False)
        # A failed write (read-only .git/config, perms) leaves the guard
        # inactive -- honor the docstring contract and report False, don't
        # claim the guard is live when core.hooksPath never took.
        if rc.returncode != 0:
            print(
                f"WARNING: failed to set core.hooksPath to '{_HOOKS_DIR_REL}' "
                f"(git config exited {rc.returncode}); state guard not activated.",
                file=sys.stderr,
            )
            return False

    # Executable bit. On POSIX git only fires a hook whose exec bit is set, so a
    # chmod failure means the guard is installed but won't run -- report False
    # and warn. On Windows git ignores the exec bit (the shim runs via sh), so a
    # chmod failure there is benign and the guard is still active.
    try:
        import os
        import stat
        os.chmod(hook, os.stat(hook).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as e:
        if os.name == "posix":
            print(
                f"WARNING: core.hooksPath set but could not make {hook} "
                f"executable ({e}); pre-commit state guard may not fire.",
                file=sys.stderr,
            )
            return False
    return True


def _ensure_hooks_installed():
    """Self-heal hook activation on every git_ops invocation (#11511).

    git_ops is the deterministic git entry point every agent uses each cycle in
    BOTH wake modes, so calling this once per invocation guarantees the
    pre-commit guard is active in every clone — covering already-provisioned
    installs with zero installer/wizard/upgrade surgery. Fully wrapped: a hook
    that won't install must never break a git operation.
    """
    try:
        current = _run("git config --get core.hooksPath", check=False).stdout.strip()
        if not current:
            # Unset -> activate our guard (covers fresh / already-provisioned
            # clones with zero installer surgery).
            install_hooks()
        # When core.hooksPath is already ours we noop here: the hook is tracked
        # with mode 100755, so git restores its exec bit on every checkout/pull
        # -- no per-invocation chmod is needed and re-running install_hooks()
        # would add a pointless os.chmod to every git_ops call (#11511 DS
        # re-review2). The shipped-executable invariant is locked by
        # TestHookShippedExecutable11511.
        # A foreign (non-empty, non-ours) hooksPath is the operator's own
        # config: respect it SILENTLY on the self-heal path. install_hooks()
        # would re-emit its foreign-hooksPath WARNING on every git_ops
        # invocation (each call is a fresh process, so a warn-once flag can't
        # help). The explicit `install-hooks` command still surfaces that
        # warning when the operator asks for it directly.
    except Exception:
        pass


def _parse_args():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)
    return args[0], args[1:]


def main():
    cmd, rest = _parse_args()

    # Self-heal the pre-commit state guard on every invocation except the guard
    # itself (which the hook calls mid-commit) and `install-hooks` (which calls
    # install_hooks() explicitly in dispatch -- self-healing first would emit a
    # duplicate foreign-hooksPath WARNING). Keeps the commit path lean and
    # avoids re-checking what's already active (#11511).
    if cmd not in ("guard-staged-state", "guard-galaxy-frontmatter", "install-hooks"):
        _ensure_hooks_installed()

    if cmd == "pull":
        pull(role=rest[0] if rest else None)
    elif cmd == "ensure-main-and-pull":
        ok, detail = ensure_main_and_pull(role=rest[0] if rest else None)
        print(detail)
        sys.exit(0 if ok else 1)
    elif cmd == "add-all":
        add_all()
    elif cmd == "commit":
        if len(rest) < 2:
            print("Usage: git_ops.py commit <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit(rest[0], " ".join(rest[1:]))
    elif cmd == "push":
        push(role=rest[0] if rest else None)
    elif cmd == "commit-push":
        if len(rest) < 2:
            print("Usage: git_ops.py commit-push <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit_push(rest[0], " ".join(rest[1:]))
    elif cmd == "branch-create":
        if not rest:
            print("Usage: git_ops.py branch-create <name>", file=sys.stderr)
            sys.exit(1)
        branch_create(rest[0])
    elif cmd == "branch-switch":
        if not rest:
            print("Usage: git_ops.py branch-switch <name>", file=sys.stderr)
            sys.exit(1)
        branch_switch(rest[0])
    elif cmd == "pr-create":
        if len(rest) < 2:
            print("Usage: git_ops.py pr-create <title> <body>", file=sys.stderr)
            sys.exit(1)
        pr_create(rest[0], " ".join(rest[1:]))
    elif cmd == "pr-ready":
        if not rest:
            print("Usage: git_ops.py pr-ready <pr-number>", file=sys.stderr)
            sys.exit(1)
        success = pr_ready(rest[0])
        sys.exit(0 if success else 1)
    elif cmd == "pr-merge":
        if not rest:
            print("Usage: git_ops.py pr-merge <pr-number> [--strategy squash|merge]", file=sys.stderr)
            sys.exit(1)
        strategy = "squash"
        if "--strategy" in rest:
            idx = rest.index("--strategy")
            if idx + 1 < len(rest):
                strategy = rest[idx + 1]
        success, msg = pr_merge(rest[0], strategy)
        sys.exit(0 if success else 1)
    elif cmd == "commit-code":
        if len(rest) < 3:
            print("Usage: git_ops.py commit-code <role> <branch> <message>", file=sys.stderr)
            sys.exit(1)
        commit_code(rest[0], rest[1], " ".join(rest[2:]))
    elif cmd == "commit-state":
        if len(rest) < 2:
            print("Usage: git_ops.py commit-state <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit_state(rest[0], " ".join(rest[1:]))
    elif cmd == "commit-role-scoped":
        if len(rest) < 2:
            print("Usage: git_ops.py commit-role-scoped <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit_role_scoped(rest[0], " ".join(rest[1:]))
    elif cmd == "branch-exists":
        if not rest:
            print("Usage: git_ops.py branch-exists <name>", file=sys.stderr)
            sys.exit(1)
        branch_exists(rest[0])
    elif cmd == "branch-delete":
        if not rest:
            print("Usage: git_ops.py branch-delete <name>", file=sys.stderr)
            sys.exit(1)
        branch_delete(rest[0])
    elif cmd == "current-branch":
        current_branch()
    elif cmd == "task-begin":
        if len(rest) < 2:
            print("Usage: git_ops.py task-begin <role> <number>", file=sys.stderr)
            sys.exit(1)
        task_begin(rest[0], rest[1])
    elif cmd == "task-end":
        if len(rest) < 2:
            print("Usage: git_ops.py task-end <role> <number>", file=sys.stderr)
            sys.exit(1)
        task_end(rest[0], rest[1])
    elif cmd == "has-changes":
        has_changes()
    elif cmd == "last-hash":
        last_hash()
    elif cmd == "check-real-conflict":
        if len(rest) < 2:
            print("Usage: git_ops.py check-real-conflict <base-ref> <head-ref>",
                  file=sys.stderr)
            sys.exit(2)
        verdict = check_real_conflict(rest[0], rest[1])
        if verdict is None:
            sys.exit(2)        # could not resolve a ref
        sys.exit(0 if verdict else 1)   # 0 = clean, 1 = real conflict
    elif cmd == "guard-staged-state":
        guard_staged_state()
        sys.exit(0)            # FAIL-OPEN: the guard never blocks a commit
    elif cmd == "guard-galaxy-frontmatter":
        # FAIL-CLOSED on a confirmed violation; FAIL-OPEN on any guard-internal
        # error (a guard bug never wedges the fleet's commits; the static gate
        # stays the safety net).
        try:
            violations = guard_galaxy_frontmatter()
        except Exception as e:  # noqa: BLE001 — defensive fail-open
            print(
                f"WARNING: galaxy-frontmatter guard errored (fail-open, commit "
                f"allowed): {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            sys.exit(0)
        if violations:
            # The pre-commit shim decides to BLOCK on THIS explicit marker, NOT
            # on the exit code — a module-level python crash (bad import/syntax)
            # also exits 1, and keying the block on the exit code would let such
            # a crash wedge every commit fleet-wide (DS-12905 Finding 1). The
            # marker is only ever emitted here, after the guard ran and confirmed
            # a real violation.
            print("__SQUIDSQUAD_GALAXY_FM_BLOCK__", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    elif cmd == "install-hooks":
        ok = install_hooks()
        sys.exit(0 if ok else 1)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
