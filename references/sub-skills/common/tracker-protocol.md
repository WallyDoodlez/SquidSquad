---
slot: instructions
ordinal: 11
---

<!-- sub-skill: tracker-protocol -->
## Tracker Protocol — GitHub Issues

All issues and tasks are tracked as GitHub Issues with structured labels. Agents use the `gh` CLI to create, read, update, and comment on Issues. No internal markdown tracker files — GitHub Issues is the single source of truth.

### Timestamps

All timestamps must use the **system local time** — never guess, estimate, or increment manually. Use the cycle script:

```bash
# For step markers (HH:MM:SS):
python references/scripts/cycle.py timestamp-short

# For Discussion comments and logs (YYYY-MM-DD HH:MM):
python references/scripts/cycle.py timestamp

# Print a formatted step marker:
python references/scripts/cycle.py step-marker "Pulling latest..."
```

### Startup Permission Check

At agent boot (before the first cycle), verify `gh` access:

```bash
python references/scripts/tracker.py check-gh
```

If this fails (exit code 1):
1. Print: `[🦑 HH:MM:SS] ERROR: GitHub Issues permission check failed. Run "gh auth refresh" with "repo" scope, or ensure gh CLI is installed and authenticated.`
2. Exit the conversation. SquidSquad requires GitHub Issues access.

If `gh` works but GitHub is **temporarily unreachable** during a cycle (network blip), skip tracker operations for this cycle and retry next cycle. Print: `[🦑 HH:MM:SS] GitHub unreachable — skipping tracker operations. Will retry next cycle.`

### Reading Issues

Use the tracker script for all queries — it encodes correct label formats:

```bash
# List approved tasks for your role
python references/scripts/tracker.py list-tasks [ROLE] --status approved

# List open issues for your role
python references/scripts/tracker.py list-issues [ROLE]

# Get labels or state for a specific issue
python references/scripts/tracker.py get-labels [NUMBER]
python references/scripts/tracker.py get-state [NUMBER]
```

To read a specific issue's full details (body, comments):

```bash
gh issue view [NUMBER] --json title,body,labels,comments
```

### Creating Issues

Use the tracker script to ensure correct label format. The base shapes:

```bash
# File an issue (bugs, improvement findings, gaps — anything tracked as `type:issue`)
python references/scripts/tracker.py create-issue \
  --title "[title]" --body "[description]" \
  --role [target-role] --severity [high|medium|low] --reporter [ROLE]-lead

# File a task (features, refactors, planned work — anything tracked as `type:task`)
python references/scripts/tracker.py create-task \
  --title "[title]" --body "[description]" \
  --role [target-role] --priority [high|medium|low] --reporter [ROLE]-lead
```

The script automatically adds `ISSUE:`/`TASK:` prefix, correct labels, and `squidsquad` tag. Returns JSON with `number` and `url`.

#### Reporter naming lock — `<alias>-lead` (canonical)

The `--reporter` flag value MUST be `<alias>-lead` — bare alias (e.g. `--reporter pm` or `--reporter verifier`) is non-canonical and breaks consistency with the rest of the `tracker.py` interface. The `-lead` suffix is a `tracker.py` flag-naming convention shared with `--role` on `transition` calls; it does NOT change the identity of the agent (which is the bare alias used in Discussion comment prefixes and `role:*` labels).

Examples:
- `--reporter pm-lead` ✓
- `--reporter verifier-lead` ✓ (not `verifier`)
- `--reporter dm-lead` ✓ (not `dm`)
- Worker variants follow the same shape: `--reporter skill-lead`, `--reporter web-lead`, `--reporter ios-lead`, etc.

When a sub-skill uses a square-bracketed placeholder, the canonical form is `--reporter [ROLE]-lead` (uppercase placeholder, dash, lowercase `lead`). Lowercase `[role]-lead` is a stylistic drift; fix on contact.

#### Per-finding-kind one-liners

Pick the shape that fits the finding, fill the bracketed slots, run the command. Body strings follow the conventions other agents and the verifier rely on when reading issue bodies.

**Bug fix** — defect with reproduction steps (body uses the standard 4-field shape):

```bash
python references/scripts/tracker.py create-issue \
  --title "[short defect summary]" \
  --body "**Description**: [what is broken and why it matters]

**Steps to Reproduce**:
1. [step 1]
2. [step 2]

**Expected**: [what should happen]
**Actual**: [what does happen]" \
  --role [owning-role] --severity [high|medium|low] --reporter [ROLE]-lead
```

**Feature task** — planned work (body emphasises scope and acceptance criteria, not reproduction):

```bash
python references/scripts/tracker.py create-task \
  --title "[short feature summary]" \
  --body "**Reported By**: [ROLE]-lead
**Priority**: [High|Medium|Low]

## Background
[why this task exists, what problem it solves]

## Acceptance Criteria
- [AC1]
- [AC2]

## Out of scope
- [explicit non-goals]" \
  --role [owning-role] --priority [high|medium|low] --reporter [ROLE]-lead
```

**Improvement-scan finding** — low-priority maintenance item surfaced by a quiet-cycle scan (body is terse):

```bash
python references/scripts/tracker.py create-issue \
  --title "improvement-scan: [short observation]" \
  --body "**Observation**: [what the scan found]
**Location**: [file:line or symbol]
**Suggested fix**: [one-line approach]" \
  --role [owning-role] --severity low --reporter [ROLE]-lead
```

**Cross-role issue** — root cause is in another agent's domain (`--role` differs from `--reporter`):

```bash
python references/scripts/tracker.py create-issue \
  --title "[short defect summary]" \
  --body "**Description**: [what is broken and why this belongs in [OTHER_ROLE]'s domain]

**Steps to Reproduce**:
1. [step 1]

**Expected**: [expected]
**Actual**: [actual]
**Cross-filed from**: #[original-issue-number-if-any]" \
  --role [other-owning-role] --severity [high|medium|low] --reporter [your-role]-lead
```

After cross-filing, comment on the original issue with the new number so the trail is two-way.

#### Legacy aliases retired

The following `tracker.py` subcommand names are LEGACY and MUST NOT appear in agent-facing instructions. They survive only in `tracker.py --help` for tool backward-compatibility; sub-skill content writes the canonical names:

| Legacy (do not use) | Canonical (use this) |
|---|---|
| `create-bug` | `create-issue` |
| `list-bugs` | `list-issues` |
| `create-feature` | `create-task` |
| `list-features` | `list-tasks` |

The rename happened when the tracker abstraction broadened from defect tracking to general work-item tracking. Encountering a legacy name inside a sub-skill is a drift bug — file it as an `improvement-scan` finding and fix on contact. The legacy name does not change script behavior, but inconsistent agent-facing instructions are how drift compounds.

### Status Transitions

Use the tracker script — it **enforces legal transitions, role authority, and auto-closes on shipped**. `--role` is REQUIRED and must identify the calling agent:

```bash
# Transition syntax: tracker.py transition <number> <from> <to> --role <r> [--force]
python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
python references/scripts/tracker.py transition [NUMBER] pending-ship shipped --role dm-lead
```

Pass your own role-class — PM uses `--role pm-lead`, verifier agents use `--role verifier-lead`, DM uses `--role dm-lead`, worker agents use `--role <role>-lead` where `<role>` is your alias (e.g. `skill-lead`). The script rejects:

- **Illegal transitions** (e.g. `pending → shipped`) — never bypassable.
- **Unauthorized transitions** — e.g. a worker trying to run `pending-ship → shipped` (DM-only) or `pending-test → pending-ship` (PM or verifier only). Use `--force` only as a human override.
- **Unassigned transitions** — worker-style transitions (pickup, pending-test) require your canonical role to match one of the issue's `role:*` labels.

Legal flows and owning roles:
- `open` → `pending-test` | `in-progress` — **assigned role** (matches `role:*` label)
- `pending` → `planning` | `approved` — **PM**
- `planning` → `planned` — **PM**
- `planned` → `approved` — **PM**
- `approved` → `in-progress` — **assigned role**
- `in-progress` → `pending-test` | `pending-ship` | `approved` | `planning` | `pending-human-review` | `pending-human-setup` — **assigned role** (pending-ship: DM only)
- `pending-human-review` → `in-progress` | `pending-ship` — **assigned role** (HITL designer loop)
- `pending-human-setup` → `in-progress` — **PM** (environment setup complete)
- `pending-test` → `in-progress` | `pending-ship` | `pending-human-review` — **PM or verifier** (pending-human-review = verifier routes to human under PR Flow when `review:human-required` is set)
- `pending-ship` → `shipped` | `in-progress` — **DM** ships (auto-closes), **PM or verifier or DM** routes back on merge conflict

### Discussion Entries

Discussion entries become Issue comments. Use the tracker script:

```bash
python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "[message]"
```

Comments are append-only — never edit or delete previous comments.

### Working State References

Reference issues by number in working-state.md: `- **Task**: #42`

### Planning Artifacts

Planning artifacts remain as local files. Under the #9184 workflow:
- PM produces RESEARCH.md and CONTEXT.md under `.squidsquad/[PM_ALIAS]/planning/`. PM does NOT produce TEST-PLAN.md.
- The verifier produces `TEST-PLAN-<NUMBER>.md`, `TEST-<NUMBER>-tests.py`, and `QA-RESULTS-<NUMBER>.md` under `.squidsquad/[VERIFIER_ALIAS]/planning/` when picking up verification.

Only the tracker (issues/tasks) moves to GitHub Issues. Reference the Issue number in artifact filenames or content for traceability.

### Caching

Within a single cycle, cache `gh issue list` results to avoid repeated API calls. Read the list once at the start of the relevant step, then operate on the cached data.
<!-- /sub-skill: tracker-protocol -->
