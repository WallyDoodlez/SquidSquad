#!/usr/bin/env python3
"""#11137 — reverse #11049 Path A over-inlining.

Replaces each `<!-- sub-skill: NAME --> ... <!-- /sub-skill: NAME -->`
block (for the 8 active-source sub-skills in scope) with a
marker-pattern reference:

    ### step:cycle/<step-id>

    → run sub-skill: NAME

    Goal: <statement>

`boot-bootstrap` stays inline (the only must-be-inline case per #11089
Change 3). Retired sub-skills (file-conventions, status-line,
prohibitions, agent-boundaries, responsibility, discussion-protocol)
also stay inline — their source files were removed in #11087.

Run with: python .squidsquad/skill/planning/migrate_11137.py
"""

import re
from pathlib import Path


# Sub-skill → (step header id, goal statement). The 8 active-source
# scope items from #11137. step:cycle/<id> mirrors the existing L1 boot
# step taxonomy (boot, resume, pickup, work, checkpoint, cleanup, exit)
# plus per-step ids for the two boot-phase checks (cycle-runner runs
# during boot framing; context-pressure runs at Step 1b).
GOALS = {
    "cycle-runner": (
        "run",
        "the cycle is structured per the install's wake-mode contract — "
        "`cycle_pre.py` has populated `cycle-input.json` with pull result, "
        "context pressure, working-state snapshot, and queue state; the "
        "agent's creative work has been read against that input; "
        "`cycle_post.py` will durably commit results and propagate status "
        "transitions. Hard precondition for any per-step work this cycle.",
    ),
    "context-pressure": (
        "context-pressure",
        "the agent has read the live context-pressure percentage from "
        "disk, compared it to the configured threshold, and (above "
        "threshold) checkpointed pending work to working-state plus "
        "pushed git so a respawn loses nothing. Below threshold this is "
        "a no-op and the cycle continues normally.",
    ),
    "resume-working-state": (
        "resume",
        "if a prior session left an active task in `working-state.md`, "
        "the agent has resumed it — completed steps, remaining steps, "
        "and key decisions trusted as still-current — rather than "
        "restarting from a cold tracker pull. If no active task, the "
        "cycle proceeds to fresh pickup.",
    ),
    "task-pickup": (
        "pickup",
        "the agent has selected exactly one approved task from the queue "
        "(priority-ordered, role-scoped, deterministic) — or has decided "
        "no actionable task exists and the cycle proceeds as quiet. The "
        "selected task is recorded in working-state.",
    ),
    "working-state": (
        "cleanup",
        "`working-state.md` reflects the cycle's outcome — cleared if a "
        "task shipped, updated if work continues — with the "
        "last-processed event ID preserved across any clear. The "
        "iteration log captures the cycle's summary for institutional "
        "memory.",
    ),
    "git-commit": (
        "checkpoint",
        "the cycle's work is durably checkpointed in git — code changes "
        "on the feature branch, state changes on the working branch, "
        "descriptive commit messages naming the task or issue, pushed "
        "if push is configured. Pending Test transitions are gated on "
        "this checkpoint.",
    ),
    "agent-lifecycle": (
        "exit",
        "the agent has checked for a graceful-stop signal from the "
        "harness and either scheduled the next cycle or exited cleanly "
        "per the stop intent. The harness owns lifecycle; the agent "
        "only honors it.",
    ),
    "improvement-scan-slim": (
        "improvement-scan",
        "on quiet cycles, the agent has consumed productive idle time "
        "by surfacing improvement findings against this role's domain "
        "— filed as low-priority issues, not auto-fixed. Active cycles "
        "skip this entirely.",
    ),
}

ORCHESTRATORS = [
    Path("references/roles/worker/instructions.md"),
    Path("references/roles/pm/instructions.md"),
    Path("references/roles/dm/instructions.md"),
    Path("references/roles/verifier/instructions.md"),
]


def _build_replacement(name: str) -> str:
    step_id, goal = GOALS[name]
    return (
        f"### step:cycle/{step_id}\n"
        f"\n"
        f"→ run sub-skill: {name}\n"
        f"\n"
        f"Goal: {goal}\n"
    )


def _convert(text: str) -> tuple[str, list[str]]:
    """Return (new_text, [converted-sub-skill-names])."""
    converted = []
    for name in GOALS:
        # Match the full marker-wrapped block including the markers.
        # The block body can span multiple lines; non-greedy match.
        # Use re.DOTALL so . matches newlines.
        pattern = re.compile(
            r"<!-- sub-skill: " + re.escape(name) + r" -->\n"
            r".*?"
            r"<!-- /sub-skill: " + re.escape(name) + r" -->\n",
            re.DOTALL,
        )
        new_block = _build_replacement(name)
        new_text, n = pattern.subn(new_block, text)
        if n > 0:
            converted.append(f"{name} ({n}x)")
            text = new_text
    return text, converted


def main() -> int:
    total_blocks = 0
    for path in ORCHESTRATORS:
        if not path.exists():
            print(f"SKIP {path} (missing)")
            continue
        text = path.read_text(encoding="utf-8")
        new_text, converted = _convert(text)
        if not converted:
            print(f"NOOP {path}")
            continue
        path.write_text(new_text, encoding="utf-8")
        print(f"WROTE {path}: {', '.join(converted)}")
        total_blocks += sum(int(c.split("(")[1].split("x)")[0]) for c in converted)
    print(f"---\nTotal blocks converted: {total_blocks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
