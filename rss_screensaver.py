#!/usr/bin/env python3
"""RSS News Screensaver for Hyprland/Wayland.

Displays news headlines from RSS feeds as animated cards on a fullscreen
overlay using GTK4 + gtk4-layer-shell. Supports swappable layout themes.
"""

import logging
import os
import random
import signal
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import json

STATE_DIR = Path.home() / ".local" / "state" / "rss-screensaver"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = STATE_DIR / "screensaver.log"
CACHE_PATH = STATE_DIR / "headlines.json"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("rss-screensaver")


@contextmanager
def timed(label):
    """Log how long a block takes. Warns if > 1s (main-loop-blocking territory)."""
    start = time.monotonic()
    yield
    elapsed = time.monotonic() - start
    if elapsed > 1.0:
        log.warning("SLOW: %s took %.2fs (>1s blocks main loop!)", label, elapsed)
    else:
        log.debug("timing: %s took %.3fs", label, elapsed)

# gtk4-layer-shell must be loaded before libwayland
if "LD_PRELOAD" not in os.environ or "libgtk4-layer-shell" not in os.environ.get("LD_PRELOAD", ""):
    os.environ["LD_PRELOAD"] = "/usr/lib/libgtk4-layer-shell.so"
    os.execvp(sys.executable, [sys.executable] + sys.argv)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell

from layouts import get_css_path, load_layout

CONFIG_PATH = Path.home() / ".config" / "rss-screensaver" / "config.toml"
STYLE_PATH = Path.home() / ".config" / "rss-screensaver" / "style.css"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {
        "general": {
            "refresh_interval": 300,
            "card_duration": 8,
            "max_headlines": 50,
            "layout": "newspaper",
        },
        "feeds": [{"name": "Hacker News", "url": "https://hnrss.org/frontpage"}],
    }


class Headline:
    __slots__ = ("title", "source", "link", "summary", "description")

    def __init__(self, title, source, link="", summary="", description=""):
        self.title = title
        self.source = source
        self.link = link
        self.summary = summary
        self.description = description


def save_cache(headlines):
    try:
        data = [
            {"title": h.title, "source": h.source, "link": h.link,
             "summary": h.summary, "description": h.description}
            for h in headlines
        ]
        CACHE_PATH.write_text(json.dumps(data))
        log.debug("cache saved: %d headlines to %s", len(data), CACHE_PATH)
    except OSError as e:
        log.warning("cache save failed: %s", e)


def load_cache():
    try:
        if CACHE_PATH.exists():
            data = json.loads(CACHE_PATH.read_text())
            headlines = [Headline(**d) for d in data]
            log.info("cache loaded: %d headlines from %s", len(headlines), CACHE_PATH)
            return headlines
    except (OSError, json.JSONDecodeError, TypeError) as e:
        log.warning("cache load failed: %s", e)
    return []


try:
    import feedparser as _feedparser
except ImportError:
    _feedparser = None

import html
import re
import shutil
import subprocess


def _strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _get_entry_text(entry):
    """Extract the best available text content from a feed entry."""
    for field in ("summary", "description", "content"):
        val = entry.get(field, "")
        if isinstance(val, list):
            val = val[0].get("value", "") if val else ""
        text = _strip_html(val)
        if len(text) > 50:
            return text
    return entry.get("title", "")


class FabricSummarizer:
    """Runs Fabric patterns on text to generate summaries."""

    _OLLAMA_CHECK_TTL = 300  # Cache ollama ps result for 5 minutes
    _MAX_CACHE_SIZE = 500

    def __init__(self, pattern="summarize_micro", enabled=True, model=None):
        self.pattern = pattern
        self.model = model
        self.enabled = enabled and shutil.which("fabric") is not None
        self._cache = {}
        self._ollama_available = None
        self._ollama_checked_at = 0

    def _is_ollama_available(self):
        """Check if Ollama is free or already has our model loaded (cached)."""
        import time
        now = time.monotonic()
        if self._ollama_available is not None and (now - self._ollama_checked_at) < self._OLLAMA_CHECK_TTL:
            log.debug("ollama check cached: available=%s", self._ollama_available)
            return self._ollama_available
        try:
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                log.warning("ollama ps returned %d, assuming available", result.returncode)
                available = True
            else:
                lines = result.stdout.strip().splitlines()
                if len(lines) <= 1:
                    log.debug("no model loaded in ollama")
                    available = True
                else:
                    loaded_model = lines[1].split()[0]
                    target = self.model or ""
                    available = loaded_model == target
                    log.info("ollama model loaded=%s, target=%s, available=%s", loaded_model, target, available)
        except (subprocess.TimeoutExpired, OSError, IndexError) as e:
            log.warning("ollama check failed: %s, assuming available", e)
            available = True
        self._ollama_available = available
        self._ollama_checked_at = now
        return available

    def summarize(self, headline):
        if not self.enabled or not headline.description:
            return
        cache_key = headline.link or headline.title
        if cache_key in self._cache:
            headline.summary = self._cache[cache_key]
            return
        try:
            cmd = ["fabric", "-p", self.pattern]
            if self.model:
                cmd.extend(["-m", self.model])
            result = subprocess.run(
                cmd,
                input=headline.description,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                summary = self._extract_summary(result.stdout)
                headline.summary = summary
                if len(self._cache) >= self._MAX_CACHE_SIZE:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[cache_key] = summary
        except (subprocess.TimeoutExpired, OSError):
            pass

    def summarize_next_page(self, headlines, page_size):
        """Summarize only the next page_size headlines that lack summaries."""
        if not self.enabled:
            return
        if not self._is_ollama_available():
            log.debug("skipping summarization — ollama busy")
            return
        to_process = [h for h in headlines[:page_size] if h.description and not h.summary]
        log.debug("summarizing %d/%d headlines", len(to_process), page_size)
        for headline in to_process:
            self.summarize(headline)

    @staticmethod
    def _extract_summary(output):
        """Pull the one-sentence summary from Fabric output."""
        lines = output.strip().splitlines()
        capture = False
        for line in lines:
            if "ONE SENTENCE SUMMARY" in line.upper():
                capture = True
                continue
            if capture and line.strip():
                return line.strip()
        # Fallback: first non-empty, non-header line
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:200]
        return output.strip()[:200]


class FeedManager:
    def __init__(self, feeds, max_headlines=50, refresh_interval=300):
        self.feeds = feeds
        self.max_headlines = max_headlines
        self.refresh_interval = refresh_interval
        self.headlines = load_cache()[:max_headlines]
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
                            description=_get_entry_text(entry),
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

        with timed("feed_fetch_all"):
            with ThreadPoolExecutor(max_workers=len(self.feeds)) as pool:
                results = pool.map(self._fetch_single, self.feeds)
            new_headlines = [h for batch in results for h in batch]

        log.info("fetched %d headlines from %d feeds", len(new_headlines), len(self.feeds))

        if new_headlines:
            random.shuffle(new_headlines)
            with self._lock:
                self.headlines = new_headlines[: self.max_headlines]
                self._index = 0
            save_cache(self.headlines)

    def next_headline(self):
        with self._lock:
            if not self.headlines:
                return Headline("Loading headlines...", "RSS Screensaver")
            headline = self.headlines[self._index % len(self.headlines)]
            self._index += 1
            return headline

    def get_headlines(self, n):
        with self._lock:
            if not self.headlines:
                return [Headline("Loading headlines...", "RSS Screensaver")]
            start = self._index % len(self.headlines)
            result = []
            for i in range(n):
                result.append(self.headlines[(start + i) % len(self.headlines)])
            self._index = (start + n) % len(self.headlines)
            return result

    def peek_headlines(self, n):
        """Return the next n headlines without advancing the index."""
        with self._lock:
            if not self.headlines:
                return []
            start = self._index % len(self.headlines)
            return [self.headlines[(start + i) % len(self.headlines)] for i in range(n)]

    def start_background_fetch(self):
        thread = threading.Thread(target=self.fetch_all, daemon=True)
        thread.start()


class ScreensaverWindow(Gtk.Window):
    def __init__(self, app, monitor, feed_manager, layout_cls, summarizer=None):
        super().__init__(application=app)
        self.feed_manager = feed_manager
        self.layout_cls = layout_cls
        self.summarizer = summarizer

        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)
        Gtk4LayerShell.set_monitor(self, monitor)
        Gtk4LayerShell.set_exclusive_zone(self, -1)
        for edge in (
            Gtk4LayerShell.Edge.TOP,
            Gtk4LayerShell.Edge.BOTTOM,
            Gtk4LayerShell.Edge.LEFT,
            Gtk4LayerShell.Edge.RIGHT,
        ):
            Gtk4LayerShell.set_anchor(self, edge, True)

        log.info("window init: monitor=%s, layer=OVERLAY, keyboard=ON_DEMAND", monitor.get_connector())

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        self.add_controller(key_ctrl)

        # TODO: re-enable mouse/click exit when used as actual screensaver
        # motion_ctrl = Gtk.EventControllerMotion()
        # motion_ctrl.connect("motion", self._on_mouse_motion)
        # self.add_controller(motion_ctrl)

        # click_ctrl = Gtk.GestureClick()
        # click_ctrl.connect("pressed", self._on_input)
        # self.add_controller(click_ctrl)
        log.debug("input controllers registered: key (Escape to exit)")

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        self.clock_label = Gtk.Label(label="")
        self.clock_label.add_css_class("clock")
        self.clock_label.set_halign(Gtk.Align.END)
        self.clock_label.set_valign(Gtk.Align.END)
        self.clock_label.set_margin_end(32)
        self.clock_label.set_margin_bottom(32)
        overlay.add_overlay(self.clock_label)

        # Scale headlines to monitor size — portrait monitors need more
        base = getattr(layout_cls, "HEADLINES_PER_PAGE", 1)
        geo = monitor.get_geometry()
        aspect = geo.width / max(geo.height, 1)
        if aspect < 0.8:  # portrait
            self.headlines_per_page = int(base * 1.8)
        elif aspect > 2.0:  # ultrawide
            self.headlines_per_page = int(base * 1.2)
        else:
            self.headlines_per_page = base
        log.debug("monitor %s: %dx%d aspect=%.2f headlines=%d",
                  monitor.get_connector(), geo.width, geo.height, aspect, self.headlines_per_page)

        headlines = feed_manager.get_headlines(self.headlines_per_page)
        self.layout = layout_cls(headlines)
        self.layout.set_halign(Gtk.Align.FILL)
        self.layout.set_valign(Gtk.Align.FILL)
        self.layout.set_hexpand(True)
        self.layout.set_vexpand(True)
        overlay.add_overlay(self.layout)

        self._initial_x = None
        self._initial_y = None

    def start_rotation(self, card_duration):
        GLib.timeout_add_seconds(card_duration, self._rotate)
        GLib.timeout_add_seconds(1, self._update_clock)

    def _rotate(self):
        with timed("rotate"):
            n = self.headlines_per_page
            headlines = self.feed_manager.get_headlines(n)
            self.layout.update(headlines)
        if self.summarizer:
            upcoming = self.feed_manager.peek_headlines(n)
            thread = threading.Thread(
                target=self.summarizer.summarize_next_page,
                args=(upcoming, n),
                daemon=True,
            )
            thread.start()
        return True

    def _update_clock(self):
        time_str = datetime.now().strftime("%H:%M")
        if self.clock_label.get_text() != time_str:
            self.clock_label.set_text(time_str)
        return True

    def _on_key(self, controller, keyval, keycode, state):
        key_name = Gdk.keyval_name(keyval)
        if key_name == "Escape":
            log.info("EXIT: Escape pressed, quitting")
            self.get_application().quit()
        else:
            log.debug("key ignored: %s", key_name)

    def _on_mouse_motion(self, controller, x, y):
        if self._initial_x is None:
            self._initial_x = x
            self._initial_y = y
            log.debug("mouse baseline set: (%.0f, %.0f)", x, y)
            return
        dx, dy = abs(x - self._initial_x), abs(y - self._initial_y)
        if dx > 10 or dy > 10:
            log.info("EXIT: mouse moved (%.0f, %.0f) from baseline, quitting", dx, dy)
            self.get_application().quit()
        else:
            log.debug("mouse jitter (%.0f, %.0f) — below threshold", dx, dy)


# Safety timeout: auto-exit after this many seconds to prevent lockouts.
# If input events fail to register (compositor bug, layer-shell issue),
# the screensaver will still exit on its own.
SAFETY_TIMEOUT_SECONDS = 1800  # 30 minutes


class RSSScreensaverApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.rss.screensaver")
        config = load_config()
        general = config.get("general", {})
        processing = config.get("processing", {})
        self.card_duration = general.get("card_duration", 120)
        self.refresh_interval = general.get("refresh_interval", 300)
        self.layout_name = general.get("layout", "newspaper")

        self.summarizer = FabricSummarizer(
            pattern=processing.get("fabric_pattern", "summarize_micro"),
            enabled=processing.get("fabric_enabled", True),
            model=processing.get("fabric_model", "qwen3:4b"),
        )

        self.feed_manager = FeedManager(
            feeds=config.get("feeds", []),
            max_headlines=general.get("max_headlines", 50),
            refresh_interval=self.refresh_interval,
        )

    def do_activate(self):
        with timed("do_activate"):
            display = Gdk.Display.get_default()

            if STYLE_PATH.exists():
                css_provider = Gtk.CssProvider()
                css_provider.load_from_path(str(STYLE_PATH))
                Gtk.StyleContext.add_provider_for_display(
                    display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )

            layout_cls = load_layout(self.layout_name)
            css_path = get_css_path(layout_cls)
            if css_path.exists():
                layout_css = Gtk.CssProvider()
                layout_css.load_from_path(str(css_path))
                Gtk.StyleContext.add_provider_for_display(
                    display, layout_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )

            # First fetch is synchronous so windows have data on first render
            with timed("initial_fetch"):
                self.feed_manager.fetch_all()

            monitors = display.get_monitors()
            for i in range(monitors.get_n_items()):
                with timed(f"window_create[{i}]"):
                    win = ScreensaverWindow(
                        self, monitors.get_item(i), self.feed_manager, layout_cls,
                        summarizer=self.summarizer,
                    )
                    win.present()
                    win.start_rotation(self.card_duration)

        GLib.timeout_add_seconds(self.refresh_interval, self._periodic_fetch)
        GLib.timeout_add_seconds(SAFETY_TIMEOUT_SECONDS, self._safety_exit)
        log.info("started: %d monitors, refresh=%ds, rotate=%ds, safety=%ds",
                 monitors.get_n_items(), self.refresh_interval,
                 self.card_duration, SAFETY_TIMEOUT_SECONDS)
        log.info("log file: %s", LOG_PATH)

    def _periodic_fetch(self):
        log.debug("periodic feed refresh triggered")
        self.feed_manager.start_background_fetch()
        return True

    def _safety_exit(self):
        log.warning("EXIT: safety timeout (%ds) reached — force quitting", SAFETY_TIMEOUT_SECONDS)
        self.quit()
        return False


def main():
    log.info("=== RSS Screensaver starting (PID %d) ===", os.getpid())
    app = RSSScreensaverApp()

    def _signal_quit():
        log.info("EXIT: received SIGINT/SIGTERM")
        app.quit()

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, _signal_quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, _signal_quit)
    app.run(None)
    log.info("=== RSS Screensaver exited cleanly ===")


if __name__ == "__main__":
    main()
