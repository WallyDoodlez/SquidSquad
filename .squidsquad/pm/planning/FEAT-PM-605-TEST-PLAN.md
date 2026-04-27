# FEAT-PM-605 Test Plan — Display issue URL links

## Test Cases

### TC-1: Issue reference expanded in comment
- **Precondition**: Agent posts a comment referencing #NNN
- **Steps**: Check the posted comment on GitHub
- **Expected**: Contains full URL alongside the issue number
- **Verification**: gh issue view comment, check for URL

### TC-2: Repo URL derived correctly
- **Precondition**: Config.md has Repo field set
- **Steps**: URL construction uses correct repo
- **Expected**: URL matches actual repo (github.com/WallyDoodlez/SquidSquad)
- **Verification**: Compare generated URL with actual issue URL

### TC-3: Multiple references in one comment
- **Precondition**: Comment mentions #100, #200, #300
- **Steps**: Post comment
- **Expected**: All three expanded with URLs
- **Verification**: Check comment body

### TC-4: No false positives
- **Precondition**: Comment contains "#" in non-issue context (e.g., "step #1", "PR #")
- **Steps**: Post comment
- **Expected**: Only valid issue references expanded, not arbitrary #numbers
- **Verification**: Manual review

## Smoke Tests
- [ ] A tracker.py comment with #NNN includes the URL
- [ ] Repo URL matches config.md

## Regression Risks
- Breaking existing comment format
- False positive expansion of non-issue #references

## Comprehension Questions
### CQ-1: How does an agent include a clickable issue URL in a Discussion comment?
- **Files**: tracker.py or agent template
- **Expected**: Issue references (#NNN) include the full forge URL
