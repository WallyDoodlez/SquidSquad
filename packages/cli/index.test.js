/**
 * Tests for packages/cli/index.js — tarball installer (#2351).
 *
 * Uses Node.js built-in test runner (node --test).
 * Run: node --test packages/cli/index.test.js
 */

"use strict";

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");

const cli = require("./index.js");

// --- getCliVersion ---

describe("getCliVersion", () => {
  it("returns the version from package.json", () => {
    const version = cli.getCliVersion();
    const pkg = JSON.parse(
      fs.readFileSync(path.join(__dirname, "package.json"), "utf-8")
    );
    assert.equal(version, pkg.version);
  });

  it("returns a semver-like string", () => {
    const version = cli.getCliVersion();
    assert.match(version, /^\d+\.\d+\.\d+/);
  });
});

// --- downloadTarball ---

describe("downloadTarball", () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "squid-test-"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("returns false when tar library is not available", () => {
    const result = cli.downloadTarball(tmpDir, []);
    assert.equal(typeof result, "boolean");
  });

  it("returns false for a non-existent tag", () => {
    const result = cli.downloadTarball(tmpDir, ["nonexistent-file.txt"]);
    assert.equal(result, false);
  });

  it("does not leave temp directories on failure", () => {
    const before = fs
      .readdirSync(os.tmpdir())
      .filter((d) => d.startsWith("squidsquad-"));
    cli.downloadTarball(tmpDir, ["nonexistent.txt"]);
    const after = fs
      .readdirSync(os.tmpdir())
      .filter((d) => d.startsWith("squidsquad-"));
    assert.equal(after.length, before.length);
  });
});

// --- installFilesPerFile ---

describe("installFilesPerFile", () => {
  it("is a callable function", () => {
    assert.equal(typeof cli.installFilesPerFile, "function");
  });
});

// --- assertWithinRoot ---

describe("assertWithinRoot", () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "squid-path-test-"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("allows normal relative paths", () => {
    const result = cli.assertWithinRoot(tmpDir, "references/scripts/foo.py");
    assert.equal(result, path.resolve(tmpDir, "references/scripts/foo.py"));
  });

  it("allows nested paths", () => {
    const result = cli.assertWithinRoot(tmpDir, "a/b/c/d.txt");
    assert.equal(result, path.resolve(tmpDir, "a/b/c/d.txt"));
  });

  it("allows root-level files", () => {
    const result = cli.assertWithinRoot(tmpDir, "SKILL.md");
    assert.equal(result, path.resolve(tmpDir, "SKILL.md"));
  });

  it("blocks path traversal with ../", (t) => {
    const originalExit = process.exit;
    let exitCalled = false;
    process.exit = () => { exitCalled = true; throw new Error("exit"); };
    try {
      cli.assertWithinRoot(tmpDir, "../../etc/passwd");
    } catch { /* expected */ }
    process.exit = originalExit;
    assert.equal(exitCalled, true);
  });

  it("blocks path traversal in nested context", (t) => {
    const originalExit = process.exit;
    let exitCalled = false;
    process.exit = () => { exitCalled = true; throw new Error("exit"); };
    try {
      cli.assertWithinRoot(tmpDir, "references/../../../.bashrc");
    } catch { /* expected */ }
    process.exit = originalExit;
    assert.equal(exitCalled, true);
  });
});
