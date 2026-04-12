# Working State

- **Task**: #335 + create-bug status fix
- **Status**: in-progress
- **Started**: 2026-04-11 23:09
- **Quiet Cycle Counter**: 0

## What to do (pick up immediately on fresh context)

Two items, do them in order:

### 1. Fix create-bug default status (quick, 5 min)

**Bug**: `tracker.py create-bug` creates bugs with `status:pending` instead
of `status:open`. This causes bugs to sit in limbo because dev agents
interpret `pending` as "awaiting human approval" — but that's a feature
lifecycle gate, not a bug lifecycle gate. The dev-agent Step 2 says
"For each bug that does not have a `status:shipped` or closed state"
which means bugs should be immediately actionable.

**Fix**: in `references/scripts/tracker.py`, change line:
```
labels = f"type:bug,{sev_label},{role_label},squidsquad,status:pending"
```
to:
```
labels = f"type:bug,{sev_label},{role_label},squidsquad,status:open"
```

Also update the LEGAL_TRANSITIONS comment / documentation that says
bugs start at `open`. Add a test. Self-file this as a bug if the human
wants a tracker entry — or just fix and commit since human approved it
live in conversation.

### 2. Pick up #335 (the actual bug to fix)

**#335**: "PM agent health check uses prose instructions, leads to
stale-reporting drift"

- PM's Step 7 health check is prose-based and reports stale incorrectly
- Fix: create `references/scripts/health_check.py` that reads
  `.local-config` + cross-clone `current-state` files, outputs JSON
- This unblocks #4 (Boot Remote Agents) which has a hard dependency
  on #335 per its CONTEXT.md §Q4

Read the full bug body: `gh issue view 335 --json title,body,comments`
Read the #4 CONTEXT for what health_check.py needs to output:
`.squidsquad/skill/planning/FEAT-4-CONTEXT.md` lines 10-23

## Key Decisions

- Human confirmed: fix create-bug status from pending→open
- Human confirmed: pick up #335 immediately (was wrongly skipped for 20 cycles)
- #335 → #4 dependency chain: health_check.py must ship before boot_remote.py

## References

- tracker.py create-bug: `references/scripts/tracker.py` line ~181
- #335 bug body: `gh issue view 335`
- #4 CONTEXT (depends on #335): `.squidsquad/skill/planning/FEAT-4-CONTEXT.md`
