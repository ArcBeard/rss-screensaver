"""Tests for FabricSummarizer — extract_summary, caching, disabled mode, resource mgmt."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["LD_PRELOAD"] = "libgtk4-layer-shell.so"

from rss_screensaver import FabricSummarizer, Headline


class TestExtractSummary:
    def test_extracts_one_sentence_summary(self):
        output = """# ONE SENTENCE SUMMARY:
AI is transforming the world rapidly.

# MAIN POINTS:
- Point one
- Point two"""
        result = FabricSummarizer._extract_summary(output)
        assert result == "AI is transforming the world rapidly."

    def test_handles_colon_in_header(self):
        output = """# ONE SENTENCE SUMMARY:
Summary text here.
"""
        result = FabricSummarizer._extract_summary(output)
        assert result == "Summary text here."

    def test_fallback_to_first_non_header_line(self):
        output = """# Some Header
This is the first real content line.
And this is second."""
        result = FabricSummarizer._extract_summary(output)
        assert result == "This is the first real content line."

    def test_truncates_long_fallback(self):
        output = "x" * 500
        result = FabricSummarizer._extract_summary(output)
        assert len(result) <= 200

    def test_handles_blank_lines_after_header(self):
        output = """# ONE SENTENCE SUMMARY:

The actual summary after blank line."""
        result = FabricSummarizer._extract_summary(output)
        assert result == "The actual summary after blank line."

    def test_case_insensitive_header(self):
        output = """# one sentence summary:
Lower case works too."""
        result = FabricSummarizer._extract_summary(output)
        assert result == "Lower case works too."


class TestSummarizerDisabled:
    def test_disabled_when_fabric_not_found(self):
        with patch("shutil.which", return_value=None):
            s = FabricSummarizer(enabled=True)
            assert s.enabled is False

    def test_disabled_by_config(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(enabled=False)
            assert s.enabled is False

    def test_enabled_when_fabric_exists(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(enabled=True)
            assert s.enabled is True


class TestSummarizerModel:
    def test_passes_model_flag_to_fabric(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "# ONE SENTENCE SUMMARY:\nTest summary."

        h = Headline("T", "S", link="http://x.com", description="Text")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            s.summarize(h)
            cmd = mock_run.call_args[0][0]
            assert "-m" in cmd
            assert "qwen3:4b" in cmd

    def test_no_model_flag_when_model_is_none(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model=None)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "# ONE SENTENCE SUMMARY:\nTest summary."

        h = Headline("T", "S", link="http://x.com", description="Text")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            s.summarize(h)
            cmd = mock_run.call_args[0][0]
            assert "-m" not in cmd


class TestOllamaAvailability:
    def test_available_when_no_model_loaded(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        ps_result = MagicMock()
        ps_result.returncode = 0
        ps_result.stdout = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\n"

        with patch("subprocess.run", return_value=ps_result):
            assert s._is_ollama_available() is True

    def test_available_when_same_model_loaded(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        ps_result = MagicMock()
        ps_result.returncode = 0
        ps_result.stdout = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\nqwen3:4b    abc123    2.3 GB    GPU    4096    4 minutes from now\n"

        with patch("subprocess.run", return_value=ps_result):
            assert s._is_ollama_available() is True

    def test_unavailable_when_different_model_loaded(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        ps_result = MagicMock()
        ps_result.returncode = 0
        ps_result.stdout = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\nqwen3:14b    abc123    8.5 GB    GPU    4096    4 minutes from now\n"

        with patch("subprocess.run", return_value=ps_result):
            assert s._is_ollama_available() is False

    def test_available_when_ollama_errors(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        with patch("subprocess.run", side_effect=OSError("not found")):
            assert s._is_ollama_available() is True


class TestSummarizeNextPage:
    def test_summarizes_only_page_size_headlines(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "# ONE SENTENCE SUMMARY:\nSummary."

        headlines = [Headline(f"T{i}", "S", link=f"http://x.com/{i}", description="Text") for i in range(10)]

        ps_result = MagicMock()
        ps_result.returncode = 0
        ps_result.stdout = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\n"

        with patch("subprocess.run", side_effect=[ps_result, mock_result, mock_result, mock_result]):
            s.summarize_next_page(headlines, 3)

        summarized = [h for h in headlines if h.summary]
        assert len(summarized) == 3

    def test_skips_when_ollama_busy(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        ps_result = MagicMock()
        ps_result.returncode = 0
        ps_result.stdout = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\nllama3:70b    abc    40 GB    GPU    4096    4 minutes\n"

        headlines = [Headline("T", "S", link="http://x.com", description="Text")]

        with patch("subprocess.run", return_value=ps_result) as mock_run:
            s.summarize_next_page(headlines, 1)

        assert headlines[0].summary == ""

    def test_skips_already_summarized(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer(model="qwen3:4b")

        ps_result = MagicMock()
        ps_result.returncode = 0
        ps_result.stdout = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\n"

        h = Headline("T", "S", link="http://x.com", description="Text", summary="Already done")

        with patch("subprocess.run", return_value=ps_result) as mock_run:
            s.summarize_next_page([h], 1)
            # Only ollama ps call, no fabric call
            assert mock_run.call_count == 1


class TestSummarizerCache:
    def test_caches_by_link(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "# ONE SENTENCE SUMMARY:\nCached result."

        h = Headline("T", "S", link="http://example.com", description="Some text")

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            s.summarize(h)
            assert h.summary == "Cached result."
            assert mock_run.call_count == 1

            # Second call should use cache
            h2 = Headline("T2", "S2", link="http://example.com", description="Other text")
            s.summarize(h2)
            assert h2.summary == "Cached result."
            assert mock_run.call_count == 1  # no additional call

    def test_skips_headline_without_description(self):
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer()

        h = Headline("T", "S", description="")
        with patch("subprocess.run") as mock_run:
            s.summarize(h)
            mock_run.assert_not_called()
            assert h.summary == ""

    def test_handles_subprocess_timeout(self):
        import subprocess
        with patch("shutil.which", return_value="/usr/bin/fabric"):
            s = FabricSummarizer()

        h = Headline("T", "S", link="http://x.com", description="Text")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("fabric", 30)):
            s.summarize(h)
            assert h.summary == ""
