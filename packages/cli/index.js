#!/usr/bin/env node

"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const REPO_URL = "https://github.com/WallyDoodlez/SquidSquad.git";
const SKILL_DIR_NAME = "squidsquad";

// --- Output helpers ---

function info(msg) {
  console.log(`  ${msg}`);
}

function success(msg) {
  console.log(`  \x1b[32m✓\x1b[0m ${msg}`);
}

function fail(msg) {
  console.error(`  \x1b[31m✗\x1b[0m ${msg}`);
}

function banner() {
  console.log();
  console.log("      \\u2597\\u2584\\u2596");
  console.log("     \\u259F\\u2588 \\u2588\\u2599");
  console.log("    \\u2590\\u2588\\u2022 \\u2022\\u2588\\u258C");
  console.log("   \\u2588\\u2588\\u2588\\u2588\\u2588\\u2588\\u2588");
  console.log("   \\u2590\\u2588\\u2588\\u2588\\u2588\\u2588\\u258C");
  console.log("    \\u2590\\u258C\\u2590\\u258C\\u2590\\u258C");
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
  // Try python3 first, then python (Windows often only has python)
  for (const bin of ["python3", "python"]) {
    const out = tryExec(`${bin} --version`);
    if (out) {
      const match = out.match(/Python (\d+)\.(\d+)/);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (major === 3 && minor >= 8) {
          success(`${out}`);
          return;
        }
        if (major > 3) {
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

  // Check authentication
  const authResult = tryExec("gh auth status");
  if (!authResult) {
    fail("GitHub CLI is not authenticated.");
    info("Run `gh auth login` first.");
    process.exit(1);
  }
  success("GitHub CLI authenticated");
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

// --- Skill installation ---

function getSkillsDir() {
  const home = os.homedir();
  return path.join(home, ".claude", "skills", SKILL_DIR_NAME);
}

function installSkill() {
  const skillsDir = getSkillsDir();
  const parentDir = path.dirname(skillsDir);

  // Create parent directories if needed
  fs.mkdirSync(parentDir, { recursive: true });

  if (fs.existsSync(skillsDir)) {
    // Update existing installation
    info("Updating existing SquidSquad skill...");
    try {
      execSync("git pull --ff-only", {
        cwd: skillsDir,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      success("SquidSquad skill updated");
    } catch {
      // If pull fails, re-clone
      info("Pull failed — re-cloning...");
      fs.rmSync(skillsDir, { recursive: true, force: true });
      execSync(`git clone --depth 1 ${REPO_URL} "${skillsDir}"`, {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      success("SquidSquad skill installed (fresh clone)");
    }
  } else {
    info("Cloning SquidSquad skill...");
    execSync(`git clone --depth 1 ${REPO_URL} "${skillsDir}"`, {
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    success("SquidSquad skill installed");
  }
}

// --- Main ---

function main() {
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
  info("All prerequisites met. Installing skill...");
  console.log();

  try {
    installSkill();
  } catch (err) {
    console.log();
    fail("Skill installation failed.");
    info(err.message || String(err));
    process.exit(1);
  }

  console.log();
  console.log("  \x1b[32m\x1b[1mSquidSquad is ready!\x1b[0m");
  console.log();
  info("Next steps:");
  console.log();
  info("  1. Start a new Claude Code session (or run /clear)");
  info("  2. Run /squidsquad-setup to configure your project");
  console.log();
  info("The setup wizard will ask for your project name, dev roles,");
  info("test commands, and loop interval — then generate everything.");
  console.log();
}

main();
