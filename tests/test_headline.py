"""Tests for the Headline data class."""

import sys
from pathlib import Path

# Allow importing from project root without install
sys.path.insert(0, str(Path(__file__).parent.parent))

# Skip the LD_PRELOAD re-exec by pretending it's already set
import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

from rss_screensaver import Headline


class TestHeadline:
    def test_basic_construction(self):
        h = Headline("Test Title", "Test Source")
        assert h.title == "Test Title"
        assert h.source == "Test Source"
        assert h.link == ""
        assert h.summary == ""
        assert h.description == ""

    def test_full_construction(self):
        h = Headline("Title", "Source", link="http://x.com", summary="Sum", description="Desc")
        assert h.link == "http://x.com"
        assert h.summary == "Sum"
        assert h.description == "Desc"

    def test_slots_prevent_arbitrary_attributes(self):
        h = Headline("T", "S")
        try:
            h.nonexistent = "value"
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass

    def test_mutable_fields(self):
        h = Headline("T", "S")
        h.summary = "Updated"
        assert h.summary == "Updated"
