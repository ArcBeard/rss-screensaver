"""WWII-era newspaper spread — open broadsheet, two facing pages with centre fold."""

import re
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002600-\U000026FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002B50"
    "\U0000203C-\U00003299"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text):
    return _EMOJI_RE.sub("", text).strip()


class NewspaperLayout(Gtk.Box):
    CSS_FILE = "newspaper.css"
    HEADLINES_PER_PAGE = 20

    def __init__(self, headlines):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("newspaper")
        self.set_hexpand(True)
        self.set_vexpand(True)

        # === MASTHEAD — spans full width ===
        self.append(self._build_masthead())

        # === SPREAD — two facing pages ===
        self.spread = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.spread.add_css_class("spread")
        self.spread.set_hexpand(True)
        self.spread.set_vexpand(True)
        self.append(self.spread)

        if headlines:
            self._build_spread(headlines)

    def _build_masthead(self):
        masthead = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        masthead.add_css_class("masthead")

        masthead.append(self._rule("rule-heavy"))
        masthead.append(self._rule("rule-hairline"))
        masthead.append(self._rule("rule-heavy"))

        title = Gtk.Label(label="THE  DAILY  TELEGRAPH")
        title.add_css_class("masthead-title")
        masthead.append(title)

        sub = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sub.add_css_class("masthead-subtitle-box")
        sub.set_halign(Gtk.Align.FILL)

        date_lbl = Gtk.Label(label=datetime.now().strftime("%A, %B %d, %Y").upper())
        date_lbl.add_css_class("masthead-date")
        date_lbl.set_halign(Gtk.Align.START)
        date_lbl.set_hexpand(True)
        sub.append(date_lbl)

        motto = Gtk.Label(label="◈  PRICE ONE PENNY  ◈")
        motto.add_css_class("masthead-motto")
        motto.set_halign(Gtk.Align.CENTER)
        motto.set_hexpand(True)
        sub.append(motto)

        edition = Gtk.Label(label="EVENING EDITION")
        edition.add_css_class("masthead-edition")
        edition.set_halign(Gtk.Align.END)
        edition.set_hexpand(True)
        sub.append(edition)

        masthead.append(sub)

        masthead.append(self._rule("rule-heavy"))
        masthead.append(self._rule("rule-hairline"))
        masthead.append(self._rule("rule-heavy"))

        return masthead

    def update(self, headlines):
        if not headlines:
            return
        child = self.spread.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.spread.remove(child)
            child = nxt
        self._build_spread(headlines)

    def _build_spread(self, headlines):
        display = headlines[: self.HEADLINES_PER_PAGE]
        if not display:
            return

        mid = max(1, len(display) // 2)
        left_headlines = display[:mid]
        right_headlines = display[mid:]

        # Left page
        left_page = self._build_page(left_headlines, page_label="Page 2")
        left_page.add_css_class("page-left")
        self.spread.append(left_page)

        # Centre fold gutter
        gutter = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        gutter.add_css_class("gutter")
        gutter_line = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        gutter_line.add_css_class("rule-gutter")
        gutter_line.set_vexpand(True)
        gutter.append(gutter_line)
        self.spread.append(gutter)

        # Right page
        right_page = self._build_page(right_headlines, page_label="Page 3")
        right_page.add_css_class("page-right")
        self.spread.append(right_page)

    def _build_page(self, headlines, page_label=""):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.add_css_class("page")
        page.set_hexpand(True)
        page.set_vexpand(True)

        if not headlines:
            return page

        # Page lead — first story, prominent
        lead = headlines[0]
        lead_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lead_box.add_css_class("page-lead")

        lead_hl = Gtk.Label(label=_strip_emoji(lead.title).upper())
        lead_hl.add_css_class("lead-headline")
        lead_hl.set_wrap(True)
        lead_hl.set_max_width_chars(50)
        lead_hl.set_halign(Gtk.Align.START)
        lead_hl.set_xalign(0)
        lead_box.append(lead_hl)

        desc = _strip_emoji(lead.description or lead.summary or "")
        if desc:
            lead_desc = Gtk.Label(label=desc[:200])
            lead_desc.add_css_class("lead-description")
            lead_desc.set_wrap(True)
            lead_desc.set_max_width_chars(60)
            lead_desc.set_halign(Gtk.Align.START)
            lead_desc.set_xalign(0)
            lead_box.append(lead_desc)

        lead_src = Gtk.Label(label=f"— {lead.source} —")
        lead_src.add_css_class("story-source")
        lead_src.set_halign(Gtk.Align.START)
        lead_src.set_xalign(0)
        lead_box.append(lead_src)

        page.append(lead_box)
        page.append(self._rule("rule-story"))
        page.append(self._ornamental_break())

        # Sub-stories in two columns
        remaining = headlines[1:]
        if remaining:
            cols_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            cols_box.add_css_class("page-columns")
            cols_box.set_hexpand(True)
            cols_box.set_vexpand(True)

            col_a = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col_a.set_hexpand(True)
            col_a.set_vexpand(True)
            col_b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col_b.set_hexpand(True)
            col_b.set_vexpand(True)

            for i, h in enumerate(remaining):
                story = self._build_story(h, faded=(i % 3 == 2))
                if i % 2 == 0:
                    col_a.append(story)
                else:
                    col_b.append(story)

            cols_box.append(col_a)
            div = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            div.add_css_class("rule-column")
            cols_box.append(div)
            cols_box.append(col_b)

            page.append(cols_box)

        # Page number at bottom
        if page_label:
            pg_num = Gtk.Label(label=page_label)
            pg_num.add_css_class("page-number")
            pg_num.set_halign(Gtk.Align.CENTER)
            pg_num.set_valign(Gtk.Align.END)
            page.append(pg_num)

        return page

    def _build_story(self, headline, faded=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.add_css_class("story")
        if faded:
            box.add_css_class("story-faded")

        clean_title = _strip_emoji(headline.title)
        title = Gtk.Label(label=clean_title)
        title.add_css_class("story-headline")
        title.set_wrap(True)
        title.set_max_width_chars(35)
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0)
        box.append(title)

        desc = _strip_emoji(headline.description or headline.summary or "")
        if desc:
            d = Gtk.Label(label=desc[:120])
            d.add_css_class("story-description")
            d.set_wrap(True)
            d.set_max_width_chars(35)
            d.set_halign(Gtk.Align.START)
            d.set_xalign(0)
            box.append(d)

        meta = [f"— {headline.source} —"]
        if headline.relevance_score:
            meta.append(f"  [{headline.relevance_score}/10]")
        src = Gtk.Label(label="".join(meta))
        src.add_css_class("story-source")
        if headline.relevance_score >= 8:
            src.add_css_class("relevance-high")
        elif headline.relevance_score >= 5:
            src.add_css_class("relevance-mid")
        src.set_halign(Gtk.Align.START)
        src.set_xalign(0)
        box.append(src)

        box.append(self._rule("rule-story"))

        return box

    @staticmethod
    def _rule(css_class):
        sep = Gtk.Separator()
        sep.add_css_class(css_class)
        return sep

    @staticmethod
    def _ornamental_break():
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class("ornamental-divider")
        box.set_halign(Gtk.Align.CENTER)

        left = Gtk.Separator()
        left.add_css_class("rule-ornament-left")
        box.append(left)

        sym = Gtk.Label(label="✦  ✦  ✦")
        sym.add_css_class("ornament-symbol")
        box.append(sym)

        right = Gtk.Separator()
        right.add_css_class("rule-ornament-right")
        box.append(right)

        return box
