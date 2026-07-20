"""#13865 -- pin gh API calls to the repo's push identity via GH_TOKEN.

gh's "active account" is machine-global mutable state (its hosts.yml `user`
field): any process can flip it with `gh auth switch`, and during the #13863
incident something external to SquidSquad kept flipping it to a read-only
identity every few minutes -- live-observed breaking a `pr-create` mid-cycle
with "GraphQL: must be a collaborator". #13863 made *git pushes* flip-proof
(pinned credential helper) and heals the active account at *boot*; this module
closes the remaining exposure: every mid-session gh API call (tracker
transitions, label writes, comments, PR operations) rode the active account.

The pin: resolve the identity the origin remote requires, fetch that user's
keyring token via `gh auth token --user X` (flip-independent -- it reads the
keyring entry, not the active-account pointer), and hand callers a subprocess
env with GH_TOKEN set. The gh CLI prefers GH_TOKEN over the active account,
so the flip becomes irrelevant to the call.

Leaf module by design: imported by tracker.py and git_ops.py; imports nothing
of theirs (they cannot import each other). Fail-open everywhere -- any
resolution failure returns None and the caller inherits the ambient env,
which is exactly today's behavior.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# Process-lifetime caches ("unset" sentinel distinguishes "never resolved"
# from a resolved None).
_IDENTITY_CACHE = "unset"
_TOKEN_CACHE = "unset"


def pinned_identity():
    """The GitHub account the origin remote requires for writes.

    Same derivation as git_ops._resolve_push_identity (#13863), duplicated
    here so this stays a leaf module: embedded https userinfo wins
    (``https://USER@github.com/owner/repo``), else the owner path segment.
    None for non-https remotes, token-bearing userinfo, or non-username
    shapes. Cached for the process lifetime.
    """
    global _IDENTITY_CACHE
    if _IDENTITY_CACHE != "unset":
        return _IDENTITY_CACHE
    ident = None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, cwd=str(REPO_ROOT), timeout=10,
        )
        url = (result.stdout or "").strip()
        if result.returncode == 0 and url.startswith("https://"):
            rest = url[len("https://"):]
            host_part, _, path_part = rest.partition("/")
            userinfo, at_sep, _host = host_part.rpartition("@")
            if at_sep and userinfo and ":" not in userinfo:
                candidate = userinfo
            else:
                candidate = path_part.split("/", 1)[0] if path_part else ""
            if re.fullmatch(r"[A-Za-z0-9-]+", candidate or ""):
                ident = candidate
    except (OSError, subprocess.TimeoutExpired):
        pass
    _IDENTITY_CACHE = ident
    return ident


def pinned_token():
    """The pinned identity's keyring token via ``gh auth token --user X``.

    Flip-independent: reads the named keyring entry regardless of which
    account is currently "active". None (fail-open) when no identity is
    derivable, gh is missing, or the identity has no keyring entry. Cached
    for the process lifetime -- one gh subprocess per process, not per call.
    """
    global _TOKEN_CACHE
    if _TOKEN_CACHE != "unset":
        return _TOKEN_CACHE
    token = None
    user = pinned_identity()
    if user:
        try:
            result = subprocess.run(
                ["gh", "auth", "token", "--user", user],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", check=False, cwd=str(REPO_ROOT), timeout=10,
            )
            out = (result.stdout or "").strip()
            if result.returncode == 0 and out:
                token = out
        except (OSError, subprocess.TimeoutExpired):
            pass
    _TOKEN_CACHE = token
    return token


def gh_env(cmd_list):
    """Subprocess env for a gh invocation, GH_TOKEN-pinned to the repo's
    identity -- or None, meaning "inherit the ambient env unchanged".

    Callers pass the result straight to ``subprocess.run(..., env=...)``
    (env=None IS the inherit contract). Returns None -- never injects -- when:

    - ``cmd_list`` is not a gh command (first element neither ``"gh"`` nor a
      resolved path whose basename starts with ``gh``);
    - it is a ``gh auth ...`` subcommand: auth operations must see the real
      keyring/hosts state, and gh refuses or bypasses keyring writes when a
      GH_TOKEN env var is present (injecting would break the very
      ``gh auth token``/``gh auth switch`` machinery the pin relies on);
    - the ambient env already carries GH_TOKEN or GITHUB_TOKEN: an
      operator-set token is an explicit override this module must not fight;
    - no identity/token is resolvable (fail-open -- today's behavior).
    """
    if not cmd_list:
        return None
    head = os.path.basename(str(cmd_list[0])).lower()
    if not (head == "gh" or head.startswith("gh.")):
        return None
    if len(cmd_list) > 1 and cmd_list[1] == "auth":
        return None
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        return None
    token = pinned_token()
    if not token:
        return None
    env = dict(os.environ)
    env["GH_TOKEN"] = token
    return env


if __name__ == "__main__":
    # Tiny diagnostic CLI: print the pinned identity and whether a token is
    # resolvable (never the token itself).
    user = pinned_identity()
    print(f"pinned identity: {user or '(none)'}")
    print(f"keyring token: {'available' if pinned_token() else 'unavailable'}")
    sys.exit(0)
