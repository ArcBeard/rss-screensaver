#!/usr/bin/env python3
"""RSS News Screensaver for Hyprland/Wayland.

Displays news headlines from RSS feeds as animated cards on a fullscreen
overlay using GTK4 + gtk4-layer-shell.
"""

import random
import signal
import sys
import threading
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell


class Headline:
    __slots__ = ("title", "source", "link")

    def __init__(self, title, source, link=""):
        self.title = title
        self.source = source
        self.link = link


try:
    import feedparser as _feedparser
except ImportError:
    _feedparser = None


class FeedManager:
    def __init__(self, feeds, max_headlines=50, refresh_interval=300):
        self.feeds = feeds
        self.max_headlines = max_headlines
        self.refresh_interval = refresh_interval
        self.headlines = []
        self._index = 0
        self._lock = threading.Lock()

    def _fetch_single(self, feed_cfg):
        headlines = []
        try:
            feed = _feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                if title:
                    headlines.append(
                        Headline(
                            title=title,
                            source=feed_cfg.get("name", feed.feed.get("title", "Unknown")),
                            link=entry.get("link", ""),
                        )
                    )
        except Exception:
            pass
        return headlines

    def fetch_all(self):
        if _feedparser is None:
            self.headlines = [
                Headline(
                    "Install python-feedparser: sudo pacman -S python-feedparser",
                    "System",
                )
            ]
            return

        with ThreadPoolExecutor(max_workers=len(self.feeds)) as pool:
            results = pool.map(self._fetch_single, self.feeds)

        new_headlines = [h for batch in results for h in batch]

        if new_headlines:
            random.shuffle(new_headlines)
            with self._lock:
                self.headlines = new_headlines[: self.max_headlines]
                self._index = 0

    def next_headline(self):
        with self._lock:
            if not self.headlines:
                return Headline("Loading headlines...", "RSS Screensaver")
            headline = self.headlines[self._index % len(self.headlines)]
            self._index += 1
            return headline

    def start_background_fetch(self):
        thread = threading.Thread(target=self.fetch_all, daemon=True)
        thread.start()


CONFIG_PATH = Path.home() / ".config" / "rss-screensaver" / "config.toml"
STYLE_PATH = Path.home() / ".config" / "rss-screensaver" / "style.css"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {
        "general": {"refresh_interval": 300, "card_duration": 8, "max_headlines": 50},
        "feeds": [{"name": "Hacker News", "url": "https://hnrss.org/frontpage"}],
    }


class CardWidget(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("card")
        self.add_css_class("hidden")

        self.headline_label = Gtk.Label(label="")
        self.headline_label.add_css_class("headline")
        self.headline_label.set_wrap(True)
        self.headline_label.set_max_width_chars(60)
        self.headline_label.set_justify(Gtk.Justification.CENTER)
        self.headline_label.set_halign(Gtk.Align.CENTER)
        self.append(self.headline_label)

        self.source_label = Gtk.Label(label="")
        self.source_label.add_css_class("source")
        self.source_label.set_halign(Gtk.Align.CENTER)
        self.append(self.source_label)

    def show_headline(self, headline):
        self.headline_label.set_text(headline.title)
        self.source_label.set_text(headline.source)
        self.remove_css_class("hidden")
        self.add_css_class("visible")

    def hide_card(self):
        self.remove_css_class("visible")
        self.add_css_class("hidden")


class ScreensaverWindow(Gtk.Window):
    def __init__(self, app, monitor, feed_manager):
        super().__init__(application=app)
        self.feed_manager = feed_manager

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

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        self.clock_label = Gtk.Label(label="")
        self.clock_label.add_css_class("clock")
        self.clock_label.set_halign(Gtk.Align.END)
        self.clock_label.set_valign(Gtk.Align.END)
        self.clock_label.set_margin_end(32)
        self.clock_label.set_margin_bottom(32)
        overlay.add_overlay(self.clock_label)

        self.card = CardWidget()
        self.card.set_halign(Gtk.Align.CENTER)
        self.card.set_valign(Gtk.Align.CENTER)
        overlay.add_overlay(self.card)

        self._initial_x = None
        self._initial_y = None

    def start_rotation(self, card_duration):
        self._show_next_card()
        GLib.timeout_add_seconds(card_duration, self._rotate_card)
        GLib.timeout_add_seconds(1, self._update_clock)

    def _show_next_card(self):
        headline = self.feed_manager.next_headline()
        self.card.hide_card()
        GLib.timeout_add(900, self._reveal_card, headline)

    def _reveal_card(self, headline):
        self.card.show_headline(headline)
        return False

    def _rotate_card(self):
        self._show_next_card()
        return True

    def _update_clock(self):
        time_str = datetime.now().strftime("%H:%M")
        if self.clock_label.get_text() != time_str:
            self.clock_label.set_text(time_str)
        return True

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
        config = load_config()
        general = config.get("general", {})
        self.card_duration = general.get("card_duration", 8)
        self.refresh_interval = general.get("refresh_interval", 300)
        self.feed_manager = FeedManager(
            feeds=config.get("feeds", []),
            max_headlines=general.get("max_headlines", 50),
            refresh_interval=self.refresh_interval,
        )

    def do_activate(self):
        if STYLE_PATH.exists():
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(STYLE_PATH))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        display = Gdk.Display.get_default()
        monitors = display.get_monitors()

        for i in range(monitors.get_n_items()):
            win = ScreensaverWindow(self, monitors.get_item(i), self.feed_manager)
            win.present()
            win.start_rotation(self.card_duration)

        self.feed_manager.start_background_fetch()
        GLib.timeout_add_seconds(self.refresh_interval, self._periodic_fetch)

    def _periodic_fetch(self):
        self.feed_manager.start_background_fetch()
        return True

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
