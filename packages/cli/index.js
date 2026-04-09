#!/usr/bin/env node

"use strict";

const { execSync, spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const readline = require("readline");

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

// --- File fetching ---

function fetchRawFile(repoPath) {
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

function installFiles(gitRoot) {
  // 1. Fetch SKILL.md → project root
  info("Fetching SKILL.md...");
  const skillContent = fetchRawFile("SKILL.md");
  if (!skillContent) {
    fail("Failed to fetch SKILL.md from GitHub.");
    process.exit(1);
  }
  fs.writeFileSync(path.join(gitRoot, "SKILL.md"), skillContent, "utf-8");
  success("SKILL.md placed in project root");

  // 2. Create .claude/commands/ and fetch squidsquad-setup.md
  const commandsDir = path.join(gitRoot, ".claude", "commands");
  fs.mkdirSync(commandsDir, { recursive: true });

  // The setup command tells Claude to read SKILL.md and run setup
  const setupCommand = [
    "---",
    "description: Run the SquidSquad setup wizard to configure your project",
    "---",
    "",
    'Read the SKILL.md file in the project root and follow its "Setup Instructions" section exactly.',
    "",
    "The setup wizard will ask for project details, generate the .squidsquad/ folder, create agent configs, boot scripts, and GitHub Issues labels.",
    "",
    "Important: The setup flow will need to fetch files from the SquidSquad repo. Use `gh api` or `curl` to download from https://raw.githubusercontent.com/WallyDoodlez/SquidSquad/main/ as needed.",
    "",
  ].join("\n");

  fs.writeFileSync(path.join(commandsDir, "squidsquad-setup.md"), setupCommand, "utf-8");
  success("Created /squidsquad-setup command");

  // 3. Commit seed files so /squidsquad-setup doesn't abort on dirty worktree
  info("Committing seed files...");
  try {
    execSync("git add SKILL.md .claude/commands/squidsquad-setup.md", {
      cwd: gitRoot, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"],
    });
    execSync('git commit -m "chore: add SquidSquad skill (via npx squidsquad)"', {
      cwd: gitRoot, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"],
    });
    success("Seed files committed");
  } catch (err) {
    fail("Failed to commit seed files. Commit them manually before running /squidsquad-setup.");
    info("  git add SKILL.md .claude/commands/squidsquad-setup.md");
    info('  git commit -m "chore: add SquidSquad skill"');
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

function launchClaude() {
  info("Launching Claude Code with /squidsquad-setup...");
  console.log();

  const child = spawn("claude", ["/squidsquad-setup"], {
    stdio: "inherit",
    shell: true,
  });

  child.on("error", (err) => {
    fail(`Failed to launch Claude: ${err.message}`);
    info("Run manually: claude /squidsquad-setup");
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
    info("  claude /squidsquad-setup");
    console.log();
  }
}

main();
