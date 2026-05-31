#!/usr/bin/env python3
"""SquidSquad vault-remember deterministic gates.

Provides scripted checks for the vault-remember sub-skill.
LLM judgment is only used for reusability assessment and content writing.

Usage:
    python scripts/vault_remember.py is-quiet <role>           # Check if cycle was quiet
    python scripts/vault_remember.py write-budget <role>        # Remaining write budget
    python scripts/vault_remember.py inc-writes <role>          # Increment write counter
    python scripts/vault_remember.py reset-writes <role>        # Reset write counter (start of cycle)
    python scripts/vault_remember.py briefing-budget            # BRIEFING.md token budget remaining
    python scripts/vault_remember.py effective-confidence <note> # Compute effective confidence with decay
    python scripts/vault_remember.py note-count                 # Total vault note count
    python scripts/vault_remember.py decay-scan                 # Find notes needing confidence decay
    python scripts/vault_remember.py --help
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
VAULT_DIR = SQUIDSQUAD_DIR / "vault"
CONFIG_PATH = SQUIDSQUAD_DIR / "config.md"

# Import config reader
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from config import get_field
except ImportError:
    def get_field(field):
        return None

from shared_fs import atomic_write_text  # #10007


def _read_working_state(role):
    """Read working-state.md for a role."""
    ws_path = SQUIDSQUAD_DIR / role / "working-state.md"
    if not ws_path.exists():
        return ""
    return ws_path.read_text(encoding="utf-8")


def _write_working_state_field(role, field_pattern, new_value):
    """Update a field in working-state.md. Returns True on success, False on failure."""
    ws_path = SQUIDSQUAD_DIR / role / "working-state.md"
    if not ws_path.exists():
        return False
    try:
        text = ws_path.read_text(encoding="utf-8")
        new_text = re.sub(field_pattern, new_value, text)
        atomic_write_text(ws_path, new_text)
        return True
    except OSError as e:
        print(f"WARNING: Failed to update {ws_path}: {e}", file=sys.stderr)
        return False


def is_quiet(role):
    """Check if current cycle was quiet based on iteration log content.

    Reads the most recent iter file within the interval window and checks
    the Type field. Returns exit code 0 if quiet, 1 if non-quiet.
    """
    iter_dir = SQUIDSQUAD_DIR / role / "iterations"
    if not iter_dir.exists():
        print("quiet")
        return True

    # Get configured interval (default 30 minutes)
    try:
        interval = int(get_field("interval"))
    except (TypeError, ValueError, SystemExit):
        interval = 30

    cutoff = datetime.now() - timedelta(minutes=interval)

    # Find most recent iter file within the interval window
    recent = None
    recent_mtime = None
    for log_file in iter_dir.glob("iter-*.md"):
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime > cutoff and (recent_mtime is None or mtime > recent_mtime):
            recent = log_file
            recent_mtime = mtime

    if recent is None:
        print("quiet")
        return True

    # Check file content for Type field
    try:
        content = recent.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- **Type**:"):
                type_val = stripped.split(":", 1)[1].strip().lower()
                if type_val == "quiet":
                    print("quiet")
                    return True
                else:
                    print("non-quiet")
                    return False
        # Old-format files without Type field — treat as active (non-quiet)
        print("non-quiet")
        return False
    except (IOError, OSError):
        print("quiet")
        return True


def write_budget(role):
    """Return remaining vault write budget for this cycle.

    Exit code 0 if budget remains, 1 if exhausted.
    """
    # Read max from config (default 2)
    try:
        max_writes = int(get_field("vault-writes-per-cycle"))
    except (TypeError, ValueError, SystemExit):
        max_writes = 2

    # Read current count from working-state
    ws_text = _read_working_state(role)
    match = re.search(r'Vault Writes This Cycle\*\*:\s*(\d+)', ws_text)
    current = int(match.group(1)) if match else 0

    remaining = max(0, max_writes - current)
    print(str(remaining))
    return remaining


def _upsert_vault_writes(role, new_value):
    """Set the Vault Writes This Cycle field, creating it if absent (#4919)."""
    ws_text = _read_working_state(role)
    match = re.search(r'Vault Writes This Cycle\*\*:\s*(\d+)', ws_text)
    if match:
        _write_working_state_field(
            role,
            r'(Vault Writes This Cycle\*\*:\s*)\d+',
            rf'\g<1>{new_value}',
        )
    else:
        ws_path = SQUIDSQUAD_DIR / role / "working-state.md"
        if ws_path.exists():
            text = ws_path.read_text(encoding="utf-8")
            text += f"\n- **Vault Writes This Cycle**: {new_value}\n"
            atomic_write_text(ws_path, text)
    return new_value


def inc_writes(role):
    """Increment vault write counter in working-state.md."""
    ws_text = _read_working_state(role)
    match = re.search(r'Vault Writes This Cycle\*\*:\s*(\d+)', ws_text)
    current = int(match.group(1)) if match else 0
    new_count = current + 1
    _upsert_vault_writes(role, new_count)
    print(str(new_count))
    return new_count


def reset_writes(role):
    """Reset vault write counter to 0."""
    _upsert_vault_writes(role, 0)
    print("0")
    return 0


def briefing_budget():
    """Check BRIEFING.md token budget. Returns remaining tokens.

    Token approximation: words * 1.3
    """
    try:
        max_tokens = int(get_field("briefing-token-budget"))
    except (TypeError, ValueError, SystemExit):
        max_tokens = 2000

    briefing_path = VAULT_DIR / "BRIEFING.md"
    if not briefing_path.exists():
        print(str(max_tokens))
        return max_tokens

    text = briefing_path.read_text(encoding="utf-8")
    word_count = len(text.split())
    approx_tokens = int(word_count * 1.3)
    remaining = max(0, max_tokens - approx_tokens)

    print(str(remaining))
    return remaining


def effective_confidence(note_path):
    """Compute effective confidence with age-based decay.

    Decay rules (from CONTEXT.md):
    - Notes tagged 'evergreen' are exempt
    - High -> Medium after decay_days without update
    - Medium -> Low after decay_days without update
    - Low stays Low

    Base confidence is never modified in the file.
    """
    try:
        decay_days = int(get_field("confidence-decay-days"))
    except (TypeError, ValueError, SystemExit):
        decay_days = 60

    path = Path(note_path)
    if not path.is_absolute():
        path = VAULT_DIR / note_path
    path = path.resolve()
    if not path.is_relative_to(VAULT_DIR.resolve()):
        print("error: note path outside vault directory", file=sys.stderr)
        sys.exit(2)
    if not path.exists():
        print("error: note not found", file=sys.stderr)
        sys.exit(2)

    text = path.read_text(encoding="utf-8")

    # Parse frontmatter
    if not text.startswith("---"):
        print("error: no frontmatter", file=sys.stderr)
        sys.exit(2)

    parts = text.split("---", 2)
    if len(parts) < 3:
        print("error: invalid frontmatter", file=sys.stderr)
        sys.exit(2)

    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()

    base_confidence = fm.get("confidence", "medium")
    tags = fm.get("tags", "")
    updated = fm.get("updated", "")

    # Evergreen exemption
    if "evergreen" in tags:
        print(base_confidence)
        return base_confidence

    # Calculate age
    if not updated:
        print(base_confidence)
        return base_confidence

    try:
        updated_date = datetime.strptime(updated, "%Y-%m-%d")
    except ValueError:
        print(base_confidence)
        return base_confidence

    age = (datetime.now() - updated_date).days

    if age <= decay_days:
        print(base_confidence)
        return base_confidence

    # Apply decay
    decay_map = {"high": "medium", "medium": "low", "low": "low"}
    effective = decay_map.get(base_confidence, base_confidence)
    print(effective)
    return effective


def note_count():
    """Count total .md files in vault."""
    if not VAULT_DIR.exists():
        print("0")
        return 0

    count = sum(1 for _ in VAULT_DIR.rglob("*.md") if _.name != ".gitkeep")
    print(str(count))
    return count


def decay_scan():
    """Find active notes needing confidence decay. Returns list of paths."""
    try:
        decay_days = int(get_field("confidence-decay-days"))
    except (TypeError, ValueError, SystemExit):
        decay_days = 60

    if not VAULT_DIR.exists():
        print("[]")
        return []

    flagged = []
    cutoff = datetime.now() - timedelta(days=decay_days)

    for md in VAULT_DIR.rglob("*.md"):
        if md.name == ".gitkeep" or md.name == "BRIEFING.md":
            continue

        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # Skip unreadable files gracefully (#7624)
        if not text.startswith("---"):
            continue

        parts = text.split("---", 2)
        if len(parts) < 3:
            continue

        fm = {}
        for line in parts[1].strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                fm[key.strip()] = val.strip()

        status = fm.get("status", "")
        if status != "active":
            continue

        tags = fm.get("tags", "")
        if "evergreen" in tags:
            continue

        confidence = fm.get("confidence", "")
        if confidence == "low":
            continue  # Already at lowest

        updated = fm.get("updated", "")
        if not updated:
            continue

        try:
            updated_date = datetime.strptime(updated, "%Y-%m-%d")
        except ValueError:
            continue

        if updated_date < cutoff:
            rel = md.relative_to(VAULT_DIR).as_posix()
            decay_map = {"high": "medium", "medium": "low"}
            decayed = decay_map.get(confidence, confidence)
            flagged.append(f"{rel} ({confidence} -> {decayed})")

    for f in flagged:
        print(f"DECAY: {f}")
    if not flagged:
        print("OK: No notes need decay")
    return flagged


def _parse_args():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)
    return args[0], args[1:]


def main():
    # Ensure UTF-8 output on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    cmd, rest = _parse_args()

    if cmd == "is-quiet":
        if not rest:
            print("Usage: vault_remember.py is-quiet <role>", file=sys.stderr)
            sys.exit(2)
        sys.exit(0 if is_quiet(rest[0]) else 1)

    elif cmd == "write-budget":
        if not rest:
            print("Usage: vault_remember.py write-budget <role>", file=sys.stderr)
            sys.exit(2)
        remaining = write_budget(rest[0])
        sys.exit(0 if remaining > 0 else 1)

    elif cmd == "inc-writes":
        if not rest:
            print("Usage: vault_remember.py inc-writes <role>", file=sys.stderr)
            sys.exit(2)
        inc_writes(rest[0])

    elif cmd == "reset-writes":
        if not rest:
            print("Usage: vault_remember.py reset-writes <role>", file=sys.stderr)
            sys.exit(2)
        reset_writes(rest[0])

    elif cmd == "briefing-budget":
        briefing_budget()

    elif cmd == "effective-confidence":
        if not rest:
            print("Usage: vault_remember.py effective-confidence <note-path>", file=sys.stderr)
            sys.exit(2)
        effective_confidence(rest[0])

    elif cmd == "note-count":
        note_count()

    elif cmd == "decay-scan":
        decay_scan()

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
