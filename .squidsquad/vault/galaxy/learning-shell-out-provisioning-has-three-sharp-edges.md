---
name: learning-shell-out-provisioning-has-three-sharp-edges
description: code that shells out to install/provision dependencies (package managers, pip, npm) has three edges DS reliably catches — wrap subprocess in OSError-catch not just TimeoutExpired; non-interactive needs per-tool treatment (apt/dnf/choco -y, winget --silent, brew HOMEBREW_NO_AUTO_UPDATE env var); a bare `python` may be py2 so version-probe it
metadata:
  type: learning
type: learning
tags: [learning, installer, provisioning, subprocess, cross-platform, wizard, 11613, deepseek]
created: 2026-06-15
updated: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-default-port-fallback-is-live-egress-trap-in-tests]
---

# Shelling out to provision dependencies has three sharp edges

**Observed (#11613, INSTALLER-ARCH §4.1 gather-all dep provisioning):** the DeepSeek review of `wizard.py` `gather_deps`/`provision_deps` caught three distinct, recurring edges in code that shells out to install system tools / Python packages / npm globals. None were caught by forward-only tests — they only surface under adversarial review.

**The three edges:**

1. **`subprocess` wrappers that only catch `TimeoutExpired` leak `OSError`.** A provisioning loop calls the binary a gather pass just detected, but a TOCTOU race (the binary vanishes / loses +x between detect and provision) raises `FileNotFoundError` / `PermissionError` — both `OSError` subclasses, **not** `TimeoutExpired`. The uncaught exception crashes mid-loop and the caller gets a stack trace instead of the documented result dict. Fix: catch `OSError` too and return a synthetic `CompletedProcess(returncode=127, stderr=str(exc))`, mirroring the timeout branch — every `.returncode`-inspecting caller keeps working.

2. **"Non-interactive" is per-tool, and brew is the odd one out.** apt/dnf/choco take `-y`, winget takes `--silent` — flags on the command. **Homebrew has no install flag for this**; its slow auto-update is suppressed by the `HOMEBREW_NO_AUTO_UPDATE=1` **environment variable**, not an argument. Forgetting it doesn't hang (so a timeout won't catch it) but adds minutes of latency behind a slow network. Pass it in the subprocess `env` for every provision call (harmless to non-brew commands).

3. **A bare `python` on PATH may be Python 2.** `shutil.which("python3") or shutil.which("python")` reports python3 "satisfied" on a box where `python` is legacy py2 and `python3` is absent — the boot scripts/helpers then fail at runtime. `python3` is unambiguous; a bare `python` must be **version-probed** (`python -c "import sys; sys.exit(0 if sys.version_info>=(3,) else 1)"`), short-circuited via `sys.version_info` only when it `realpath`-matches our own `sys.executable`.

**How to apply:** any future code that provisions via subprocess (installer, start scripts, capability bootstrap) gets all three by default. They're the standard DS findings for this shape — front-load them rather than waiting for the review. Detection + dispatch stay deterministic in the script; the consent gate stays in the agent runbook (the deterministic/probabilistic seam). See [[learning-default-port-fallback-is-live-egress-trap-in-tests]] for the sibling "real-code-path egress must be guarded" instinct.
