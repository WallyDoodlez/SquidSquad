#!/usr/bin/env python3
"""SquidSquad self-diagnostic logging and issue report generation.

Local anomaly detection log + upstream issue report helper.

Usage:
    python scripts/diagnostics.py log <severity> <source> <message> [--context <json>]
    python scripts/diagnostics.py read [--last N]         # Read last N entries (default 20)
    python scripts/diagnostics.py rotate                  # Rotate log if over 1MB
    python scripts/diagnostics.py report                  # Generate bug report content
    python scripts/diagnostics.py is-public               # Check if repo is public
    python scripts/diagnostics.py --help
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
MAX_LOG_BYTES = 1_000_000  # 1MB cap

# Import config reader and state_bus path resolution (#3664)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from config import get_field, _read_config
except ImportError:
    def get_field(f):
        return None
    def _read_config():
        return ""

try:
    from state_bus import state_path as _state_path
    DIAGNOSTICS_DIR = _state_path("diagnostics")
except ImportError:
    DIAGNOSTICS_DIR = REPO_ROOT / ".squidsquad" / "diagnostics"
LOG_FILE = DIAGNOSTICS_DIR / "diagnostic.jsonl"


def log_entry(severity, source, message, context=None):
    """Append a diagnostic entry to the log file."""
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "severity": severity,  # info, warning, error
        "source": source,      # tracker, compose, git_ops, cycle, boot
        "message": message,
    }
    if context:
        try:
            entry["context"] = json.loads(context) if isinstance(context, str) else context
        except json.JSONDecodeError:
            entry["context"] = {"raw": context}

    # Auto-rotate before write if over cap (#5385)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_BYTES:
        rotate()

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def read_entries(last=20):
    """Read the last N diagnostic entries."""
    if not LOG_FILE.exists():
        print("[]")
        return []

    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines[-last:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    print(json.dumps(entries, indent=2))
    return entries


def rotate():
    """Rotate log file — keep last 500 entries, discard older."""
    if not LOG_FILE.exists():
        return

    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) <= 500:
        return

    # Keep last 500
    LOG_FILE.write_text("\n".join(lines[-500:]) + "\n", encoding="utf-8")
    print(f"Rotated: kept last 500 of {len(lines)} entries")


def _sanitize_config():
    """Read config.md and redact sensitive fields."""
    try:
        text = _read_config()
    except SystemExit:
        return "(config not found)"

    # Redact potential sensitive values — any line with a sensitive keyword
    # and a colon is treated as a key-value pair and redacted (#7518).
    lines = []
    for line in text.splitlines():
        lower = line.lower()
        if any(k in lower for k in ["repo", "path", "email", "token", "secret", "key", "url", "clone", "webhook", "password"]):
            if ":" in line:
                field = line.split(":", 1)[0]
                lines.append(f"{field}: [REDACTED]")
                continue
        lines.append(line)
    return "\n".join(lines)


def is_public_repo():
    """Check if current repo is public."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "isPrivate"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=True, cwd=str(REPO_ROOT),
        )
        data = json.loads(result.stdout)
        is_private = data.get("isPrivate", True)
        public = not is_private
        print("true" if public else "false")
        return public
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print("unknown")
        return None


def generate_report():
    """Generate an issue report template with diagnostic context."""
    try:
        version = get_field("version")
    except SystemExit:
        version = "unknown"

    config_snapshot = _sanitize_config()

    # Recent diagnostics
    entries = []
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
        for line in lines[-20:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    diag_text = ""
    if entries:
        diag_text = "\n### Recent Diagnostics\n\n```json\n"
        for e in entries:
            diag_text += json.dumps(e) + "\n"
        diag_text += "```\n"

    report = f"""## Issue Report — SquidSquad

### Environment
- **SquidSquad Version**: {version}
- **Platform**: (fill in: Windows/macOS/Linux)
- **Claude Code Version**: (fill in)

### Description
(Describe the issue — what happened, what you expected)

### Steps to Reproduce
1. (step 1)
2. (step 2)

### Config Snapshot (sanitized)

```
{config_snapshot}
```
{diag_text}
---
*Filed via /squidsquad-issue*
"""
    print(report)
    return report


def _parse_args():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)
    return args[0], args[1:]


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    cmd, rest = _parse_args()

    if cmd == "log":
        if len(rest) < 3:
            print("Usage: diagnostics.py log <severity> <source> <message> [--context <json>]", file=sys.stderr)
            sys.exit(1)
        context = None
        if "--context" in rest:
            idx = rest.index("--context")
            if idx + 1 < len(rest):
                context = rest[idx + 1]
                rest = rest[:idx] + rest[idx+2:]
        log_entry(rest[0], rest[1], " ".join(rest[2:]), context)

    elif cmd == "read":
        last = 20
        if "--last" in rest:
            idx = rest.index("--last")
            if idx + 1 < len(rest):
                try:
                    last = int(rest[idx + 1])
                except ValueError:
                    print(f"ERROR: --last requires an integer, got: {rest[idx + 1]!r}",
                          file=sys.stderr)
                    sys.exit(1)
        read_entries(last)

    elif cmd == "rotate":
        rotate()

    elif cmd == "report":
        generate_report()

    elif cmd == "is-public":
        is_public_repo()

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
