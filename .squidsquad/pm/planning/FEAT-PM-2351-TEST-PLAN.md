# FEAT-PM-2351 Test Plan — Tarball Installer

## Test Cases

### TC-1: Happy path — tarball downloads, extracts, all files present
- **Precondition**: Clean git repo with no `.squidsquad/` directory. `gh` authenticated. Network available. Tag `v0.23.0` (or current package.json version) exists on `WallyDoodlez/SquidSquad`.
- **Steps**:
  1. Run `npx squidsquad` in the target repo.
  2. Installer downloads tarball via `gh api repos/WallyDoodlez/SquidSquad/tarball/v0.23.0`.
  3. Extracts to temp dir, copies allowlisted files into repo.
  4. Commits and prompts for wizard launch.
- **Expected**: All 119 files listed in `references/installer-files.txt` are present on disk under the git root. Commit message matches existing format (`chore: add SquidSquad skill + wizard infrastructure (via npx squidsquad)`). Exit code 0.
- **Verification**: `wc -l < references/installer-files.txt` matches count of non-comment lines. For each line in `installer-files.txt` (excluding comments/blanks), `test -f <path>` passes. `git log --oneline -1` shows the expected commit.

### TC-2: GitHub archive prefix stripping
- **Precondition**: Downloaded tarball from GitHub repo archive API.
- **Steps**:
  1. Inspect the tarball contents — GitHub wraps all files in a `SquidSquad-<sha>/` top-level directory.
  2. Extraction logic strips this prefix so `SquidSquad-abc123/SKILL.md` becomes `SKILL.md`.
- **Expected**: No `SquidSquad-<sha>/` directory exists in the temp extraction dir or the target repo. All extracted paths match entries in `installer-files.txt` exactly (relative to repo root).
- **Verification**: After extraction to temp dir, `ls` the temp dir — should contain `SKILL.md`, `references/`, etc. directly (no nested repo-name dir). In the target repo, `find . -maxdepth 1 -name "SquidSquad-*" -type d` returns nothing.

### TC-3: Allowlist enforcement — only installer-files.txt entries extracted
- **Precondition**: Tarball contains the full repo (hundreds of files beyond the 119 in the manifest). Target repo has user files that must not be overwritten.
- **Steps**:
  1. Run the installer.
  2. Check that files NOT in `installer-files.txt` (e.g., `packages/cli/index.js`, `.github/workflows/`, `tests/`, `CHANGELOG.md`, `README.md`) are NOT written to the target repo.
- **Expected**: Only files listed in `installer-files.txt` are written. No extra files from the tarball appear in the target repo. User's existing files are untouched.
- **Verification**: `git status` after install shows only the 119 manifest files plus `.claude/commands/squidsquad-setup.md` as new/staged. Count of `git diff --cached --name-only` lines equals 120 (119 manifest + 1 setup command). Spot-check: `test ! -f packages/cli/index.js` in target repo (should not exist — it is CLI-only, not in the manifest).

### TC-4: Atomic install — failed extraction leaves no partial state
- **Precondition**: Simulate extraction failure (e.g., corrupt tarball, disk full, permission error mid-extraction).
- **Steps**:
  1. Introduce a failure during tarball extraction (mock or inject error after partial extraction).
  2. Observe that the installer does not copy partial files into the repo.
  3. Observe that no git commit is created.
- **Expected**: Target repo is unchanged — no new files, no staged changes, no commits. Temp directory is cleaned up. Installer either falls back to per-file fetch or exits with a clear error.
- **Verification**: `git status` shows clean working tree. `git log --oneline -1` shows the same commit as before the install attempt. No orphaned temp directories remain (check OS temp dir).

### TC-5: Version tag matching — CLI requests tarball for its own package.json version
- **Precondition**: `packages/cli/package.json` has `"version": "0.23.0"`. Tag `v0.23.0` exists on the remote repo.
- **Steps**:
  1. Run the installer.
  2. Observe the tarball URL constructed by the CLI.
- **Expected**: CLI reads its own `package.json` version and requests `gh api repos/WallyDoodlez/SquidSquad/tarball/v0.23.0`. The version in the URL matches the npm package version exactly.
- **Verification**: Add debug logging or intercept the `gh api` call. The tag in the URL is `v<package.json version>`. If the tag does not exist, the installer falls back to per-file fetch (see TC-6).

### TC-6: Silent fallback — tarball failure triggers per-file fetch
- **Precondition**: Tarball download fails (network error, non-existent tag, or rate limit).
- **Steps**:
  1. Simulate tarball failure (e.g., request a non-existent tag like `v0.0.0-nonexistent`).
  2. Observe that the installer silently falls back to the existing per-file `gh api` fetch loop.
  3. Installation completes successfully via the fallback path.
- **Expected**: All 119 files are installed. A log note indicates fallback occurred (e.g., `info("Tarball unavailable, falling back to per-file fetch...")`). No error is shown to the user. Exit code 0.
- **Verification**: All files from `installer-files.txt` present on disk. Console output contains a fallback note. `git log --oneline -1` shows the commit. Installation succeeds end-to-end.

### TC-7: Fallback trigger — network error
- **Precondition**: Network available for `gh auth status` but tarball endpoint unreachable (e.g., DNS failure, timeout).
- **Steps**:
  1. Block network access to the tarball endpoint after prereq checks pass.
  2. Run the installer.
- **Expected**: Tarball download fails. Installer falls back to per-file fetch. If per-file also fails (same network issue), installer exits with error. If per-file works (different endpoint), install completes.
- **Verification**: Console output shows fallback note. If fallback succeeds, all files present. If fallback also fails, exit code is non-zero with a clear error message.

### TC-8: Fallback trigger — no tag exists (pre-release version)
- **Precondition**: CLI `package.json` version is `0.24.0-beta.1` or similar, and no matching tag exists on the remote.
- **Steps**:
  1. Modify local `package.json` version to a non-existent tag.
  2. Run the installer.
- **Expected**: `gh api repos/.../tarball/v0.24.0-beta.1` returns 404. Installer silently falls back to per-file fetch from `main` branch. Install completes.
- **Verification**: Fallback note in console. All 119 files installed. Commit created.

### TC-9: Fallback trigger — rate limit
- **Precondition**: GitHub API rate limit exhausted (or simulated via mock).
- **Steps**:
  1. Exhaust or mock GitHub API rate limit.
  2. Run the installer.
- **Expected**: Tarball request returns 403/429. Installer falls back. If per-file fetch is also rate-limited, installer exits with error and suggests waiting.
- **Verification**: Console shows fallback or rate-limit error. Behavior is graceful — no crash, no partial state.

### TC-10: Existing repo guard — .squidsquad/ exists, exit early
- **Precondition**: Target repo already has a `.squidsquad/` directory (previous install).
- **Steps**:
  1. Run `npx squidsquad`.
- **Expected**: Installer prints "SquidSquad is already installed in this project." and "To upgrade, run `/squidsquad-upgrade`". Exits with code 0. No tarball download attempted. No files modified.
- **Verification**: Console output matches expected messages. `git log --oneline -1` unchanged. No network requests to tarball endpoint.

### TC-11: Windows compatibility — paths, extraction, temp dir
- **Precondition**: Windows 11 machine. Node.js 18+, `gh` CLI installed and authenticated.
- **Steps**:
  1. Run `npx squidsquad` in a git repo on Windows.
  2. Observe path handling during extraction (forward slashes vs backslashes).
  3. Observe temp directory creation and cleanup.
- **Expected**: All paths use `path.join()` (OS-appropriate separators). Tarball extraction via Node `tar` library works without shelling out to system `tar`. Temp directory created in `os.tmpdir()` and cleaned up after install. All 119 files installed with correct content.
- **Verification**: Run on Windows. All files present. No path errors in console. `os.tmpdir()` directory does not contain leftover `squidsquad-*` temp dirs after install. File contents match source (no line-ending corruption on text files).

### TC-12: installer-files.txt validation — all listed files present after extraction
- **Precondition**: Tarball downloaded and extracted successfully.
- **Steps**:
  1. After extraction to temp dir (before copying to repo), validate that every non-comment line in `installer-files.txt` has a corresponding file in the extracted contents.
  2. If any file is missing, fail the tarball path and fall back to per-file fetch.
- **Expected**: Validation catches missing files. If the tarball is from a different version that removed a file, validation fails and fallback triggers. If all files present, copy proceeds.
- **Verification**: Introduce a mismatch (add a fake entry to `installer-files.txt`). Tarball path should fail validation and fall back. Remove the fake entry — tarball path succeeds.

### TC-13: Performance — single HTTP request vs ~119 per-file requests
- **Precondition**: Network available. Tag exists.
- **Steps**:
  1. Time the tarball install path end-to-end (from "Fetching..." to "files fetched and placed").
  2. Time the per-file fallback path end-to-end (force fallback for comparison).
- **Expected**: Tarball path completes in roughly 1 network round-trip + extraction time. Per-file path takes ~119 sequential `gh api` calls. Tarball should be 10-30x faster (per CONTEXT.md scope).
- **Verification**: Compare wall-clock times. Tarball path should be under 10 seconds on a reasonable connection. Per-file path typically takes 30-120 seconds.

### TC-14: Temp dir cleanup — temp directory removed after successful install
- **Precondition**: Tarball install path succeeds.
- **Steps**:
  1. Run the installer.
  2. After completion, check the OS temp directory for leftover extraction artifacts.
- **Expected**: No `squidsquad-*` or similar temp directories remain in `os.tmpdir()`. Cleanup runs even if extraction succeeds but copy fails (via try/finally).
- **Verification**: `ls $(node -e "console.log(require('os').tmpdir())")` — no squidsquad temp dirs. On Windows: `dir %TEMP% | findstr squidsquad` returns nothing.

### TC-15: Edge case — empty tarball or corrupt archive
- **Precondition**: Tarball endpoint returns a 0-byte response or corrupt data.
- **Steps**:
  1. Mock or intercept the tarball response with empty/corrupt data.
  2. Run the installer.
- **Expected**: Node `tar` library throws an extraction error. Installer catches it, cleans up temp dir, falls back to per-file fetch. No crash.
- **Verification**: Console shows fallback note. Install completes via per-file path. No temp dirs remain.

### TC-16: Edge case — very long file paths in tarball
- **Precondition**: `installer-files.txt` contains paths like `references/sub-skills/capabilities/google_stitch/sub-skill.md` (deeply nested).
- **Steps**:
  1. Run the installer on Windows where MAX_PATH (260 chars) can be an issue.
  2. Git root path + longest manifest path must stay under OS limits.
- **Expected**: All deeply nested files extracted and written successfully. If path length exceeds OS limit, a clear error is shown (not a cryptic ENAMETOOLONG).
- **Verification**: Longest path in manifest: `references/sub-skills/capabilities/google_stitch/sub-skill.md` (58 chars). Combined with a typical git root (e.g., `C:\Users\user\projects\myapp\` = 30 chars), total is ~88 chars — well under 260. Verify all nested files exist.

### TC-17: Tarball content integrity — extracted files match source
- **Precondition**: Tarball downloaded for a known version tag.
- **Steps**:
  1. After tarball extraction, compare file contents against `gh api` per-file fetch for a sample of 5 files (e.g., `SKILL.md`, `references/scripts/compose.py`, `references/roles/pm/CLAUDE.md`).
- **Expected**: File contents are byte-identical between tarball extraction and per-file fetch. No encoding issues, no truncation, no BOM differences.
- **Verification**: `diff <(tarball-extracted-file) <(per-file-fetched-file)` returns no differences for each sampled file.

## Smoke Tests

- [ ] `npx squidsquad` in a fresh git repo completes without errors
- [ ] All 119 files from `installer-files.txt` present after install
- [ ] `SKILL.md` content is correct (not truncated, not from wrong version)
- [ ] `.claude/commands/squidsquad-setup.md` created with correct content
- [ ] Git commit created with expected message
- [ ] Installer exits early when `.squidsquad/` already exists
- [ ] Forced fallback (bad tag) still installs all files
- [ ] Windows: `npx squidsquad` works end-to-end without path errors
- [ ] No temp directories left behind after install (success or failure)
- [ ] Progress output shown during download (not silent for extended periods)

## Regression Risks

- **Existing per-file fetch path removed or broken**: The fallback depends on the current `fetchRawFile()` loop (`index.js:123-175`) remaining functional. If tarball refactoring accidentally breaks this code path, fallback is dead. Mitigation: keep `fetchRawFile()` and the loop intact, only add tarball as a "try first" wrapper.
- **Manifest fetch chicken-and-egg**: Current code fetches `installer-files.txt` via `fetchRawFile()` before the file loop. With tarball, the manifest is inside the tarball. The installer must either: (a) still fetch the manifest separately to validate tarball contents, or (b) bundle the manifest list in the CLI code itself. Either approach must not regress the current "manifest as source of truth" guarantee.
- **`gh api` behavior differences for tarball endpoint**: The tarball endpoint (`/repos/{owner}/{repo}/tarball/{ref}`) returns a redirect + binary stream, unlike the JSON contents API used by `fetchRawFile()`. The `gh api` client handles this differently — may need `-H "Accept: application/octet-stream"` or `--output` flag. Incorrect handling would break the happy path.
- **Git staging changes**: Current code stages `SKILL.md references/ .claude/commands/squidsquad-setup.md`. If tarball extraction writes files to different paths or misses the staging list, the commit would be incomplete. The `git add` command must still match the installed file set.
- **Node `tar` library added as dependency**: Adding `tar` to `package.json` increases the CLI package size (~50KB per CONTEXT.md). Verify `npm pack` size is acceptable and the dependency resolves correctly on all platforms (Windows, macOS, Linux). The `tar` package must be listed in `dependencies` (not `devDependencies`) since it runs at install time via `npx`.
- **Line ending handling**: GitHub tarballs may contain LF line endings. On Windows, Node `fs.writeFileSync` writes as-is. If the existing per-file path preserved CRLF and the tarball path writes LF, file diffs would appear in git. Ensure consistent behavior.
- **Wizard launch unaffected**: The `launchClaude()` function and `askLaunch()` prompt must work identically after tarball install. The wizard reads committed files — verify the commit includes everything the wizard expects.

## Comprehension Questions

### CQ-1: What API endpoint does the CLI use to download the tarball?
- **Files**: `packages/cli/index.js`
- **Expected**: `gh api repos/WallyDoodlez/SquidSquad/tarball/v<version>` where `<version>` comes from the CLI's own `package.json`.

### CQ-2: What happens if the tarball download fails?
- **Files**: `packages/cli/index.js`
- **Expected**: The installer silently falls back to the existing per-file `fetchRawFile()` loop, logging a note about the fallback. The user sees a slower install but it completes successfully.

### CQ-3: How does the installer handle the GitHub archive prefix directory?
- **Files**: `packages/cli/index.js`
- **Expected**: GitHub tarballs wrap contents in `RepoName-<sha>/`. The extraction logic strips this top-level prefix so files are placed at their correct relative paths matching `installer-files.txt` entries.

### CQ-4: What prevents the tarball from overwriting user files outside the manifest?
- **Files**: `packages/cli/index.js`, `references/installer-files.txt`
- **Expected**: Only files listed in `installer-files.txt` are extracted from the tarball. The allowlist is enforced during extraction — files not in the manifest are skipped even though they exist in the tarball.
