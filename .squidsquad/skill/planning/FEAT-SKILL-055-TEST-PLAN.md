# FEAT-SKILL-055 Test Plan — Take SquidSquad Public

## Test Cases

### License and Legal

#### TC-1: AGPL-3.0 LICENSE file present and correct
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `LICENSE` file exists in repo root
  2. Read the file and confirm it contains the full AGPL-3.0 text
  3. Verify the opening line references "GNU AFFERO GENERAL PUBLIC LICENSE" and "Version 3"
- **Expected**: LICENSE file exists, contains the complete AGPL-3.0 license text, and is correctly formatted.
- **Verification**:
  ```bash
  test -f LICENSE && echo "PASS" || echo "FAIL"
  grep "GNU AFFERO GENERAL PUBLIC LICENSE" LICENSE && echo "PASS" || echo "FAIL"
  grep "Version 3" LICENSE && echo "PASS" || echo "FAIL"
  ```

#### TC-2: SKILL.md license field in YAML frontmatter
- **Precondition**: SKILL.md exists in repo root
- **Steps**:
  1. Read SKILL.md
  2. Verify YAML frontmatter contains `license: AGPL-3.0`
- **Expected**: The frontmatter includes a license field set to AGPL-3.0.
- **Verification**:
  ```bash
  grep -i "license.*AGPL" SKILL.md && echo "PASS" || echo "FAIL"
  ```

---

### Community Governance Documentation

#### TC-3: CONTRIBUTING.md exists with required sections
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `CONTRIBUTING.md` exists in repo root
  2. Verify it contains a section on reporting bugs
  3. Verify it contains a section on proposing features
  4. Verify it contains a section on contributing sub-skills (the primary contribution path)
  5. Verify it contains a section on submitting PRs
  6. Verify it references the sub-skill format in `references/sub-skills/`
- **Expected**: CONTRIBUTING.md exists and covers bugs, features, sub-skills, and PR process. Sub-skill contribution is highlighted as the main community contribution path.
- **Verification**:
  ```bash
  test -f CONTRIBUTING.md && echo "PASS" || echo "FAIL"
  grep -i "bug" CONTRIBUTING.md > /dev/null && echo "PASS: bugs" || echo "FAIL: bugs"
  grep -i "feature" CONTRIBUTING.md > /dev/null && echo "PASS: features" || echo "FAIL: features"
  grep -i "sub-skill" CONTRIBUTING.md > /dev/null && echo "PASS: sub-skills" || echo "FAIL: sub-skills"
  grep -i "pull request\|PR" CONTRIBUTING.md > /dev/null && echo "PASS: PRs" || echo "FAIL: PRs"
  ```

#### TC-4: CODE_OF_CONDUCT.md exists and uses Contributor Covenant
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `CODE_OF_CONDUCT.md` exists in repo root
  2. Verify it references the Contributor Covenant
  3. Verify it includes enforcement information
- **Expected**: CODE_OF_CONDUCT.md exists, is based on the Contributor Covenant, and specifies enforcement.
- **Verification**:
  ```bash
  test -f CODE_OF_CONDUCT.md && echo "PASS" || echo "FAIL"
  grep -i "Contributor Covenant" CODE_OF_CONDUCT.md && echo "PASS" || echo "FAIL"
  grep -i "enforcement\|enforce" CODE_OF_CONDUCT.md > /dev/null && echo "PASS" || echo "FAIL"
  ```

---

### GitHub Issues Templates

#### TC-5: Bug report template exists
- **Precondition**: `.github/ISSUE_TEMPLATE/` directory exists
- **Steps**:
  1. Verify a bug report template file exists in `.github/ISSUE_TEMPLATE/`
  2. Verify it contains fields for: SquidSquad version, OS, steps to reproduce, expected/actual behavior
- **Expected**: Bug report template exists with YAML frontmatter (name, about, labels) and body fields for version, OS, reproduction steps, and expected/actual behavior.
- **Verification**:
  ```bash
  ls .github/ISSUE_TEMPLATE/bug* && echo "PASS" || echo "FAIL"
  grep -i "reproduce" .github/ISSUE_TEMPLATE/bug* > /dev/null && echo "PASS" || echo "FAIL"
  grep -i "version" .github/ISSUE_TEMPLATE/bug* > /dev/null && echo "PASS" || echo "FAIL"
  ```

#### TC-6: Feature request template exists
- **Precondition**: `.github/ISSUE_TEMPLATE/` directory exists
- **Steps**:
  1. Verify a feature request template file exists in `.github/ISSUE_TEMPLATE/`
  2. Verify it contains fields for: problem description, proposed solution, alternatives considered
- **Expected**: Feature request template exists with appropriate YAML frontmatter and body fields.
- **Verification**:
  ```bash
  ls .github/ISSUE_TEMPLATE/feature* && echo "PASS" || echo "FAIL"
  grep -i "solution\|describe" .github/ISSUE_TEMPLATE/feature* > /dev/null && echo "PASS" || echo "FAIL"
  ```

#### TC-7: Sub-skill proposal template exists
- **Precondition**: `.github/ISSUE_TEMPLATE/` directory exists
- **Steps**:
  1. Verify a sub-skill proposal template file exists in `.github/ISSUE_TEMPLATE/`
  2. Verify it contains fields for: sub-skill name, description, which roles benefit, composition point
- **Expected**: Sub-skill proposal template exists with fields specific to the sub-skill contribution model.
- **Verification**:
  ```bash
  ls .github/ISSUE_TEMPLATE/sub_skill* .github/ISSUE_TEMPLATE/sub-skill* 2>/dev/null && echo "PASS" || echo "FAIL"
  grep -i "composition\|role" .github/ISSUE_TEMPLATE/sub*skill* > /dev/null && echo "PASS" || echo "FAIL"
  ```

---

### Security Audit

#### TC-8: No hardcoded local paths in tracked files
- **Precondition**: All tracked files accessible via git
- **Steps**:
  1. Search all tracked files for Windows-style absolute paths (e.g., `D:\Dev`, `C:\Users`)
  2. Search for Unix-style absolute paths to home directories (e.g., `/home/`, `/Users/`)
  3. Exclude LICENSE, .git/, and binary files from the search
- **Expected**: Zero matches for hardcoded local paths in any tracked file. Paths like `D:\Dev\Dev\SquidSquad` must not appear.
- **Verification**:
  ```bash
  git ls-files | xargs grep -l "D:\\\\Dev\|C:\\\\Users\|/home/\|/Users/" 2>/dev/null | grep -v ".git" && echo "FAIL: hardcoded paths found" || echo "PASS"
  ```

#### TC-9: No API keys or secrets in tracked files
- **Precondition**: All tracked files accessible via git
- **Steps**:
  1. Search all tracked files for common secret patterns: `sk-`, `api_key`, `api-key`, `secret`, `token`, `password`, `credential`
  2. Exclude false positives (e.g., documentation about security concepts, LICENSE file)
  3. Review any matches manually
- **Expected**: No actual secrets, API keys, or tokens in any tracked file. Matches should only be documentation references (e.g., "no API keys needed").
- **Verification**:
  ```bash
  git ls-files | xargs grep -il "sk-[a-zA-Z0-9]\{20,\}\|api_key.*=\|PRIVATE.KEY\|BEGIN RSA" 2>/dev/null && echo "FAIL: potential secrets" || echo "PASS"
  ```

#### TC-10: No personal information beyond git commits
- **Precondition**: All tracked files accessible
- **Steps**:
  1. Search tracked files for email addresses (outside of LICENSE, CODE_OF_CONDUCT, and git metadata)
  2. Search for phone numbers or other PII patterns
- **Expected**: No personal email addresses, phone numbers, or PII in tracked file content. Git commit metadata (author name/email) is acceptable and expected.
- **Verification**:
  ```bash
  git ls-files | xargs grep -l "[a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]*\.[a-zA-Z]" 2>/dev/null | grep -v "LICENSE\|CODE_OF_CONDUCT\|CONTRIBUTING" && echo "REVIEW matches" || echo "PASS"
  ```

---

### .gitignore Coverage

#### TC-11: .gitignore covers .obsidian/
- **Precondition**: `.gitignore` exists in repo root
- **Steps**:
  1. Read `.gitignore`
  2. Verify `.obsidian/` or `.obsidian` is listed
- **Expected**: `.obsidian/` is covered by a gitignore rule.
- **Verification**:
  ```bash
  grep -i "obsidian" .gitignore && echo "PASS" || echo "FAIL"
  ```

#### TC-12: .gitignore covers .local-config
- **Precondition**: `.gitignore` exists
- **Steps**:
  1. Verify `.local-config` or a pattern matching it is in `.gitignore`
- **Expected**: `.local-config` files are excluded from tracking.
- **Verification**:
  ```bash
  grep "local-config" .gitignore && echo "PASS" || echo "FAIL"
  ```

#### TC-13: .gitignore covers current-state files
- **Precondition**: `.gitignore` exists
- **Steps**:
  1. Verify `current-state` or a pattern matching it is in `.gitignore`
- **Expected**: Agent `current-state` files (used for status bar) are excluded from tracking.
- **Verification**:
  ```bash
  grep "current-state" .gitignore && echo "PASS" || echo "FAIL"
  ```

#### TC-14: .gitignore covers .active-role
- **Precondition**: `.gitignore` exists
- **Steps**:
  1. Verify `.active-role` or a pattern matching it is in `.gitignore`
- **Expected**: `.active-role` files are excluded from tracking.
- **Verification**:
  ```bash
  grep "active-role" .gitignore && echo "PASS" || echo "FAIL"
  ```

#### TC-15: .gitignore covers OS/shell artifacts
- **Precondition**: `.gitignore` exists
- **Steps**:
  1. Verify `*.stackdump` or similar OS artifact patterns are in `.gitignore`
- **Expected**: Windows crash dumps and similar OS artifacts are excluded.
- **Verification**:
  ```bash
  grep "stackdump" .gitignore && echo "PASS" || echo "FAIL"
  ```

---

### Dogfooding Proof — .squidsquad/ Tracked

#### TC-16: .squidsquad/ directory is tracked in git
- **Precondition**: Repo is the SquidSquad repo itself (dogfooding)
- **Steps**:
  1. Verify `.squidsquad/` is NOT fully gitignored in this repo
  2. Verify git tracks files within `.squidsquad/`
  3. Verify tracker files (bugs, features, iterations) are present in git history
- **Expected**: `.squidsquad/` remains tracked as dogfooding proof. The git history shows SquidSquad being used to build itself.
- **Verification**:
  ```bash
  git ls-files .squidsquad/ | head -5 && echo "PASS: .squidsquad tracked" || echo "FAIL"
  ```

#### TC-17: .squidsquad/config.md is tracked
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `.squidsquad/config.md` exists and is tracked by git
- **Expected**: config.md is tracked, showing the project's active configuration.
- **Verification**:
  ```bash
  git ls-files .squidsquad/config.md | grep -q "config.md" && echo "PASS" || echo "FAIL"
  ```

---

### references/ Directory Tracked

#### TC-18: references/ directory is tracked and populated
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `references/` directory exists
  2. Verify it contains sub-skill source files in `references/sub-skills/`
  3. Verify it contains vault templates, hints, statusline source
  4. Verify these files are tracked by git
- **Expected**: `references/` is tracked and contains the skill's source of truth (sub-skills, templates, hints, scripts).
- **Verification**:
  ```bash
  test -d references/ && echo "PASS: dir exists" || echo "FAIL"
  test -d references/sub-skills/ && echo "PASS: sub-skills" || echo "FAIL"
  git ls-files references/ | wc -l | xargs -I{} test {} -gt 0 && echo "PASS: files tracked" || echo "FAIL"
  ```

---

### Setup Flow

#### TC-19: Setup flow works on clean clone (conceptual)
- **Precondition**: A fresh clone of the repo with no prior `.squidsquad/` data (or a separate test project)
- **Steps**:
  1. Clone the repo (or create a new project and install SquidSquad as a skill)
  2. Run the setup command ("Set up SquidSquad")
  3. Verify `.squidsquad/` directory is created with config.md
  4. Verify agent CLAUDE.md files are generated for each role
  5. Verify boot scripts are generated
  6. Verify tracker directories (bugs/, features/) are created
- **Expected**: Setup completes without errors. All expected directories and files are created. The project is ready for agents to boot.
- **Verification**:
  ```bash
  # After setup on a test project:
  test -f .squidsquad/config.md && echo "PASS: config" || echo "FAIL"
  test -f .squidsquad/skill/CLAUDE.md && echo "PASS: skill agent" || echo "FAIL"
  test -f .squidsquad/pm/CLAUDE.md && echo "PASS: pm agent" || echo "FAIL"
  test -d .squidsquad/skill/bugs && echo "PASS: bug tracker" || echo "FAIL"
  test -d .squidsquad/skill/features && echo "PASS: feature tracker" || echo "FAIL"
  ```

#### TC-20: Setup flow adds .squidsquad/ to user project's .gitignore
- **Precondition**: Fresh project with no `.gitignore` or an existing `.gitignore`
- **Steps**:
  1. Run setup
  2. Check `.gitignore` for `.squidsquad/` entry (or relevant patterns)
- **Expected**: Setup either creates or updates `.gitignore` to exclude runtime/generated `.squidsquad/` data from the user's project. (Note: in the SquidSquad repo itself, this is overridden for dogfooding.)
- **Verification**:
  ```bash
  grep "squidsquad" .gitignore && echo "PASS" || echo "FAIL"
  ```

---

### Demo Project

#### TC-21: Demo project exists
- **Precondition**: Demo project has been created (separate repo or directory)
- **Steps**:
  1. Verify the demo project repository/directory exists
  2. Verify it contains a README explaining what it is
  3. Verify it has SquidSquad installed as a skill
- **Expected**: A purpose-built demo project exists that showcases SquidSquad in action. It has a clear README and SquidSquad is installed.
- **Verification**:
  ```bash
  # Location depends on dev discretion — verify the chosen location:
  # e.g., test -d ../squidsquad-demo/ or check a separate GitHub repo
  echo "Manual verification: confirm demo project exists and has SquidSquad installed"
  ```

#### TC-22: Demo project setup completes without errors
- **Precondition**: Demo project exists
- **Steps**:
  1. Run SquidSquad setup on the demo project
  2. Verify all agents can boot
  3. Verify at least one cycle completes (PM check-in, dev triage)
- **Expected**: The demo project works end-to-end with SquidSquad. Agents boot, coordinate, and produce meaningful output.
- **Verification**:
  ```bash
  # After running agents on demo project:
  test -d .squidsquad/skill/iterations/ && echo "PASS: iterations exist" || echo "FAIL"
  ls .squidsquad/skill/iterations/iter-*.md 2>/dev/null | head -1 && echo "PASS: at least one cycle" || echo "FAIL"
  ```

---

### Pre-Launch Checklist

#### TC-23: bash.exe.stackdump removed from tracking
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `bash.exe.stackdump` is NOT tracked by git
  2. Verify it does not appear in `git ls-files`
- **Expected**: The Windows crash artifact is removed from git tracking.
- **Verification**:
  ```bash
  git ls-files bash.exe.stackdump | grep -q "stackdump" && echo "FAIL: still tracked" || echo "PASS"
  ```

#### TC-24: No internal-only references that confuse public users
- **Precondition**: All tracked files accessible
- **Steps**:
  1. Search for references to internal tooling, private repos, or internal URLs
  2. Search for TODO/FIXME/HACK comments that reference internal context
  3. Verify all links in README and CONTRIBUTING.md resolve (no broken internal links)
- **Expected**: No references that would confuse a public user. All links point to publicly accessible resources.
- **Verification**:
  ```bash
  git ls-files | xargs grep -l "internal\|private.*repo\|FIXME.*internal" 2>/dev/null | grep -v ".squidsquad/" && echo "REVIEW matches" || echo "PASS"
  ```

#### TC-25: CHANGELOG.md exists and is current
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `CHANGELOG.md` exists
  2. Verify it contains version entries
  3. Verify the most recent entry matches or is close to the current version
- **Expected**: CHANGELOG.md exists with a meaningful version history.
- **Verification**:
  ```bash
  test -f CHANGELOG.md && echo "PASS" || echo "FAIL"
  grep -c "^## " CHANGELOG.md | xargs -I{} test {} -gt 0 && echo "PASS: has versions" || echo "FAIL"
  ```

#### TC-26: CLAUDE.md auto-boot configuration is present
- **Precondition**: Repo root accessible
- **Steps**:
  1. Verify `CLAUDE.md` exists in repo root
  2. Verify it contains the `SQUIDSQUAD_ROLE=` auto-boot instructions
- **Expected**: CLAUDE.md exists and provides auto-boot configuration for developing SquidSquad itself.
- **Verification**:
  ```bash
  test -f CLAUDE.md && echo "PASS" || echo "FAIL"
  grep "SQUIDSQUAD_ROLE" CLAUDE.md && echo "PASS" || echo "FAIL"
  ```

---

## Smoke Tests

- [ ] `LICENSE` file exists in repo root
- [ ] `LICENSE` contains "GNU AFFERO GENERAL PUBLIC LICENSE"
- [ ] `CONTRIBUTING.md` exists in repo root
- [ ] `CODE_OF_CONDUCT.md` exists in repo root
- [ ] `.github/ISSUE_TEMPLATE/` directory exists with 3 templates (bug, feature, sub-skill)
- [ ] No `sk-` prefixed API keys in any tracked file
- [ ] No `D:\Dev` or `C:\Users` hardcoded paths in tracked files (outside .squidsquad/ planning artifacts)
- [ ] `.gitignore` covers `.obsidian/`, `.local-config`, `current-state`, `.active-role`, `*.stackdump`
- [ ] `.squidsquad/` is tracked in git (dogfooding proof)
- [ ] `references/` is tracked in git with sub-skills and templates
- [ ] `SKILL.md` has `license: AGPL-3.0` in frontmatter
- [ ] `CHANGELOG.md` exists and has version entries
- [ ] `bash.exe.stackdump` is NOT tracked
- [ ] Demo project exists and SquidSquad setup completes on it
- [ ] At least one agent cycle completes on the demo project

---

## Regression Risks

- **Dogfooding data exposed**: The `.squidsquad/` directory is intentionally kept for dogfooding proof. Risk: planning artifacts or tracker data contain embarrassing, incorrect, or confusing content for public viewers. Mitigation: review all tracked `.squidsquad/` content for anything inappropriate.
- **Hardcoded paths in planning artifacts**: Files like `FEAT-SKILL-055-CONTEXT.md` or research docs may reference `D:\Dev\Dev\SquidSquad`. Since `.squidsquad/` is tracked for dogfooding, these paths will be visible publicly. Mitigation: accept as authentic development artifacts or scrub paths from planning files.
- **Setup flow assumes clean state**: If the public repo ships with a populated `.squidsquad/`, new users running setup may encounter conflicts with existing config or tracker files. Mitigation: setup flow should detect existing config and offer upgrade vs fresh install.
- **Missing .gitignore entries break user projects**: If `.gitignore` does not cover all generated runtime files, user projects will have noisy `git status` output with untracked `.squidsquad/` ephemeral files. Mitigation: comprehensive .gitignore testing.
- **License badge in README depends on FEAT-SKILL-056**: The README rewrite is a separate feature. If FEAT-SKILL-055 ships before 056, the license badge may not be in the README yet. Mitigation: coordinate with FEAT-SKILL-056 or add badge as part of 055.
- **Demo project technology choice**: If the demo project uses a technology that requires specific setup (Node.js, Python, etc.), it narrows the audience who can easily try it. Mitigation: choose a minimal technology stack or provide clear setup instructions.
- **Security audit false negatives**: Grep-based secret scanning may miss obfuscated secrets or secrets in unusual formats. Mitigation: combine automated scanning with manual review of all tracked files.
