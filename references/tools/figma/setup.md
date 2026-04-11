# Figma — setup

Figma is accessed via a Figma MCP server. Setting it up is a one-time
infrastructure step per workstation. The designer cannot draw frames
without it.

## What you need before you start

- A Figma account (free or paid — both work for design work)
- A Figma personal access token (PAT) — created in Figma's account
  settings under "Personal access tokens"
- A Figma project or file where the designs will live. A new file is
  fine; the project can be created later and shared with the human

## Steps

### 1. Install the Figma MCP server

The Figma MCP server connects Claude to your Figma account. The Claude
host exposes MCP servers via its settings file. The exact path depends
on which Claude client you are using — ask inside this session and it
will walk you through the right file.

You will need to add an entry like the following to the Claude host's
MCP servers list (specific syntax varies by host):

```
"figma": {
  "command": "npx",
  "args": ["-y", "figma-mcp"],
  "env": {
    "FIGMA_PERSONAL_ACCESS_TOKEN": "<paste-your-PAT-here>"
  }
}
```

Replace `<paste-your-PAT-here>` with the token you created in Figma's
account settings.

### 2. Restart Claude

After editing the MCP servers list, restart Claude so the new server is
loaded. You can confirm the server is registered by asking Claude
"what MCP servers are available?"; `figma` (or `figma_mcp`) should
appear in the list.

### 3. Authorize the account for your project

Open Figma in a browser, sign in with the same account whose PAT you
used, and either:
- Create a new Figma file for this project, OR
- Open an existing file the team already uses

Take note of the file URL — you will share it with the designer agent
the first time it picks up a design task so it knows where to put frames.

## Troubleshooting

- **MCP server does not appear after restart.** Double-check the JSON
  syntax in the MCP settings file — a trailing comma or missing quote
  will silently drop the entry. Ask inside this Claude session for a
  syntax check.
- **MCP is registered but calls fail with 403.** The personal access
  token is wrong, expired, or missing the scopes Figma now requires.
  Regenerate the token and update the settings file.
- **Designs don't appear where you expect.** The designer agent writes
  to the Figma file URL you gave it. If you haven't shared a URL yet,
  ask the agent for its current target — it will tell you or ask.

## After setup

Once the MCP server is installed and the file URL is shared, the
designer can open, edit, and share frames without further help. The
human reviews iterations by opening the frame URL the designer posts.
