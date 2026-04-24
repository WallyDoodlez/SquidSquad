# FEAT-PM-2351 Context — Tarball Installer

## Scope

Replace the per-file fetch loop in `packages/cli/index.js` (~119 individual `gh api` calls) with a single tarball download via GitHub's repo archive API. Extract only files listed in `references/installer-files.txt`. 10-30x faster installs.

**Tarball transport only.** CLI model routing and scan summary display are explicitly out of scope — filed separately if needed.

## Locked Decisions (human decided)

- **Tarball only scope**: No CLI model routing, no scan summary display. Pure transport optimization.
- **GitHub repo archive API**: Use `gh api repos/{owner}/{repo}/tarball/{tag}` to download. No custom release asset or DM delivery hook. Already works today.
- **Node tar library**: Add `tar` npm package for cross-platform extraction. No shell-out to system tar or PowerShell. Adds ~50KB to CLI.
- **Silent fallback**: If tarball download fails (network error, no tag, rate limit), fall back to current per-file fetch method silently. Log a note about the fallback. User sees slower install but it works.

## Dev Discretion (dev agent can choose)

- Exact `tar` npm package (e.g., `tar` by npm/node-tar vs alternatives)
- Temp directory strategy for download/extraction before copying into repo
- GitHub archive path prefix stripping implementation
- Progress output during download (spinner, percentage, silent)
- Whether to keep `installer-files.txt` as allowlist or derive from tarball contents

## Side Effect Mitigations (required)

- **GitHub archive prefix**: GitHub tarballs wrap contents in `RepoName-<sha>/`. Must strip this prefix during extraction.
- **Allowlist enforcement**: Only extract files listed in `installer-files.txt`. Do not extract the entire repo.
- **Atomic install**: Download and extract to temp dir first. Validate all required files exist. Then copy into repo and commit. Partial failure must not leave broken state.
- **Existing repo guard**: Installer already exits early if `.squidsquad/` exists. This behavior must not change.
- **Version verification**: CLI should request tarball for its own version tag (from package.json). If no tag exists (pre-release), fallback handles it.

## Upgrade Path (required)

- **N/A — no upgrade impact**. This changes the installer, not installed repos. Existing installs are unaffected. The installer already exits if `.squidsquad/` exists.

## Out of Scope

- CLI model routing prompts (separate task)
- Scan summary display in CLI (separate task)
- DM delivery hook for tarball production (not needed — using GitHub archive API)
- Changes to `references/installer-files.txt` format
- Upgrade flow (`/squidsquad-upgrade`) — separate concern
