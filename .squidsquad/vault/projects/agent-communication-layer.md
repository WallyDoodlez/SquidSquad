---
type: project
tags: [communication, architecture, agents, vault, real-time]
created: 2026-04-26
updated: 2026-04-27
owner: pm
status: active
confidence: high
source: conversation
links: [decision-vault-remember-source-agnostic, human-profile, squidsquad]
---

## Overview

Redesign agent communication from async cycle-based (GitHub Issue comments, 30m waits) to real-time multi-party discussions. This is a foundational infrastructure change that affects every agent role definition.

**Tracker**: #3415 (epic index — supersedes #3393 which is closed)

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

## Architecture (DECIDED — 2026-04-26/27)

### Transport Layer — DECIDED: Telegram-first, platform-abstracted

Locked decisions from human discussion (cycles 638-641):
- **Telegram-first**, one bot per agent (PM-bot, QA-bot, Skill-bot, DM-bot)
- **Per-project Telegram group**
- **Platform abstraction**: deterministic sub-skills (rules) over mechanical adapters (API translation) — same pattern as tracker.py
- **Feature flag** in config.md — disabled by default, zero behavior change until enabled
- **Secrets via env vars** — never in git, never exposed to LLM
- **No file uploads** — documents live on the forge (Issues/PRs), chat is discussion only
- **Hard stop on comms failure** — halt + notify human, no silent degradation

### Shipped Components

- **#3416** (SHIPPED): CommsAdapter ABC, Message dataclass, NullAdapter, config parser, adapter registry
- **#3417** (SHIPPED): 3 deterministic sub-skills — chat-etiquette, mention-protocol, consensus-protocol

### Remaining Sub-Tasks

- **#3418**: Telegram adapter (one bot per agent, per-project group)
- **#3419**: Human expertise mapping (vault extension)
- **#3420**: Audit bridge (chat → forge sync)
- **#3421**: Feature flag + Ralph Loop integration

### Conversation Protocol (DECIDED)

- **Who can initiate**: Any agent
- **Who must be included**: PM always; human when agents disagree or confidence is low
- **Thread types**: decision, question, escalation, FYI (via abstract ThreadRef)
- **Timeout**: If no consensus in N minutes, escalate to human
- **Persistence**: Locked decisions sync to forge via audit bridge (#3420)
- **Mention protocol**: 3-tier escalation (inform → need-input → blocking), noise budget per agent

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

## Resolved Questions

1. **Transport**: Telegram-first, platform-abstracted (DECIDED)
2. **Human inclusion**: @mention via mention-protocol, 3-tier escalation (DECIDED)
3. **Tie-breaking**: PM summarizes, human locks. Timeout escalates to human (DECIDED)
4. **Scope boundary**: Consensus required before vault writes and issue filing (DECIDED)
5. **Fallback**: Hard stop + notify human when comms enabled but failing. No silent degradation (DECIDED)
6. **Backlog**: #3393 superseded by epic #3415 (RESOLVED)

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
- 2026-04-27 — Updated by pm-lead. Architecture decisions locked. #3393 superseded by epic #3415. #3416 and #3417 shipped. Open questions resolved. TBD sections replaced with decided architecture.
