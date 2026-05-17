#!/usr/bin/env python3
"""SquidSquad cycle operations -- timestamps, quiet detection, counters, iteration logs.

Single source of truth for cycle management operations.

Usage:
    python scripts/cycle.py timestamp              # YYYY-MM-DD HH:MM
    python scripts/cycle.py timestamp-short        # HH:MM:SS
    python scripts/cycle.py step-marker <message>   # Print step marker
    python scripts/cycle.py status-bar <role> <phase> <desc>  # Write current-state
    python scripts/cycle.py get-counter <role>      # Read quiet cycle counter
    python scripts/cycle.py inc-counter <role>      # Increment quiet cycle counter
    python scripts/cycle.py reset-counter <role>    # Reset counter to 0
    python scripts/cycle.py log-iteration <role> <n> [--quiet] [--work <w>] [--notes <n>]
    python scripts/cycle.py cleanup-iterations <role> [--keep 20]
    python scripts/cycle.py --help
"""

import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"

# Import state_bus for path resolution (#3664)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from state_bus import state_path as _state_path
except ImportError:
    def _state_path(rel):
        return SQUIDSQUAD_DIR / rel


def _now():
    """Get current local time."""
    return datetime.now()


def timestamp():
    """Return YYYY-MM-DD HH:MM timestamp."""
    ts = _now().strftime("%Y-%m-%d %H:%M")
    print(ts)
    return ts


def timestamp_short():
    """Return HH:MM:SS timestamp."""
    ts = _now().strftime("%H:%M:%S")
    print(ts)
    return ts


def step_marker(message):
    """Print a formatted step marker."""
    ts = _now().strftime("%H:%M:%S")
    marker = f"[🦑 {ts}] {message}"
    print(marker)
    return marker


def status_bar(role, phase, description=""):
    """Write current-state atomically for status bar display."""
    state_dir = SQUIDSQUAD_DIR / role
    tmp_path = state_dir / "current-state.tmp"
    final_path = state_dir / "current-state"

    content = f"{phase}|{description}" if description else f"{phase}|"
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(final_path)
    return content


def _get_working_state_path(role):
    return _state_path(f"{role}/working-state.md")


def _read_counter(role):
    """Read quiet cycle counter without printing (#7610)."""
    ws_path = _get_working_state_path(role)
    if not ws_path.exists():
        return 0
    text = ws_path.read_text(encoding="utf-8")
    match = re.search(r'Quiet Cycle Counter\*\*:\s*(\d+)', text)
    return int(match.group(1)) if match else 0


def get_counter(role):
    """Read quiet cycle counter from working-state.md."""
    count = _read_counter(role)
    print(str(count))
    return count


def set_counter(role, value):
    """Set quiet cycle counter in working-state.md (upserts if field absent)."""
    ws_path = _get_working_state_path(role)
    if not ws_path.exists():
        return
    text = ws_path.read_text(encoding="utf-8")
    if re.search(r'Quiet Cycle Counter\*\*:\s*\d+', text):
        new_text = re.sub(
            r'(Quiet Cycle Counter\*\*:\s*)\d+',
            rf'\g<1>{value}',
            text,
        )
    else:
        new_text = text.rstrip("\n") + f"\n- **Quiet Cycle Counter**: {value}\n"
    ws_path.write_text(new_text, encoding="utf-8")
    return value


def inc_counter(role):
    """Increment quiet cycle counter."""
    count = _read_counter(role)
    new_count = count + 1
    set_counter(role, new_count)
    print(str(new_count))
    return new_count


def reset_counter(role):
    """Reset quiet cycle counter to 0."""
    set_counter(role, 0)
    print("0")
    return 0


def log_iteration(role, n, quiet=False, work=None, notes="",
                   bugs=None, features=None, issues=None, tasks=None, tests=None):
    """Create an iteration log file in unified format.

    All roles use the same format: Date, Type, Work Summary, Notes.
    Quiet cycles get a condensed 2-3 line entry.
    Legacy params (bugs/features/issues/tasks/tests) are converted to work bullets.
    """
    ts = _now().strftime("%Y-%m-%d %H:%M")
    iter_dir = _state_path(f"{role}/iterations")
    iter_dir.mkdir(parents=True, exist_ok=True)
    path = iter_dir / f"iter-{n}.md"

    if quiet:
        content = (
            f"# Iteration {n}\n\n"
            f"- **Date**: {ts}\n"
            f"- **Type**: quiet\n"
            f"- **Note**: {notes or 'No actionable work available'}\n"
        )
    else:
        # Build work summary from explicit bullets or legacy params
        work_bullets = []
        if work:
            work_bullets = work if isinstance(work, list) else [work]
        else:
            issues_val = issues if issues is not None else bugs
            tasks_val = tasks if tasks is not None else features
            if issues_val and issues_val != "none":
                work_bullets.append(f"Issues: {issues_val}")
            if tasks_val and tasks_val != "none":
                work_bullets.append(f"Tasks: {tasks_val}")
            if tests and tests != "n/a":
                work_bullets.append(f"Tests: {tests}")

        work_lines = "\n".join(f"  - {b}" for b in work_bullets) if work_bullets else "  - none"
        content = (
            f"# Iteration {n}\n\n"
            f"- **Date**: {ts}\n"
            f"- **Type**: active\n"
            f"- **Work Summary**:\n"
            f"{work_lines}\n"
            f"- **Notes**: {notes or 'none'}\n"
        )

    path.write_text(content, encoding="utf-8")
    print(f"Created {path.relative_to(REPO_ROOT)}")
    return str(path)


def cleanup_iterations(role, keep=20):
    """Remove oldest iteration files, keeping the most recent `keep` count."""
    iter_dir = _state_path(f"{role}/iterations")
    if not iter_dir.exists():
        return 0

    files = sorted(iter_dir.glob("iter-*.md"), key=lambda f: f.stat().st_mtime)
    to_remove = files[:-keep] if len(files) > keep else []
    for f in to_remove:
        f.unlink()
    if to_remove:
        print(f"Removed {len(to_remove)} old iteration files")
    return len(to_remove)


def _parse_args():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    pos = []
    opts = {}
    i = 1
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                opts[key] = args[i + 1]
                i += 2
            else:
                opts[key] = True
                i += 1
        else:
            pos.append(args[i])
            i += 1
    return cmd, pos, opts


def main():
    # Ensure UTF-8 output on Windows (cp1252 can't handle emoji)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    cmd, pos, opts = _parse_args()

    if cmd == "timestamp":
        timestamp()
    elif cmd == "timestamp-short":
        timestamp_short()
    elif cmd == "step-marker":
        step_marker(pos[0] if pos else "")
    elif cmd == "status-bar":
        if len(pos) < 2:
            print("Usage: cycle.py status-bar <role> <phase> [desc]", file=sys.stderr)
            sys.exit(1)
        status_bar(pos[0], pos[1], pos[2] if len(pos) > 2 else "")
    elif cmd == "get-counter":
        if not pos:
            print("Usage: cycle.py get-counter <role>", file=sys.stderr)
            sys.exit(1)
        get_counter(pos[0])
    elif cmd == "inc-counter":
        if not pos:
            print("Usage: cycle.py inc-counter <role>", file=sys.stderr)
            sys.exit(1)
        inc_counter(pos[0])
    elif cmd == "reset-counter":
        if not pos:
            print("Usage: cycle.py reset-counter <role>", file=sys.stderr)
            sys.exit(1)
        reset_counter(pos[0])
    elif cmd == "log-iteration":
        if len(pos) < 2:
            print("Usage: cycle.py log-iteration <role> <n> [--quiet] [--work <w>] [--notes <n>]", file=sys.stderr)
            sys.exit(1)
        try:
            iter_n = int(pos[1])
        except ValueError:
            print(f"ERROR: iteration number must be numeric, got '{pos[1]}'", file=sys.stderr)
            sys.exit(1)
        is_quiet_flag = opts.get("quiet", False)
        work_val = opts.get("work")
        work_list = [w.strip() for w in work_val.split(",")] if isinstance(work_val, str) else None
        log_iteration(pos[0], iter_n,
                       quiet=bool(is_quiet_flag),
                       work=work_list,
                       notes=opts.get("notes", ""),
                       issues=opts.get("issues", opts.get("bugs")),
                       tasks=opts.get("tasks", opts.get("features")),
                       tests=opts.get("tests"))
    elif cmd == "cleanup-iterations":
        if not pos:
            print("Usage: cycle.py cleanup-iterations <role> [--keep N]", file=sys.stderr)
            sys.exit(1)
        try:
            keep_n = int(opts.get("keep", 20))
        except ValueError:
            print(f"ERROR: --keep must be numeric, got '{opts.get('keep')}'", file=sys.stderr)
            sys.exit(1)
        cleanup_iterations(pos[0], keep_n)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
