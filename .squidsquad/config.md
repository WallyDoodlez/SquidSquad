# SquidSquad Config

- **SquidSquad Version**: 0.16.0
- **Tracker**: github-issues
- **Architecture Version**: 1

## Agents

- **Dev Agents**: designer, qa, skill
- **PM/QA**: always present
- **DM**: present

## Aliases

- **skill**: skill
- **pm**: pm
- **dm**: dm
- **qa**: qa
- **designer**: designer

## Project

- **Name**: SquidSquad
- **Repo**: github.com/WallyDoodlez/SquidSquad

## Test Commands

- **skill Tests**: python tests/run_tests.py
- **E2E Tests**: (none)

## Git Protocol

- Always `git pull --rebase` before starting work.
- Discussion comments on GitHub Issues are append-only.
- Push after every completed work unit.

## Iteration Interval

- **Minutes**: 30

## Context Pressure

- **Threshold**: 70

## Auto Boot Agents

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

## Diagnostics

- **Enabled**: yes
- **Upstream Reporting**: ask

## Auto Versioning

- **Ship Threshold**: 10
- **Shipped Since Last Bump**: 14
