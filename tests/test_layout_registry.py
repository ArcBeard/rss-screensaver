"""Tests for layout registry — loading, CSS paths, unknown layouts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

import pytest
from layouts import load_layout, get_css_path, LAYOUTS, LAYOUTS_DIR


class TestLayoutRegistry:
    def test_registry_has_cards(self):
        assert "cards" in LAYOUTS

    def test_registry_has_newspaper(self):
        assert "newspaper" in LAYOUTS

    def test_load_cards_layout(self):
        cls = load_layout("cards")
        assert cls.__name__ == "CardsLayout"
        assert hasattr(cls, "CSS_FILE")
        assert hasattr(cls, "update")

    def test_load_newspaper_layout(self):
        cls = load_layout("newspaper")
        assert cls.__name__ == "NewspaperLayout"
        assert hasattr(cls, "CSS_FILE")
        assert hasattr(cls, "update")
        assert cls.HEADLINES_PER_PAGE == 25

    def test_unknown_layout_raises(self):
        with pytest.raises(ValueError, match="Unknown layout"):
            load_layout("nonexistent")

    def test_error_lists_available_layouts(self):
        try:
            load_layout("bad_name")
        except ValueError as e:
            for name in LAYOUTS:
                assert name in str(e)


class TestCssPaths:
    def test_cards_css_exists(self):
        cls = load_layout("cards")
        path = get_css_path(cls)
        assert path.exists()
        assert path.name == "cards.css"

    def test_newspaper_css_exists(self):
        cls = load_layout("newspaper")
        path = get_css_path(cls)
        assert path.exists()
        assert path.name == "newspaper.css"

    def test_css_path_relative_to_layouts_dir(self):
        cls = load_layout("cards")
        path = get_css_path(cls)
        assert path.parent == LAYOUTS_DIR


class TestLayoutProtocol:
    """Verify all registered layouts follow the expected protocol."""

    @pytest.mark.parametrize("name", list(LAYOUTS.keys()))
    def test_has_css_file_attribute(self, name):
        cls = load_layout(name)
        assert isinstance(cls.CSS_FILE, str)
        assert cls.CSS_FILE.endswith(".css")

    @pytest.mark.parametrize("name", list(LAYOUTS.keys()))
    def test_has_update_method(self, name):
        cls = load_layout(name)
        assert callable(getattr(cls, "update", None))

    @pytest.mark.parametrize("name", list(LAYOUTS.keys()))
    def test_has_headlines_per_page(self, name):
        cls = load_layout(name)
        n = getattr(cls, "HEADLINES_PER_PAGE", 1)
        assert isinstance(n, int)
        assert n >= 1
