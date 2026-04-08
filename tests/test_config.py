"""Tests for config loading and defaults."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

from rss_screensaver import load_config, CONFIG_PATH


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self):
        with patch.object(Path, "exists", return_value=False):
            config = load_config()
        assert config["general"]["refresh_interval"] == 300
        assert config["general"]["card_duration"] == 8
        assert config["general"]["max_headlines"] == 50
        assert config["general"]["layout"] == "newspaper"
        assert len(config["feeds"]) == 1
        assert config["feeds"][0]["name"] == "Hacker News"

    def test_loads_toml_file(self):
        toml_content = b"""
[general]
layout = "cards"
refresh_interval = 60
card_duration = 10
max_headlines = 20

[[feeds]]
name = "Test Feed"
url = "https://example.com/rss"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            tmp_path = Path(f.name)

        try:
            with patch("rss_screensaver.CONFIG_PATH", tmp_path):
                config = load_config()
            assert config["general"]["layout"] == "cards"
            assert config["general"]["refresh_interval"] == 60
            assert config["feeds"][0]["name"] == "Test Feed"
        finally:
            tmp_path.unlink()

    def test_processing_section_optional(self):
        with patch.object(Path, "exists", return_value=False):
            config = load_config()
        # processing section not in defaults — that's fine
        assert config.get("processing") is None
