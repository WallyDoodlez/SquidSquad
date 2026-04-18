---
type: pattern
tags: [model-routing, multi-provider, subagent, cost-optimization, plugin-architecture]
created: 2026-04-18
updated: 2026-04-18
owner: skill
status: active
confidence: high
source: code
links: []
---

## Context

#1291 introduced multi-model subagent routing to reduce token costs. External models (GPT 5.2) handle bulk analysis work while Claude handles safety-critical tasks.

## Content

The model router uses a plugin architecture with YAML manifests per provider. Each provider directory contains a manifest (API config, deps, auth, tools) and an adapter module. The router implements an agentic tool-use loop — external models get Read, Grep, Glob access via Python-native implementations, sandboxed to repo root with a 4-layer security model (tool whitelist, path sandbox, no shell, sensitive file deny-list).

Key design decisions:
- PID-based process detection (not .health files) for liveness
- Exit code contract: 0=success, 1=fallback to Claude, 2=config error
- Prompt templates use simple `{{ variable }}` substitution (no Jinja2 dependency)
- Auto-install pip deps from manifest on first use
- Claude-locked tasks (comprehension, QA execution) always return exit 1

## Rationale

Plugin architecture chosen over monolithic adapter for extensibility — each provider is self-contained. YAML manifests are human-readable and declarative. The exit code contract makes fallback seamless — parent agent just checks the return code and spawns Claude Agent tool if non-zero.

## Related

[[decision-pid-primary-liveness]]

---

### Changelog

- 2026-04-18 — Created by skill. Documented model_router.py architecture from #1291 implementation.
