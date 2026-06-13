"""Tests for #11587 — uvicorn must not impose a ProactorEventLoop on Windows.

Background: #9562 set ``WindowsSelectorEventLoopPolicy`` in ``harness.main()``
to dodge the ProactorEventLoop ``ConnectionResetError`` (WinError 10054) HTTP
wedge. But the exception kept recurring (#11587): uvicorn's default
``loop="auto"`` resolves (no uvloop on Windows) to
``uvicorn.loops.asyncio.asyncio_loop_factory``, which HARD-CODES
``asyncio.ProactorEventLoop`` on win32 — bypassing the event-loop *policy*
entirely. So the server loop that actually runs in uvicorn's daemon thread is a
ProactorEventLoop regardless of the main-thread policy.

Fix (#11587): the harness builds its uvicorn Config via
``_build_uvicorn_config()``, which sets ``loop="none"``. That makes uvicorn pass
``loop_factory=None`` to ``asyncio.run``, which creates the loop via
``asyncio.new_event_loop()`` — respecting the policy and yielding a
SelectorEventLoop.

These tests pin BOTH the behavioral contract (the harness Config's loop factory
is ``None``) and the rationale (the default ``loop="auto"`` WOULD yield a
ProactorEventLoop on win32), plus the source wiring (``main()`` uses the helper
so the fix can't be silently reverted to an inline ``uvicorn.Config(...)``).
"""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
HARNESS_PATH = SCRIPTS / "harness.py"


def _load_module(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    if not (spec and spec.loader):
        raise ImportError(f"cannot build spec for {source}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _harness = _load_module("_harness_for_11587", HARNESS_PATH)
    HARNESS_AVAILABLE = True
except Exception as _e:  # pragma: no cover - env-dependent
    print(
        f"[test_11587] harness import failed: {type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    HARNESS_AVAILABLE = False
    _harness = None  # type: ignore


async def _dummy_app(scope, receive, send):  # pragma: no cover - never called
    pass


@unittest.skipUnless(HARNESS_AVAILABLE, "harness.py could not be imported here")
class TestHarnessUvicornLoopFactory(unittest.TestCase):
    def _config(self):
        return _harness._build_uvicorn_config(_dummy_app, host="127.0.0.1", port=0)

    def test_harness_config_loop_is_none(self):
        """The harness Config must set ``loop="none"`` so uvicorn does not
        impose its own (win32-Proactor) loop factory."""
        self.assertEqual(self._config().loop, "none")

    def test_harness_config_loop_factory_is_none(self):
        """``loop="none"`` -> ``get_loop_factory()`` returns None -> uvicorn
        passes ``loop_factory=None`` to ``asyncio.run``, which builds the loop
        via ``new_event_loop()`` and so respects the #9562
        ``WindowsSelectorEventLoopPolicy``. This None is the whole fix (#11587)."""
        self.assertIsNone(self._config().get_loop_factory())

    def test_default_auto_loop_would_be_proactor_on_win32(self):
        """Rationale lock: prove the bug is real and ``loop="none"`` is
        load-bearing. The DEFAULT ``loop="auto"`` resolves to a
        ProactorEventLoop factory on win32 — exactly what bypasses the policy.
        (No-op off win32, where the factory is Selector anyway.)"""
        import uvicorn

        auto_factory = uvicorn.Config(
            _dummy_app, host="127.0.0.1", port=0
        ).get_loop_factory()
        if sys.platform != "win32":
            self.skipTest("ProactorEventLoop factory is win32-specific")
        self.assertIsNotNone(
            auto_factory,
            msg="expected uvicorn loop='auto' to yield a concrete factory on win32",
        )
        loop = auto_factory()
        try:
            self.assertEqual(
                type(loop).__name__,
                "ProactorEventLoop",
                msg=(
                    "uvicorn loop='auto' should hard-code ProactorEventLoop on "
                    "win32 — if this changed, the #11587 rationale needs review."
                ),
            )
        finally:
            loop.close()

    def test_none_factory_under_policy_yields_selector_on_win32(self):
        """End-to-end net effect on win32: with the loop factory deferred (None,
        from our Config) AND the #9562 policy set, the loop asyncio creates is a
        Selector loop — never Proactor."""
        if sys.platform != "win32":
            self.skipTest("Selector-vs-Proactor distinction is win32-specific")
        self.assertIsNone(self._config().get_loop_factory())
        prev = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        try:
            loop = asyncio.new_event_loop()
            try:
                name = type(loop).__name__
                self.assertNotIn("Proactor", name)
                self.assertIn("Selector", name)
            finally:
                loop.close()
        finally:
            asyncio.set_event_loop_policy(prev)


class TestHarnessUvicornLoopWiring(unittest.TestCase):
    """Source-level wiring: ``main()`` must build its Config via the helper, so
    the ``loop="none"`` fix cannot be silently bypassed by reverting to an
    inline ``uvicorn.Config(...)`` call."""

    def setUp(self):
        self.source = HARNESS_PATH.read_text(encoding="utf-8")

    def test_main_uses_build_uvicorn_config_helper(self):
        self.assertIn(
            "_build_uvicorn_config(",
            self.source,
            msg="main() must construct its uvicorn Config via _build_uvicorn_config().",
        )

    def test_helper_sets_loop_none(self):
        self.assertRegex(
            self.source,
            r'loop\s*=\s*["\']none["\']',
            msg='_build_uvicorn_config must set loop="none" (#11587).',
        )
