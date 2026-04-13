# Google Stitch — setup

Google Stitch is accessed via its MCP server. Setup is a one-time
infrastructure step per workstation. The designer cannot generate
mockups without it.

## What you need before you start

- A Google account with access to Google Stitch (the product is in
  limited availability at this writing — confirm your account can
  sign in at https://stitch.withgoogle.com/ before proceeding)
- Whatever credential Google Stitch currently requires (OAuth flow,
  API key, or personal access token — this changes as the product
  matures, so follow the docs page rather than any hard-coded
  instruction here)

## Steps

### 1. Sign in to Google Stitch

Open https://stitch.withgoogle.com/ in a browser and sign in with the
Google account you plan to use for this project. If the tool is not
yet available for your account, stop here — the tool cannot be
installed without access.

### 2. Install the Stitch MCP server

The Stitch MCP server connects Claude to your Stitch account. Add it
to your Claude host's MCP servers list (specific syntax varies by
host — ask inside this session if you are not sure which file to
edit).

A typical entry looks like:

```
"google_stitch": {
  "command": "npx",
  "args": ["-y", "@google/stitch-mcp"],
  "env": {
    "STITCH_CREDENTIAL": "<paste-your-credential-here>"
  }
}
```

Replace `<paste-your-credential-here>` with whatever Stitch currently
issues for programmatic access.

### 3. Restart Claude

Restart Claude so the MCP server is loaded. Confirm the `google_stitch`
server appears by asking Claude "what MCP servers are available?".

### 4. Point the designer at a project workspace

Google Stitch organises work into workspaces or projects. Create one
for this team (or reuse an existing one), and take note of the
workspace identifier — you will share it with the designer agent the
first time it picks up a design task.

## Troubleshooting

- **MCP server does not appear after restart.** The settings file
  syntax is probably wrong. Ask inside this Claude session to lint
  the MCP settings file.
- **MCP is registered but calls fail with auth errors.** The
  credential you pasted is wrong, expired, or missing scopes. Rotate
  the credential and update the settings file.
- **Stitch says the feature is unavailable.** Google Stitch is an
  evolving product and some capabilities are rolled out gradually.
  Check the Stitch docs for the current feature matrix.

## After setup

Once the MCP server is installed and the workspace identifier is
shared, the designer can generate and iterate on mockups through
natural-language prompts and share the resulting artifact URLs with
the human for review.
