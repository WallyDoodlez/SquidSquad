# SquidSquad Config

- **SquidSquad Version**: 0.39.0
- **Tracker**: github-issues
- **Architecture Version**: 1

## Agents

- **Dev Agents**: qa, skill
- **PM**: always present
- **QA**: always present
- **DM**: present

## Aliases

- **skill**: skill
- **pm**: pm
- **dm**: dm
- **qa**: qa


## Project

- **Name**: SquidSquad
- **Repo**: github.com/WallyDoodlez/SquidSquad
- **Intent Description**: (not set)

## Test Commands

- **skill Tests**: python tests/run_tests.py
- **E2E Tests**: (none)

## Git Protocol

- Always `git pull` before starting work.
- Discussion comments on GitHub Issues are append-only.
- Push after every completed work unit.

## Git Branches

- **Working Branch**: main
- **State Branch**: squid-squad
- **Branch Pattern**: squidsquad/task/{number}

## Iteration Interval

- **Minutes**: 30

## Context Pressure

- **Threshold**: 70

## Auto Merge

- **Enabled**: yes

## Branch Workflow

- **Enabled**: yes

## PR Flow

- **Enabled**: yes

## Improvement Scanning

- **Enabled**: yes

## Vault Optimize

- **Enabled**: yes
- **Threshold**: 20

## Vault Remember

- **Enabled**: yes
- **Writes Per Cycle**: 2
- **BRIEFING Token Budget**: 2000
- **Confidence Decay Days**: 60

## Cycle Runner

- **Enabled**: yes

## Agent Compose

- **Enabled**: no

## Diagnostics

- **Enabled**: yes
- **Upstream Reporting**: ask

## Model Routing

- **Default Model**: claude
- **Research Model**: deepseek-v4-pro
- **Discussion Prep Model**: claude
- **Test Plan Model**: claude
- **QA Execution Model**: claude
- **Comprehension Model**: claude
- **Improvement Scan Model**: claude
- **Code Review Model**: deepseek-v4-pro
- **Fallback Model**: claude
- **API Timeout Seconds**: 120

## Forge Backend

- **Provider**: github
- **Endpoint**: https://api.github.com

## Mandatory Human Approval

- **Enabled**: yes

## Auto Versioning

- **Ship Threshold**: 10
- **Shipped Since Last Bump**: 1

## Agent Effort

- **effort-pm**: high
- **effort-skill**: high
- **effort-dm**: high
- **effort-qa**: high

## Harness

- **Enabled**: yes
- **Port**: 7373

## Event Reactions

### dm
- **emits**: request-merge, status-transition, tracker-comment
- **reacts-to**: pr-merged, status-transition

### pm
- **emits**: status-transition, tracker-comment
- **reacts-to**: agent-health, pr-create, pr-merged, status-transition, tracker-comment, verification-failed, verification-passed

### qa
- **emits**: request-merge, status-transition, tracker-comment, verification-failed, verification-passed
- **reacts-to**: agent-health, git-commit, pr-create, pr-merged, status-transition

### skill
- **emits**: pr-create, status-transition, tracker-comment
- **reacts-to**: pr-merged, status-transition, tracker-comment, verification-failed, verification-passed
