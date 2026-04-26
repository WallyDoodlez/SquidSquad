---
type: project
tags: [communication, architecture, agents, vault, real-time]
created: 2026-04-26
updated: 2026-04-26
owner: pm
status: active
confidence: high
source: conversation
links: [decision-vault-remember-source-agnostic, human-profile, squidsquad]
---

## Overview

Redesign agent communication from async cycle-based (GitHub Issue comments, 30m waits) to real-time multi-party discussions. This is a foundational infrastructure change that affects every agent role definition.

**Tracker**: #3393

### Goals

- Any agent can initiate a discussion with other agents in real-time
- PM is always included in decisions
- Human can be consulted when needed (not always required)
- Eliminate 30-minute cycle waits for simple questions
- Achieve consensus before writing to vault or filing issues

### Constraints

- Must not break existing async workflow (graceful degradation if chat unavailable)
- Human should not be overwhelmed with notifications
- Must work across clone isolation architecture (agents in separate repos)

---

## Problem Statement

### Current Model (Async, Cycle-Based)

```
Agent A observes something
  → waits for cycle end
    → writes comment on GitHub Issue
      → Agent B reads on NEXT cycle (30m later)
        → responds on THEIR next cycle
          → 60-90 minutes for a single exchange
```

**Pain points**:
- Vault writes are unilateral — one agent decides, one agent writes, no consensus
- Improvement scan findings filed as issues without discussion — creates noise
- Mid-task ambiguities block for 30m+ waiting for PM response
- QA rejections take multiple cycles to resolve (see #3341: 3 rejection cycles)
- No mechanism for agents to challenge each other's reasoning before acting

### Target Model (Real-Time, Multi-Party)

```
Agent A observes something
  → initiates discussion thread (PM auto-included)
    → agents exchange views in seconds/minutes
      → consensus reached (or human consulted)
        → action taken with agreement
```

---

## Use Cases

### 1. Vault Consensus

**Before**: Skill finds a pattern → writes vault note unilaterally → may be noise or duplicate reasoning.

**After**: Skill finds a pattern → opens thread: "Found X, vault-worthy?" → PM: "Aligns with priority Y, write it" or "Too specific, skip" → consensus → write or skip.

### 2. Improvement Scan Findings

**Before**: Skill scans → files issue to PM → PM evaluates next cycle → may reject as noise.

**After**: Skill scans → discusses with PM inline: "Found dead code in X, worth filing?" → PM: "Yes, medium priority" or "Known, skip" → only real findings enter the tracker.

### 3. In-Task Communication

**Before**: Skill hits ambiguity → comments on issue → PM reads next cycle → responds → skill reads next cycle → 60-90 min delay.

**After**: Skill hits ambiguity → asks PM directly → PM responds in seconds → skill continues immediately.

### 4. Cross-Agent Debate

**Before**: No mechanism for agents to disagree before acting. QA rejection is post-hoc.

**After**: Skill proposes approach → QA raises concern early → discussion → better implementation on first pass.

### 5. Human Escalation

**Before**: Human gets pulled in via issue comments, reads on own schedule.

**After**: Agents discuss, identify they need human input → structured question posted → human notified → responds when available → agents unblocked.

---

## Architecture (TBD)

### Transport Layer — Open Question

Options under consideration:

| Option | Pros | Cons |
|--------|------|------|
| **Slack/Discord** | Real-time, human already there, rich UI | External dependency, API rate limits, cost |
| **File-based immediate pickup** | No dependencies, works offline, git-tracked | Polling overhead, no push notification |
| **Custom local channel** | Full control, zero dependencies | Build cost, no mobile access |
| **Shared conversation context** | Native to Claude, zero infra | Limited to same session, no persistence |

**Decision needed**: Which transport? May be multiple (primary + fallback).

### Role Definition Changes

Every agent role gets communication as a core capability:

```
## Communication (new sub-skill for all roles)

- Initiate discussion threads
- Respond to threads you're mentioned in
- Escalate to human when consensus not reached
- PM auto-included in all decision threads
```

### Conversation Protocol (TBD)

- **Who can initiate**: Any agent
- **Who must be included**: PM always; human when agents disagree or confidence is low
- **Thread types**: decision, question, escalation, FYI
- **Timeout**: If no response in N minutes, fall back to async (issue comment)
- **Persistence**: Threads archived for audit trail

### Integration Points

- **Vault remember**: Consensus gate before writes
- **Improvement scan**: Discuss-before-file gate
- **Task implementation**: Real-time Q&A with PM
- **QA verification**: Early feedback before rejection
- **Bug filing**: Cross-agent validation before filing

---

## Prerequisites

1. Chat integration infrastructure (transport decision + implementation)
2. Source-agnostic vault reflection ([[decision-vault-remember-source-agnostic]])
3. Role definition sub-skill for communication
4. Conversation protocol specification

---

## Open Questions

1. **Transport**: Slack, Discord, file-based, or custom? (Human to decide)
2. **Human inclusion**: Pulled into thread directly, or async question + notification?
3. **Tie-breaking**: PM always breaks ties? Or escalate to human on disagreement?
4. **Scope boundary**: Which decisions require consensus vs. unilateral action?
5. **Fallback**: What happens when chat is unavailable? Revert to async?
6. **Chat integration backlog item**: Is this the same initiative or a dependency?

---

## Timeline

Not estimated. This is a large initiative spanning multiple milestones. Prerequisites must land first.

---

## Related

- [[decision-vault-remember-source-agnostic]] — source-agnostic reflection (prerequisite)
- [[human-profile]] — design philosophy section on inter-agent communication
- [[squidsquad]] — core project context

---

### Changelog

- 2026-04-26 — Created by skill-lead. Initialized from human discussion about vault consensus, inter-agent debate, and real-time communication. Tracker: #3393.
