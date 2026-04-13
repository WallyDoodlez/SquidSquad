## Design Capabilities

The designer connects to external design capability sub-skills via MCP servers or CLI commands when available. Configuration is in `config.md` under `## Design Capabilities`.

### Capability Discovery

At the start of each cycle (or when first picking up a design request), check `config.md` for configured capabilities:

```markdown
## Design Capabilities

- **Capability**: [none / figma / stitch / custom]
- **Access**: [mcp / cli / none]
- **Capability Name**: [MCP server name or CLI command, e.g. "mcp__figma__get_file"]
- **Project ID**: [project/file ID for the connected capability]
```

**If `Capability: none`** (default): Operate in **manual mode**. Produce specs from text descriptions, conversation with the human, and general design knowledge. Note `Source: manual (no design capability connected)` in spec headers.

**If a capability is configured**: Attempt to use it for:
- Fetching component specs and design references
- Exporting design tokens (colors, spacing, typography)
- Reading annotations and comments from design files
- Downloading asset references (URLs only — no binary commits)

If the configured capability sub-skill is unavailable at runtime (MCP server not connected, CLI not on PATH), fall back to manual mode and note the fallback in the Discussion.

### Supported Capability Patterns

**Figma (via MCP)**: Figma is a design tool accessed through its MCP server to fetch file data, component specs, and design tokens. Reference components by node ID.

**Google Stitch (via MCP/CLI)**: Google Stitch is a design tool accessed through available Stitch sub-skills to fetch design data.

**Custom capabilities**: Any MCP server or CLI command that provides design data can be configured. The designer discovers available sub-skills via the MCP server list and matches against the configured capability name.

### Zero Credential Management

SquidSquad does NOT manage design capability credentials. MCP servers handle authentication externally. If a capability requires authentication, the human must configure the MCP server separately. The designer only uses capabilities that are already authenticated and available.
