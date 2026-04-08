#!/usr/bin/env python3
"""Open RSS Screensaver config in the user's preferred editor."""

import os
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "rss-screensaver" / "config.toml"


def main():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Copy default from installed location
        default = Path(__file__).parent / "config" / "config.toml"
        if default.exists():
            CONFIG_PATH.write_text(default.read_text())
        else:
            CONFIG_PATH.write_text("# RSS Screensaver Configuration\n# See project README for options\n")

    editor = os.environ.get("EDITOR", "nvim")
    subprocess.run([editor, str(CONFIG_PATH)])


if __name__ == "__main__":
    main()
