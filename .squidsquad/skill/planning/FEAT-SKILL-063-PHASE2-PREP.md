# FEAT-SKILL-063 Phase 2 Prep -- Open Question Analysis

Source: `FEAT-SKILL-063-RESEARCH.md`, Section 10

---

## Optimal Question Order

Questions should be resolved in this order (dependency rationale follows each):

1. **Q5** (Project detection) -- foundational; scan strategies in Q4 and filing behavior in Q1 depend on knowing how the agent understands the project
2. **Q1** (Default priority of scan items) -- affects filing protocol, which Q2 and Q3 build on
3. **Q3** (Global scan budget) -- must be settled before Q2, since a periodic report would need to know the volume it is summarizing
4. **Q4** (Status bar visibility) -- low dependency, but resolving it before Q2 avoids rework if the report includes scan stats
5. **Q2** (Periodic improvement report) -- most subjective / controversial; benefits from all other decisions being locked first

---

## Q5 -- How does the agent know what kind of project it is?

**Category:** Infrastructure / Context Discovery

Research recommendation: Read `config.md` project metadata + infer from file extensions and structure.

### Option A -- Explicit `config.md` project metadata field (RECOMMENDED)

Add fields like `Project > Language`, `Project > Framework`, `Project > Type` to config.md. The agent reads these before scanning.

| Pros | Cons |
|------|------|
| Deterministic -- no guessing | Requires human to fill in during setup |
| Cheap at runtime -- no file-tree scanning needed | Can go stale if project evolves (e.g., adds a new language) |
| Enables role-specific scan checklists to be precise | One more config section to maintain |

### Option B -- Auto-detect from file extensions and structure at scan time

Agent reads directory listing, counts file extensions, checks for marker files (`package.json`, `Cargo.toml`, `go.mod`, etc.), and infers project type.

| Pros | Cons |
|------|------|
| Zero human configuration | Consumes tokens on every scan cycle for detection |
| Always current -- adapts as project evolves | Can misidentify polyglot or unusual projects |
| Works for any repo without setup | Non-deterministic; may flip between scans if heuristic is fragile |

### Option C -- Hybrid: auto-detect with config override

Auto-detect on first scan, write results to a `Project > Detected` field in config. Human can override. Re-detect periodically (e.g., every 20 scans).

| Pros | Cons |
|------|------|
| Best of both worlds -- works out of the box, human can correct | Most complex to implement |
| Self-documenting -- detected values are visible in config | Re-detection adds a maintenance dimension |
| Handles polyglot projects if human overrides | Edge case: re-detection overwrites human override unless guarded |

**Recommended: Option C.** It removes setup friction while allowing human correction. Implementation cost is modest -- detection is a one-time file-tree read that writes to config.

---

## Q1 -- Should improvement-scan items have a lower default priority?

**Category:** Filing Protocol / Triage Policy

Research recommendation: Yes, default to `Low` priority.

### Option A -- Default to `Low` priority (RECOMMENDED)

All improvement-scan items are filed as `Low` priority unless the agent judges them High-severity (e.g., security issue, data loss risk).

| Pros | Cons |
|------|------|
| Human-filed work always takes precedence naturally | Genuinely important findings (security gaps) may be deprioritized |
| Prevents scan noise from crowding out real work | Agents must make a judgment call on when to escalate to Medium/High |
| Matches user expectation: proactive suggestions are lower urgency | Low-priority items may accumulate and never get addressed |

### Option B -- Same priority rules as human-filed items

Agent assigns priority using the same criteria it would for any bug/feature (severity-based, not source-based).

| Pros | Cons |
|------|------|
| Critical findings (security, data integrity) get appropriate priority | A flood of Medium-priority scan items could compete with human work |
| Simpler rule -- no special-casing by source | Undermines the "human work first" principle |
| Agent does not need to second-guess its own findings | Human may feel overwhelmed by agent-generated backlog |

### Option C -- New priority tier: `Suggestion`

Add a priority level below `Low` specifically for scan items: `Suggestion`. Only promoted to `Low`+ when human approves.

| Pros | Cons |
|------|------|
| Cleanest separation between human and scan work | Requires schema changes to priority enum across all templates |
| Human can filter/ignore suggestions entirely | Adds complexity to priority ordering logic |
| No risk of scan items competing with real work | A new concept for users to learn |

**Recommended: Option A.** Lowest implementation cost, achieves the goal. The escape hatch (agent can escalate genuine security/data issues to Medium/High) handles the edge case without a schema change.

---

## Q3 -- Should there be a global scan budget?

**Category:** Rate Limiting / Multi-Agent Coordination

Research recommendation: No, per-agent rate limiting is sufficient.

### Option A -- No global budget; per-agent limits only (RECOMMENDED)

Each agent independently enforces its own `Max Items Per Scan` and `Quiet Cycles Before Scan`. No cross-agent coordination.

| Pros | Cons |
|------|------|
| Simplest to implement -- no shared state | In theory, 5 agents x 2 items/scan could produce 10 items in one interval |
| Consistent with existing SquidSquad concurrency model | No central throttle if all agents go quiet simultaneously |
| Each agent's rate limit is already conservative | Human could be surprised by a burst of filings |

### Option B -- Global daily cap in config.md

Add `Improvement Scan > Global Daily Cap: 10`. Each agent reads a shared counter in config.md and stops filing when the cap is reached.

| Pros | Cons |
|------|------|
| Hard ceiling on total scan output per day | Shared counter creates concurrency risk (two agents read/increment simultaneously) |
| Human has one knob for total volume | First agents to scan "use up" the budget; later agents get nothing |
| Predictable maximum daily noise | Adds config complexity and cross-agent coupling |

### Option C -- PM-mediated throttle

PM agent monitors total improvement-scan filings across all trackers. If volume exceeds a threshold, PM sets a `scan-throttle: true` flag that other agents check before scanning.

| Pros | Cons |
|------|------|
| PM already has cross-tracker visibility | Requires PM to run frequently enough to react |
| Decoupled -- agents just check a flag | Adds a dependency on PM being active |
| PM can apply judgment (not just count) | More complex; PM needs new logic |

**Recommended: Option A.** The research already showed that per-agent limits plus the human approval gate make runaway filing unlikely. In practice, quiet cycles rarely align across all agents simultaneously. If it becomes a problem, Option B can be added later without breaking anything.

---

## Q4 -- Should scan findings be visible in the status bar?

**Category:** UX / Observability

Research recommendation: Yes, as a status bar phase `scanning|...`.

### Option A -- New `scanning` phase in status bar (RECOMMENDED)

Add `scanning` to the valid phase list. When an agent is running an improvement scan, its status bar shows e.g. `scanning|Scanned 3 files, filed 1 item`.

| Pros | Cons |
|------|------|
| Human knows the agent is doing useful work, not just idle | Requires updating statusline script to recognize new phase |
| Transparent -- no hidden activity | Minor: adds one more phase to the phase enum |
| Consistent with existing status bar conventions | Scan details may be too long for the 60-char limit |

### Option B -- Fold into existing `idle` phase with annotation

Keep the `idle` phase but append scan info: `idle|Scanned 3 files, filed 1 item`.

| Pros | Cons |
|------|------|
| No new phase needed -- zero statusline changes | Misleading: agent is not idle during a scan |
| Simple | Loses the semantic distinction between "truly idle" and "scanning" |
| Compatible with existing tooling | Human cannot tell at a glance if the agent is active |

### Option C -- No status bar change; log scan results in iteration log only

Scan activity is recorded in `iter-N.md` but not shown in the status bar.

| Pros | Cons |
|------|------|
| Zero implementation cost for status bar | Human has no real-time visibility into scan activity |
| Keeps status bar simple | Scans appear to be "silent" idle cycles |
| Avoids status bar clutter | Inconsistent: other work types show in status bar, scans do not |

**Recommended: Option A.** The status bar exists to give the human real-time visibility. A scan is meaningful work that should be visible. Adding one phase is trivial.

---

## Q2 -- Should the PM aggregate scan findings into a periodic improvement report?

**Category:** Workflow / Reporting

Research recommendation: No, use normal tracker flow.

### Option A -- No periodic report; use normal tracker flow (RECOMMENDED)

Improvement-scan items appear in the tracker like any other item. PM surfaces them during normal intake. No special aggregation.

| Pros | Cons |
|------|------|
| Zero new infrastructure | Human must scan tracker to see improvement-scan items among others |
| Consistent with existing workflow | No high-level summary of "what the agents found" across roles |
| No additional PM complexity | Harder to evaluate the feature's overall value at a glance |

### Option B -- Weekly digest in PM iteration log

PM collects all improvement-scan items filed in the past week and includes a summary section in its iteration log.

| Pros | Cons |
|------|------|
| Human gets a periodic "here is what the agents found" overview | PM needs new logic to aggregate cross-tracker scan items |
| Helps evaluate whether the scan feature is producing value | Weekly cadence may not match project rhythm |
| Low-touch -- just a section in an existing log | If few items are filed, the digest is noise |

### Option C -- Dedicated improvement report file

PM writes `.squidsquad/pm/improvement-report.md` summarizing all scan findings, updated after each PM cycle.

| Pros | Cons |
|------|------|
| Single place to see all scan activity | Yet another file to maintain |
| Can include metrics (items filed, approved, rejected) | PM must read all agent scan histories -- expensive |
| Useful for evaluating ROI of the scan feature | Overhead may not justify value for small teams |

**Recommended: Option A.** The research correctly identified that improvement-scan items should flow through the normal pipeline. A periodic report is a nice-to-have that can be added in Phase 3 if the human requests it, but building it upfront adds complexity for uncertain value.

---

## Summary Table

| Order | Question | Category | Recommended Option |
|-------|----------|----------|--------------------|
| 1 | Q5: Project type detection | Infrastructure | C: Hybrid auto-detect + config override |
| 2 | Q1: Default priority | Filing Protocol | A: Default to Low, escalate when warranted |
| 3 | Q3: Global scan budget | Rate Limiting | A: No global budget; per-agent limits suffice |
| 4 | Q4: Status bar visibility | UX | A: New `scanning` phase |
| 5 | Q2: Periodic report | Workflow | A: No report; normal tracker flow |
