# FEAT-SKILL-063 Test Plan — Self-Improvement Loop: Agents Suggest Improvements During Quiet Cycles

## Test Cases

### TC-1: Config toggle exists and defaults to enabled
- **Precondition**: Feature implementation complete, config.md updated
- **Steps**: Read `.squidsquad/config.md`; locate the Improvement Scanning section
- **Expected**: An `Improvement Scanning: yes` field exists. The field accepts `yes` or `no` values.
- **Verification**: `grep -i "Improvement Scanning" .squidsquad/config.md` returns a line with value `yes`

### TC-2: 3 consecutive quiet cycles trigger scanning
- **Precondition**: Config toggle enabled; agent template updated with improvement scan step
- **Steps**: Simulate an agent running 3 consecutive quiet cycles (no bugs fixed, no features progressed). On the 4th quiet cycle, check whether the improvement scan step activates.
- **Expected**: Quiet cycle counter increments each quiet cycle. After 3 consecutive quiet cycles, the next quiet cycle triggers the improvement scan step. Counter resets when real work occurs.
- **Verification**: Agent output shows scanning activity only after the 3rd consecutive quiet cycle; if a non-quiet cycle interrupts, the counter resets to 0

### TC-3: Counter resets after a scan completes
- **Precondition**: Agent has triggered an improvement scan (3 quiet cycles reached)
- **Steps**: After a scan completes (regardless of whether items were filed), observe the next quiet cycles
- **Expected**: The quiet cycle counter resets to 0 after each scan. The agent must accumulate 3 more quiet cycles before the next scan triggers.
- **Verification**: Scan does not trigger on the cycle immediately following a completed scan; 3 more quiet cycles are required

### TC-4: Counter resets when real work occurs
- **Precondition**: Agent has accumulated 1-2 quiet cycles toward the threshold
- **Steps**: Simulate the agent performing real work (fixing a bug or progressing a feature) mid-accumulation
- **Expected**: The quiet cycle counter resets to 0 when any real work happens
- **Verification**: After real work, scanning does not trigger until 3 fresh consecutive quiet cycles pass

### TC-5: Scanning disabled via config toggle
- **Precondition**: Config set to `Improvement Scanning: no`
- **Steps**: Run the agent through 5+ consecutive quiet cycles
- **Expected**: No improvement scanning occurs regardless of quiet cycle count. Agent behaves as it did before this feature.
- **Verification**: Agent output contains no scanning activity; no scan history files are created

### TC-6: Common sub-skill file exists under FEAT-SKILL-030 architecture
- **Precondition**: Feature implementation complete
- **Steps**: Check for the common improvement scan sub-skill file
- **Expected**: A shared sub-skill file exists at `references/sub-skills/common/improvement-scan.md` containing: quiet cycle counter logic, scan trigger threshold check, scan history management, rate limiting, file selection algorithm, and filing protocol
- **Verification**: File exists and contains sections covering all 6 components listed above

### TC-7: Dev agent scan strategy targets code quality
- **Precondition**: Common sub-skill exists; dev agent template updated
- **Steps**: Read the dev agent's scan configuration or inline strategy
- **Expected**: Dev agent scans for code quality issues: dead code, missing error handling, code complexity, code duplication, outdated patterns, security issues, inconsistent naming
- **Verification**: Dev scan checklist or strategy section references code-quality-specific concerns distinct from other roles

### TC-8: QA agent scan strategy targets test coverage
- **Precondition**: Common sub-skill exists; QA agent template updated
- **Steps**: Read the QA agent's scan configuration or inline strategy
- **Expected**: QA agent scans for test coverage gaps: source files without tests, untested public functions, missing edge case tests, flaky test indicators
- **Verification**: QA scan checklist references test-coverage-specific concerns distinct from other roles

### TC-9: Designer agent scan strategy targets design consistency
- **Precondition**: Common sub-skill exists; designer agent template updated
- **Steps**: Read the designer agent's scan configuration or inline strategy
- **Expected**: Designer agent scans for design consistency: hardcoded values vs tokens, missing component states, accessibility gaps, inconsistent patterns
- **Verification**: Designer scan checklist references design-specific concerns distinct from other roles

### TC-10: DM agent scan strategy targets documentation
- **Precondition**: Common sub-skill exists; DM agent template updated
- **Steps**: Read the DM agent's scan configuration or inline strategy
- **Expected**: DM agent scans for documentation issues: outdated README content, missing API docs, stale references, missing changelog entries
- **Verification**: DM scan checklist references documentation-specific concerns distinct from other roles

### TC-11: PM agent scan strategy targets process
- **Precondition**: Common sub-skill exists; PM agent template updated
- **Steps**: Read the PM agent's scan configuration or inline strategy
- **Expected**: PM agent scans for process issues: stale tracker items, priority imbalances, vaguely specified features, workflow bottlenecks
- **Verification**: PM scan checklist references process-specific concerns distinct from other roles

### TC-12: Incremental scanning reads 3-5 files per cycle
- **Precondition**: Scan triggered on an agent
- **Steps**: Observe or read the scan instructions for file selection
- **Expected**: Each scan cycle reads 3-5 target project files (not the entire codebase). File selection prioritizes: recently changed files, then never-scanned files, then oldest-scanned files.
- **Verification**: Scan instructions specify 3-5 files per cycle with a priority ordering; scan history confirms different files are selected across consecutive scans

### TC-13: Scans target different files each cycle
- **Precondition**: Agent has triggered multiple scans across several quiet periods
- **Steps**: Read the scan history file after 2+ scan cycles
- **Expected**: Each scan cycle selects different files than the previous cycle. Files already scanned are deprioritized in favor of unscanned or stale-scanned files.
- **Verification**: Scan history shows distinct file sets across scan cycles; no file appears in consecutive scans unless the entire project has been covered

### TC-14: Findings reported to PM, not filed directly
- **Precondition**: Agent finds an improvement during a scan
- **Steps**: Check how the agent reports the finding
- **Expected**: The scanning agent does NOT file directly to any tracker. Instead, it reports findings to the PM via Discussion entries. PM reviews and files as features or bugs through the normal pipeline.
- **Verification**: No direct tracker entries created by the scanning agent; PM's tracker or Discussion section receives the finding; the finding includes `Reported By: [role]-lead (improvement-scan)` tag

### TC-15: Default Low priority for scan-initiated items
- **Precondition**: PM has received a scan finding and filed it
- **Steps**: Read the filed tracker item
- **Expected**: Items originating from improvement scans are filed with Low priority by default. Human can manually bump priority if the finding is valuable.
- **Verification**: Filed items from scans have `Priority: Low` unless human has explicitly changed it

### TC-16: Per-agent rate limit of 2 items per scan
- **Precondition**: Agent performs a scan and finds more than 2 issues
- **Steps**: Observe how many findings the agent reports in a single scan
- **Expected**: Maximum 2 items reported per scan cycle, even if the agent identifies more issues. The agent picks the 2 highest-impact findings and logs the rest in scan history for future consideration.
- **Verification**: No scan cycle produces more than 2 reported findings; additional findings appear in scan history as noted-but-not-filed

### TC-17: Scan history file created and maintained per agent
- **Precondition**: Agent has performed at least one scan
- **Steps**: Check for the scan history file at the expected location
- **Expected**: A scan history file exists (e.g., `.squidsquad/[role]/scan-history.md`) tracking: scanned files with timestamps, filed items with IDs, and rejected items marked as rejected
- **Verification**: File exists after first scan; contains entries for scanned files and any filed/rejected items

### TC-18: Scan history prevents duplicate filings
- **Precondition**: Agent has previously reported a finding for a specific file and issue
- **Steps**: Trigger another scan that covers the same file
- **Expected**: The agent checks scan history before reporting. If the same file + similar issue was already reported (whether pending, approved, or rejected), it is not reported again.
- **Verification**: No duplicate findings appear in PM's Discussion after scanning the same file twice; scan history shows the dedup check occurred

### TC-19: Rejected items tracked and never refiled
- **Precondition**: A scan-originated item was rejected by the human
- **Steps**: Mark a scan item as rejected; trigger subsequent scans covering the same file
- **Expected**: Rejected items are recorded in scan history with `rejected` status. The agent never refiles the same finding after rejection.
- **Verification**: Scan history shows `rejected` status for the item; subsequent scans of the same file do not produce the same finding

### TC-20: New 'scanning' status bar phase displayed
- **Precondition**: Agent is performing an improvement scan
- **Steps**: Check the agent's `current-state` file during a scan
- **Expected**: The status bar phase shows `scanning|` with a descriptive message (e.g., `scanning|Scanning src/components...`) during improvement scans
- **Verification**: `cat .squidsquad/[role]/current-state` during a scan shows the `scanning` phase prefix

### TC-21: Scan excludes internal SquidSquad files
- **Precondition**: Scan triggered
- **Steps**: Review scan file selection logic and scan history
- **Expected**: The `.squidsquad/` directory is never included in scan targets. Only target project files are scanned. Other standard exclusions apply: `node_modules/`, `vendor/`, `.git/`, build output, generated files, binaries.
- **Verification**: Scan history never contains files from `.squidsquad/`, `node_modules/`, or other excluded paths

### TC-22: SOUL.md self-improvement lens defines scan focus
- **Precondition**: Soul files exist with self-improvement lens dimension; scan sub-skill integrated
- **Steps**: Compare each role's scan behavior against its SOUL.md self-improvement lens
- **Expected**: The scan strategy for each role aligns with the self-improvement lens defined in its soul file. The lens shapes what the agent looks for (QA: coverage gaps; Dev: code quality; DM: documentation gaps; PM: process bottlenecks; Designer: UX friction).
- **Verification**: Each role's scan checklist or strategy references or is consistent with the corresponding SOUL.md self-improvement lens content

### TC-23: Hybrid auto-detect for project type
- **Precondition**: Scan triggered on a project with identifiable stack (e.g., package.json for Node, Cargo.toml for Rust)
- **Steps**: Observe how the agent determines what kind of project it is scanning
- **Expected**: The agent reads config.md project metadata and scans file extensions, package files, and directory structure to infer the project stack. No new config field is required for project type.
- **Verification**: Agent scan output or scan history reflects awareness of the project type (e.g., scanning .ts files for a TypeScript project, .py files for Python)

### TC-24: Scan cycle that files items is no longer "quiet"
- **Precondition**: Improvement scan triggers and produces findings
- **Steps**: Observe whether the agent logs and commits after a scan that reported items
- **Expected**: If the improvement scan reported findings to PM, the cycle is no longer quiet. The agent proceeds to log the iteration and commit/push changes (scan history updates, Discussion entries).
- **Verification**: Iteration log and git commit occur after a scan that produced findings; no iteration log if scan found nothing

### TC-25: Agent does not act on its own scan findings
- **Precondition**: Agent has reported findings to PM during a scan
- **Steps**: Observe the agent's behavior for the remainder of that cycle and subsequent cycles
- **Expected**: The scanning agent does not pick up or implement its own scan findings in the same cycle or any cycle before PM files and human approves. Findings require human approval through the normal pipeline.
- **Verification**: No implementation work begins on scan findings until they appear as Approved items in the relevant tracker

### TC-26: Manifest updated with improvement-scan sub-skill
- **Precondition**: Common sub-skill created
- **Steps**: Read `references/sub-skills/manifest.md`
- **Expected**: The manifest lists `common/improvement-scan` in its file inventory and documents it as a shared sub-skill included by all role compositions
- **Verification**: `grep "improvement-scan" references/sub-skills/manifest.md` returns at least 1 match; all role composition entries include the sub-skill

### TC-27: Upgrade path is non-destructive
- **Precondition**: Existing SquidSquad installation without improvement scanning
- **Steps**: Review the upgrade path for adding the feature to an existing install
- **Expected**: Config addition (`Improvement Scanning: yes`) is additive. No existing config fields are removed or renamed. Scan history files are created on first scan, not at install time. Templates regenerated with the new sub-skill. Existing tracker items and iteration logs are untouched.
- **Verification**: Config diff shows only additions; no data migration required; existing files unchanged

### TC-28: PM does not auto-approve scan items
- **Precondition**: Agent has reported findings to PM
- **Steps**: Observe PM's handling of scan-originated items
- **Expected**: PM files scan items as Pending (features) or Open (bugs) but does NOT auto-approve them. Human must explicitly approve before any agent acts on the item.
- **Verification**: All scan-originated items remain in Pending/Open status until human explicitly changes them; no scan item appears as Approved without human action

## Smoke Tests
- [ ] Read the common sub-skill file (`references/sub-skills/common/improvement-scan.md`) and confirm it parses as valid markdown
- [ ] Verify config.md contains the `Improvement Scanning` field with a `yes`/`no` value
- [ ] Confirm at least one role template (e.g., dev) includes the improvement scan step between work steps and logging
- [ ] Check that the `scanning` phase is used in status bar writes during scan execution
- [ ] Verify scan history file format includes columns for file path, timestamp, and findings
- [ ] Confirm the manifest lists `common/improvement-scan` as a shared sub-skill

## Regression Risks
- **Template bloat**: Adding the improvement scan sub-skill to all 5+ role templates increases composed template size. Verify total template size remains within context budget after inclusion.
- **Quiet cycle behavior change**: Existing quiet cycle logic must still work correctly when scanning is disabled. The quiet-cycle-counter must not interfere with the existing designer quiet cycle counter (FEAT-SKILL-059 self-improvement lens).
- **Filing pipeline overload**: If multiple agents scan simultaneously and all report to PM, PM could receive a burst of findings. The per-agent rate limit (2 items/scan) mitigates this, but verify PM handles concurrent scan reports gracefully.
- **Scan history file growth**: Over long periods, scan history files could grow large. Verify there is a mechanism (or note the need for one) to prune old scan history entries.
- **Counter persistence**: The quiet cycle counter must persist across context window resets. Verify it is stored in working state or a durable file, not just in-memory.
- **Cycle time extension**: Improvement scans read 3-5 project files, which consumes tokens and time. Verify scanning does not push cycle duration beyond reasonable bounds for the loop interval.
- **Cross-role scan overlap**: Multiple roles might flag the same file for different reasons (e.g., dev flags code quality, QA flags missing tests for the same module). This is acceptable but verify PM can handle overlapping findings without confusion.
