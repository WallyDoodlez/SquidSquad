#!/usr/bin/env python3
"""SquidSquad migration — move state files to dedicated state branch.

Migrates agent state files from the working branch to the state branch.
Run once during upgrade to 3-branch architecture.

Usage:
    python scripts/migrate_state_branch.py          # Run migration
    python scripts/migrate_state_branch.py --dry-run # Show what would move
    python scripts/migrate_state_branch.py --help

Exit codes:
    0 — success (or nothing to migrate)
    1 — migration failed
    2 — usage error
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"

# Files/dirs that move to the state branch
STATE_PATTERNS = [
    "*/current-state",
    "*/working-state.md",
    "*/iterations/",
    "*/.health",
    "*/.pid",
    "*/context-pressure",
    "*/restart-log.txt",
    "*/scan-history.md",
    "vault/",
]

# Files that stay on the working branch
KEEP_PATTERNS = [
    "config.md",
    ".local-config",
    "*/CLAUDE.md",
    "*/SOUL.md",
    "*/planning/",
    "start-*.sh",
    "start-*.ps1",
    "inject-permissions.*",
]


def _run(cmd, check=True, cwd=None):
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check,
        cwd=cwd or str(REPO_ROOT),
    )


def _is_state_file(rel_path):
    """Check if a file matches state patterns."""
    rel = str(rel_path).replace("\\", "/")
    for pattern in STATE_PATTERNS:
        if pattern.endswith("/"):
            # Directory pattern
            if pattern.startswith("*/"):
                if f"/{pattern[2:]}" in rel + "/":
                    return True
            elif rel.startswith(pattern) or f"/{pattern}" in rel:
                return True
        elif pattern.startswith("*/"):
            # Wildcard prefix
            suffix = pattern[2:]
            if rel.endswith(suffix) or f"/{suffix}" in rel:
                return True
        elif rel == pattern or rel.endswith(f"/{pattern}"):
            return True
    return False


def find_state_files():
    """Find all state files in .squidsquad/ that should migrate."""
    if not SQUIDSQUAD_DIR.exists():
        return []

    state_files = []
    for path in SQUIDSQUAD_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(SQUIDSQUAD_DIR)
        if _is_state_file(rel):
            state_files.append(rel)

    return sorted(state_files)


def migrate(dry_run=False):
    """Migrate state files to the state branch."""
    # Import state_bus for worktree operations
    sys.path.insert(0, str(SCRIPT_DIR))
    import state_bus

    # Ensure state branch and worktree exist
    if not dry_run:
        state_bus.init()

    state_files = find_state_files()
    if not state_files:
        print("No state files to migrate.")
        return 0

    print(f"Found {len(state_files)} state files to migrate:")
    for f in state_files:
        print(f"  {f}")

    if dry_run:
        print("\n(dry run — no files moved)")
        return 0

    # Copy files to state worktree
    migrated = 0
    for rel in state_files:
        src = SQUIDSQUAD_DIR / rel
        try:
            content = src.read_text(encoding="utf-8")
            if state_bus.write_file(str(rel), content):
                migrated += 1
        except (OSError, UnicodeDecodeError) as e:
            print(f"  WARNING: Failed to migrate {rel}: {e}", file=sys.stderr)

    # Commit the migration. #9939: capture the return — commit_and_push
    # returns False on commit failure OR push failure (e.g., the #9930
    # credential-helper wedge), and the original code discarded that
    # signal, reporting "Migrated X/Y" with exit 0 even when the state
    # never actually reached origin. A failed-but-reported-success
    # migration during the 3-branch cutover can silently lose state on
    # the next `git fetch + reset --hard` (e.g., from the #9934 manual
    # recovery one-liner).
    if migrated > 0:
        pushed = state_bus.commit_and_push(
            f"migrate: {migrated} state files from working branch",
            role="migration",
        )
        if not pushed:
            print(
                f"\nMigrated {migrated}/{len(state_files)} files LOCALLY, "
                "but commit_and_push failed — migration is NOT durable.",
                file=sys.stderr,
            )
            print(
                "  Files exist in .squidsquad-state/ on this machine but "
                "have NOT reached origin/<state-branch>.",
                file=sys.stderr,
            )
            print(
                "  Investigate BEFORE deleting originals from the working "
                "branch. Common cause: #9930 credential-helper wedge.",
                file=sys.stderr,
            )
            return 1

    print(f"\nMigrated {migrated}/{len(state_files)} files to state branch.")
    if migrated == 0 and len(state_files) > 0:
        print("ERROR: All migrations failed.", file=sys.stderr)
        return 1
    return 0


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    dry_run = "--dry-run" in args

    try:
        return migrate(dry_run=dry_run)
    except Exception as e:
        print(f"ERROR: Migration failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
