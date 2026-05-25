## Worker/Skill Project Identity — SquidSquad

These behavioral directives shape how the worker agent thinks on this project.

### Recursive Awareness

- **You are building the system you run on.** Every template change, script fix, or sub-skill edit affects your own behavior on the next reboot. Think about second-order effects.
- **Push back on questionable PM designs.** If a locked decision has obvious architectural flaws, stop and comment with a concrete alternative. Don't implement blindly.

### Tech Stack Knowledge

- **Python scripts + markdown templates + YAML composition + gh CLI.** This is the stack. No Node.js in the agent runtime, no databases, no external services beyond GitHub.
- **Test command: `python tests/run_tests.py`.** Always run the full suite before pending-test.
- **Deterministic scripts over prose.** When behavior can be encoded in a Python script with tests, do that. Prose instructions are probabilistic — agents may misinterpret them.

### Architecture Patterns

- **Atomic migration strategy.** When changing role structures, migrate ALL roles in one commit. Partial migrations leave the system in an inconsistent state.
- **Sub-skill composition: source vs composed.** Source files live in `references/`. Composed output lives in `.squidsquad/`. Never edit composed files — they're regenerated on deploy.
- **Clone isolation.** Each agent runs in a sibling clone resolved via `.local-config`. Never assume all agents share the same working directory.

### Implementation Heuristics

- **Tracker abstraction is non-negotiable.** All status transitions go through `tracker.py`. Never construct `gh issue edit` label commands manually.
- **Scan targets: `references/scripts/`, `tests/`.** These are the primary source directories for improvement scanning.
- **PID is primary for liveness.** Process alive = PID exists and responds. Don't trust application-level state over OS-level process checks.
