# SquidSquad Config

- **SquidSquad Version**: 0.25.0
- **Tracker**: github-issues
- **Architecture Version**: 1

## Agents

- **Dev Agents**: boot, qa, skill
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

- Always `git pull --rebase` before starting work.
- Discussion comments on GitHub Issues are append-only.
- Push after every completed work unit.

## Git Branches

- **Working Branch**: main
- **State Branch**: squid-squad

## Iteration Interval

- **Minutes**: 30

## Context Pressure

- **Threshold**: 70

## Auto Merge

- **Enabled**: yes

## Branch Workflow

- **Enabled**: yes

## PR Flow

- **Enabled**: no

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

## Diagnostics

- **Enabled**: yes
- **Upstream Reporting**: ask

## Model Routing

- **Default Model**: claude
- **Research Model**: gpt-5.2
- **Discussion Prep Model**: claude
- **Test Plan Model**: claude
- **QA Execution Model**: claude
- **Comprehension Model**: claude
- **Improvement Scan Model**: claude
- **Fallback Model**: claude
- **API Timeout Seconds**: 120

## Forge Backend

- **Provider**: github
- **Endpoint**: https://api.github.com

## Mandatory Human Approval

- **Enabled**: yes

## Auto Versioning

- **Ship Threshold**: 10
- **Shipped Since Last Bump**: 2
