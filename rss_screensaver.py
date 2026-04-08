#!/usr/bin/env python3
"""RSS News Screensaver for Hyprland/Wayland.

Displays news headlines from RSS feeds as animated cards on a fullscreen
overlay using GTK4 + gtk4-layer-shell.
"""

import signal
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell


class ScreensaverWindow(Gtk.Window):
    def __init__(self, app, monitor):
        super().__init__(application=app)

        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_monitor(self, monitor)
        Gtk4LayerShell.set_exclusive_zone(self, -1)
        for edge in (
            Gtk4LayerShell.Edge.TOP,
            Gtk4LayerShell.Edge.BOTTOM,
            Gtk4LayerShell.Edge.LEFT,
            Gtk4LayerShell.Edge.RIGHT,
        ):
            Gtk4LayerShell.set_anchor(self, edge, True)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_input)
        self.add_controller(key_ctrl)

        motion_ctrl = Gtk.EventControllerMotion()
        motion_ctrl.connect("motion", self._on_mouse_motion)
        self.add_controller(motion_ctrl)

        click_ctrl = Gtk.GestureClick()
        click_ctrl.connect("pressed", self._on_input)
        self.add_controller(click_ctrl)

        self._initial_x = None
        self._initial_y = None

    def _on_input(self, *args):
        self.get_application().quit()

    def _on_mouse_motion(self, controller, x, y):
        if self._initial_x is None:
            self._initial_x = x
            self._initial_y = y
            return
        if abs(x - self._initial_x) > 10 or abs(y - self._initial_y) > 10:
            self.get_application().quit()


# Safety timeout: auto-exit after this many seconds to prevent lockouts.
# If input events fail to register (compositor bug, layer-shell issue),
# the screensaver will still exit on its own.
SAFETY_TIMEOUT_SECONDS = 1800  # 30 minutes


class RSSScreensaverApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.rss.screensaver")

    def do_activate(self):
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()

        for i in range(monitors.get_n_items()):
            win = ScreensaverWindow(self, monitors.get_item(i))
            win.present()

        GLib.timeout_add_seconds(SAFETY_TIMEOUT_SECONDS, self._safety_exit)

    def _safety_exit(self):
        self.quit()
        return False


def main():
    app = RSSScreensaverApp()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, app.quit)
    app.run(None)


if __name__ == "__main__":
    main()
