I've carefully analyzed the diff and the surrounding context in the changed files. Here's my assessment:

**Summary of the change**: The "Determine wake mode from config" sub-step is removed from the boot block in all 9 files (8 composed CLAUDE.md files + 1 source `instructions.md`). The harness probe is promoted from a conditional step (event-mode candidate only) to the universal mode selector. The EVENT mode and POLLING mode blocks below remain unchanged.

**Trace through all scenarios**:

| Scenario | Old behavior | New behavior | Match? |
|---|---|---|---|
| `event-driven: yes` + harness reachable | EVENT mode | EVENT mode | ✓ |
| `event-driven: yes` + harness unreachable | POLLING mode | POLLING mode | ✓ |
| No `event-driven` field + harness reachable | POLLING (skip probe) | EVENT mode | Intentional per §2 |
| No `event-driven` field + harness unreachable | POLLING (skip probe) | POLLING (after probe timeout) | ✓ |
| `event-driven: no` + harness reachable | POLLING (skip probe) | EVENT mode | Intentional per §2 |
| Missing/unreadable config + harness reachable | POLLING (skip probe) | EVENT mode | Intentional per §2 |

The two "different" scenarios are intentional per AGENT-RUNTIME §2 ("the harness probe IS the mode selector"), not regressions. The old config-gate path that forced polling when the harness was actually running was the bug being fixed.

**Integration check with Python runtime**: `config.py:get_wake_mode()`, `cycle_post.py`, and `statusline_data.py` still use config.md for mode detection. This creates a theoretical divergence when an agent boots EVENT via harness probe but Python scripts see POLLING via config. However, this divergence already existed in the opposite direction before (config says event-driven, harness unreachable → agent boots polling, scripts see event-driven). This is a pre-existing architectural issue (noted as remaining work G10/G11 in the commit message) and is not worsened by this change.

**Structural integrity**: All 8 composed files + the source `instructions.md` are updated consistently. The `<!-- sub-skill: boot-bootstrap -->` markers are intact. The EVENT mode and POLLING mode blocks are unmodified. No stale references to "Determine wake mode from config" remain in the changed files.

NO_FINDINGS