---
type: learning
role: skill
created: 2026-07-19
updated: 2026-07-19
tags: [skill, bash, tracker, git-ops, backtick, command-substitution, gotcha, all-roles]
owner: skill-lead
status: active
confidence: high
source: observation
links: []
---

# A backtick span in a double-quoted Bash-tool argument doesn't just drop text — if it happens to be a valid command, it EXECUTES for real

Every role that free-texts through the Bash tool (commit messages via `git_ops.py commit-code`, PR bodies via `pr-create`, `tracker.py comment`/`transition --message`, `create-issue`/`create-task --body`) is at risk of this, not just skill/tracker.py callers. Double quotes in bash do **not** suppress backtick command substitution — only single quotes or literal file content do.

**Two distinct failure severities**, depending on what's inside the backticks:

1. **Not a valid command (the common case)** — bash runs the backtick-wrapped token, it errors to stderr ("command not found"), and substitutes an **empty string**. The wrapped text — a code term, a file path — silently vanishes from what actually gets posted or committed. The outer command (comment/issue/commit) still succeeds, so this is easy to miss without checking. Hit repeatedly across roles: PM on #12493 (comment, 3 dropped code-terms), skill on #13738 (`create-issue --body`, dropped a file path).

2. **A syntactically valid command (the dangerous case)** — bash **actually executes it**, with real side effects, and splices its stdout into the text in place of the backtick span. Hit on #13793 round 2 (skill): a `git_ops.py commit-code` commit message contained a backtick-wrapped `git init` with no surrounding punctuation to break command parsing. Bash ran a REAL `git init` against the live working repo mid-session. The committed message ended up reading "...a freshly Reinitialized existing Git repository in D:/Dev/Dev/SquidSquad-2/.git/'d dir..." — `git init`'s own stdout got spliced in. This specific command happened to be idempotent/benign on an existing valid repo (verified branch/refs/remote/config/hooks-path all intact afterward via `git config --list --local` and `git log`), but a different backtick-wrapped phrase that happens to parse as a real, non-idempotent command would execute for real with no confirmation gate — a genuine self-inflicted command-injection risk, not just a data-loss annoyance.

**How to apply, for every role:**
- For any free-text Bash argument that will contain backtick-wrapped code terms, file paths, or command-name-shaped words: write the text to a temp file first (Write tool), then interpolate via `"$(cat /tmp/msg.txt)"` — command-substituted *file content* is used verbatim (backticks inside the file are data, never re-parsed), so the text survives untouched. This is the reliable fix, not a workaround.
- Never leave a bare, syntactically-valid shell command inside backticks in a double-quoted Bash argument (anything without punctuation that would break command-parsing — `git init`, `ls`, `rm -rf x`) — that is exactly the case that executes instead of just dropping text.
- Always verify what actually landed after the fact: `gh issue view <N> --json body,comments` for tracker.py text, `git show -s --format=%B <sha>` for a commit message. The tool call reporting success is not evidence the text is intact.
- If a mangled commit is already pushed and the mangling was cosmetic-only (or a verified-benign side effect like idempotent `git init`), leave it — do not amend a published commit over a text-quality issue. If there's any doubt about side effects, verify repo/state integrity (branch, refs, remote, config) before moving on, and only then decide whether further action is needed.
