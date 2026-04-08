"""Tests for feed persistence — cache save/load, startup with cached data."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

from rss_screensaver import Headline, save_cache, load_cache, FeedManager, CACHE_PATH


class TestSaveCache:
    def test_saves_headlines_to_json(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        headlines = [
            Headline("Title 1", "Source 1", link="http://a.com", description="Desc 1"),
            Headline("Title 2", "Source 2", summary="Sum 2"),
        ]
        with patch("rss_screensaver.CACHE_PATH", cache_file):
            save_cache(headlines)

        data = json.loads(cache_file.read_text())
        assert len(data) == 2
        assert data[0]["title"] == "Title 1"
        assert data[0]["description"] == "Desc 1"
        assert data[1]["summary"] == "Sum 2"

    def test_overwrites_existing_cache(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        cache_file.write_text('[{"old": "data"}]')

        headlines = [Headline("New", "Source")]
        with patch("rss_screensaver.CACHE_PATH", cache_file):
            save_cache(headlines)

        data = json.loads(cache_file.read_text())
        assert len(data) == 1
        assert data[0]["title"] == "New"

    def test_handles_write_failure(self, tmp_path):
        cache_file = tmp_path / "nonexistent_dir" / "headlines.json"
        with patch("rss_screensaver.CACHE_PATH", cache_file):
            save_cache([Headline("T", "S")])  # should not raise


class TestLoadCache:
    def test_loads_cached_headlines(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        data = [
            {"title": "Cached Title", "source": "Cached Source",
             "link": "http://x.com", "summary": "Sum", "description": "Desc"}
        ]
        cache_file.write_text(json.dumps(data))

        with patch("rss_screensaver.CACHE_PATH", cache_file):
            headlines = load_cache()

        assert len(headlines) == 1
        assert headlines[0].title == "Cached Title"
        assert headlines[0].description == "Desc"

    def test_returns_empty_when_no_cache(self, tmp_path):
        cache_file = tmp_path / "nonexistent.json"
        with patch("rss_screensaver.CACHE_PATH", cache_file):
            headlines = load_cache()
        assert headlines == []

    def test_returns_empty_on_corrupt_json(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        cache_file.write_text("not valid json{{{")
        with patch("rss_screensaver.CACHE_PATH", cache_file):
            headlines = load_cache()
        assert headlines == []

    def test_returns_empty_on_wrong_schema(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        cache_file.write_text('[{"wrong_field": "value"}]')
        with patch("rss_screensaver.CACHE_PATH", cache_file):
            headlines = load_cache()
        assert headlines == []


class TestFeedManagerCache:
    def test_starts_with_cached_data(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        data = [
            {"title": f"Cached {i}", "source": "S", "link": "", "summary": "", "description": ""}
            for i in range(5)
        ]
        cache_file.write_text(json.dumps(data))

        with patch("rss_screensaver.CACHE_PATH", cache_file):
            fm = FeedManager(feeds=[], max_headlines=50)

        assert len(fm.headlines) == 5
        assert fm.headlines[0].title == "Cached 0"

    def test_respects_max_headlines_on_cache_load(self, tmp_path):
        cache_file = tmp_path / "headlines.json"
        data = [
            {"title": f"H{i}", "source": "S", "link": "", "summary": "", "description": ""}
            for i in range(100)
        ]
        cache_file.write_text(json.dumps(data))

        with patch("rss_screensaver.CACHE_PATH", cache_file):
            fm = FeedManager(feeds=[], max_headlines=10)

        assert len(fm.headlines) == 10
