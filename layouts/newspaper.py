"""Old-school newspaper front page layout — multi-column grid with masthead."""

from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk


class NewspaperLayout(Gtk.Box):
    CSS_FILE = "newspaper.css"
    HEADLINES_PER_PAGE = 9

    def __init__(self, headlines):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("newspaper")

        # Masthead
        masthead = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        masthead.add_css_class("masthead")

        rule_top = Gtk.Separator()
        rule_top.add_css_class("rule-thick")
        masthead.append(rule_top)

        self.title_label = Gtk.Label(label="THE DAILY WIRE")
        self.title_label.add_css_class("masthead-title")
        masthead.append(self.title_label)

        subtitle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        subtitle_box.add_css_class("masthead-subtitle-box")
        subtitle_box.set_halign(Gtk.Align.FILL)

        self.date_label = Gtk.Label(label=datetime.now().strftime("%A, %B %d, %Y").upper())
        self.date_label.add_css_class("masthead-date")
        self.date_label.set_halign(Gtk.Align.START)
        self.date_label.set_hexpand(True)
        subtitle_box.append(self.date_label)

        edition_label = Gtk.Label(label="EVENING EDITION")
        edition_label.add_css_class("masthead-edition")
        edition_label.set_halign(Gtk.Align.END)
        subtitle_box.append(edition_label)

        masthead.append(subtitle_box)

        rule_bottom = Gtk.Separator()
        rule_bottom.add_css_class("rule-thick")
        masthead.append(rule_bottom)

        self.append(masthead)

        # Content area
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.add_css_class("content")
        self.content.set_vexpand(True)
        self.append(self.content)

        if headlines:
            self._build_page(headlines)

    def update(self, headlines):
        if not headlines:
            return
        child = self.content.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.content.remove(child)
            child = next_child
        self._build_page(headlines)

    def _build_page(self, headlines):
        display = headlines[: self.HEADLINES_PER_PAGE]
        if not display:
            return

        # Lead story — full width
        lead = display[0]
        lead_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lead_box.add_css_class("lead-story")

        lead_headline = Gtk.Label(label=lead.title.upper())
        lead_headline.add_css_class("lead-headline")
        lead_headline.set_wrap(True)
        lead_headline.set_max_width_chars(80)
        lead_headline.set_halign(Gtk.Align.CENTER)
        lead_box.append(lead_headline)

        if lead.summary:
            lead_summary = Gtk.Label(label=lead.summary)
            lead_summary.add_css_class("lead-summary")
            lead_summary.set_wrap(True)
            lead_summary.set_max_width_chars(90)
            lead_summary.set_halign(Gtk.Align.CENTER)
            lead_box.append(lead_summary)

        lead_source = Gtk.Label(label=lead.source)
        lead_source.add_css_class("story-source")
        lead_source.set_halign(Gtk.Align.CENTER)
        lead_box.append(lead_source)

        self.content.append(lead_box)

        rule = Gtk.Separator()
        rule.add_css_class("rule-thin")
        self.content.append(rule)

        # Remaining stories in columns
        remaining = display[1:]
        if not remaining:
            return

        columns = Gtk.Grid()
        columns.add_css_class("columns")
        columns.set_column_homogeneous(True)
        columns.set_column_spacing(24)
        columns.set_row_spacing(16)

        num_cols = 3 if len(remaining) >= 6 else 2
        for i, headline in enumerate(remaining):
            col = i % num_cols
            row = i // num_cols

            story = self._build_story(headline, is_secondary=(row == 0))
            columns.attach(story, col, row, 1, 1)

        self.content.append(columns)

    def _build_story(self, headline, is_secondary=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("story")

        title = Gtk.Label(label=headline.title)
        title.add_css_class("secondary-headline" if is_secondary else "story-headline")
        title.set_wrap(True)
        title.set_max_width_chars(40)
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0)
        box.append(title)

        if headline.summary:
            summary = Gtk.Label(label=headline.summary)
            summary.add_css_class("story-summary")
            summary.set_wrap(True)
            summary.set_max_width_chars(40)
            summary.set_halign(Gtk.Align.START)
            summary.set_xalign(0)
            box.append(summary)

        source = Gtk.Label(label=headline.source)
        source.add_css_class("story-source")
        source.set_halign(Gtk.Align.START)
        source.set_xalign(0)
        box.append(source)

        sep = Gtk.Separator()
        sep.add_css_class("rule-light")
        box.append(sep)

        return box
