## Design Tools

The designer connects to external design tools via MCP servers or CLI tools when available. Configuration is in `config.md` under `## Design Tools`.

### Tool Discovery

At the start of each cycle (or when first picking up a design request), check `config.md` for configured tools:

```markdown
## Design Tools

- **Tool**: [none / figma / stitch / custom]
- **Access**: [mcp / cli / none]
- **Tool Name**: [MCP tool name or CLI command, e.g. "mcp__figma__get_file"]
- **Project ID**: [project/file ID for the connected tool]
```

**If `Tool: none`** (default): Operate in **manual mode**. Produce specs from text descriptions, conversation with the human, and general design knowledge. Note `Source: manual (no design tool connected)` in spec headers.

**If a tool is configured**: Attempt to use it for:
- Fetching component specs and design references
- Exporting design tokens (colors, spacing, typography)
- Reading annotations and comments from design files
- Downloading asset references (URLs only — no binary commits)

If the configured tool is unavailable at runtime (MCP server not connected, CLI not on PATH), fall back to manual mode and note the fallback in the Discussion.

### Supported Tool Patterns

**Figma (via MCP)**: Use the Figma MCP server to fetch file data, component specs, and design tokens. Reference components by node ID.

**Google Stitch (via MCP/CLI)**: Use available Stitch tools to fetch design data.

**Custom tools**: Any MCP server or CLI tool that provides design data can be configured. The designer discovers available tools via the MCP tool list and matches against the configured tool name.

### Zero Credential Management

SquidSquad does NOT manage design tool credentials. MCP servers handle authentication externally. If a tool requires authentication, the human must configure the MCP server separately. The designer only uses tools that are already authenticated and available.
