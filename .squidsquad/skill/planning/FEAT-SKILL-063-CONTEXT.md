# FEAT-SKILL-063 Context — Self-Improvement Loop

## Scope

During quiet cycles, agents scan the TARGET PROJECT for improvements in their domain expertise. This is a capability SquidSquad provides to any repo it manages — turning idle time into proactive project improvement. Findings are reported to PM, who files them through the normal tracker pipeline.

**In scope:**
- Quiet cycle detection (3 consecutive quiet cycles trigger)
- Per-role scan strategies (dev=code, QA=tests, designer=design, DM=docs, PM=process)
- Incremental scanning (3-5 files per cycle, different each time)
- Scan history per agent (prevent duplicate filings)
- All findings reported to PM (PM files as Low priority items)
- New 'scanning' status bar phase
- Config toggle for opt-out
- Built as common sub-skill under FEAT-SKILL-030 architecture
- SOUL.md self-improvement lens defines scan focus per role

## Locked Decisions (human decided)

- **Hybrid auto-detect for project type**: Agent reads config.md project info + scans file extensions, package.json, etc. at scan time to understand the stack. No new config field needed.
- **Default Low priority**: All scan-initiated items filed as Low priority. Human can bump if valuable. Prevents noise competing with real work.
- **No global budget**: Per-agent rate limit (2 items per scan) is sufficient. Global coordination adds unnecessary complexity.
- **New 'scanning' status bar phase**: Shows `scanning|🔍 Scanning src/components...` during improvement scans so human knows the agent is productive, not just idle.
- **All improvements reported to PM**: Agents don't file directly to trackers. They report findings to PM via Discussion entries. PM reviews and files as features or bugs through normal pipeline. PM is the single coordination point.
- **3 consecutive quiet cycles trigger**: Not every quiet cycle triggers scanning. Agent must be idle for 3 cycles before starting improvement scans.
- **Incremental scanning**: 3-5 files per scan cycle, prioritized by recency of changes, then coverage gaps, then staleness. Different files each cycle.
- **Scan history per agent**: Tracks what was already scanned and filed to prevent duplicate suggestions. Rejected items tracked so they're not refiled.
- **Config toggle**: `Improvement Scanning: yes/no` in config.md. Default yes. Human can disable.
- **SOUL.md defines scan lens**: The self-improvement lens dimension in each role's SOUL.md defines what the agent looks for. Without it, agents default to narrow/literal interpretations.

## Dev Discretion (dev agent can choose)

- Exact scan checklist per role (what specific things to look for)
- How to format findings reported to PM (Discussion entry format)
- Scan history file format and location
- How to prioritize files for scanning (exact algorithm)
- How hybrid auto-detect determines project type

## Side Effect Mitigations (required)

- Scan items must be clearly tagged as `Reported By: [role]-lead (improvement-scan)` so human can filter
- Per-agent rate limit enforced — max 2 items per scan
- Rejected/dismissed items tracked in scan history — never refiled
- Scanning must not extend cycle time beyond reasonable bounds
- PM must not auto-approve scan items — human decides

## Upgrade Path (required)

- New `Improvement Scanning: yes` in config.md
- New common sub-skill `references/sub-skills/common/improvement-scan.md`
- Scan history files per agent (`.squidsquad/[role]/scan-history.md`)
- Templates regenerated with improvement-scan sub-skill
- Non-destructive — existing installs gain the feature, can opt out via config

## Out of Scope

- Agents filing directly to their own trackers (must go through PM)
- Global scan budget across agents
- Automated implementation of improvements (findings only, human approves)
- Improving SquidSquad itself (targets the project SquidSquad is applied to)
