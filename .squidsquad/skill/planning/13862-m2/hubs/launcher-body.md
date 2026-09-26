
# Launcher & Clones

_Hub note (VAULT-ARCH 3.2): connective anchor for this subsystem. Keep it a
map, not an essay -- galaxy leaves carry the knowledge; this note carries
the links._

## What It Is

start.ps1/start.sh + thin_launcher.py: spawn each agent in its sibling clone (resolved via .local-config), sync clones at boot, write .claude-pid, respawn on death.

## Key Files

`.squidsquad/start.ps1`, `references/scripts/thin_launcher.py`, `.squidsquad/.local-config`, `docs/ARCHITECTURE.md`

## Knowledge Map

- Clone isolation: [[decision-clone-isolation-architecture]], [[decision-local-config-priority]]
- Boot recovery: [[learning-deploy-pull-block-divergence-recover-by-merge]], [[learning-deploy-error-pull-block-recover-by-discarding-composed-artifacts]]

## Distilled leaves (vault v2)

- [[cli-anything-research]]
- [[decision-watchdog-supervisor]]
- [[learning-cq-applies-to-launcher-injected-prompts]]
- [[learning-spawn-prompt-must-not-decide-wake-mode]]
- [[learning-windows-cmd-start-title-must-be-quoted]]

## Changelog

- **2026-09-26** — migrated to vault v2 (#13862).
