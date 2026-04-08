"""Single-card rotating layout — one headline at a time with fade transitions."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk


class CardsLayout(Gtk.Box):
    CSS_FILE = "cards.css"

    def __init__(self, headlines):
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

        if headlines:
            self._show(headlines[0])

    def update(self, headlines):
        if not headlines:
            return
        self.remove_css_class("visible")
        self.add_css_class("hidden")
        GLib.timeout_add(900, self._reveal, headlines[0])

    def _show(self, headline):
        self.headline_label.set_text(headline.title)
        self.source_label.set_text(headline.source)
        self.remove_css_class("hidden")
        self.add_css_class("visible")

    def _reveal(self, headline):
        self._show(headline)
        return False
