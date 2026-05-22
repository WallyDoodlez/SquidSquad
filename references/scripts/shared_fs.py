#!/usr/bin/env python3
"""SquidSquad shared filesystem — ~/.squidsquad/ for cross-clone secrets and config.

All agent clones read from this shared location. Secrets are plain text
key=value files with restricted permissions (no env var contamination).

Usage:
    python scripts/shared_fs.py init                    # Create ~/.squidsquad/ structure
    python scripts/shared_fs.py read-secret KEY         # Read a secret value
    python scripts/shared_fs.py write-secret KEY VALUE  # Write a secret (chmod 600)
    python scripts/shared_fs.py read-clones             # Read cross-clone paths (JSON)
    python scripts/shared_fs.py write-clone ROLE PATH   # Register a clone path
    python scripts/shared_fs.py home                    # Print ~/.squidsquad/ path
"""

import json
import os
import stat
import sys
import tempfile
from pathlib import Path


def get_home():
    """Return the shared filesystem root: ~/.squidsquad/"""
    return Path.home() / ".squidsquad"


def init():
    """Create ~/.squidsquad/ directory structure if it doesn't exist.

    Creates:
        ~/.squidsquad/
        ~/.squidsquad/secrets      (chmod 600)
        ~/.squidsquad/config
        ~/.squidsquad/clones/
    """
    home = get_home()
    home.mkdir(parents=True, exist_ok=True)

    secrets_file = home / "secrets"
    if not secrets_file.exists():
        secrets_file.write_text(
            "# SquidSquad secrets — one KEY=VALUE per line\n"
            "# Permissions are restricted to current user only\n",
            encoding="utf-8",
        )
        _restrict_permissions(secrets_file)

    config_file = home / "config"
    if not config_file.exists():
        config_file.write_text(
            "# SquidSquad global config — shared across all clones\n",
            encoding="utf-8",
        )

    clones_dir = home / "clones"
    clones_dir.mkdir(exist_ok=True)

    print(f"Initialized {home}")
    return str(home)


def _restrict_permissions(path):
    """Set file permissions to owner-only (chmod 600 / Windows ACL).

    Uses ``sys.platform`` instead of ``platform.system()`` to avoid the
    Python 3.12 Windows WMI wedge (#9903).
    """
    path = Path(path)
    if sys.platform == "win32":
        # Windows: use icacls to restrict to current user
        import subprocess
        user = os.environ.get("USERNAME", "")
        if user:
            subprocess.run(
                ["icacls", str(path), "/inheritance:r",
                 "/grant:r", f"{user}:(R,W)"],
                capture_output=True, check=False,
            )
    else:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _parse_secrets(text):
    """Parse KEY=VALUE lines from secrets file."""
    secrets = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            secrets[key.strip()] = value.strip()
    return secrets


def read_secret(key):
    """Read a secret from ~/.squidsquad/secrets.

    Returns the value if found, None if not found or file doesn't exist.
    """
    secrets_file = get_home() / "secrets"
    if not secrets_file.exists():
        return None
    try:
        text = secrets_file.read_text(encoding="utf-8")
        secrets = _parse_secrets(text)
        return secrets.get(key)
    except (OSError, UnicodeDecodeError):
        return None


def read_secret_or_env(key):
    """Read a secret from ~/.squidsquad/secrets, falling back to env var.

    Priority: secrets file > environment variable.
    """
    value = read_secret(key)
    if value is not None:
        return value
    return os.environ.get(key)


def write_secret(key, value):
    """Write or update a secret in ~/.squidsquad/secrets.

    #9932: atomic write. ``Path.write_text`` opens in ``'w'`` mode which
    truncates the destination before writing — a crash between the
    truncate and the final flush would leave the secrets file empty,
    losing API keys for every configured provider (not just the one
    being updated). Instead we write to a sibling ``.tmp``, restrict
    permissions on it (so the brief window between rename and chmod
    can't expose the new file with directory default ACLs), and
    ``os.replace`` for an atomic swap (atomic on both POSIX and
    Windows per Python docs).
    """
    secrets_file = get_home() / "secrets"
    if not secrets_file.parent.exists():
        init()

    # Read existing
    existing = {}
    if secrets_file.exists():
        text = secrets_file.read_text(encoding="utf-8")
        existing = _parse_secrets(text)

    # Update
    existing[key] = value

    # Write back
    lines = ["# SquidSquad secrets — one KEY=VALUE per line\n"]
    for k, v in sorted(existing.items()):
        lines.append(f"{k}={v}\n")

    # #9932: write to a sibling .tmp first, restrict its permissions,
    # then atomic-rename. NamedTemporaryFile gives us a unique name
    # in the same directory (so os.replace stays on the same filesystem
    # and is truly atomic) and cleans up if the write itself raises.
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".secrets-", suffix=".tmp", dir=str(secrets_file.parent)
    )
    tmp_path = Path(tmp_path)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write("".join(lines))
        _restrict_permissions(tmp_path)
        os.replace(tmp_path, secrets_file)
    except Exception:
        # Best-effort cleanup of the tmp file if anything went wrong
        # between mkstemp and os.replace. The original secrets file is
        # untouched (the whole point of the atomic-write fix).
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
    print(f"Secret '{key}' written to {secrets_file}")


def read_clones():
    """Read cross-clone paths from ~/.squidsquad/clones/.

    Returns dict: {role: path_string}
    """
    clones_dir = get_home() / "clones"
    if not clones_dir.exists():
        return {}

    result = {}
    for clone_file in clones_dir.iterdir():
        if clone_file.is_file() and not clone_file.name.startswith("."):
            try:
                path = clone_file.read_text(encoding="utf-8").strip()
                if path:
                    result[clone_file.name] = path
            except (OSError, UnicodeDecodeError):
                continue
    return result


def write_clone(role, path):
    """Register a clone path in ~/.squidsquad/clones/."""
    clones_dir = get_home() / "clones"
    if not clones_dir.exists():
        init()

    clone_file = clones_dir / role
    clone_file.write_text(str(path) + "\n", encoding="utf-8")
    print(f"Clone '{role}' registered: {path}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    cmd = args[0]

    if cmd == "init":
        init()
    elif cmd == "home":
        print(get_home())
    elif cmd == "read-secret":
        if len(args) < 2:
            print("Usage: shared_fs.py read-secret KEY", file=sys.stderr)
            return 2
        value = read_secret_or_env(args[1])
        if value is not None:
            print(value)
        else:
            print(f"Secret '{args[1]}' not found", file=sys.stderr)
            return 1
    elif cmd == "write-secret":
        if len(args) < 3:
            print("Usage: shared_fs.py write-secret KEY VALUE", file=sys.stderr)
            return 2
        write_secret(args[1], args[2])
    elif cmd == "read-clones":
        clones = read_clones()
        print(json.dumps(clones, indent=2))
    elif cmd == "write-clone":
        if len(args) < 3:
            print("Usage: shared_fs.py write-clone ROLE PATH", file=sys.stderr)
            return 2
        write_clone(args[1], args[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
