---
type: learning
tags: [powershell, windows, start-job, boot-wrapper]
created: 2026-04-18
updated: 2026-04-18
owner: skill
status: active
confidence: high
source: code
links: []
---

## Context

Boot wrapper watcher job (#1345) could not detect .restart sentinel because Start-Job runs in a separate process.

## Content

PowerShell `Start-Job` runs its ScriptBlock in a **new process** whose working directory defaults to `$HOME` (e.g. `C:\Users\naaht`), NOT the caller's working directory. Any relative paths passed via `-ArgumentList` will resolve against `$HOME`, silently failing `Test-Path` checks.

**Fix**: Always resolve paths to absolute before passing to `Start-Job`. Use `Join-Path $repoRoot` or `Resolve-Path` at definition time.

**Contrast**: Bash subshells `( ... ) &` inherit the parent's cwd — this is a PowerShell-specific gotcha.

## Rationale

This caused the .restart sentinel to never be detected, breaking self-restart and context pressure restart. Silent failure — no error, just Test-Path returning $false forever.

## Related

---

### Changelog

- 2026-04-18 — Created by skill. Found via #1345 fix.
