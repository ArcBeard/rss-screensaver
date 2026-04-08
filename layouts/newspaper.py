"""Victorian newspaper front page — The Strand Magazine / Times of London (1890s) aesthetic."""

import re
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"  # zero width joiner
    "\U00002600-\U000026FF"  # misc symbols
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U00002B50"  # star
    "\U0000203C-\U00003299"  # misc
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text):
    return _EMOJI_RE.sub("", text).strip()


class NewspaperLayout(Gtk.Box):
    CSS_FILE = "newspaper.css"
    HEADLINES_PER_PAGE = 25

    def __init__(self, headlines):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("newspaper")
        self.set_hexpand(True)
        self.set_vexpand(True)

        # === MASTHEAD ===
        masthead = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        masthead.add_css_class("masthead")

        # Triple rule: thick-thin-thick
        masthead.append(self._rule("rule-heavy"))
        masthead.append(self._rule("rule-hairline"))
        masthead.append(self._rule("rule-heavy"))

        self.title_label = Gtk.Label(label="THE  DAILY  TELEGRAPH")
        self.title_label.add_css_class("masthead-title")
        masthead.append(self.title_label)

        # Subtitle row: date — motto — edition
        subtitle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        subtitle_box.add_css_class("masthead-subtitle-box")
        subtitle_box.set_halign(Gtk.Align.FILL)

        self.date_label = Gtk.Label(
            label=datetime.now().strftime("%A, %B %d, %Y").upper()
        )
        self.date_label.add_css_class("masthead-date")
        self.date_label.set_halign(Gtk.Align.START)
        self.date_label.set_hexpand(True)
        subtitle_box.append(self.date_label)

        motto = Gtk.Label(label="— Established 1855 —")
        motto.add_css_class("masthead-motto")
        motto.set_halign(Gtk.Align.CENTER)
        motto.set_hexpand(True)
        subtitle_box.append(motto)

        edition_label = Gtk.Label(label="EVENING EDITION")
        edition_label.add_css_class("masthead-edition")
        edition_label.set_halign(Gtk.Align.END)
        edition_label.set_hexpand(True)
        subtitle_box.append(edition_label)

        masthead.append(subtitle_box)

        # Bottom dramatic rules
        masthead.append(self._rule("rule-heavy"))
        masthead.append(self._rule("rule-hairline"))
        masthead.append(self._rule("rule-heavy"))

        # Price/motto art line
        art_line = Gtk.Label(label="◈  PRICE ONE PENNY  ◈                    ◈  LATEST INTELLIGENCE  ◈")
        art_line.add_css_class("section-art")
        art_line.set_halign(Gtk.Align.CENTER)
        masthead.append(art_line)
        masthead.append(self._rule("rule-hairline"))

        self.append(masthead)

        # === CONTENT ===
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

        # === LEAD STORY ===
        lead = display[0]
        lead_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        lead_box.add_css_class("lead-story")

        lead_headline = Gtk.Label(label=_strip_emoji(lead.title).upper())
        lead_headline.add_css_class("lead-headline")
        lead_headline.set_wrap(True)
        lead_headline.set_max_width_chars(70)
        lead_headline.set_halign(Gtk.Align.CENTER)
        lead_box.append(lead_headline)

        desc_text = _strip_emoji(lead.description or lead.summary or "")
        if desc_text:
            lead_desc = Gtk.Label(label=desc_text[:250])
            lead_desc.add_css_class("lead-description")
            lead_desc.set_wrap(True)
            lead_desc.set_max_width_chars(80)
            lead_desc.set_halign(Gtk.Align.CENTER)
            lead_box.append(lead_desc)

        lead_source = Gtk.Label(label=f"— {lead.source} —")
        lead_source.add_css_class("story-source")
        lead_source.set_halign(Gtk.Align.CENTER)
        lead_box.append(lead_source)

        self.content.append(lead_box)

        # Dramatic ornamental divider
        self.content.append(self._ornamental_break("✦  ✦  ✦"))

        # === COLUMN STORIES ===
        remaining = display[1:]
        if not remaining:
            return

        # WWII-era newspapers used fewer, wider columns
        # Portrait (45 headlines) = 1 column, landscape/ultrawide = 2 columns
        n = len(remaining)
        num_cols = 1 if n >= 30 else 2
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        columns_box.add_css_class("columns")
        columns_box.set_hexpand(True)
        columns_box.set_vexpand(True)

        cols = []
        for c in range(num_cols):
            col_scroll = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            col_scroll.set_hexpand(True)
            col_scroll.set_vexpand(True)
            cols.append(col_scroll)

        for i, headline in enumerate(remaining):
            col_idx = i % num_cols
            is_top = i < num_cols
            story = self._build_story(headline, is_secondary=is_top, faded=(i % 3 == 2))
            cols[col_idx].append(story)

        for c, col in enumerate(cols):
            if c > 0:
                divider = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                divider.add_css_class("rule-column")
                columns_box.append(divider)
            columns_box.append(col)

        self.content.append(columns_box)

    def _build_story(self, headline, is_secondary=False, faded=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("story")
        if faded:
            box.add_css_class("story-faded")

        clean_title = _strip_emoji(headline.title)
        title = Gtk.Label(label=clean_title.upper() if is_secondary else clean_title)
        title.add_css_class("secondary-headline" if is_secondary else "story-headline")
        title.set_wrap(True)
        title.set_max_width_chars(40)
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0)
        box.append(title)

        desc_text = _strip_emoji(headline.description or headline.summary or "")
        if desc_text:
            # Truncate to ~2 lines worth
            limit = 160 if is_secondary else 120
            desc = Gtk.Label(label=desc_text[:limit])
            desc.add_css_class("story-description")
            desc.set_wrap(True)
            desc.set_max_width_chars(40)
            desc.set_halign(Gtk.Align.START)
            desc.set_xalign(0)
            box.append(desc)

        # Source + relevance score on same line
        meta_parts = [f"— {headline.source} —"]
        if headline.relevance_score:
            meta_parts.append(f"  [{headline.relevance_score}/10]")
        source = Gtk.Label(label="".join(meta_parts))
        source.add_css_class("story-source")
        if headline.relevance_score >= 8:
            source.add_css_class("relevance-high")
        elif headline.relevance_score >= 5:
            source.add_css_class("relevance-mid")
        source.set_halign(Gtk.Align.START)
        source.set_xalign(0)
        box.append(source)

        # Decorative story separator
        sep_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sep_box.append(self._rule("rule-story"))
        art = Gtk.Label(label="— ◆ —")
        art.add_css_class("section-art")
        art.set_halign(Gtk.Align.CENTER)
        sep_box.append(art)
        sep_box.append(self._rule("rule-story"))
        box.append(sep_box)

        return box

    @staticmethod
    def _rule(css_class):
        sep = Gtk.Separator()
        sep.add_css_class(css_class)
        return sep

    @staticmethod
    def _ornamental_break(symbols="✦  ✦  ✦"):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class("ornamental-divider")
        box.set_halign(Gtk.Align.CENTER)

        left = Gtk.Separator()
        left.add_css_class("rule-ornament-left")
        box.append(left)

        ornament = Gtk.Label(label=symbols)
        ornament.add_css_class("ornament-symbol")
        box.append(ornament)

        right = Gtk.Separator()
        right.add_css_class("rule-ornament-right")
        box.append(right)

        return box
