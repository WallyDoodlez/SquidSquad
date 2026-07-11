#!/usr/bin/env python3
"""SquidSquad config.md reader/writer.

Single source of truth for reading and writing config.md values.
All agents use this instead of parsing config.md themselves.

Usage:
    python scripts/config.py get <field>           # Get a field value
    python scripts/config.py set <field> <value>   # Set a field value
    python scripts/config.py dump                  # Dump all fields as JSON
    python scripts/config.py agents                # List agents as JSON
    python scripts/config.py schema-version        # Print 1 or 2
    python scripts/config.py alias <role>          # Get role alias (falls back to role name)
    python scripts/config.py sync-agents           # Sync Agents section from .squidsquad/*/CLAUDE.md
    python scripts/config.py list-agents           # Tab-separated agents for shell consumers
    python scripts/config.py --help                # Show usage

Schema versions:
    v1 (legacy) — Flat `## Agents` with a `- **Dev Agents**: fe, be` line.
        Per-role details live in `## Aliases`, `## Test Commands`, etc.
        Used by everything that shipped before #328.
    v2 (Q-new17) — `## Agents` with one entry per agent, nested fields
        (role / variant / iteration_mode / stack / test_command / setup).
        Written by the install wizard (Phase G) and resolved by Phase H.

Schema detection uses the top-level `- **Architecture Version**: N`
field. v1 files have `1`, v2 files have `2`. Readers that don't care
about agents (e.g. `get interval`) work unchanged against either schema.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

# Auto-detect repo root (walk up from script location)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = REPO_ROOT / ".squidsquad" / "config.md"

# #12823: the ship counter lives in its OWN file with `merge=ours`, separate from
# config.md. config.md previously carried `merge=ours` solely to protect this one
# DM-owned counter from regression when a stale sibling clone pushed an old value
# — but `merge=ours` is all-or-nothing, so it silently dropped every OTHER agent's
# concurrent config.md edit (a feature flag, a new key). Splitting the counter out
# lets config.md merge 3-way normally (real conflicts surface; non-overlapping
# edits merge cleanly), while the transient machine-regenerated counter keeps its
# ours-wins protection in `.ship-counter`. This is the same separate-file +
# `merge=ours` pattern already used for working-state / current-state / cycle-io.
SHIP_COUNTER_PATH = REPO_ROOT / ".squidsquad" / ".ship-counter"
# The single config field whose storage is redirected to SHIP_COUNTER_PATH.
_SHIP_COUNTER_FIELD = "shipped-since-bump"

# Harness wake-mode probe (#11401). Per AGENT-RUNTIME §2 the wake mechanism
# is selected solely by the boot-time harness probe — there is no
# `event-driven:` config field. These mirror the agent boot probe target.
_HARNESS_PORT_FILE = REPO_ROOT / ".squidsquad" / ".harness-port"
_DEFAULT_HARNESS_PORT = 7373
# Tight timeout: the only live caller (statusline `mode` badge) runs under a
# 1s shell `timeout`, and that budget also has to cover Python startup. Keep
# the probe well inside it. A healthy local harness answers /status in
# milliseconds; this bound only delays the "polling" answer when the harness
# is actually down.
_WAKE_PROBE_TIMEOUT = 0.5

sys.path.insert(0, str(SCRIPT_DIR))
from shared_fs import atomic_write_text  # #10007

# Known field mappings: short name -> (section_heading, field_name)
# Section heading is used for disambiguation when field names repeat (e.g. "Enabled")
FIELD_MAP = {
    "version": (None, "SquidSquad Version"),
    "tracker": (None, "Tracker"),
    "arch-version": (None, "Architecture Version"),
    "dev-agents": ("Agents", "Dev Agents"),
    # #6274 D2 dual-aware: `workers` is the canonical post-rename field
    # (`Workers:` in config.md). Pre-6274.3 cutover, get_field("workers")
    # reads `Workers:` first then falls back to `Dev Agents:` with a
    # deprecation warning — see `_DUAL_AWARE_CONFIG_FIELDS_6274` below.
    # In 6274.3 the `dev-agents` row above is deleted and this stays.
    "workers": ("Agents", "Workers"),
    "project-name": ("Project", "Name"),
    "repo": ("Project", "Repo"),
    "project-intent": ("Project", "Intent Description"),
    "skill-tests": ("Test Commands", "skill Tests"),
    "e2e-tests": ("Test Commands", "E2E Tests"),
    "interval": ("Iteration Interval", "Minutes"),
    "context-threshold": ("Context Pressure", "Threshold"),
    "pr-flow": ("PR Flow", "Enabled"),
    "improvement-scanning": ("Improvement Scanning", "Enabled"),
    "improvement-scan-cool-down": ("Improvement Scanning", "Improvement Scan Cool-Down"),  # #11091
    "idle-scan-burst": ("Improvement Scanning", "Idle Scan Burst"),  # #12506
    "verbose-mode": ("Verbose Mode", "Enabled"),  # #13162 — boot-read narration toggle
    "ship-threshold": ("Auto Versioning", "Ship Threshold"),
    "shipped-since-bump": ("Auto Versioning", "Shipped Since Last Bump"),
    "alias-skill": ("Aliases", "skill"),
    "alias-pm": ("Aliases", "pm"),
    "alias-dm": ("Aliases", "dm"),
    "alias-designer": ("Aliases", "designer"),
    "alias-qa": ("Aliases", "qa"),
    "vault-remember": ("Vault Remember", "Enabled"),
    "vault-writes-per-cycle": ("Vault Remember", "Writes Per Cycle"),
    "briefing-token-budget": ("Vault Remember", "BRIEFING Token Budget"),
    "confidence-decay-days": ("Vault Remember", "Confidence Decay Days"),
    "vault-optimize": ("Vault Optimize", "Enabled"),
    "agent-compose": ("Agent Compose", "Enabled"),
    "auto-merge": ("Auto Merge", "Enabled"),
    "mandatory-human-approval": ("Mandatory Human Approval", "Enabled"),
    "event-driven": ("Event Driven", "Enabled"),
    "scan-idle-timeout": ("Event Driven", "Scan Idle Timeout"),
    "diagnostics": ("Diagnostics", "Enabled"),
    "upstream-reporting": ("Diagnostics", "Upstream Reporting"),
    "default-model": ("Model Routing", "Default Model"),
    "research-model": ("Model Routing", "Research Model"),
    "discussion-prep-model": ("Model Routing", "Discussion Prep Model"),
    "test-plan-model": ("Model Routing", "Test Plan Model"),
    "qa-execution-model": ("Model Routing", "QA Execution Model"),
    "comprehension-model": ("Model Routing", "Comprehension Model"),
    "improvement-scan-model": ("Model Routing", "Improvement Scan Model"),
    "code-review-model": ("Model Routing", "Code Review Model"),  # #5932
    "fallback-model": ("Model Routing", "Fallback Model"),
    "api-timeout-seconds": ("Model Routing", "API Timeout Seconds"),
    "forge-provider": ("Forge Backend", "Provider"),
    "forge-endpoint": ("Forge Backend", "Endpoint"),
    "forge-owner": ("Forge Backend", "Owner"),
    "forge-repo": ("Forge Backend", "Repo"),
    "working-branch": ("Git Branches", "Working Branch"),
    "state-branch": ("Git Branches", "State Branch"),
    "branch-pattern": ("Git Branches", "Branch Pattern"),
    "harness-enabled": ("Harness", "Enabled"),
    "harness-port": ("Harness", "Port"),
    # Event-driven architecture (#7630 Phase 3)
    "event-timeout-minutes": ("Event Driven", "Timeout Minutes"),
    "event-max-retries": ("Event Driven", "Max Retries"),
    "event-poll-interval": ("Event Driven", "Poll Interval"),
    "event-queue-cap": ("Event Driven", "Queue Cap"),
    "scan-cooldown": ("Event Driven", "Scan Cooldown"),
    "effort-pm": ("Agent Effort", "pm"),
    "effort-skill": ("Agent Effort", "skill"),
    "effort-qa": ("Agent Effort", "qa"),
    "effort-dm": ("Agent Effort", "dm"),
}


def _read_config():
    """Read config.md and return raw text."""
    if not CONFIG_PATH.exists():
        print(f"ERROR: config.md not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    return CONFIG_PATH.read_text(encoding="utf-8")


def _parse_sections(text):
    """Parse config.md into {section_heading: section_text} dict."""
    sections = {"": ""}  # content before first heading
    current = ""
    for line in text.splitlines():
        heading_match = re.match(r'^##\s+(.+)', line)
        if heading_match:
            current = heading_match.group(1).strip()
            sections[current] = ""
        else:
            sections[current] = sections.get(current, "") + line + "\n"
    return sections


def _parse_field_in_text(text, field_name):
    """Extract a field value from a block of markdown text."""
    pattern = rf'-\s*\*\*{re.escape(field_name)}\*\*:\s*(.+)'
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _parse_field(text, section, field_name):
    """Extract a field value, optionally scoped to a section."""
    if section:
        sections = _parse_sections(text)
        section_text = sections.get(section, "")
        return _parse_field_in_text(section_text, field_name)
    return _parse_field_in_text(text, field_name)


def _parse_all(text):
    """Parse all known fields from config.md."""
    result = {}
    for short_name, (section, field_name) in FIELD_MAP.items():
        val = _parse_field(text, section, field_name)
        if val is not None:
            result[short_name] = val
    # #12823: the ship counter is stored in .ship-counter, not config.md. Overlay
    # the authoritative value so `dump`/`_parse_all` agree with `get_field` (else
    # dump would report the stale/absent config.md field after migration).
    sc = _read_ship_counter()
    result[_SHIP_COUNTER_FIELD] = (
        sc if sc is not None
        else _FIELD_DEFAULTS.get(_SHIP_COUNTER_FIELD, "0")
    )
    return result


# Fields that default to a value when absent from config.md (rather than exiting)
_FIELD_DEFAULTS = {
    "event-driven": "no",
    # #12823 — a fresh install with neither .ship-counter nor a legacy config.md
    # counter field starts the counter at 0.
    "shipped-since-bump": "0",
    # #11091 — minutes between idle improvement-scans (event-mode cool-down loop)
    "improvement-scan-cool-down": "30",
    # #12506 — max idle improvement-scans per sustained-idle burst before the
    # event-mode periodic driver cancels itself (graceful default per §8.6.1).
    "idle-scan-burst": "3",
    # #13162 — Verbose Mode narration toggle. Shipped default OFF; graceful
    # default `no` so a config.md without the section reads as quiet (no sys.exit).
    "verbose-mode": "no",
    # #13335 (QA TC-3) — context-pressure restart threshold. Graceful default 70
    # so a config.md without the `## Context Pressure` section never sys.exit(1)s:
    # SystemExit is a BaseException, so it would escape the harness health
    # poller's except-Exception and silently kill the whole poller on first tick.
    "context-threshold": "70",
    # #13328 — polling-fallback cadence. Event mode is the always-on default and
    # the loop is a boot-time fallback, so the interval is never prompted; a
    # config.md missing the `## Iteration Interval` section reads 30 minutes
    # rather than sys.exit(1)ing (the section used to be mis-written under a dead
    # `## Loop` heading — same drift class as PR Flow, #13355).
    "interval": "30",
    # #13355 — PR flow is an INSTALLER-RUNTIME.md §3 invariant (branch+PR is
    # the only mode, #9478 D2): a config.md missing the `## PR Flow` section
    # reads `yes`, never sys.exit(1)s and never silently flips the runtime
    # into a direct-commit mode that no longer exists.
    "pr-flow": "yes",
    # #13355 — the merge gate is the one surviving PR variable. Fresh installs
    # always carry an explicit `## Auto Merge` section (build_config_md); for
    # a legacy/hand-rolled config.md missing it, default to the conservative
    # direction — a human approves each merge — rather than self-merging.
    "auto-merge": "no",
}


def _read_ship_counter():
    """Return the ship counter (#12823) as a string, or None if unavailable.

    Source of truth is ``SHIP_COUNTER_PATH``. For backward compatibility with
    installs that still carry the counter in config.md (pre-#12823), fall back to
    the config.md ``Auto Versioning > Shipped Since Last Bump`` field when the
    counter file is absent — so an in-place upgrade keeps reading the right value
    until the next write migrates it. Never raises.
    """
    try:
        if SHIP_COUNTER_PATH.exists():
            raw = SHIP_COUNTER_PATH.read_text(encoding="utf-8").strip()
            if raw:
                return raw
    except OSError:
        pass
    # Migration fallback: read the legacy in-config.md value.
    section, field_name = FIELD_MAP[_SHIP_COUNTER_FIELD]
    return _parse_field(_read_config(), section, field_name)


def _write_ship_counter(value):
    """Atomically write the ship counter (#12823) to ``SHIP_COUNTER_PATH``."""
    SHIP_COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(SHIP_COUNTER_PATH, f"{value}\n")
    return value


def get_field(field):
    """Get a config field by short name or full name.

    #6274 D2: for fields in `_DUAL_AWARE_CONFIG_FIELDS_6274`, read the new
    field first and fall back to the deprecated one with a stderr warning.
    """
    # #12823: the ship counter is stored in its own file (.ship-counter), not
    # config.md — redirect the read (with a config.md migration fallback).
    if field == _SHIP_COUNTER_FIELD:
        val = _read_ship_counter()
        if val is None:
            return _FIELD_DEFAULTS.get(_SHIP_COUNTER_FIELD, "0")
        return val

    text = _read_config()
    entry = FIELD_MAP.get(field)
    if entry:
        section, field_name = entry
        val = _parse_field(text, section, field_name)
    else:
        val = _parse_field_in_text(text, field)

    # #6274 D2 dual-aware fallback: if the canonical field is absent but
    # the deprecated field is present, return the deprecated value and
    # log a one-time warning. Removed in 6274.3 — the deprecated field
    # then raises the normal "Field not found" error.
    if val is None and field in _DUAL_AWARE_CONFIG_FIELDS_6274:
        deprecated_short = _DUAL_AWARE_CONFIG_FIELDS_6274[field]
        deprecated_entry = FIELD_MAP.get(deprecated_short)
        if deprecated_entry is not None:
            dsection, dfield = deprecated_entry
            val = _parse_field(text, dsection, dfield)
            if val is not None:
                print(
                    f"WARNING: config.md uses deprecated field "
                    f"`{dfield}:` -- rename to `{entry[1] if entry else field}:` "
                    f"before #6274.3 cutover.",
                    file=sys.stderr,
                )

    if val is None:
        if field in _FIELD_DEFAULTS:
            return _FIELD_DEFAULTS[field]
        print(f"ERROR: Field '{field}' not found in config.md", file=sys.stderr)
        sys.exit(1)
    return val


# #6274 D2 dual-aware mapping: { canonical_short: deprecated_short }.
# Looked up by get_field when the canonical field is absent. Deleted in
# 6274.3 along with the deprecated FIELD_MAP rows.
_DUAL_AWARE_CONFIG_FIELDS_6274 = {
    "workers": "dev-agents",
}


def is_verbose():
    """Return True iff Verbose Mode is enabled in config.md (#13162).

    Boot-read narration toggle: the agent calls this once at session boot to
    select its narration posture for the whole session (verbose firehose vs.
    quiet default). Graceful — returns False (quiet, the shipped default) when
    the ``## Verbose Mode`` section is absent, since ``verbose-mode`` carries a
    ``no`` default in ``_FIELD_DEFAULTS`` (so ``get_field`` never sys.exits here).
    Mirrors the string-bool convention used elsewhere (e.g. ``pr-flow`` →
    ``== "yes"`` in harness.py).
    """
    return (get_field("verbose-mode") or "").strip().lower() == "yes"


def _harness_wake_port():
    """Resolve the harness port from the port file, default 7373.

    Mirrors the agent boot probe (AGENT-RUNTIME §8.0) and
    ``statusline_data._harness_port``. Never raises.
    """
    try:
        return int(_HARNESS_PORT_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return _DEFAULT_HARNESS_PORT


def _harness_reachable():
    """True iff the harness answers ``GET /status`` with HTTP 200 in time.

    This is the same signal the agent boot uses to select event vs. polling
    mode. Any failure (missing/unreachable port, timeout, non-200, no curl
    equivalent) means "not reachable" → polling. Never raises.
    """
    url = f"http://127.0.0.1:{_harness_wake_port()}/status"
    try:
        with urllib.request.urlopen(url, timeout=_WAKE_PROBE_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        # Any probe failure means "not reachable" → polling. Catch broadly
        # (not just URLError/OSError) so a malformed response mid-restart
        # — e.g. http.client.BadStatusLine, which is NOT an OSError — can't
        # break the never-raises contract this helper owes statusline.
        return False


def get_wake_mode(role=None):
    """Resolve the wake mode by probing the harness (#11401).

    Per AGENT-RUNTIME §2, event mode is the unconditional architecture and
    the wake mechanism is selected **solely by the boot-time harness
    probe** — there is no ``event-driven:`` config field, no per-role
    override, and no operator-flipped flag. This function mirrors that
    contract for the Python runtime so the scripts never disagree with the
    agent's actual mode: a reachable harness (``GET /status`` → 200) means
    event-driven; any failure means polling.

    Before #11401 this read ``event-driven[-<role>]`` from ``config.md``,
    which could diverge from the agent (e.g. ``event-driven: yes`` in
    config while the harness was down → agent polled but scripts reported
    event). The probe removes that divergence at the source.

    ``role`` is accepted for caller-signature compatibility but unused —
    harness reachability is global, not per-role.

    Returns ``"event-driven"`` or ``"polling"`` — never ``None``, never
    raises.
    """
    return "event-driven" if _harness_reachable() else "polling"


def set_field(field, value):
    """Set a config field value."""
    # #12823: the ship counter is stored in its own file (.ship-counter), not
    # config.md — redirect the write there. This is also the migration write:
    # once it runs, .ship-counter is authoritative and the (now-ignored) legacy
    # config.md field, if any, is left for config.md's normal 3-way merge.
    if field == _SHIP_COUNTER_FIELD:
        return _write_ship_counter(value)

    text = _read_config()
    entry = FIELD_MAP.get(field)
    if entry:
        section, field_name = entry
    else:
        section, field_name = None, field

    if section:
        # Section-aware replacement: find the section, then the field within it
        sections = _parse_sections(text)
        section_text = sections.get(section, "")
        if not section_text:
            print(f"ERROR: Section '{section}' is empty or missing in config.md", file=sys.stderr)
            sys.exit(1)
        pattern = rf'(-\s*\*\*{re.escape(field_name)}\*\*:\s*).+'
        new_section, count = re.subn(pattern, rf'\g<1>{value}', section_text, count=1)
        if count == 0:
            print(f"ERROR: Field '{field}' not found in section '{section}'", file=sys.stderr)
            sys.exit(1)
        new_text = text.replace(section_text, new_section, 1)
    else:
        pattern = rf'(-\s*\*\*{re.escape(field_name)}\*\*:\s*).+'
        new_text, count = re.subn(pattern, rf'\g<1>{value}', text, count=1)
        if count == 0:
            print(f"ERROR: Field '{field}' not found in config.md", file=sys.stderr)
            sys.exit(1)

    atomic_write_text(CONFIG_PATH, new_text)
    return value


# `## Aliases` registry parser — PRD-A Story A5 (#10385).
# Spec lives in docs/COMPOSE-ARCHITECTURE.md §3.0; do not re-document here.
# Greenfield: legacy bullet-form `- **alias**: value` still read by
# `_parse_field_in_text` for `get_alias` etc., untouched by this function.

# Agent role-classes — map to composed CLAUDE.md / L1-L4 sources and are
# spawned + supervised by the harness.
AGENT_ROLE_CLASSES = frozenset({"pm", "worker", "verifier", "dm"})
# Non-agent role-classes (#12800) — routable on the forge but NOT agents: no
# composed CLAUDE.md, no L1-L4, no SOUL, not spawned/supervised, not on the
# event bus. `human` is the first: agents assign work to a human alias and a
# person acts on it asynchronously. compose.py MUST skip these (no CLAUDE.md /
# L4), and the harness must not poll them for liveness.
NON_AGENT_ROLE_CLASSES = frozenset({"human"})
# Every role-class accepted in the `## Aliases` registry (agent + non-agent).
ALIASES_ROLE_CLASSES = AGENT_ROLE_CLASSES | NON_AGENT_ROLE_CLASSES

# #6274 dual-aware shim mirror — bullet-form fallback and table-form
# normalization both pre-map legacy aliases (`qa` → `verifier`,
# `dev` → `worker`) before validation, so a real install that still
# declares `- **qa**: qa` resolves to `(verifier, None)` instead of
# raising "unknown role-class `qa`". Symmetric with
# `compose._BASE_ALIAS_6274` — avoids importing compose into config
# (would create a cycle).
_BULLET_LEGACY_ROLE_CLASS_SHIM = {"qa": "verifier", "dev": "worker"}

# Worker-variant L3 domains carry the "skill" / "ios" / "web" /
# "android" / "fullstack" shorthand in the legacy bullet form
# (`- **skill**: skill` means alias=skill / role_class=worker /
# l3_domain=skill — the dev-agent L3 fan-out). Used only by the
# bullet-form fallback; table-form callers pass the explicit
# (role-class, L3 domain) cells.
_BULLET_LEGACY_WORKER_L3_DOMAINS = frozenset({
    "skill", "ios", "web", "android", "fullstack",
})

# U+2014 EM DASH only. Hyphen-minus and en-dash are rejected by the strict
# cell comparison below, giving the operator a crisper diagnostic than
# silent acceptance of three lookalike characters.
ALIASES_L3_NONE_SENTINEL = "—"

_ALIASES_HEADING = "Aliases"
_ALIASES_HEADER_COLUMNS = ("alias", "role-class", "L3 domain")


class AliasesRegistryError(ValueError):
    """Raised when `.squidsquad/config.md`'s `## Aliases` table is malformed.

    Subclass of `ValueError` so callers that already catch `ValueError` for
    config-parsing errors keep working; tests assert against the more
    specific type when they care about the diagnostic source.
    """


def _parse_aliases_bullet_form(section_text):
    """Parse the legacy bullet-form `## Aliases` block.

    Recognizes lines of shape ``- **<alias>**: <value>`` and returns
    ``{alias: (role_class, l3_domain)}`` using these rules:

    - ``<value>`` in ``ALIASES_ROLE_CLASSES`` -> ``role_class=value``,
      ``l3_domain=None``.
    - ``<value>`` in ``_BULLET_LEGACY_ROLE_CLASS_SHIM`` (e.g. ``qa`` /
      ``dev``) -> ``role_class=<shim-target>`` (``verifier`` /
      ``worker``), ``l3_domain=None``.
    - ``<value>`` in ``_BULLET_LEGACY_WORKER_L3_DOMAINS`` (e.g.
      ``skill`` / ``ios`` / ``web`` / ``android`` / ``fullstack``)
      -> ``role_class="worker"``, ``l3_domain=<value>``. This is the
      legacy convention that ``- **skill**: skill`` declares a
      worker-skill variant.
    - Any other ``<value>`` -> bullet form does not recognize it;
      ``_parse_aliases_bullet_form`` returns ``{}`` so the caller
      raises its normal "needs table format" diagnostic.

    Returns ``{}`` (NOT ``None``) when the section has NO bullet rows
    at all so the caller's "needs table format" diagnostic stays the
    canonical on-empty path. When at least one bullet row IS present,
    every row must resolve via the rules above — an unrecognized value
    raises :class:`AliasesRegistryError` rather than being silently
    dropped. Per DS-10751 review: silent skip + ``return registry``
    (when other rows were recognized) would make a single-character
    typo like ``- **skill**: skil`` invisible to the operator; matches
    the docstring's "rather than silently dropping it" guarantee.
    """
    bullet_re = re.compile(
        r"^\s*-\s+\*\*([^*]+)\*\*\s*:\s*(\S+)\s*$",
    )
    registry = {}
    for raw_line in section_text.splitlines():
        m = bullet_re.match(raw_line)
        if m is None:
            continue
        alias, value = m.group(1).strip(), m.group(2).strip()
        if not alias or not value:
            continue
        if value in ALIASES_ROLE_CLASSES:
            role_class, l3_domain = value, None
        elif value in _BULLET_LEGACY_ROLE_CLASS_SHIM:
            role_class = _BULLET_LEGACY_ROLE_CLASS_SHIM[value]
            l3_domain = None
        elif value in _BULLET_LEGACY_WORKER_L3_DOMAINS:
            role_class, l3_domain = "worker", value
        elif "/" in value:
            # Explicit `<role_class>/<l3_domain>` form (e.g. `dm/skill`).
            # Generalizes domain attachment beyond the worker shorthand
            # above to any role-class, so a non-worker role (e.g. a
            # skill-domain DM) can carry an L3 variant in the bullet form
            # without migrating the whole section to the table form. The
            # legacy role-class shim still applies to the class half
            # (`qa/<d>` → verifier, `dev/<d>` → worker).
            class_part, _, domain_part = value.partition("/")
            class_part, domain_part = class_part.strip(), domain_part.strip()
            class_part = _BULLET_LEGACY_ROLE_CLASS_SHIM.get(class_part, class_part)
            # The L3 domain becomes a filesystem subdirectory name in the
            # compose walk (`references/roles/<class>/<domain>/`), so a
            # domain containing `/` would be (mis)read as a nested path.
            # Reject it here rather than let the walk silently miss the dir.
            if (class_part not in ALIASES_ROLE_CLASSES
                    or not domain_part
                    or "/" in domain_part):
                raise AliasesRegistryError(
                    f"`## Aliases` bullet form has unrecognized "
                    f"`<role-class>/<l3-domain>` value `{value}` for alias "
                    f"`{alias}`. The class half must be a role-class "
                    f"({sorted(ALIASES_ROLE_CLASSES)}) or legacy shim "
                    f"({sorted(_BULLET_LEGACY_ROLE_CLASS_SHIM)}); the "
                    f"domain half must be non-empty and contain no `/`."
                )
            role_class, l3_domain = class_part, domain_part
        else:
            # Unrecognized value — raise so a typo can't slip past
            # the operator. Names the bullet that failed AND the
            # accepted value set so the fix is obvious from the
            # diagnostic alone.
            raise AliasesRegistryError(
                f"`## Aliases` bullet form has unrecognized value "
                f"`{value}` for alias `{alias}`. Accepted values are "
                f"role-classes ({sorted(ALIASES_ROLE_CLASSES)}), legacy "
                f"shim aliases ({sorted(_BULLET_LEGACY_ROLE_CLASS_SHIM)}), "
                f"or worker L3 domains "
                f"({sorted(_BULLET_LEGACY_WORKER_L3_DOMAINS)})."
            )
        if alias in registry:
            raise AliasesRegistryError(
                f"`## Aliases` bullet form has duplicate alias `{alias}`."
            )
        registry[alias] = (role_class, l3_domain)
    return registry


def _split_table_row(line):
    """Split a markdown table row into stripped cells, or None if not a row."""
    if "|" not in line:
        return None
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def _is_table_separator(cells):
    """Recognize a markdown table separator row like `|---|---|---|`."""
    if not cells:
        return False
    sep_re = re.compile(r"^\s*:?-+:?\s*$")
    return all(sep_re.match(cell) for cell in cells)


def parse_aliases_registry(text=None):
    """Parse the `## Aliases` table per COMPOSE-ARCHITECTURE §3.0.

    Returns `{alias: (role_class, l3_domain)}`; `l3_domain` is `None` when
    the cell carries the em-dash sentinel, otherwise the trimmed cell value.
    Reads `.squidsquad/config.md` from disk when `text` is None. Raises
    `AliasesRegistryError` on any structural malformation (see tests for
    the exhaustive list of rejected shapes).

    L3 domain values are NOT allow-list-validated — the taxonomy lives in
    the role-class L3 fan-out and is the caller's concern, not the
    registry's.
    """
    if text is None:
        text = _read_config()

    sections = _parse_sections(text)
    if _ALIASES_HEADING not in sections:
        raise AliasesRegistryError(
            "config.md is missing the required `## Aliases` section "
            "(see docs/COMPOSE-ARCHITECTURE.md §3.0 for the canonical schema)."
        )

    section_text = sections[_ALIASES_HEADING]

    rows = []
    for raw_line in section_text.splitlines():
        cells = _split_table_row(raw_line)
        if cells is None:
            continue
        rows.append(cells)

    if not rows:
        # #10751 ERROR: bullet-form fallback. Real installs still ship
        # the legacy `- **alias**: value` form (e.g. this repo's
        # config.md). Without the fallback every v2 deploy aborts here
        # before any link-stage work. Symmetric in semantics with the
        # canonical 3-column table — see `_parse_aliases_bullet_form`
        # for the per-row interpretation.
        bullet_registry = _parse_aliases_bullet_form(section_text)
        if bullet_registry:
            return bullet_registry
        raise AliasesRegistryError(
            "`## Aliases` section is present but contains no table — expected "
            "a 3-column markdown table with header `| alias | role-class | "
            "L3 domain |` (see COMPOSE-ARCHITECTURE §3.0), OR the legacy "
            "`- **alias**: value` bullet form."
        )

    header = rows[0]
    if len(header) != 3 or tuple(h.lower() for h in header) != tuple(
        c.lower() for c in _ALIASES_HEADER_COLUMNS
    ):
        raise AliasesRegistryError(
            f"`## Aliases` header row must be exactly "
            f"`| {' | '.join(_ALIASES_HEADER_COLUMNS)} |`; got "
            f"`| {' | '.join(header)} |`."
        )

    if len(rows) < 2 or not _is_table_separator(rows[1]):
        raise AliasesRegistryError(
            "`## Aliases` table is missing the separator row (expected "
            "`|---|---|---|` immediately after the header)."
        )

    registry = {}
    for data_row_index, cells in enumerate(rows[2:], start=1):
        if len(cells) != 3:
            raise AliasesRegistryError(
                f"`## Aliases` data row {data_row_index} has {len(cells)} "
                f"column(s); expected 3. Row: `| {' | '.join(cells)} |`."
            )

        alias, role_class, l3_cell = cells

        if not alias:
            raise AliasesRegistryError(
                f"`## Aliases` data row {data_row_index} has an empty "
                f"`alias` cell."
            )
        if not role_class:
            raise AliasesRegistryError(
                f"`## Aliases` data row {data_row_index} (`{alias}`) has an "
                f"empty `role-class` cell."
            )
        # #10751 W2: pre-normalize via the #6274 shim so a real
        # install with `qa` / `dev` in the role-class column resolves
        # to `verifier` / `worker` instead of raising. Symmetric with
        # `_parse_aliases_bullet_form` above and with
        # `compose._BASE_ALIAS_6274` elsewhere.
        if role_class in _BULLET_LEGACY_ROLE_CLASS_SHIM:
            role_class = _BULLET_LEGACY_ROLE_CLASS_SHIM[role_class]
        if role_class not in ALIASES_ROLE_CLASSES:
            raise AliasesRegistryError(
                f"`## Aliases` data row {data_row_index} (`{alias}`) has "
                f"unknown role-class `{role_class}` — must be one of "
                f"{sorted(ALIASES_ROLE_CLASSES)} (with legacy `qa`/`dev` "
                f"auto-mapped to `verifier`/`worker`)."
            )
        if alias in registry:
            raise AliasesRegistryError(
                f"`## Aliases` has duplicate alias `{alias}` "
                f"(data row {data_row_index})."
            )

        l3_domain = None if l3_cell == ALIASES_L3_NONE_SENTINEL else (l3_cell or None)
        registry[alias] = (role_class, l3_domain)

    if not registry:
        raise AliasesRegistryError(
            "`## Aliases` table has a header but zero data rows. An install "
            "must declare at least one alias."
        )

    return registry


def get_alias(role):
    """Get the alias for a role. Falls back to bare role name if not set."""
    text = _read_config()
    alias_key = f"alias-{role}"
    entry = FIELD_MAP.get(alias_key)
    if entry:
        section, field_name = entry
        val = _parse_field(text, section, field_name)
        if val:
            # #12749: the `## Aliases` cell may carry the
            # `<role_class>/<l3_domain>` compose syntax (e.g. `dm/skill`).
            # The L3 domain is a compose-only concern (see
            # parse_aliases_registry) — the agent's *display alias* is the
            # class part only. Strip any `/<domain>` so callers embedding
            # `config.py alias <role>` in tracker signatures get `dm`, not
            # `dm/skill`. No-op for plain values.
            return val.split("/", 1)[0]
    # Fallback: bare role name
    return role


# ---------------------------------------------------------------------------
# Event Reactions section parsing (#5868)
# ---------------------------------------------------------------------------


def get_event_reactions(text=None):
    """Parse the ## Event Reactions section from config.md.

    Returns a dict: {role: {"emits": [str], "reacts_to": [str]}} or empty dict
    if the section is absent or malformed. Never raises — graceful fallback.
    """
    if text is None:
        text = _read_config()
    sections = _parse_sections(text)
    section_text = sections.get("Event Reactions", "")
    if not section_text.strip():
        return {}

    result = {}
    current_role = None

    for line in section_text.splitlines():
        # Detect ### role heading
        role_match = re.match(r'^###\s+(\w+)', line)
        if role_match:
            current_role = role_match.group(1).strip()
            result[current_role] = {"emits": [], "reacts_to": []}
            continue

        if not current_role:
            continue

        # Parse - **emits**: event1, event2, ...
        emits_match = re.match(r'-\s*\*\*emits\*\*:\s*(.+)', line)
        if emits_match:
            raw = emits_match.group(1).strip()
            result[current_role]["emits"] = [
                e.strip() for e in raw.split(",") if e.strip()
            ]
            continue

        # Parse - **reacts-to**: event1, event2, ...
        reacts_match = re.match(r'-\s*\*\*reacts-to\*\*:\s*(.+)', line)
        if reacts_match:
            raw = reacts_match.group(1).strip()
            result[current_role]["reacts_to"] = [
                e.strip() for e in raw.split(",") if e.strip()
            ]
            continue

    return result


def get_event_filters_for_role(role, text=None):
    """Get the reacts-to event types for a specific role from Event Reactions.

    Returns a set of event type strings, or None if the section is absent
    (caller should fall back to hardcoded defaults).
    """
    reactions = get_event_reactions(text)
    if not reactions:
        return None
    role_data = reactions.get(role)
    if not role_data:
        return None
    reacts_to = role_data.get("reacts_to", [])
    return set(reacts_to) if reacts_to else None


def write_event_reactions(reactions_dict, text=None):
    """Write the ## Event Reactions section to config.md.

    reactions_dict: {role: {"emits": [str], "reacts_to": [str]}}
    Atomic write — replaces the entire section or appends if absent.
    """
    if text is None:
        text = _read_config()

    # Build the new section content
    lines = ["\n## Event Reactions\n"]
    for role in sorted(reactions_dict.keys()):
        data = reactions_dict[role]
        lines.append(f"\n### {role}")
        emits = ", ".join(data.get("emits", []))
        reacts_to = ", ".join(data.get("reacts_to", []))
        lines.append(f"- **emits**: {emits}")
        lines.append(f"- **reacts-to**: {reacts_to}")
    new_section = "\n".join(lines) + "\n"

    # Replace existing section or append
    sections = _parse_sections(text)
    if "Event Reactions" in sections:
        # Find and replace the section in the raw text
        # Match from "## Event Reactions" to next "## " or end of file
        pattern = r'(## Event Reactions\s*\n)(.*?)(?=\n## |\Z)'
        replacement = "## Event Reactions\n" + "\n".join(lines[1:]) + "\n"
        new_text = re.sub(pattern, replacement, text, count=1, flags=re.DOTALL)
    else:
        # Append to end of file
        new_text = text.rstrip() + "\n" + new_section

    # #10007 DS review Finding 5: route through shared atomic helper so this
    # function and set_field stay consistent (both use the same newline
    # handling and mkstemp/replace pattern; previously this used a bespoke
    # `with_suffix(".tmp") + write_text + replace` pattern that diverged).
    atomic_write_text(CONFIG_PATH, new_text)


# ---------------------------------------------------------------------------
# Schema-aware agent parsing (#328 Phase H)
# ---------------------------------------------------------------------------


def detect_schema_version(text=None):
    """Return 1 or 2 based on the top-level `Architecture Version` field.

    Missing field -> assume v1 (legacy). Malformed/non-integer -> v1.
    """
    if text is None:
        text = _read_config()
    raw = _parse_field_in_text(text, "Architecture Version")
    if not raw:
        return 1
    try:
        n = int(raw.strip())
    except (TypeError, ValueError):
        return 1
    return 2 if n >= 2 else 1


def _parse_agents_v1(text):
    """Parse the legacy `- **Dev Agents**: fe, be` format.

    Returns a list of dicts shaped like the v2 output:
        [{"id": "fe", "alias": "fe", "role": "dev"}, ...]

    Infrastructure roles (pm, verifier, dm) are always present (#6261 fixed
    team; #6274 D5: qa→verifier — see _parse_agents_v1 mandatory loop and
    sync_agents() for the dual-aware behaviour during the migration window).
    Aliases are read from the `## Aliases` section.
    """
    sections = _parse_sections(text)
    agents_text = sections.get("Agents", "")
    aliases_text = sections.get("Aliases", "")
    test_cmd_text = sections.get("Test Commands", "")

    dev_roles_raw = _parse_field_in_text(agents_text, "Dev Agents") or ""
    dev_roles = [r.strip() for r in dev_roles_raw.split(",") if r.strip()]

    def _alias(role):
        val = _parse_field_in_text(aliases_text, role)
        return val if val else role

    def _test_cmd(role):
        # "skill Tests" is the legacy naming — keyed by role name
        return _parse_field_in_text(test_cmd_text, f"{role} Tests")

    result = []

    # PM is always present
    result.append({"id": "pm", "alias": _alias("pm"), "role": "pm"})

    # Dev roles — detect actual role identity from references/roles/
    # Agents like qa, designer have their own role templates and are NOT dev variants.
    known_identities = set()
    roles_dir = REPO_ROOT / "references" / "roles"
    if roles_dir.exists():
        known_identities = {
            d.name for d in roles_dir.iterdir()
            if d.is_dir() and (d / "CLAUDE.md").exists()
        }

    for role in dev_roles:
        # If this role has its own identity (not just dev), use it
        if role in known_identities and role != "dev":
            actual_role = role
        else:
            actual_role = "dev"
        entry = {"id": role, "alias": _alias(role), "role": actual_role}
        cmd = _test_cmd(role)
        if cmd:
            entry["test_command"] = cmd
        result.append(entry)

    # Fixed team: verifier + DM always present (#6261/#6274: qa→verifier per D5)
    seen_ids = {e["id"] for e in result}
    for mandatory_role in ("verifier", "dm"):
        if mandatory_role not in seen_ids:
            result.append({"id": mandatory_role, "alias": _alias(mandatory_role), "role": mandatory_role})

    return result


_AGENT_ENTRY_RE = re.compile(r"^-\s*\*\*([^*]+)\*\*:\s*(.*?)\s*$")
_NESTED_FIELD_RE = re.compile(r"^  -\s*([a-z_][a-z0-9_]*):\s*(.*?)\s*$")
_SETUP_FIELD_RE = re.compile(r"^    -\s*([a-z_][a-z0-9_]*):\s*(.*?)\s*$")


def _strip_yaml_quotes(value):
    """Remove surrounding double quotes if present — matches _quote_if_needed."""
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def _parse_agents_v2(text):
    """Parse the Q-new17 nested agent block.

    Returns a list of dicts with the same shape the wizard writes:
        {id, alias, role, variant, iteration_mode, stack, test_command, setup}
    """
    sections = _parse_sections(text)
    agents_text = sections.get("Agents", "")

    result = []
    current = None
    in_setup = False

    for raw_line in agents_text.splitlines():
        line = raw_line.rstrip()

        # Top-level agent entry line
        m = _AGENT_ENTRY_RE.match(line)
        if m:
            if current is not None:
                result.append(current)
            agent_id = m.group(1).strip()
            alias = _strip_yaml_quotes(m.group(2).strip())
            current = {"id": agent_id, "alias": alias or agent_id}
            in_setup = False
            continue

        if current is None:
            continue

        # `  - setup:` sentinel opens the nested setup block
        if re.match(r"^\s\s-\s*setup:\s*$", line):
            current["setup"] = {}
            in_setup = True
            continue

        # `    - key: value` inside the setup block
        if in_setup:
            sm = _SETUP_FIELD_RE.match(line)
            if sm:
                key = sm.group(1)
                value = _strip_yaml_quotes(sm.group(2))
                current["setup"][key] = value
                continue
            # Anything else closes the setup block
            in_setup = False

        # Nested field directly under the agent (role/variant/.../test_command)
        nm = _NESTED_FIELD_RE.match(line)
        if nm:
            key = nm.group(1)
            value = _strip_yaml_quotes(nm.group(2))
            current[key] = value
            continue

    if current is not None:
        result.append(current)

    return result


def get_agents(text=None):
    """Return the agent list for the active schema.

    Schema is detected via `detect_schema_version`. Callers that just want
    "the agents on this install" should use this — it abstracts the
    legacy vs wizard-shape distinction.
    """
    if text is None:
        text = _read_config()
    if detect_schema_version(text) == 2:
        return _parse_agents_v2(text)
    return _parse_agents_v1(text)


def sync_agents():
    """Scan .squidsquad/*/CLAUDE.md and update config.md Agents section."""
    sqdir = REPO_ROOT / ".squidsquad"
    # Find all roles with CLAUDE.md
    dev_roles = []
    for subdir in sorted(sqdir.iterdir()):
        if not subdir.is_dir():
            continue
        if (subdir / "CLAUDE.md").exists():
            name = subdir.name
            # Fixed team roles are listed separately (#6261/#6274: qa→verifier
            # per D5 — skip BOTH names during the dual-aware migration window
            # so neither leaks into dev_roles regardless of which directory
            # name exists on disk before/after wizard.py D4 rename).
            if name in ("pm", "qa", "verifier", "dm"):
                continue
            dev_roles.append(name)

    # Update config
    if dev_roles:
        set_field("dev-agents", ", ".join(dev_roles))

    # Report — include fixed team roles that have CLAUDE.md (#6274 D5:
    # the verifier directory replaces qa post-rename; during the dual-aware
    # window only one of the two will exist on disk, so check both and
    # report whichever is present).
    roles = dev_roles + ["pm"]
    if (sqdir / "dm" / "CLAUDE.md").exists():
        roles.append("dm")
    if (sqdir / "verifier" / "CLAUDE.md").exists():
        roles.append("verifier")
    elif (sqdir / "qa" / "CLAUDE.md").exists():
        roles.append("qa")
    print(f"Synced agents: {', '.join(roles)}")
    return roles


def dump_all():
    """Dump all config fields as JSON."""
    text = _read_config()
    return _parse_all(text)


def main():
    from cli_stdio import harden_stdio  # #13198: crash-proof CLI stdio (cp1252)
    harden_stdio()
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print(__doc__)
        print("Fields:", ", ".join(sorted(FIELD_MAP.keys())))
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: config.py get <field>", file=sys.stderr)
            sys.exit(1)
        print(get_field(sys.argv[2]))

    elif cmd == "set":
        if len(sys.argv) < 4:
            print("Usage: config.py set <field> <value>", file=sys.stderr)
            sys.exit(1)
        set_field(sys.argv[2], sys.argv[3])
        print(f"Set {sys.argv[2]} = {sys.argv[3]}")

    elif cmd == "alias":
        if len(sys.argv) < 3:
            print("Usage: config.py alias <role>", file=sys.stderr)
            sys.exit(1)
        print(get_alias(sys.argv[2]))

    elif cmd == "dump":
        print(json.dumps(dump_all(), indent=2))

    elif cmd == "sync-agents":
        sync_agents()

    elif cmd == "agents":
        print(json.dumps(get_agents(), indent=2))

    elif cmd == "schema-version":
        print(detect_schema_version())

    elif cmd == "list-agents":
        # Tab-separated columns: id<TAB>role<TAB>alias — one agent per line.
        # Designed for shell consumers (statusline.sh) that can't or
        # shouldn't depend on JSON parsing. Works against both v1 and v2
        # schemas via get_agents().
        for a in get_agents():
            agent_id = a.get("id", "")
            role = a.get("role", "")
            alias = a.get("alias", agent_id)
            print(f"{agent_id}\t{role}\t{alias}")

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
