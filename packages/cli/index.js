#!/usr/bin/env node

"use strict";

const { execSync, spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

let tar;
try {
  tar = require("tar");
} catch {
  tar = null;
}

const REPO_OWNER = "WallyDoodlez";
const REPO_NAME = "SquidSquad";
const BRANCH = "main";
const RAW_BASE = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}`;

// --- Output helpers ---

function info(msg) {
  console.log(`  ${msg}`);
}

function success(msg) {
  console.log(`  \x1b[32m\u2713\x1b[0m ${msg}`);
}

function fail(msg) {
  console.error(`  \x1b[31m\u2717\x1b[0m ${msg}`);
}

function banner() {
  console.log();
  console.log("      \u2597\u2584\u2596");
  console.log("     \u259F\u2588 \u2588\u2599");
  console.log("    \u2590\u2588\u2022 \u2022\u2588\u258C");
  console.log("   \u2588\u2588\u2588\u2588\u2588\u2588\u2588");
  console.log("   \u2590\u2588\u2588\u2588\u2588\u2588\u258C");
  console.log("    \u2590\u258C\u2590\u258C\u2590\u258C");
  console.log("  S Q U I D S Q U A D");
  console.log();
}

// --- Prerequisite checks ---

function checkNodeVersion() {
  const major = parseInt(process.versions.node.split(".")[0], 10);
  if (major < 18) {
    fail(`Node.js 18+ is required (found v${process.versions.node}).`);
    info("Install the latest LTS from https://nodejs.org/");
    process.exit(1);
  }
  success(`Node.js v${process.versions.node}`);
}

function tryExec(cmd) {
  try {
    return execSync(cmd, { encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }).trim();
  } catch {
    return null;
  }
}

function checkGitRepo() {
  const root = tryExec("git rev-parse --show-toplevel");
  if (!root) {
    fail("Not a git repository.");
    info("Run this command from inside a git repository.");
    process.exit(1);
  }
  success("Git repository detected");
  return root;
}

function checkPython() {
  for (const bin of ["python3", "python"]) {
    const out = tryExec(`${bin} --version`);
    if (out) {
      const match = out.match(/Python (\d+)\.(\d+)/);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if ((major === 3 && minor >= 8) || major > 3) {
          success(`${out}`);
          return;
        }
      }
    }
  }
  fail("Python 3.8+ is required.");
  info("Install from https://www.python.org/downloads/");
  process.exit(1);
}

function checkGhCli() {
  const ver = tryExec("gh --version");
  if (!ver) {
    fail("GitHub CLI (gh) is required.");
    info("Install from https://cli.github.com/");
    process.exit(1);
  }
  success("GitHub CLI installed");

  try {
    execSync("gh auth status", { encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] });
    success("GitHub CLI authenticated");
  } catch {
    fail("GitHub CLI is not authenticated.");
    info("Run `gh auth login` first.");
    process.exit(1);
  }
}

function checkClaudeCli() {
  const ver = tryExec("claude --version");
  if (!ver) {
    fail("Claude Code CLI is required.");
    info("Install from https://docs.anthropic.com/en/docs/claude-code/overview");
    process.exit(1);
  }
  success(`Claude Code CLI v${ver}`);
}

// --- Path safety ---

function assertWithinRoot(root, filePath) {
  const resolved = path.resolve(root, filePath);
  if (!resolved.startsWith(path.resolve(root) + path.sep) && resolved !== path.resolve(root)) {
    fail(`Path traversal blocked: ${filePath}`);
    process.exit(1);
  }
  return resolved;
}

// --- File fetching ---

function fetchRawFile(repoPath) {
  // Defense-in-depth: validate repoPath against shell metacharacter injection (#6316)
  if (!/^[\w.\/\-]+$/.test(repoPath)) {
    fail(`Unsafe repoPath rejected: ${repoPath}`);
    return null;
  }
  const url = `${RAW_BASE}/${repoPath}`;
  try {
    const content = execSync(
      `gh api -H "Accept: application/vnd.github.raw+json" "/repos/${REPO_OWNER}/${REPO_NAME}/contents/${repoPath}?ref=${BRANCH}"`,
      { encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"], maxBuffer: 1024 * 1024 }
    );
    return content;
  } catch {
    // Fallback: try curl/wget for raw URL
    const fallback = tryExec(`curl -fsSL "${url}"`);
    if (fallback) return fallback;
    return null;
  }
}

function getCliVersion() {
  try {
    const pkgPath = path.join(__dirname, "package.json");
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
    return pkg.version || null;
  } catch {
    return null;
  }
}

function downloadTarball(gitRoot, filePaths) {
  if (!tar) {
    info("tar library not available, skipping tarball path");
    return false;
  }

  const version = getCliVersion();
  if (!version) {
    info("Could not determine CLI version, skipping tarball path");
    return false;
  }

  const tag = `v${version}`;
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "squidsquad-"));
  const tarballPath = path.join(tmpDir, "repo.tar.gz");

  try {
    info(`Downloading tarball for ${tag}...`);
    execSync(
      `gh api "repos/${REPO_OWNER}/${REPO_NAME}/tarball/${tag}" > "${tarballPath}"`,
      { encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"], shell: true, maxBuffer: 50 * 1024 * 1024 }
    );

    if (!fs.existsSync(tarballPath) || fs.statSync(tarballPath).size === 0) {
      info("Tarball download produced empty file");
      return false;
    }

    // Extract to temp dir
    const extractDir = path.join(tmpDir, "extracted");
    fs.mkdirSync(extractDir, { recursive: true });

    tar.extract({
      file: tarballPath,
      cwd: extractDir,
      sync: true,
    });

    // Find the GitHub archive prefix directory (RepoName-<sha>/)
    const entries = fs.readdirSync(extractDir);
    if (entries.length !== 1 || !fs.statSync(path.join(extractDir, entries[0])).isDirectory()) {
      info("Unexpected tarball structure");
      return false;
    }
    const prefixDir = path.join(extractDir, entries[0]);

    // Validate all manifest files exist in the tarball
    const missing = [];
    for (const filePath of filePaths) {
      const srcPath = path.join(prefixDir, filePath);
      if (!fs.existsSync(srcPath)) {
        missing.push(filePath);
      }
    }

    if (missing.length > 0) {
      info(`Tarball missing ${missing.length} manifest files, falling back`);
      return false;
    }

    // Copy only allowlisted files into the target repo
    let copied = 0;
    for (const filePath of filePaths) {
      const srcPath = path.join(prefixDir, filePath);
      const destPath = assertWithinRoot(gitRoot, filePath);
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      fs.copyFileSync(srcPath, destPath);
      copied++;
      if (copied % 20 === 0) {
        info(`  ${copied}/${filePaths.length} files...`);
      }
    }

    success(`${copied} files fetched and placed (via tarball)`);
    return true;
  } catch (err) {
    info(`Tarball unavailable, falling back to per-file fetch...`);
    return false;
  } finally {
    // Clean up temp dir
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // Best-effort cleanup
    }
  }
}

function installFilesPerFile(gitRoot, filePaths) {
  info(`Fetching ${filePaths.length} files from SquidSquad...`);
  let fetched = 0;
  for (const filePath of filePaths) {
    const content = fetchRawFile(filePath);
    if (!content) {
      fail(`Failed to fetch ${filePath}`);
      process.exit(1);
    }
    const dest = assertWithinRoot(gitRoot, filePath);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, content, "utf-8");
    fetched++;
    if (fetched % 20 === 0) {
      info(`  ${fetched}/${filePaths.length} files...`);
    }
  }
  success(`${fetched} files fetched and placed`);
}

function installFiles(gitRoot) {
  // 1. Fetch the file manifest — the single source of truth for what the
  //    wizard needs. Every script, manifest, sub-skill, template, and
  //    config file is listed in `references/installer-files.txt`.
  //    (#373 fix: deterministic pre-fetch replaces probabilistic
  //    "Claude figures it out" approach.)
  info("Fetching file manifest...");
  const manifestContent = fetchRawFile("references/installer-files.txt");
  if (!manifestContent) {
    fail("Failed to fetch references/installer-files.txt from GitHub.");
    process.exit(1);
  }

  const filePaths = manifestContent
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"));

  // Try tarball first (10-30x faster), fall back to per-file fetch
  if (!downloadTarball(gitRoot, filePaths)) {
    installFilesPerFile(gitRoot, filePaths);
  }

  // 3. Create .claude/commands/ and write squidsquad-setup.md
  const commandsDir = path.join(gitRoot, ".claude", "commands");
  fs.mkdirSync(commandsDir, { recursive: true });

  // The setup command tells Claude to read the wizard runbook and
  // follow it exactly — not SKILL.md's Setup Instructions section,
  // which is now just a pointer at the runbook.
  const setupCommand = [
    "---",
    "description: Run the SquidSquad install wizard (intent-driven team setup)",
    "---",
    "",
    "Read `references/wizard/WIZARD.md` in this repo and follow it exactly.",
    "You are the **installer agent** (Q-new21) — ephemeral, single-session,",
    "disposes after the install commits and pushes.",
    "",
    "The runbook is the single source of truth for the setup flow. Do not",
    "reimplement any step from memory — call the helpers it points at",
    "(`references/scripts/wizard.py`, `references/scripts/manifest.py`,",
    "`references/scripts/compose.py`) and act on their JSON output.",
    "",
    "The wizard needs additional source files from the SquidSquad repo",
    "(scripts, role/tool/preset manifests, sub-skill composition sources).",
    "Fetch them on demand using `gh api` or `curl` against",
    "`https://raw.githubusercontent.com/WallyDoodlez/SquidSquad/main/` when",
    "the runbook instructs you to call a helper that is not yet in the",
    "target repo.",
    "",
    "Before Step 7 nothing touches disk — the user can abort at any review",
    "step with zero trace. After Step 7.6 you must exit the conversation.",
    "",
  ].join("\n");

  fs.writeFileSync(path.join(commandsDir, "squidsquad-setup.md"), setupCommand, "utf-8");
  success("Created /squidsquad-setup command");

  // 3b. Copy skill commands from references/commands/ to .claude/commands/
  const refCommandsDir = path.join(gitRoot, "references", "commands");
  if (fs.existsSync(refCommandsDir)) {
    for (const file of fs.readdirSync(refCommandsDir)) {
      if (file.endsWith(".md")) {
        const src = path.join(refCommandsDir, file);
        const dest = path.join(commandsDir, file);
        fs.copyFileSync(src, dest);
      }
    }
    success("Copied skill commands (compose, upgrade)");
  }

  // 4. Commit ALL fetched files + the slash command so /squidsquad-setup
  //    doesn't abort on a dirty worktree. This stages references/, SKILL.md,
  //    and .claude/commands/ in a single commit.
  info("Committing SquidSquad files...");
  try {
    execSync(
      "git add SKILL.md start.sh start.ps1 references/ .claude/commands/",
      { cwd: gitRoot, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
    );
    execSync(
      'git commit -m "chore: add SquidSquad skill + wizard infrastructure (via npx squidsquad)"',
      { cwd: gitRoot, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] },
    );
    success("All SquidSquad files committed");
  } catch (err) {
    fail("Failed to commit files.");
    if (err.stderr) {
      info(`  git error: ${err.stderr.trim()}`);
    }
    info("  Fix the issue above, then run:");
    info("    git add SKILL.md references/ .claude/commands/squidsquad-setup.md");
    info('    git commit -m "chore: add SquidSquad skill"');
    info("    claude --dangerously-skip-permissions /squidsquad-setup");
    process.exit(1);
  }
}

// --- Launch prompt ---

function askLaunch() {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
    rl.question("  Launch SquidSquad setup now? (Y/n) ", (answer) => {
      rl.close();
      const trimmed = answer.trim().toLowerCase();
      resolve(trimmed === "" || trimmed === "y" || trimmed === "yes");
    });
  });
}

function getPythonBin() {
  for (const bin of ["python3", "python"]) {
    const out = tryExec(`${bin} --version`);
    if (out && out.match(/Python 3/)) return bin;
  }
  return "python";
}

function runRepoScan() {
  const scanScript = path.join("references", "scripts", "repo_scan.py");
  if (fs.existsSync(scanScript)) {
    info("Scanning repository tech stack...");
    try {
      execSync(`${getPythonBin()} ${scanScript} --save`, {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      info("Repo scan saved to .squidsquad/.repo-scan.json");
    } catch (err) {
      // Non-fatal — wizard works without scan results
      info("Repo scan skipped (non-fatal)");
    }
  }
}

function launchClaude() {
  runRepoScan();
  info("Launching Claude Code with /squidsquad-setup...");
  console.log();

  const child = spawn("claude", ["--dangerously-skip-permissions", "/squidsquad-setup"], {
    stdio: "inherit",
    shell: true,
  });

  child.on("error", (err) => {
    fail(`Failed to launch Claude: ${err.message}`);
    info("Run manually: claude --dangerously-skip-permissions /squidsquad-setup");
    process.exit(1);
  });

  child.on("exit", (code) => {
    process.exit(code || 0);
  });
}

// --- Main ---

async function main() {
  banner();

  // Check if already set up in this project
  const gitRoot = checkGitRepo();
  const squidDir = path.join(gitRoot, ".squidsquad");
  if (fs.existsSync(squidDir)) {
    console.log();
    info("SquidSquad is already installed in this project.");
    info("To upgrade, run `/squidsquad-upgrade` from a Claude session.");
    console.log();
    process.exit(0);
  }

  console.log();
  info("Checking prerequisites...");
  console.log();

  checkNodeVersion();
  checkPython();
  checkGhCli();
  checkClaudeCli();

  console.log();
  info("All prerequisites met. Fetching SquidSquad files...");
  console.log();

  try {
    installFiles(gitRoot);
  } catch (err) {
    console.log();
    fail("Installation failed.");
    info(err.message || String(err));
    process.exit(1);
  }

  console.log();
  console.log("  \x1b[32m\x1b[1mSquidSquad is ready!\x1b[0m");
  console.log();

  const shouldLaunch = await askLaunch();

  if (shouldLaunch) {
    launchClaude();
  } else {
    console.log();
    info("To set up later, run:");
    console.log();
    info("  claude --dangerously-skip-permissions /squidsquad-setup");
    console.log();
  }
}

// Export for testing when loaded as a module
if (require.main === module) {
  main();
} else {
  module.exports = { getCliVersion, downloadTarball, installFilesPerFile, fetchRawFile, assertWithinRoot };
}
