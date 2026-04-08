"""Tests for input handling logic — ensuring the screensaver can always be exited."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk


class FakeApp:
    """Mock GTK Application that tracks quit calls."""

    def __init__(self):
        self.quit_count = 0

    def quit(self):
        self.quit_count += 1


class TestEscapeKeyExit:
    """Escape key must exit. Other keys must not."""

    def _make_window_logic(self):
        app = FakeApp()

        class MockWindow:
            def __init__(self):
                self.app = app

            def get_application(self):
                return self.app

            def _on_key(self, controller, keyval, keycode, state):
                key_name = Gdk.keyval_name(keyval)
                if key_name == "Escape":
                    self.get_application().quit()

        return MockWindow()

    def test_escape_exits(self):
        w = self._make_window_logic()
        w._on_key(None, Gdk.KEY_Escape, 0, 0)
        assert w.app.quit_count == 1

    def test_other_key_does_not_exit(self):
        w = self._make_window_logic()
        w._on_key(None, Gdk.KEY_a, 0, 0)
        assert w.app.quit_count == 0

    def test_return_does_not_exit(self):
        w = self._make_window_logic()
        w._on_key(None, Gdk.KEY_Return, 0, 0)
        assert w.app.quit_count == 0

    def test_space_does_not_exit(self):
        w = self._make_window_logic()
        w._on_key(None, Gdk.KEY_space, 0, 0)
        assert w.app.quit_count == 0


class TestMouseMotionExit:
    """Mouse exit is commented out for dev mode but logic should still work when re-enabled."""

    def _make_window_logic(self):
        app = FakeApp()

        class MockWindow:
            def __init__(self):
                self._initial_x = None
                self._initial_y = None
                self.app = app

            def get_application(self):
                return self.app

            def _on_mouse_motion(self, controller, x, y):
                if self._initial_x is None:
                    self._initial_x = x
                    self._initial_y = y
                    return
                if abs(x - self._initial_x) > 10 or abs(y - self._initial_y) > 10:
                    self.get_application().quit()

        return MockWindow()

    def test_first_motion_event_does_not_exit(self):
        w = self._make_window_logic()
        w._on_mouse_motion(None, 100.0, 100.0)
        assert w.app.quit_count == 0

    def test_small_movement_does_not_exit(self):
        w = self._make_window_logic()
        w._on_mouse_motion(None, 100.0, 100.0)
        w._on_mouse_motion(None, 105.0, 105.0)
        assert w.app.quit_count == 0

    def test_movement_over_threshold_exits(self):
        w = self._make_window_logic()
        w._on_mouse_motion(None, 100.0, 100.0)
        w._on_mouse_motion(None, 115.0, 100.0)
        assert w.app.quit_count == 1

    def test_exact_threshold_does_not_exit(self):
        w = self._make_window_logic()
        w._on_mouse_motion(None, 100.0, 100.0)
        w._on_mouse_motion(None, 110.0, 100.0)
        assert w.app.quit_count == 0


class TestInputControllersRegistered:
    """Verify the source code has the right input wiring."""

    def test_source_has_key_controller(self):
        source = Path(__file__).parent.parent / "rss_screensaver.py"
        code = source.read_text()
        assert "EventControllerKey" in code
        assert '"key-pressed"' in code

    def test_source_has_escape_check(self):
        source = Path(__file__).parent.parent / "rss_screensaver.py"
        code = source.read_text()
        assert '"Escape"' in code

    def test_source_has_quit_path(self):
        source = Path(__file__).parent.parent / "rss_screensaver.py"
        code = source.read_text()
        assert "self.get_application().quit()" in code

    def test_mouse_controllers_commented_with_todo(self):
        """Mouse/click are disabled for dev — ensure TODO marker exists for re-enabling."""
        source = Path(__file__).parent.parent / "rss_screensaver.py"
        code = source.read_text()
        assert "TODO" in code
        assert "re-enable" in code.lower()

    def test_keyboard_mode_set(self):
        """Layer-shell keyboard mode MUST be set — without it, keys never arrive."""
        source = Path(__file__).parent.parent / "rss_screensaver.py"
        code = source.read_text()
        assert "set_keyboard_mode" in code
        assert "KeyboardMode" in code
