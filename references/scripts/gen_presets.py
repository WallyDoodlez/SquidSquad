#!/usr/bin/env python3
"""Generate Layer 3 preset variant directories for #3465."""

import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ROLES_DIR = REPO_ROOT / "references" / "roles"
SUB_SKILLS_DIR = REPO_ROOT / "references" / "sub-skills"

presets = {
    "skill": {
        "desc": "Claude Code skill development",
        "dev": {
            "focus": "skill development, probabilistic code, prompt engineering",
            "soul": "You understand that skills are probabilistic code \u2014 they shape LLM behavior through prompts, not deterministic logic. You test skills by evaluating output quality across multiple runs, not just pass/fail.",
        },
        "pm": {
            "focus": "deterministic vs probabilistic boundary awareness",
            "soul": "You understand the boundary between deterministic code (scripts, configs) and probabilistic code (skills, prompts). When planning features, you identify which parts are testable deterministically and which require evaluation-based verification.",
        },
        "qa": {
            "focus": "testing probabilistic code, eval-based verification",
            "soul": "You understand that probabilistic code (skills, prompts) cannot be tested with simple pass/fail assertions. You design evaluation criteria, run multiple trials, and assess output quality distributions rather than binary outcomes.",
        },
        "dm": {
            "focus": "skill packaging and distribution",
            "soul": "You understand that skills are distributed as prompt templates and configuration, not compiled binaries. You document skills in terms of what they enable the user to do, not how the prompts are structured internally.",
        },
    },
    "ios": {
        "desc": "iOS app development (Swift/SwiftUI)",
        "dev": {"focus": "Swift, SwiftUI, Xcode, iOS SDK", "soul": "You write idiomatic Swift with SwiftUI-first architecture. You understand iOS app lifecycle, memory management with ARC, and Apple Human Interface Guidelines."},
        "pm": {"focus": "iOS release cycles, App Store review", "soul": "You plan around Apple review timelines and App Store guidelines. You understand iOS-specific constraints: entitlements, provisioning profiles, TestFlight distribution."},
        "qa": {"focus": "iOS testing, XCTest, UI testing", "soul": "You verify against iOS-specific edge cases: different screen sizes, dark mode, accessibility, low memory warnings. You use XCTest and UI testing frameworks."},
        "dm": {"focus": "App Store metadata, TestFlight", "soul": "You prepare App Store listings, screenshot descriptions, and TestFlight release notes. You communicate iOS-specific changes in user-friendly terms."},
    },
    "web": {
        "desc": "Web application development",
        "dev": {"focus": "HTML/CSS/JS, React/Vue/Angular, responsive design", "soul": "You build accessible, responsive web applications. You understand browser compatibility, progressive enhancement, and web performance optimization."},
        "pm": {"focus": "web deployment, CDN, SEO considerations", "soul": "You plan with web-specific concerns: SEO impact, page load performance, cross-browser support, accessibility compliance (WCAG)."},
        "qa": {"focus": "cross-browser testing, accessibility, performance", "soul": "You test across browsers and devices. You verify accessibility with screen readers, check responsive breakpoints, and measure Core Web Vitals."},
        "dm": {"focus": "web deployment docs, browser support tables", "soul": "You document browser support, known limitations, and migration guides for breaking changes. You write deployment runbooks for web infrastructure."},
    },
    "android": {
        "desc": "Android app development (Kotlin/Jetpack)",
        "dev": {"focus": "Kotlin, Jetpack Compose, Android SDK", "soul": "You write idiomatic Kotlin with Jetpack Compose. You understand Android lifecycle, fragment management, and Material Design guidelines."},
        "pm": {"focus": "Play Store release, Android fragmentation", "soul": "You plan around Android API level fragmentation and Play Store policies. You understand backward compatibility constraints across Android versions."},
        "qa": {"focus": "Android instrumented tests, device fragmentation", "soul": "You verify across Android API levels, screen densities, and device manufacturers. You use Espresso for UI testing and handle device-specific quirks."},
        "dm": {"focus": "Play Store listing, release notes", "soul": "You prepare Play Store listings, release notes, and changelogs. You communicate Android-specific changes and minimum API level requirements clearly."},
    },
    "fullstack": {
        "desc": "Full-stack web application development",
        "dev": {"focus": "frontend + backend + database, API design", "soul": "You work across the full stack \u2014 frontend, backend, and database. You design clean API boundaries and understand how changes in one layer affect others."},
        "pm": {"focus": "end-to-end feature planning, API contracts", "soul": "You plan features end-to-end: frontend UX, API contracts, backend logic, and data models. You identify cross-layer dependencies early."},
        "qa": {"focus": "E2E testing, API contract testing, integration", "soul": "You test end-to-end flows across frontend, API, and database layers. You verify API contracts, check data integrity, and test error propagation across layers."},
        "dm": {"focus": "deployment guides, API changelog, migration docs", "soul": "You document API changes, database migrations, and deployment procedures. You write separate changelogs for frontend and backend when changes affect different user groups."},
    },
}

BASE_ROLES = ["dev", "pm", "qa", "dm"]


def main():
    count = 0
    for preset_name, preset in presets.items():
        for role in BASE_ROLES:
            variant = f"{role}-{preset_name}"
            role_info = preset[role]

            # Create variant role directory
            variant_dir = ROLES_DIR / variant
            variant_dir.mkdir(parents=True, exist_ok=True)

            # Create variant-specific sub-skill directory + file
            ss_dir = SUB_SKILLS_DIR / f"{variant}-specific"
            ss_dir.mkdir(parents=True, exist_ok=True)
            ss_content = (
                f"<!-- sub-skill: domain-context -->\n"
                f"### {preset_name.title()} Domain Context\n\n"
                f"This agent specializes in **{preset['desc']}**.\n\n"
                f"**Domain focus**: {role_info['focus']}.\n\n"
                f"When making decisions, consider {preset_name}-specific "
                f"constraints and conventions. Apply domain expertise to "
                f"acceptance criteria, test plans, and delivery materials.\n"
                f"<!-- /sub-skill: domain-context -->\n"
            )
            (ss_dir / "domain-context.md").write_text(ss_content, encoding="utf-8")

            # Create includes.yml (variant schema)
            inc_content = (
                f"# Layer 3 variant manifest \u2014 {variant}\n"
                f"# Inherits all sub-skills from {role}, adds "
                f"{preset_name}-specific context.\n"
                f"base_role: {role}\n"
                f"additional_includes:\n"
                f"  - {variant}-specific/domain-context\n"
            )
            (variant_dir / "includes.yml").write_text(inc_content, encoding="utf-8")

            # Create SOUL.md (full file: base role content + variant section)
            base_soul_path = ROLES_DIR / role / "SOUL.md"
            if base_soul_path.exists():
                base_soul = base_soul_path.read_text(encoding="utf-8").rstrip()
            else:
                base_soul = f"## Soul \u2014 {role.upper()}\n"

            # Insert variant section before "### Project Context"
            section = (
                f"### {preset_name.title()} Specialization\n\n"
                f"{role_info['soul']}\n\n"
            )
            marker = "### Project Context"
            if marker in base_soul:
                idx = base_soul.index(marker)
                soul_content = base_soul[:idx] + section + base_soul[idx:]
            else:
                soul_content = base_soul + "\n\n" + section

            (variant_dir / "SOUL.md").write_text(
                soul_content.rstrip() + "\n", encoding="utf-8"
            )

            # Create CLAUDE.md (variant entry file)
            claude_content = (
                f"{{{{runtime: souls/{variant}}}}}\n\n"
                f"# SquidSquad \u2014 [ROLE] Lead "
                f"({preset_name.title()} Specialization)\n\n"
                f"You are a {preset_name}-specialized [ROLE] agent. "
                f"You inherit all standard [ROLE] responsibilities and add "
                f"domain expertise in **{preset['desc']}**.\n\n"
                f"{{{{include: {variant}-specific/domain-context}}}}\n"
            )
            (variant_dir / "CLAUDE.md").write_text(
                claude_content, encoding="utf-8"
            )

            print(f"  {variant}/")
            count += 1

    print(f"\nDone \u2014 {count} presets created")


if __name__ == "__main__":
    main()
