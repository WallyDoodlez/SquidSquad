# FEAT-PM-2351 Research — Tarball installer + CLI integration (unshipped scope from #13)

## Summary
Researched the current Node.js `npx` installer implementation and the shipped Python-side infrastructure (repo scan + model router). The current installer (`packages/cli/index.js`) fetches a manifest (`references/installer-files.txt`) and then downloads ~119 files one-by-one via `gh api`, writing them into the target repo and committing them. This is slow, brittle (rate limits / per-file failures), and is explicitly the part to replace with a single tarball download + extraction that must work on Windows.

Recommendation: replace the per-file fetch loop in `installFiles()` with a “download tarball once → extract only needed paths → write into repo → commit” flow. Keep `gh` as the transport (already required), but avoid relying on Unix `tar` availability on Windows by implementing extraction in Node (either via a JS tar library or by shelling out to a known-available tool with fallback). Also integrate (a) CLI model routing awareness by surfacing `.squidsquad/config.md` “Model Routing” and/or provider availability, and (b) display a repo scan summary after `repo_scan.py --save` runs (currently it runs silently and only logs “saved”).

Primary risks: Windows tar extraction compatibility; tarball path layout differences (GitHub auto-generated archives include a top-level `repo-<sha>/` folder); ensuring the tarball version matches the npm package version (locked decision from #13 context); and avoiding partial installs that leave a dirty worktree.

## Vault Context
- **BRIEFING.md priorities**: #1772 “DM delivery missing npm publish” (high) is adjacent: tarball delivery hook + npm version alignment must be reliable. Also “Never ship with failed test cases” is a standing priority. (See `.squidsquad/vault/BRIEFING.md:7-11,24-28`.)
- **Related decisions**: none found in vault search (vault grep returned no matches for tarball/npx/installer/#13 keywords).
- **Related patterns**: none found in vault search.
- **Human preferences**: Windows 11 primary platform; prefers direct/mechanical checks over indirect state files; terse/direct. (See `.squidsquad/vault/areas/human-profile.md:27-34`.)
- **Related learnings**: none found in vault search.

## Impact Analysis
- **Files touched**:
  - `packages/cli/index.js` — main change: replace per-file GitHub fetch loop with tarball download + extraction; add repo scan summary display; add model routing/provider surfacing. (Key areas: file fetching at `index.js:121-175`, repo scan at `index.js:263-278`.)
  - `references/installer-files.txt` — may remain as the “subset list” to extract from the tarball; might need adjustments if tarball layout changes or if new files are required. (Manifest described at `references/installer-files.txt:1-7`.)
  - Potentially `.claude/commands/squidsquad-setup.md` generation text inside `packages/cli/index.js` if instructions change from “fetch on demand using gh api” to “already present from tarball”. (Generated content at `index.js:180-207`.)
- **Behavior changes**:
  - Installer will perform **one** GitHub download (tarball) instead of ~119 `gh api` calls (`index.js:157-173` currently loops).
  - Extraction must handle GitHub archive top-folder prefix and only place the files listed in `references/installer-files.txt`.
  - After `repo_scan.py --save`, CLI should read `.squidsquad/.repo-scan.json` and print a human-readable summary (currently it only logs “saved” and suppresses output; `index.js:263-276`).
  - “CLI model routing integration”: likely means reading `.squidsquad/config.md` “## Model Routing” (parsed by Python router) and/or listing available providers; at minimum, display which model would be used for key task types or warn if external routing is configured but missing keys.
- **Dependencies**:
  - Current hard dependency on `gh` CLI remains (`checkGhCli()` at `index.js:92-109`).
  - New dependency decision: either
    - add a Node tar extraction library (best for Windows reliability), or
    - shell out to `tar`/PowerShell with robust fallback (riskier).
  - Python scripts already present and used: `references/scripts/repo_scan.py` (invoked at `index.js:264-276`) and `references/scripts/model_router.py` exists and parses config routing (`references/scripts/model_router.py:69-119`).

## Side Effects
- **Risk 1**: Windows extraction failures (no `tar`, path length issues, permissions) — Severity: **H** — Mitigation: implement extraction in Node (library-based) and normalize paths; explicitly strip the GitHub archive’s top-level directory; write files using `fs.mkdirSync(..., {recursive:true})` like current code (`index.js:166-167`).
- **Risk 2**: Tarball contains more than intended; accidental overwrite of user files — Severity: **H** — Mitigation: extract only the allowlisted paths from `references/installer-files.txt` (keep it as the single source of truth per current comment at `index.js:140-145`), and refuse to overwrite if destination exists and differs unless it’s a fresh install.
- **Risk 3**: Version mismatch between npm package and tarball (locked decision from #13 context) — Severity: **M/H** — Mitigation: embed expected version in CLI (from its own `package.json`) and request the tarball for that version tag/release; fail fast if the downloaded archive doesn’t match expected (e.g., verify a version file inside tarball like `SKILL.md` frontmatter version, then compare).
- **Risk 4**: Partial install leaves dirty worktree and breaks `/squidsquad-setup` expectations — Severity: **M** — Mitigation: download/extract into a temp dir first, validate all required files exist, then copy into repo atomically; only then `git add`/`git commit` (commit logic currently at `index.js:212-236`).

## Edge Cases
- **GitHub archive top-level folder prefix**: GitHub tarballs typically wrap contents in `RepoName-<sha>/...` — handle by stripping first path segment during extraction.
- **Rate limits / auth**: `gh auth status` is already enforced (`index.js:101-108`), but tarball download should still handle transient failures with retry/backoff.
- **Repo already has `.squidsquad/`**: installer exits early (`index.js:306-315`). Ensure tarball approach doesn’t change this behavior.
- **Repo scan script missing**: `runRepoScan()` checks existence (`index.js:265-277`). With tarball install, it should always exist post-install; still keep non-fatal behavior.
- **Python not on PATH / Windows launcher quirks**: `checkPython()` and `getPythonBin()` already try `python3` then `python` (`index.js:72-90`, `255-261`). Keep as-is; for scan summary display, handle missing `.squidsquad/.repo-scan.json` gracefully.

## Integration Risks
- **Interaction with shipped Python router**: `references/scripts/model_router.py` reads `.squidsquad/config.md` and has Claude-locked tasks (`CLAUDE_LOCKED_TASKS` at `model_router.py:42-44`). If CLI starts surfacing routing info, it must reflect these constraints (don’t claim “qa-execution routed to X” when it is forced to Claude).
- **Interaction with wizard runbook expectations**: The generated `/squidsquad-setup` command text currently tells Claude to “Fetch them on demand using `gh api` or `curl`…” (`packages/cli/index.js:197-202`). If tarball install guarantees all wizard-needed files are present, this instruction becomes misleading and should be updated to reduce unnecessary network behavior.

## Upgrade & Migration
- **New config values**: none required for tarball install itself (model routing already lives in `.squidsquad/config.md` and is parsed by Python router; see `model_router.py:69-87`).
- **New files**: likely **none** in the target repo (still installing the same set from `references/installer-files.txt`), but the CLI implementation may add temporary download/extract locations (should be outside repo or cleaned up).
- **Template changes**: possible change to generated `.claude/commands/squidsquad-setup.md` content (currently generated in `packages/cli/index.js:183-207`).
- **Upgrade steps**: **N/A — no upgrade impact** for existing installed repos, since this is the installer path. (Installer already exits if `.squidsquad/` exists; `index.js:306-315`.)
- **Graceful degradation**: If tarball download/extract fails, fallback could be the existing per-file fetch method (current `fetchRawFile()` + loop at `index.js:123-173`) to preserve functionality, especially on constrained Windows environments.

## Open Questions
- **Q1**: What exact GitHub API endpoint/asset is the “DM delivery hook” producing (release asset? tag tarball? repo archive?) — **Why**: determines how CLI constructs the download URL and how it verifies “tarball matches npm package version”.
- **Q2**: Should the CLI *only display* model routing info, or actually *invoke* Python `model_router.py` for certain tasks during install/setup? — **Why**: affects scope and whether Node needs to understand provider auth/env validation vs. leaving it to Python.
- **Q3**: What scan summary format is desired (top languages, frameworks, test tools, responsibilities)? — **Why**: `repo_scan.py` outputs structured JSON; without a defined summary, CLI output may be noisy or miss key signals.

## Recommendation
Feasible with caveats. The core change is localized to `packages/cli/index.js` (replace `installFiles()` fetch loop at `index.js:139-175`), but Windows-safe tar extraction and version/tarball verification need explicit design. Keep `references/installer-files.txt` as the allowlist to prevent overwriting and to ensure deterministic installs, and add a fallback to the current per-file fetch path for robustness. Integrate repo scan summary by reading `.squidsquad/.repo-scan.json` after `repo_scan.py --save` (`index.js:263-278`) and printing a concise summary; integrate model routing by reading `.squidsquad/config.md` “Model Routing” semantics consistent with `references/scripts/model_router.py` (`model_router.py:69-119`, `42-44`).