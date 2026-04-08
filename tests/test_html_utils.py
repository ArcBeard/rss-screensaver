"""Tests for HTML stripping and entry text extraction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

from rss_screensaver import _strip_html, _get_entry_text


class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_decodes_entities(self):
        assert _strip_html("&amp; &lt; &gt;") == "& < >"

    def test_collapses_whitespace(self):
        assert _strip_html("  hello   world  ") == "hello world"

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_nested_tags(self):
        assert _strip_html("<div><span><a href='#'>link</a></span></div>") == "link"

    def test_self_closing_tags(self):
        assert _strip_html("before<br/>after") == "before after"


class TestGetEntryText:
    def test_prefers_summary_field(self):
        entry = {"summary": "A " * 30, "title": "Title"}
        result = _get_entry_text(entry)
        assert result.startswith("A ")

    def test_falls_back_to_description(self):
        entry = {"summary": "short", "description": "D " * 30, "title": "Title"}
        result = _get_entry_text(entry)
        assert result.startswith("D ")

    def test_handles_content_list(self):
        entry = {"content": [{"value": "<p>" + "Content " * 10 + "</p>"}], "title": "T"}
        result = _get_entry_text(entry)
        assert "Content" in result

    def test_falls_back_to_title(self):
        entry = {"summary": "short", "title": "Fallback Title"}
        result = _get_entry_text(entry)
        assert result == "Fallback Title"

    def test_empty_entry(self):
        result = _get_entry_text({"title": "Only Title"})
        assert result == "Only Title"

    def test_strips_html_from_content(self):
        entry = {"summary": "<b>" + "Bold " * 20 + "</b>", "title": "T"}
        result = _get_entry_text(entry)
        assert "<b>" not in result
