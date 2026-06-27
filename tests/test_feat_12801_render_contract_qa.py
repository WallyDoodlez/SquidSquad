"""QA independent action-bar contract check for #12801 — asserts the harness
TUI's bottom action bar (BINDINGS) advertises the reboot actions: reboot (AC1),
reboot-all (AC2), and a distinct force reboot (AC5).

Independent of skill's test_tui_render_12801.py (which drives the live Pilot
render): this is a robust static contract on the App's declared BINDINGS, so it
stays green regardless of Textual's run_test internals. Authored by verifier (qa);
preserved permanently. Skips if textual / the tui package is unavailable.
"""
import importlib
import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

try:
    _app_mod = importlib.import_module("tui.app")
    import textual  # noqa: F401
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


@unittest.skipUnless(_AVAILABLE, "textual / tui.app unavailable")
class TestActionBarContract12801(unittest.TestCase):
    def _app_class(self):
        for _, obj in inspect.getmembers(_app_mod, inspect.isclass):
            if obj.__module__ == "tui.app" and hasattr(obj, "run_test"):
                return obj
        return None

    @staticmethod
    def _binding_descriptions(App):
        """Textual BINDINGS entries may be Binding objects (`.description`) or
        plain tuples `(key, action, description)`."""
        out = []
        for b in getattr(App, "BINDINGS", []):
            desc = getattr(b, "description", None)
            if desc is None and isinstance(b, (tuple, list)):
                desc = b[2] if len(b) > 2 else (b[1] if len(b) > 1 else "")
            out.append(str(desc or "").lower())
        return out

    def test_action_bar_advertises_reboot_actions(self):
        App = self._app_class()
        self.assertIsNotNone(App, "no Textual App subclass found in tui.app")
        descs = self._binding_descriptions(App)
        self.assertTrue(descs, "the App must declare BINDINGS (the action bar)")

        self.assertTrue(any("reboot" in d for d in descs),
                        "action bar must advertise reboot (AC1)")
        self.assertTrue(any("all" in d for d in descs),
                        "action bar must advertise reboot-all (AC2)")
        self.assertTrue(any("force" in d for d in descs),
                        "action bar must advertise a distinct force reboot (AC5)")


if __name__ == "__main__":
    unittest.main()
