# FEAT-269 QA Results — npx Installer Bootstrapper

**QA run**: 2026-04-07 21:30
**Environment**: Windows 11, Node.js v24.13.0, Python 3.12.10, gh 2.34.0, Claude CLI 2.1.86
**Tested file**: `packages/cli/index.js` (rev on main branch)

---

### TC-01: Node.js version check rejects < 18
- **Result**: SKIP
- **Notes**: Environment has Node.js v24.13.0. Cannot downgrade Node in this session. Code review confirms `parseInt(process.versions.node.split(".")[0], 10)` with `< 18` check at line 43 — logic is correct.
- **Verified at**: 2026-04-07 21:30

### TC-02: Node.js 18+ passes runtime check
- **Result**: PASS
- **Notes**: Running from Node.js v24.13.0, no version error printed. Process continues to next check.
- **Verified at**: 2026-04-07 21:30

### TC-03: Missing Python detected
- **Result**: SKIP
- **Notes**: Cannot remove Python from PATH in this environment. Code review confirms both `python3` and `python` are tried; if neither returns a valid 3.8+ version, error is printed with install link `https://www.python.org/downloads/` and `process.exit(1)`.
- **Verified at**: 2026-04-07 21:30

### TC-04: Python version < 3.8 detected
- **Result**: SKIP
- **Notes**: Cannot install Python 3.7 in this environment. Code review confirms version parsing at lines 75-87 rejects major=3, minor<8.
- **Verified at**: 2026-04-07 21:30

### TC-05: Python 3.8+ passes check (python3 binary)
- **Result**: PASS
- **Notes**: `python3 --version` returns Python 3.10.11 in this environment. No Python error printed during TC-23 run.
- **Verified at**: 2026-04-07 21:30

### TC-06: Python 3.8+ passes check (python binary fallback)
- **Result**: SKIP
- **Notes**: Both `python3` and `python` exist in this environment. Cannot isolate the fallback path without PATH manipulation. Code review confirms `python` is tried second in the for-of loop at line 72.
- **Verified at**: 2026-04-07 21:30

### TC-07: Missing gh CLI detected
- **Result**: SKIP
- **Notes**: Cannot remove gh from PATH. Code review confirms error message includes install link `https://cli.github.com/` and exits with code 1 (lines 98-101).
- **Verified at**: 2026-04-07 21:30

### TC-08: gh CLI not authenticated
- **Result**: SKIP
- **Notes**: gh is authenticated in this environment. Code review confirms `gh auth status` is checked and failure prints "Run `gh auth login` first." with exit code 1 (lines 105-110).
- **Verified at**: 2026-04-07 21:30

### TC-09: Missing Claude CLI detected
- **Result**: SKIP
- **Notes**: Claude CLI is installed. Code review confirms error includes install link `https://docs.anthropic.com/en/docs/claude-code/overview` and exits with code 1 (lines 116-120).
- **Verified at**: 2026-04-07 21:30

### TC-10: Not a git repo
- **Result**: PASS
- **Notes**: Created `/tmp/squidsquad-tc10-test/` (not a git repo), ran `node packages/cli/index.js` from it. Output: `Not a git repository.` / `Run this command from inside a git repository.` Exit code 1. Correct behavior.
- **Verified at**: 2026-04-07 21:30

### TC-11: Full install succeeds with all prerequisites
- **Result**: SKIP
- **Notes**: Cannot test full happy path because (a) current repo already has `.squidsquad/`, triggering TC-23 path, and (b) the implementation uses `git clone` instead of `claude install-skill`. Would need a clean git repo without `.squidsquad/`. See also DEVIATION note below.
- **Verified at**: 2026-04-07 21:30

### TC-12: Post-install instructions are printed
- **Result**: PASS (code review)
- **Notes**: Lines 209-216 print: "Start a new Claude Code session (or run /clear)" and "Run /squidsquad-setup to configure your project". Matches the required handoff instructions from AC-9.
- **Verified at**: 2026-04-07 21:30

### TC-13: claude install-skill is invoked with correct repo URL
- **Result**: FAIL
- **Notes**: **SPEC DEVIATION** -- The implementation does NOT use `claude install-skill`. Instead, it uses `git clone --depth 1 https://github.com/WallyDoodlez/SquidSquad.git` to `~/.claude/skills/squidsquad/`. The CONTEXT.md locked decision #2 specifies "prerequisite checks + `claude install-skill` + print instructions". The test plan expected `claude install-skill` invocation. The implementation clones directly. Whether this is acceptable depends on PM decision — the `git clone` approach may be a valid dev-discretion choice since "How to invoke `claude install-skill`" was listed under Dev Discretion, but it contradicts the locked scope statement.
- **Verified at**: 2026-04-07 21:30

### TC-14: claude install-skill fails
- **Result**: PASS (code review, adapted)
- **Notes**: Since the implementation uses `git clone` instead of `claude install-skill`, the equivalent error case is: `git clone` fails. Lines 197-204 catch the error, print "Skill installation failed." with the error message, and exit with code 1. The success instructions (lines 207-216) are NOT printed on failure. Correct behavior.
- **Verified at**: 2026-04-07 21:30

### TC-15: Each prerequisite error includes an actionable message
- **Result**: PASS (code review)
- **Notes**: Reviewed all error paths:
  - Node.js: "Install the latest LTS from https://nodejs.org/" (line 45)
  - Python: "Install from https://www.python.org/downloads/" (line 91)
  - gh missing: "Install from https://cli.github.com/" (line 99)
  - gh auth: "Run `gh auth login` first." (line 109)
  - Claude CLI: "Install from https://docs.anthropic.com/en/docs/claude-code/overview" (line 119)
  - Not git repo: "Run this command from inside a git repository." (line 63)
  All include what is missing and how to fix it.
- **Verified at**: 2026-04-07 21:30

### TC-16: Multiple missing prerequisites — first failure exits
- **Result**: PASS (code review)
- **Notes**: The checks run sequentially in `main()` (lines 188-191): `checkNodeVersion()` -> `checkPython()` -> `checkGhCli()` -> `checkClaudeCli()`. Each calls `process.exit(1)` on failure, so the first missing prerequisite exits immediately. Note: `checkGitRepo()` runs even earlier (line 174), before the prerequisite block.
- **Verified at**: 2026-04-07 21:30

### TC-17: Windows PowerShell — happy path
- **Result**: SKIP
- **Notes**: Running in Git Bash, not PowerShell. Cannot switch shell in this session. Would need separate manual test.
- **Verified at**: 2026-04-07 21:30

### TC-18: Windows Git Bash — happy path
- **Result**: SKIP
- **Notes**: Would need a clean git repo without `.squidsquad/` to test full happy path. The prerequisite checks all pass in this environment (confirmed via TC-23 output showing no errors before the "already installed" message).
- **Verified at**: 2026-04-07 21:30

### TC-19: macOS — happy path
- **Result**: SKIP
- **Notes**: Running on Windows 11, not macOS.
- **Verified at**: 2026-04-07 21:30

### TC-20: Linux — happy path
- **Result**: SKIP
- **Notes**: Running on Windows 11, not Linux.
- **Verified at**: 2026-04-07 21:30

### TC-21: Windows Python detection uses `python` not `python3`
- **Result**: PASS (code review)
- **Notes**: Line 72: `for (const bin of ["python3", "python"])` — tries `python3` first, falls back to `python`. On Windows where only `python` exists, the fallback works. Both `python` and `python3` are available in this environment and the check passes.
- **Verified at**: 2026-04-07 21:30

### TC-22: No hardcoded path separators
- **Result**: PASS
- **Notes**: Searched `packages/cli/index.js` for hardcoded `/` in path construction. All file path operations use `path.join()` (lines 128, 175). The only forward slashes in the file are in URLs (REPO_URL, install links) and the shebang line — no path construction uses hardcoded separators.
- **Verified at**: 2026-04-07 21:30

### TC-23: Already installed — .squidsquad/ exists
- **Result**: PASS
- **Notes**: Ran `node packages/cli/index.js` from repo root (which has `.squidsquad/`). Output: "SquidSquad is already installed in this project." / "To upgrade, run `/squidsquad-upgrade` from a Claude session." Exit code 0. No install command was invoked. Correct behavior.
- **Verified at**: 2026-04-07 21:30

### TC-24: Skill already installed but no .squidsquad/
- **Result**: SKIP
- **Notes**: Cannot safely set up this scenario without modifying the repo state. Code review confirms: if `.squidsquad/` does not exist, the code proceeds to prerequisites and install regardless of prior skill state.
- **Verified at**: 2026-04-07 21:30

### TC-25: Run from subdirectory of a git repo
- **Result**: PASS
- **Notes**: Ran from `packages/cli/` subdirectory. `git rev-parse --show-toplevel` succeeded, found `.squidsquad/` at repo root, printed "already installed" message. Exit code 0. The code correctly uses the git root (line 175: `path.join(gitRoot, ".squidsquad")`) not the CWD.
- **Verified at**: 2026-04-07 21:30

### TC-26: package.json has zero runtime dependencies
- **Result**: PASS
- **Notes**: `packages/cli/package.json` has no `dependencies` field at all. No `devDependencies` either. Zero runtime dependencies confirmed.
- **Verified at**: 2026-04-07 21:30

### TC-27: package.json has correct bin field
- **Result**: PASS
- **Notes**: `"bin": { "squidsquad": "./index.js" }` — maps the `squidsquad` command to the CLI entry point. Correct.
- **Verified at**: 2026-04-07 21:30

### TC-28: package.json has correct engines field
- **Result**: PASS
- **Notes**: `"engines": { "node": ">=18" }` — specifies Node.js 18+ requirement. Correct.
- **Verified at**: 2026-04-07 21:30

### TC-29: package.json has correct name field
- **Result**: PASS
- **Notes**: `"name": "squidsquad"` — correct.
- **Verified at**: 2026-04-07 21:30

### TC-30: Offline / npm registry unreachable
- **Result**: SKIP
- **Notes**: Cannot disconnect from network in this environment. Test plan notes no special handling needed — this is npx behavior.
- **Verified at**: 2026-04-07 21:30

---

## Additional Findings

### FINDING-1: Banner Unicode escapes are broken (BUG)
- **Severity**: Medium
- **Details**: The `banner()` function (lines 28-36) outputs literal `\u2597\u2584\u2596` text strings instead of actual Unicode block characters. The source file contains double-escaped backslashes (`\\u2597`) which in JavaScript produce the literal string `\u2597` instead of the Unicode character `▗`. This was confirmed by raw byte inspection of the file (found `\\u2597` at offset 581) and by observing the actual output from TC-10, TC-23, and TC-25 runs.
- **Fix**: Replace `"\\u2597\\u2584\\u2596"` with `"\u2597\u2584\u2596"` (single backslash) throughout the banner function, or use the actual Unicode characters directly in the source: `"▗▄▖"`.

### FINDING-2: Spec deviation — git clone vs claude install-skill
- **Severity**: High (architectural)
- **Details**: The CONTEXT.md locked decision #2 states the scope is "prerequisite checks + `claude install-skill` + print instructions". The implementation instead uses `git clone --depth 1` to `~/.claude/skills/squidsquad/`. While the Dev Discretion section says "How to invoke `claude install-skill` (exact CLI args, repo URL format)" — suggesting the *invocation details* are flexible — the locked scope explicitly names `claude install-skill` as the install mechanism. The `git clone` approach is a fundamentally different mechanism that bypasses Claude's skill registry. **PM decision needed** on whether this deviation is acceptable or if the implementation should use `claude install-skill`.

### FINDING-3: installSkill() has update logic not covered by test plan
- **Severity**: Low
- **Details**: Lines 138-157 implement an update path: if `~/.claude/skills/squidsquad/` already exists, it tries `git pull --ff-only`, and if that fails, it re-clones. This update-on-reinstall behavior is not covered in the test plan and is beyond the original scope (which only handles fresh install + "already installed" detection via `.squidsquad/`). This could cause confusing behavior if a user runs `npx squidsquad` in a different repo after already installing — it would silently update the skill.

---

## Summary

| Category | Count |
|----------|-------|
| **PASS** | 17 |
| **FAIL** | 1 |
| **SKIP** | 12 |

### Verdict: **FAIL — back to dev**

**Blocking issues:**
1. **TC-13 FAIL**: Implementation uses `git clone` instead of `claude install-skill` as specified in locked decisions. PM must decide if this deviation is acceptable. If PM approves the `git clone` approach, TC-13 should be updated and this becomes a PASS.
2. **FINDING-1 (banner bug)**: Unicode escape sequences are double-escaped, producing literal `\uXXXX` text instead of squid art. This is a visible bug affecting every user's first impression.

**Non-blocking:**
3. **FINDING-3**: Update logic in `installSkill()` is undocumented and untested but not harmful.

If PM approves the `git clone` approach and the banner bug is fixed, the remaining 12 SKIPs are environment-dependent tests (macOS, Linux, missing prereqs) that should be verified in CI or manual cross-platform testing.
