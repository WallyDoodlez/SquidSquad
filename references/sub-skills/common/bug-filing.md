## Filing Bugs (Self and Cross-Team)

You can file bugs to your own domain or directly to any other agent's domain via GitHub Issues. Do not wait for PM/QA to discover and route issues you find yourself.

**Self-file** when you discover a standalone issue during feature work:

```bash
gh issue create --title "BUG: [title]" \
  --body "**Reported By**: [ROLE]-lead\n**Severity**: [High/Medium/Low]\n\n**Description**: [what and why]\n\n**Steps to Reproduce**:\n1. [steps]\n\n**Expected**: [expected]\n**Actual**: [actual]" \
  --label "type:bug,severity:[level],role:[ROLE],squidsquad"
```

**Cross-file** when the root cause is in another agent's domain:

```bash
gh issue create --title "BUG: [title]" \
  --body "**Reported By**: [ROLE]-lead\n**Assigned To**: [OTHER_ROLE]\n**Severity**: [High/Medium/Low]\n\n**Description**: [what and why]\n\n**Steps to Reproduce**:\n1. [steps]\n\n**Expected**: [expected]\n**Actual**: [actual]" \
  --label "type:bug,severity:[level],role:[OTHER_ROLE],squidsquad"
```

After filing, note the returned Issue number and comment on the original issue if cross-filing.
