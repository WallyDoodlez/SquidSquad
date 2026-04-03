# FEAT-SKILL-059 Test Plan — SOUL.md: Agent Personality and Operational Philosophy

## Test Cases

### TC-1: Soul files exist for all 5 roles
- **Precondition**: Feature implementation complete
- **Steps**: List files in `references/sub-skills/souls/`
- **Expected**: Exactly 5 files exist: `pm.md`, `qa.md`, `dev.md`, `designer.md`, `dm.md`
- **Verification**: `ls references/sub-skills/souls/` returns all 5 files, no extras

### TC-2: Each soul contains all 7 dimensions
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file and check for section headings or clearly delineated dimensions
- **Expected**: Every soul file covers: professional identity, quality bar, decision-making style, communication style, boundaries, collaboration posture, self-improvement lens
- **Verification**: `grep -ci "identity\|quality bar\|decision.making\|communication\|boundar\|collaboration\|self.improvement" references/sub-skills/souls/<role>.md` returns >= 7 for each role

### TC-3: 70% philosophy / 30% personality ratio
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; categorize content as operational philosophy ("assume every implementation has a defect", "find what everyone else missed") vs personality traits ("be diplomatic", "be concise")
- **Expected**: The majority of each file is operational philosophy (how to approach work) with personality traits as secondary modifiers on communication style
- **Verification**: Manual review — philosophy statements outnumber personality adjectives roughly 2:1 or greater in each file

### TC-4: Structure + anti-patterns format used
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; check that dimensions use a structure (what to do) + anti-patterns (what to NEVER do) format
- **Expected**: Each dimension (or at minimum communication style and boundaries) includes both positive guidance and explicit anti-patterns
- **Verification**: `grep -ci "never\|do not\|anti.pattern\|avoid" references/sub-skills/souls/<role>.md` returns >= 1 for each file; anti-patterns are specific enough to be verifiable (not generic like "don't be bad")

### TC-5: 2-3 example Discussion entries per role
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; locate example Discussion entries
- **Expected**: Each file contains 2-3 example Discussion entries that demonstrate the role's voice and communication style
- **Verification**: Each soul file contains 2-3 blocks formatted as Discussion entries (using `>` blockquote format); examples are clearly marked as examples (e.g., "Example:" label or similar) so they cannot be mistaken for real history

### TC-6: Vault references present (BRIEFING.md + human-profile)
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; search for references to BRIEFING.md and human-profile
- **Expected**: Each soul file references consulting BRIEFING.md for project priorities and human-profile for communication adaptation
- **Verification**: `grep -l "BRIEFING\|human.profile" references/sub-skills/souls/*.md` returns all 5 files

### TC-7: Soul is first include in template composition
- **Precondition**: Soul files created; manifest updated
- **Steps**: Read `references/sub-skills/manifest.md`; check composition order for each role
- **Expected**: The soul include (`souls/<role>`) appears as the FIRST include (position 0) in each role's composition order, before any other sub-skill includes
- **Verification**: For each role entry in the manifest, the first numbered include references `souls/<role>`

### TC-8: One PM soul shared by both pm-agent and pm-lean
- **Precondition**: Soul files exist per TC-1; manifest updated per TC-7
- **Steps**: Check that only one PM soul file exists; verify both pm-agent.md and pm-lean.md reference the same soul file
- **Expected**: Single `souls/pm.md` file; both PM variants include it
- **Verification**: `ls references/sub-skills/souls/pm*.md` returns exactly one file; manifest shows both pm-agent and pm-lean compositions reference `souls/pm`

### TC-9: Soul file size within ~60-80 lines
- **Precondition**: Soul files exist per TC-1
- **Steps**: Count lines in each soul file
- **Expected**: Each file is approximately 60-80 lines (tolerance: 50-100 lines acceptable)
- **Verification**: `wc -l references/sub-skills/souls/*.md` — all files between 50 and 100 lines

### TC-10: Soul is static — contains no dynamic/mutable content
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; check for any self-modification instructions, learning loops, or content that would change over time
- **Expected**: No instructions to update the soul file, no "evolve based on feedback" language, no mutable state. The soul is a static artifact.
- **Verification**: `grep -ci "update this\|modify this\|evolve\|change over time\|learn from\|adapt this file" references/sub-skills/souls/*.md` returns 0

### TC-11: Human instruction override clause present
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; locate the override clause
- **Expected**: Each soul file explicitly states that human instructions override soul defaults. The agent should comply and note the override in Discussion.
- **Verification**: `grep -li "human.*override\|override.*default\|human can override" references/sub-skills/souls/*.md` returns all 5 files (or a single shared section referenced by all)

### TC-12: No procedural duplication with existing templates
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read each soul file; compare against the corresponding role template (e.g., `roles/dev-agent.md`, `roles/qa-agent.md`)
- **Expected**: Soul files contain NO mechanical procedures, file paths, step-by-step loop instructions, acceptance criteria patterns, or tool usage instructions. These belong in the template, not the soul.
- **Verification**: Manual review — soul files contain only identity, philosophy, style, and lens content; no overlap with Ralph Loop steps, file conventions, or specific tool commands

### TC-13: Roles have distinct voices
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read all 5 soul files side by side; compare communication styles, decision-making styles, and example Discussion entries
- **Expected**: Each role's soul produces a distinguishable voice. PM is diplomatic/structured, QA is evidence-first/direct, Dev is concise/technical, Designer is user-experience-focused, DM is user-centric/adoption-focused.
- **Verification**: Example Discussion entries across the 5 files are clearly different in tone and structure; no two roles could be confused for each other

### TC-14: Anti-patterns are specific and verifiable
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read all anti-patterns across the 5 soul files
- **Expected**: Anti-patterns are concrete and testable (e.g., "Never present test results without specific evidence" not "Don't be vague"). Each anti-pattern describes a specific behavior that can be observed in agent output.
- **Verification**: Manual review — each anti-pattern could be turned into a yes/no checklist item when reviewing an agent's Discussion entry

### TC-15: Self-improvement lens dimension is forward-looking
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read the self-improvement lens section in each soul file
- **Expected**: Each role's lens describes what to scan for during quiet cycles, aligned with the role's identity (QA: coverage gaps/edge cases; Dev: code quality/maintainability; DM: adoption barriers; PM: process bottlenecks; Designer: UX friction)
- **Verification**: Each lens section contains role-specific scan targets; no two roles have identical lens content

### TC-16: Manifest updated with souls directory
- **Precondition**: Soul files created
- **Steps**: Read `references/sub-skills/manifest.md`
- **Expected**: Manifest lists `souls/` in its file inventory and documents each soul file
- **Verification**: `grep -c "souls/" references/sub-skills/manifest.md` returns >= 1; all 5 soul files are inventoried

### TC-17: Composed templates include soul content
- **Precondition**: Soul files created; manifest updated; templates regenerated
- **Steps**: Read a regenerated template (e.g., the composed dev-agent output)
- **Expected**: Soul content appears near the top of the composed template, after the role identification line and before procedural instructions
- **Verification**: Soul dimensions (identity, quality bar, etc.) appear in the first quarter of the composed template output

### TC-18: Collaboration posture defines inter-agent relationships
- **Precondition**: Soul files exist per TC-1
- **Steps**: Read the collaboration posture in each soul file
- **Expected**: Each role defines how it relates to other specific roles (e.g., QA's posture toward dev, PM's posture toward QA, DM's posture toward dev). The postures are complementary — QA challenges dev constructively, dev respects QA verification, PM mediates.
- **Verification**: Each collaboration posture section mentions at least 2 other roles by name and describes the relationship

## Smoke Tests
- [ ] Read all 5 soul files and confirm they parse as valid markdown without broken formatting
- [ ] Verify `{{include: souls/<role>}}` directive appears in each role's entry file or manifest composition
- [ ] Manually check that one soul file (e.g., `qa.md`) has all 7 dimensions, example entries, vault references, and override clause
- [ ] Confirm no soul file contains Ralph Loop steps, file path conventions, or tool-specific instructions
- [ ] Verify the PM soul is referenced by both pm-agent and pm-lean composition entries

## Regression Risks
- **Template bloat**: Each soul adds ~60-80 lines to the composed template. Verify total composed template size remains within context budget. If templates exceed a size threshold, the soul may need trimming.
- **Soul-template contradiction**: If a soul boundary contradicts a template instruction (e.g., soul says "never do X" but template says "do X in this case"), the agent may behave inconsistently. Review for conflicts between soul boundaries and existing template procedures.
- **Example entry mimicry**: Agents may copy example Discussion entries verbatim instead of adapting them. Examples must be clearly labeled as illustrations.
- **Override clause misuse**: The "human overrides soul" clause could be used to justify ignoring soul defaults entirely. The clause should specify that overrides are per-instance, not blanket.
- **Manifest ordering**: If the soul include is not truly first in composition order, it may not effectively color subsequent instructions. Verify composition engine respects the position.
