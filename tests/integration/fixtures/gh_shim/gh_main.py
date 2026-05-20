#!/usr/bin/env python3
"""PATH-shim for the ``gh`` CLI — used by #9398 Phase A real-agent-
subprocess tests so the spawned agent's ``tracker.py`` calls don't
hit the live GitHub forge.

The fixture (``tests/integration/fixtures/event_mode_subprocess.py``)
prepends this directory to the subprocess's ``PATH``, ahead of any
real ``gh`` install. When ``tracker.py`` then runs e.g.
``gh issue list --label "role:skill" --state open --json ...``, this
script runs instead and serves a canned response from the directory
named by the ``$GH_SHIM_FIXTURES_DIR`` env var.

Response selection: each invocation looks up
``$GH_SHIM_FIXTURES_DIR/<subcommand>/<key>.json`` where:
- ``subcommand`` is the joined first two args after ``gh`` (e.g.
  ``issue-list``, ``issue-view``, ``issue-edit``).
- ``key`` is derived from the remaining args. For ``issue view N``
  the key is the issue number; for ``issue list ...`` the key is
  the literal string ``default`` (tests can override by setting
  ``$GH_SHIM_LIST_KEY``).

If the fixture file is missing, exits 0 with empty output for read-
type commands (``view``, ``list``) so the agent sees "nothing to do"
rather than crashing. For write-type commands (``edit``, ``create``,
``comment``, ``close``) the script appends a one-line JSON record
to ``$GH_SHIM_FIXTURES_DIR/_writes.log`` and exits 0 — tests assert
on the log contents to verify the agent issued the expected
transition.

This is intentionally a minimal contract. Once #9398 work-pickup
tests need richer behavior (e.g. issue create returning a new
number), this can grow to consult a Python callback registered via
env var, but YAGNI for now.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


_READ_COMMANDS = {"view", "list", "status"}
_WRITE_COMMANDS = {"edit", "create", "comment", "close", "delete", "transfer"}


def _fixtures_dir() -> Path | None:
    raw = (os.environ.get("GH_SHIM_FIXTURES_DIR") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _emit_empty_for_read(verb: str) -> int:
    """Best-effort empty response for read-type commands when no
    fixture is configured. ``gh ... --json ...`` outputs a JSON
    array for ``list`` and an object for ``view``; emit shape-
    appropriate defaults so tracker.py's JSON parse succeeds."""
    if verb == "list":
        sys.stdout.write("[]\n")
    else:
        sys.stdout.write("{}\n")
    return 0


def _log_write(topic: str, verb: str, args: list[str],
               fixtures_dir: Path | None) -> int:
    """Record a write-type invocation. If a fixtures dir is
    configured, append to its _writes.log. Otherwise just succeed
    silently — agents fire-and-forget on most write paths and
    shouldn't crash if no test cares about the call.

    Log shape: ``{"ts", "topic", "verb", "subcmd", "args"}``. Tests
    can assert on any field; ``verb`` is the most useful for
    'agent transitioned this issue' style assertions."""
    if fixtures_dir is not None:
        log = fixtures_dir / "_writes.log"
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "topic": topic,
                "verb": verb,
                "subcmd": f"{topic}-{verb}",
                "args": args,
            }) + "\n"
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError as e:
            sys.stderr.write(f"gh-shim: failed to log write: {e}\n")
            return 0  # don't fail the agent on a logging failure
    return 0


def _serve_read(subcmd: str, verb: str, args: list[str],
                fixtures_dir: Path) -> int:
    """Serve a canned response for a read-type subcommand. Returns
    exit code; writes the response to stdout."""
    # Key derivation: ``view N`` → key=N; everything else → "default"
    # unless overridden via env.
    if verb == "view" and args:
        key = args[0]
    else:
        key = os.environ.get("GH_SHIM_LIST_KEY", "default")

    fixture = fixtures_dir / subcmd / f"{key}.json"
    if fixture.is_file():
        sys.stdout.write(fixture.read_text(encoding="utf-8"))
        if not fixture.read_text(encoding="utf-8").endswith("\n"):
            sys.stdout.write("\n")
        return 0
    # No fixture for this key — fall back to empty.
    return _emit_empty_for_read(verb)


def main(argv: list[str]) -> int:
    # Strip the program name; what remains is the gh invocation.
    args = argv[1:]
    if not args:
        sys.stderr.write("gh-shim: missing subcommand\n")
        return 2

    # Recognize a handful of bare flags that the live gh supports
    # so tracker.py's pre-flight checks succeed cleanly.
    if args[0] in ("--version", "-v"):
        sys.stdout.write("gh-shim 0.1 (fixture for SquidSquad tests)\n")
        return 0
    if args[0] in ("--help", "-h"):
        sys.stdout.write(__doc__)
        return 0

    # Standard form: ``gh <topic> <verb> [args...]``. The shim
    # serves only the small set of subcommands the agent invokes.
    if len(args) < 2:
        sys.stderr.write(
            f"gh-shim: expected `gh <topic> <verb> ...`, got {args!r}\n"
        )
        return 2

    topic, verb = args[0], args[1]
    rest = args[2:]
    subcmd = f"{topic}-{verb}"

    fixtures_dir = _fixtures_dir()

    if verb in _READ_COMMANDS:
        if fixtures_dir is None or not fixtures_dir.is_dir():
            return _emit_empty_for_read(verb)
        return _serve_read(subcmd, verb, rest, fixtures_dir)

    if verb in _WRITE_COMMANDS:
        return _log_write(topic, verb, rest, fixtures_dir)

    # Unrecognized — fall through to empty success. Loud failures
    # tend to mask the actual test intent.
    sys.stderr.write(
        f"gh-shim: unrecognized verb {verb!r} (subcmd={subcmd!r}); "
        f"returning empty success.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
