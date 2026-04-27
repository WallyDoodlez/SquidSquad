# Iteration 398

- **Date**: 2026-04-27 10:04
- **Type**: active
- **Work Summary**:
  - Fixed #3495 — reboot_agent.py now kills claude subprocess (.claude-pid) instead of wrapper (.pid). Wrapper stays alive and handles respawn via .restart sentinel. Updated both shell templates (sh + ps1) to write .claude-pid. PR #3560 opened. 21 reboot tests + 97 boot script tests + 1102 full suite all green. Vault: created decision-reboot-kills-child.
- **Notes**: none
