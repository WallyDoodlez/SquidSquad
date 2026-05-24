Here is the complete punch-list of findings, ordered by severity:

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 925-926 (boot decision tree)
- **Severity**: HIGH
- **Issue**: The boot decision tree uses harness reachability as the sole mode gate — if harness is reachable, event mode loads; if not, polling mode loads — without ever checking `config.md`'s `event-driven:` field.
- **Evidence**: The tree shows `Start → Probe → |yes| LoadEvent` but never consults the `event-driven:` config value that §8.1 says controls mode selection. A user who sets `event-driven: no` globally but has a running harness would be forced into event mode against their explicit configuration.
- **Suggested fix**: Insert a config-check node between `Probe:yes` and `LoadEvent` that reads `event-driven:` and `event-driven-<role>:`; only route to `LoadEvent` if event-driven is enabled for that role AND harness is reachable.

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 210 (signal catalog) vs 741 (handoff sequence diagram)
- **Severity**: HIGH
- **Issue**: The wire format for `assigned-to` payload uses `issue_number` and `target_role` in the signal catalog (§4.2), but the `/work/assign` POST body in the handoff sequence (§7.3) uses `issue` and `next_role` for the same fields.
- **Evidence**: §4.2 table shows `{issue_number, title, target_role, event_context, payload}`; §7.3 mermaid line 741 shows `{issue:9926, next_role:verifier,...}`. An implementer cannot know which field names to use in the HTTP API.
- **Suggested fix**: Normalize to one set of field names everywhere (e.g., `issue_number` + `target_role`), and audit the doc for any remaining `issue` or `next_role` references in wire-format contexts.

---

### Finding 3

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 305 (harness internals diagram) and 816 (EAD safety net diagram)
- **Severity**: HIGH
- **Issue**: Two Mermaid diagrams show EAD calling `gh api / search` against Forge, but §4.4 explicitly locks the decision to use the REST API (`gh api repos/<owner>/<repo>/issues?...`), with a dedicated "Why REST, not Search API" justification box.
- **Evidence**: Line 305: `EAPoll <-- "gh api / search" --> Forge`; line 816: `EAD->>F: gh api / search`. Both contradict the locked REST decision on line 374 and the rationale on lines 382-385.
- **Suggested fix**: Change both diagram labels from `gh api / search` to `gh api repos/.../issues?since=...` to match the locked REST endpoint.

---

### Finding 4

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 562-566 (§6.4) vs 46-47 (§2 mode table) and 182 (§3.3)
- **Severity**: HIGH
- **Issue**: §6.4 states the harness respawns the agent on exit-42 from context-pressure, but loop mode is documented as working without the harness (§2 table: "works without the harness"), and §3.3 confirms `event_poll` is not spawned in loop mode. In harness-less loop mode, exit-42 kills the agent with no respawn path.
- **Evidence**: Line 564: "The harness sees the non-zero exit and respawns the agent." Line 46: "Battle-tested fallback; works without the harness; current default." Line 566: "This is loop mode's primary form of session lifecycle." These cannot all be true simultaneously for the harness-less loop-mode case.
- **Suggested fix**: Specify two different respawn paths: (a) with harness → harness respawns, (b) without harness → `thin_launcher` loops or the `/loop` cron survives context-pressure through a sub-process handoff, or document that exit-42 is harness-gated and harness-less loop mode uses a different session-lifecycle strategy.

---

### Finding 5

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 901 (§8.1) vs 905 (§8.2)
- **Severity**: MED
- **Issue**: §8.1 says `compose.py` routes to mode-specific fragments at compose time ("compose.py reads this and routes to the appropriate sub-skill manifest at compose time"), but §8.2 says no recompose is needed for a mode flip because boot-bootstrap reads mode fragments at runtime. These are contradictory statements about when mode-specific fragment selection occurs.
- **Evidence**: Line 901: compose-time routing; line 905: "No recompose is needed because boot-bootstrap reads the mode-specific fragments at runtime." If both are true, the model must be that compose.py includes BOTH fragment sets and boot-bootstrap picks, but this resolution is never stated.
- **Suggested fix**: Clarify that compose.py bundles both loop-mode and event-mode fragments into the composed output, and boot-bootstrap selects the active set at runtime based on the probe + config decision.

---

### Finding 6

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 624 (nudge contract sequence diagram)
- **Severity**: MED
- **Issue**: The nudge format is documented as literal `NUDGE\n` with no payload (§7.0 lines 574, 588; §8.5 migration line 947), but the sequence diagram at line 624 shows event_poll writing `"NUDGE 3 new events"` — a string carrying event count and descriptive text.
- **Evidence**: Line 574: "writes a literal `NUDGE\n` line"; line 588: "Nudge format is literal `NUDGE\n` with no payload"; line 624: `"NUDGE 3 new events"`. The diagram format would break any implementation that does exact string matching on the nudge line.
- **Suggested fix**: Change line 624 to show literal `NUDGE` (no payload) to match the locked format, or explicitly declare that the payload after `NUDGE` is informational/debug-only and agents must not parse it.

---

### Finding 7

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 574 (§7.0) and 157 (§3.2)
- **Severity**: MED
- **Issue**: `event_poll.py --wait --target stdout` is shown without a `--role` argument, but event_poll must know the agent's role to construct the `GET /events/for/{role}?since=cursor` URL against the harness.
- **Evidence**: Line 157 shows `event_poll.py --wait --target stdout`; line 165 shows it calling `GET /events/for/{role}`. The role is not derivable from the CLI signature shown. If it comes from an environment variable or discovery file, that contract is not specified.
- **Suggested fix**: Add `--role <role>` to the `event_poll` CLI signature in §3.2 and §7.0, or document the environment variable / file-based mechanism by which event_poll discovers its role.

---

### Finding 8

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 686-692 (boot sequence) vs 597-611 (nudge contract)
- **Severity**: MED
- **Issue**: The boot sequence (§7.2) shows the agent reading `working-state.md` after getting the cursor and then either resuming, acking stale events, or entering idle — but it never executes `GET /events/for/{role}?since=cursor` to check for queued events on boot. The agent depends on `event_poll`'s first poll cycle (up to 5-60s latency per §7.0) to discover already-queued work.
- **Evidence**: The nudge contract (§7.1 lines 597-599) mandates `GET /events/for/{role}?since=cursor` as the core work-discovery step, but the boot sequence diagram (lines 680-692) jumps from cursor fetch directly to working-state read without this GET.
- **Suggested fix**: Add `GET /events/for/{role}?since=cursor` after the working-state decision block in the boot sequence, or explicitly state that the agent intentionally defers queue discovery to the first nudge and explain the latency trade-off.

---

### Finding 9

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 942-949 (§8.5 migration table)
- **Severity**: MED
- **Issue**: The 6 migration groups are numbered 1-6 but lettered A, C, D, B, F, E — neither alphabetical nor matching the numerical sequence. The implementation order (numerical) puts Group C at position 2 and Group B at position 4, but the letter prefixes suggest B should be a dependency of C.
- **Evidence**: Line 944-949: Group 1=A, Group 2=C, Group 3=D, Group 4=B, Group 5=F, Group 6=E. An implementer reading Group 4 labeled "B — Cursor + delivery wire" will wonder whether cursor infrastructure (B) must land before EAD restart safety (C, landed earlier at position 2).
- **Suggested fix**: Either re-letter the groups to match numerical implementation order (A, B, C, D, E, F) or add a sentence explaining that the letter prefixes are logical-grouping identifiers and the numerical order is the dependency-driven implementation sequence.

---

### Finding 10

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 771 (§7.3 auto-routing table)
- **Severity**: MED
- **Issue**: The `pending-test → in-progress` routing rule resolves `next_role` to "assigned role from `role:*` label," but no fallback is specified for issues that lack a `role:*` label at the moment of transition.
- **Evidence**: Line 771: `assigned role from role:* label`. The `approved → in-progress` row (line 776) handles this with "(no assign — self-pickup)," but the rejection path has no equivalent fallback.
- **Suggested fix**: Add a fallback rule, e.g., "if no `role:*` label exists, route to the issue's original worker or emit `assigned-to(pm, event_context="unowned-rejection")`."

---

### Finding 11

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 492-503 (§5 state persistence map)
- **Severity**: LOW
- **Issue**: The state persistence map does not list `.squidsquad/<role>/.claude-pid`, which is documented in §3.3 as the singleton handle the harness watches, written by `thin_launcher` at boot, and referenced by the harness health poller.
- **Evidence**: §3.3 (lines 180-182) describes `.claude-pid` semantics; §7.2 boot diagram (line 671) shows `TL->>TL: write .claude-pid`; but §5 omits this file entirely.
- **Suggested fix**: Add a row: `Agent singleton PID | .squidsquad/<role>/.claude-pid | agent (thin_launcher) | Harness watches for singleton enforcement + health polling`.

---

### Finding 12

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 865 (§7.6 improvement subloop flowchart)
- **Severity**: LOW
- **Issue**: The flowchart node is labeled "token-burn throttle OK?" but the throttle mechanism described in the accompanying text is purely time-based (`.subloop-last-run` timestamp, default 30 min cooldown), not token-based.
- **Evidence**: Line 866: `Throttle{token-burn\nthrottle OK?}`; line 878: "at most one subloop per agent per N minutes (default 30) ... `.subloop-last-run` records the timestamp." The "token-burn" label implies a different mechanism than what's specified.
- **Suggested fix**: Change the flowchart node label to "time-based throttle OK?" or "cooldown elapsed?" to match the described mechanism.

---