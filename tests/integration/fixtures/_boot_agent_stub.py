"""Minimal boot-agent stub for the #9398 Phase A fixture.

Spawned by ``boot_agent_subprocess`` to exercise the bootup-complete
contract end-to-end across a real process boundary. Imports
``event_bus`` (which picks up ``SQUIDSQUAD_DIR`` from the env), calls
``event_bus.bootup_complete(role)`` once, and exits.

Not a full agent — there is no cycle_pre/cycle_post loop here, no
work_queue, no L1 init beyond the bootup signal. The intent is the
smallest reproducible exercise of the contract: an agent process
discovers the harness via the port file and posts the boot signal.

Usage:
    python _boot_agent_stub.py <role>

Exit codes:
    0 - bootup_complete emitted successfully (event_bus is
        fire-and-forget; emission "success" means no exception, not
        a 200 ack from the harness).
    2 - bad arguments.
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        sys.stderr.write(
            "usage: python _boot_agent_stub.py <role>\n"
        )
        sys.exit(2)
    role = sys.argv[1].strip()

    # Ensure we can find the SquidSquad scripts on sys.path so the
    # subprocess works regardless of which directory pytest happened
    # to chdir to when invoking us.
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(repo_root / "references" / "scripts"))

    import event_bus  # noqa: E402 — path adjusted above

    event_bus.bootup_complete(role)
    sys.exit(0)
