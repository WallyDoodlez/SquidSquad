"""E3: L4-write file-watch + restart-required event (#10682, PRD-E Story E3).

Layer 2 of the compose-freshness chain. The harness file-watches
``.squidsquad/project/`` for L4 commits. On any write to a role-class
file (e.g. ``.squidsquad/project/pm.md``):

1. Identify every alias bound to that role-class via the
   ``.squidsquad/config.md`` ``## Aliases`` registry.
2. For each affected alias, run ``compose.py deploy <alias>``.
3. Per-alias outcome:
   - **Success** -> emit ``assigned-to(target_alias=<alias>,
     event_context="restart-required", payload={reason:"l4-recompose"})``
     per AGENT-RUNTIME §8.5 catalog-trim translators.
   - **Failure** -> emit ``assigned-to(target_alias=<alias>,
     event_context="compose-failed", payload={reason:"l4-recompose",
     stderr:<truncated>})``. Agents stay on their existing CLAUDE.md
     until a successful recompose lands.

The module is structured so the **pure logic** (alias filtering, per-
alias recompose, event payload construction) is testable without the
watchdog library installed; the ``watchdog``-based ``Observer`` shell
is built on top of those functions and imported lazily so unit tests
on the pure surface never trigger the watchdog import.

Per PRD §8 Q-E1, ``watchdog`` is the cross-platform default; the
harness can substitute a platform-native fallback later if reliability
surfaces issues.

Per PRD §8 Q-E2, the file-watch is the **primary** trigger; an
optional ``.git/hooks/post-commit`` script can call ``recompose_path``
directly for human-driven L4 edits made outside the agent dialog.
"""

import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


WATCH_SUBDIR = ".squidsquad/project"
"""Path under repo root that the file-watch covers."""

DEFAULT_DEBOUNCE_SECONDS = 0.5
"""Coalesce multiple writes within this window into one recompose run.

Editor "save" sequences often produce multiple FS events (write, atomic-
replace, attribute-touch). The debounce window collapses those to a
single recompose per role-class file.
"""

_COMPOSE_FAILED_STDERR_MAX = 4000
"""Cap the stderr blob in compose-failed events so the event bus doesn't
balloon on a 10MB pyyaml stack trace."""


@dataclass
class RecomposeResult:
    """Per-alias outcome of a single recompose attempt.

    Built by ``recompose_for_role_class`` for each alias bound to the
    changed role-class. The caller (file-watch handler) emits exactly
    one event per result.
    """

    alias: str
    role_class: str
    succeeded: bool
    event_type: str = "assigned-to"
    event_context: str = ""
    payload: dict = field(default_factory=dict)


def role_class_from_path(path, *, repo_root):
    """Return the role-class for an L4 file path, or ``None`` if the
    path is not a watched role-class file.

    Watched: ``<repo_root>/.squidsquad/project/<role-class>.md``. Files
    under ``.squidsquad/project/`` that are NOT a bare ``<name>.md``
    (e.g. subdirs, tempfiles starting with ``.``, or non-``.md``
    extensions) return ``None`` so the watcher can ignore them without
    triggering compose runs.
    """
    path = Path(path)
    repo_root = Path(repo_root)
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) != 3:
        return None
    if parts[0] != ".squidsquad" or parts[1] != "project":
        return None
    name = parts[2]
    if not name.endswith(".md"):
        return None
    stem = name[:-3]
    if not stem or stem.startswith("."):
        return None
    return stem


def compute_affected_aliases(role_class, registry):
    """Return the sorted list of aliases bound to ``role_class``.

    ``registry`` is the parsed ``## Aliases`` table — a mapping
    ``{alias: (role_class, l3_domain)}`` per
    ``config.parse_aliases_registry``. An alias is "affected" when its
    registry entry's role-class matches ``role_class``; the L3 domain
    is not part of the match because every alias under that role-class
    consumes the same L4 file (per PRD §8.2).

    Returns ``[]`` (not ``None``) when no alias matches — the caller
    treats that as "no agents to restart" and emits no events.
    """
    return sorted(
        alias
        for alias, (rc, _l3) in registry.items()
        if rc == role_class
    )


def recompose_for_role_class(
    role_class,
    registry,
    *,
    run_compose,
):
    """Run compose for every affected alias and return one result per alias.

    ``run_compose(alias)`` is injected so the pure logic can be tested
    against a stub. The real binding lives in ``_default_run_compose``
    below and shells out to ``compose.py deploy <alias>``.

    Per AC5 failure-mode rule: a compose failure for one alias does
    NOT emit ``restart-required`` for that alias and does NOT halt
    iteration over the remaining aliases. Each alias's outcome is
    independent.
    """
    results = []
    for alias in compute_affected_aliases(role_class, registry):
        try:
            outcome = run_compose(alias)
        except Exception as exc:  # noqa: BLE001 — any unexpected raise is a failure
            outcome = (False, "", f"compose runner raised: {exc!r}")
        ok, _stdout, stderr = outcome
        if ok:
            results.append(RecomposeResult(
                alias=alias,
                role_class=role_class,
                succeeded=True,
                event_context="restart-required",
                payload={"reason": "l4-recompose"},
            ))
        else:
            truncated = (stderr or "")[:_COMPOSE_FAILED_STDERR_MAX]
            results.append(RecomposeResult(
                alias=alias,
                role_class=role_class,
                succeeded=False,
                event_context="compose-failed",
                payload={
                    "reason": "l4-recompose",
                    "stderr": truncated,
                },
            ))
    return results


def emit_results(results, *, emit_event):
    """Emit one ``assigned-to`` event per :class:`RecomposeResult`.

    ``emit_event(event_type, role, payload=..., **extra)`` matches the
    in-harness ``_emit_event`` signature so the file-watch wires
    straight into ``harness._emit_event`` at integration time.
    ``target_alias`` and ``event_context`` are passed as ``payload``
    fields per the AGENT-RUNTIME §8.5 schema for ``assigned-to``
    (where ``target_alias`` is a top-level field on the event payload
    that the harness uses for the alias-care filter).

    Dual-emit note: the mainstream EAD path in ``harness.py`` currently
    emits ``payload.target_role`` (legacy field name pre-#6274 dev→worker
    rename) and the ``/events/for/{role}`` filter at ``harness.py:2181``
    reads the same legacy field. Until the harness catches up to the
    canonical ``target_alias`` field name from AGENT-RUNTIME §8 (follow-up
    tracker issue filed in polish-session), we emit BOTH fields with the
    same alias value so the harness filter actually picks up our events.
    Without the dual emit, file-watch ``assigned-to`` events are silently
    dropped from the per-role filter stream.
    """
    for r in results:
        emit_event(
            r.event_type,
            "harness",
            payload={
                **r.payload,
                "target_alias": r.alias,
                "target_role": r.alias,
                "event_context": r.event_context,
            },
        )


def _default_run_compose(alias, *, repo_root):
    """Shell out to ``compose.py deploy <alias>`` and return (ok, stdout, stderr).

    Lives behind ``run_compose=`` injection so tests never spawn a
    Python subprocess just to validate the wrapping logic.
    """
    cmd = [
        sys.executable,
        str(Path(repo_root) / "references" / "scripts" / "compose.py"),
        "deploy",
        alias,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    return proc.returncode == 0, proc.stdout, proc.stderr


def recompose_path(
    path,
    *,
    repo_root,
    registry,
    emit_event,
    run_compose=None,
):
    """Handle a single L4 file change end-to-end.

    Public entry point for both the file-watch handler AND the optional
    ``.git/hooks/post-commit`` script per Q-E2. Returns the list of
    :class:`RecomposeResult` records emitted (callers can log them).

    Returns ``[]`` when ``path`` is not a watched role-class file —
    the watcher uses this as the "ignore unrelated change" signal
    that drives the AC6 test about temp files.
    """
    role_class = role_class_from_path(path, repo_root=repo_root)
    if role_class is None:
        return []
    if run_compose is None:
        def run_compose(alias):
            return _default_run_compose(alias, repo_root=repo_root)
    results = recompose_for_role_class(
        role_class, registry, run_compose=run_compose,
    )
    emit_results(results, emit_event=emit_event)
    return results


# ---------------------------------------------------------------------------
# Debounce wrapper — shared by the watchdog Observer shell and by tests
# that want to validate the coalesce-multiple-writes-into-one-recompose
# behavior without monkey-patching ``threading.Timer``.
# ---------------------------------------------------------------------------


class _Debouncer:
    """Per-key timer that fires ``callback(key)`` once the key has been
    idle for ``window_seconds``.

    Thread-safe: events arrive on watchdog's worker thread; the
    callback runs on a ``threading.Timer`` thread. Cancel-and-replace
    is the coalescing primitive — every ``schedule(key)`` call resets
    the timer for that key, so a burst of writes within ``window``
    produces exactly one ``callback`` invocation per key.

    Race safety (DS-E3 review F1): a generation counter pinned to
    each scheduled timer guards the cancel-vs-fire window. A timer
    whose generation no longer matches the latest stored generation
    is **stale** and exits without firing. Without this guard, a
    burst pattern where T1 enters ``_fire`` then T2 is scheduled
    before T1 acquires the lock would produce two callback
    invocations instead of one.
    """

    def __init__(self, window_seconds, callback):
        self._window = window_seconds
        self._callback = callback
        # generation -> (gen:int, timer:threading.Timer)
        self._timers = {}
        self._lock = threading.Lock()

    def schedule(self, key):
        with self._lock:
            entry = self._timers.get(key)
            if entry is not None:
                entry[1].cancel()
                gen = entry[0] + 1
            else:
                gen = 1
            timer = threading.Timer(
                self._window, self._fire, args=(key, gen))
            timer.daemon = True
            self._timers[key] = (gen, timer)
            timer.start()

    def _fire(self, key, generation):
        with self._lock:
            entry = self._timers.get(key)
            if entry is None or entry[0] != generation:
                # Stale: a newer schedule replaced us. Caller will
                # arrive via the newer timer's _fire — drop this one.
                return
            self._timers.pop(key, None)
        try:
            self._callback(key)
        except Exception as exc:  # noqa: BLE001 — log + survive
            print(
                f"WARNING: l4_file_watcher debounce callback for "
                f"{key!r} raised: {exc!r}",
                file=sys.stderr,
            )

    def flush(self):
        """Cancel all pending timers (used at watcher shutdown).

        Does NOT fire the callback for pending keys — at shutdown we
        no longer have a running watch to react to results.
        """
        with self._lock:
            for _gen, t in self._timers.values():
                t.cancel()
            self._timers.clear()


def make_change_callback(
    *,
    repo_root,
    registry_provider,
    emit_event,
    run_compose=None,
):
    """Build the callback the watcher/debouncer hands a role-class to.

    ``registry_provider()`` is called fresh on every change so a mid-
    session edit to ``config.md`` (e.g. an alias added) is reflected
    immediately. Static-binding the registry at watcher-start time
    would silently miss new aliases until the harness restarts.

    Returns a callable that takes ``role_class`` and runs the full
    recompose-and-emit sequence for it. Used as the debounce
    callback so the burst of writes a single editor save produces
    collapses to one recompose.
    """
    def _on_change(role_class):
        try:
            registry = registry_provider()
        except Exception as exc:  # noqa: BLE001 — registry parse failure
            # Emit a single compose-failed targeted at PM (per AGENT-
            # RUNTIME §8.5 "compose-needed" / "compose-failed" land in
            # PM's inbox) so the registry breakage surfaces.
            emit_event(
                "assigned-to",
                "harness",
                payload={
                    "target_alias": "pm",
                    "event_context": "compose-failed",
                    "reason": "registry-unreadable",
                    "stderr": f"registry parse failed: {exc!r}"[
                        :_COMPOSE_FAILED_STDERR_MAX
                    ],
                },
            )
            return
        resolved_compose = run_compose
        if resolved_compose is None:
            def resolved_compose(alias):
                return _default_run_compose(alias, repo_root=repo_root)
        results = recompose_for_role_class(
            role_class, registry, run_compose=resolved_compose,
        )
        emit_results(results, emit_event=emit_event)
    return _on_change


def start_watcher(
    *,
    repo_root,
    registry_provider,
    emit_event,
    run_compose=None,
    debounce_seconds=DEFAULT_DEBOUNCE_SECONDS,
):
    """Start a ``watchdog.Observer`` watching ``.squidsquad/project/``.

    Returns ``(observer, debouncer)`` — the harness owns lifecycle and
    must call ``observer.stop() + observer.join() + debouncer.flush()``
    at shutdown. ``watchdog`` is imported lazily so unit tests on the
    pure logic surface above never require it.

    Per AC5: if the observer thread dies, the harness logs + restarts
    the watcher. This function only constructs and starts the observer;
    the survive-and-restart loop lives in the harness.
    """
    try:
        from watchdog.observers import Observer  # lazy import per AC5
        from watchdog.events import FileSystemEventHandler
    except ImportError as exc:
        raise RuntimeError(
            "watchdog is required for L4 file-watch (PRD-E Q-E1). "
            "Install with `pip install watchdog`."
        ) from exc

    repo_root = Path(repo_root)
    watch_path = repo_root / WATCH_SUBDIR
    watch_path.mkdir(parents=True, exist_ok=True)

    on_change = make_change_callback(
        repo_root=repo_root,
        registry_provider=registry_provider,
        emit_event=emit_event,
        run_compose=run_compose,
    )
    debouncer = _Debouncer(debounce_seconds, on_change)

    class _Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            # Directory events have no useful src_path for our purpose;
            # rg-style filtering keeps us in the watched-file lane.
            if event.is_directory:
                return
            role_class = role_class_from_path(
                event.src_path, repo_root=repo_root)
            if role_class is None:
                return
            debouncer.schedule(role_class)

    observer = Observer()
    observer.schedule(_Handler(), str(watch_path), recursive=True)
    observer.start()
    return observer, debouncer
