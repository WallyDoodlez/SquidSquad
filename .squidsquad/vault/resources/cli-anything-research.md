---
type: resource
tags: [tooling, agent-capabilities, gui-automation, cli-generation, research-spike]
created: 2026-04-14
updated: 2026-04-14
owner: pm
status: active
confidence: medium
source: research
links: []
---

# CLI-Anything — Agent-Controllable GUI Software

## What It Is

[CLI-Anything](https://github.com/HKUDS/CLI-Anything) (21K+ stars) auto-generates production-ready CLIs for open-source GUI software. It analyzes target app source code, maps GUI actions to backend APIs, and builds a Python Click CLI with JSON output, undo/redo, and session management.

**Core idea for SquidSquad**: Any agent role that needs to control GUI software without native LLM integration (no MCP, no API) can use CLI-Anything to get structured CLI access. It fills the gap between "has a native CLI" and "requires computer-use."

## 65+ Supported Apps

Includes GIMP, Blender, LibreOffice, Audacity, FreeCAD, Krita, Godot, Zotero, Obsidian, OBS Studio, Shotcut, Draw.io, Zoom, n8n, Dify. All open-source.

## How It Works

7-phase pipeline: Analyze source → Design CLI → Implement (Python Click) → Plan Tests → Write Tests → Document → Publish. Generates `SKILL.md` for agent auto-discovery. Installs as `cli-anything-<software>` on PATH.

**Key constraint**: Requires target software source code access. Cannot wrap proprietary/closed-source apps (Figma, Adobe, Slack desktop, Microsoft Office).

## Value Per SquidSquad Role

### Designer (HIGH value)
- **GIMP**: Batch image manipulation, layer composition, export
- **Krita**: Digital painting operations
- **Draw.io**: Programmatic diagram creation (architecture, flows)
- **Blender**: 3D asset creation and rendering
- **Inkscape/FreeCAD**: Vector graphics and CAD

Designer is the biggest beneficiary — enables deterministic, version-controllable visual asset generation without computer-use.

### QA (MODERATE value)
- Validate non-code artifacts: PDF page counts, image dimensions, document formatting
- **LibreOffice**: Verify generated documents
- **OBS Studio**: Record test sessions

### Skill/Dev (LOW-MODERATE value)
- Most dev tools already have native CLIs. Useful for GUI-first tools only:
- **Godot**: Game engine operations
- **Obsidian**: Knowledge base management with graph queries
- **n8n/Dify**: Workflow automation configuration

### DM / PM (LOW value)
- Most coordination tools have APIs/CLIs already. Minimal added value.

## Decision Framework: When to Use What

1. Tool has native CLI? (git, npm, docker) → **Use native CLI**
2. Tool has MCP server? → **Use MCP**
3. Tool is open-source GUI with accessible source? → **CLI-Anything**
4. Tool is proprietary with API? (Figma REST, Slack API) → **API wrapper**
5. Tool is proprietary with no API? → **Computer-use (last resort)**

## Integration Approach

**Recommended**: Direct subprocess invocation, NOT MCP server wrapper.

- CLIs already produce structured JSON via `--json` flag
- Agents invoke via Bash tool: `cli-anything-gimp --json layer add -n "Logo"`
- Install during role setup: `pip install cli-anything-gimp cli-anything-drawio`
- Discovery via SKILL.md files from installed packages
- Also available as Claude Code plugin (`/plugin install cli-anything`)

## Limitations

- **Source code required**: Cannot wrap proprietary software
- **Python 3.10+** required
- **Target software must be installed** on the machine
- **Latency**: Subprocess invocation per command; complex renders take seconds-minutes
- **Quality varies**: Well-structured codebases produce excellent CLIs; monolithic ones produce poor CLIs
- **Rendering gap**: GUI apps apply effects at render time; CLI must delegate to native renderer
- **Cannot control web SaaS**: Figma, Notion, Linear, Jira need APIs, not CLI-Anything

## Concrete Examples

```bash
# Designer: Create architecture diagram
cli-anything-drawio --json diagram create -n "system-arch"
cli-anything-drawio --json shape add --type rectangle --label "API Gateway"
cli-anything-drawio --json edge add --from "API Gateway" --to "PostgreSQL"
cli-anything-drawio --json export --format png --output ./docs/architecture.png

# QA: Validate document export
cli-anything-libreoffice --json document verify ./report.pdf --check-pages 5

# Designer: Batch image processing
cli-anything-gimp --json image resize --width 800 --height 600
cli-anything-gimp --json export --format webp --quality 85
```

## Next Steps

1. Install `cli-anything-gimp` and `cli-anything-drawio` on test machine
2. Run designer agent against a real visual asset task
3. Measure reliability of generated CLIs for production SquidSquad use
4. If viable, add to designer role manifest as optional capability

## Changelog

- 2026-04-14 — Created by pm. Research spike from human request. Analyzed repo, mapped to SquidSquad roles, defined decision framework and integration approach.
