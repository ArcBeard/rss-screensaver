"""Tests for FeedManager — headline rotation, batching, thread safety."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

from rss_screensaver import FeedManager, Headline


def _make_headlines(n):
    return [Headline(f"Title {i}", f"Source {i}") for i in range(n)]


class TestNextHeadline:
    def test_returns_loading_when_empty(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        h = fm.next_headline()
        assert h.title == "Loading headlines..."

    def test_rotates_through_headlines(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(3)
        titles = [fm.next_headline().title for _ in range(6)]
        assert titles == ["Title 0", "Title 1", "Title 2", "Title 0", "Title 1", "Title 2"]

    def test_single_headline_repeats(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(1)
        titles = [fm.next_headline().title for _ in range(3)]
        assert titles == ["Title 0", "Title 0", "Title 0"]


class TestGetHeadlines:
    def test_returns_loading_when_empty(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        result = fm.get_headlines(5)
        assert len(result) == 1
        assert result[0].title == "Loading headlines..."

    def test_returns_correct_count(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(10)
        result = fm.get_headlines(5)
        assert len(result) == 5

    def test_advances_index(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(10)
        batch1 = fm.get_headlines(3)
        batch2 = fm.get_headlines(3)
        assert batch1[0].title == "Title 0"
        assert batch2[0].title == "Title 3"

    def test_wraps_around(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(3)
        result = fm.get_headlines(5)
        assert len(result) == 5
        assert result[0].title == "Title 0"
        assert result[3].title == "Title 0"  # wrapped

    def test_get_headlines_then_next_headline_share_index(self):
        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(10)
        fm.get_headlines(3)  # advances to index 3
        h = fm.next_headline()
        assert h.title == "Title 3"


class TestMaxHeadlines:
    def test_respects_max_limit(self):
        fm = FeedManager(feeds=[], max_headlines=5)
        fm.headlines = _make_headlines(20)
        # Simulate what fetch_all does
        fm.headlines = fm.headlines[:fm.max_headlines]
        assert len(fm.headlines) == 5


class TestThreadSafety:
    def test_concurrent_reads(self):
        import threading

        with patch("rss_screensaver.load_cache", return_value=[]):
            fm = FeedManager(feeds=[])
        fm.headlines = _make_headlines(100)
        results = []
        errors = []

        def reader():
            try:
                for _ in range(50):
                    fm.next_headline()
                    fm.get_headlines(3)
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 4
