"""Layout registry for RSS Screensaver.

A layout is a Gtk.Widget subclass that:
  - Has a CSS_FILE class attribute (filename relative to layouts/ dir)
  - Accepts (headlines: list[Headline]) in __init__
  - Has an update(headlines: list[Headline]) method

To add a new layout: create a .py and .css file in this directory,
then add one entry to the LAYOUTS dict below.
"""

from importlib import import_module
from pathlib import Path

LAYOUTS_DIR = Path(__file__).parent

# Registry: name → (module_path, class_name)
LAYOUTS = {
    "cards": ("layouts.cards", "CardsLayout"),
    "newspaper": ("layouts.newspaper", "NewspaperLayout"),
}


def load_layout(name):
    """Import and return the layout class for the given name."""
    if name not in LAYOUTS:
        available = ", ".join(LAYOUTS.keys())
        raise ValueError(f"Unknown layout '{name}'. Available: {available}")
    module_path, class_name = LAYOUTS[name]
    module = import_module(module_path)
    return getattr(module, class_name)


def get_css_path(layout_cls):
    """Return the absolute path to a layout's CSS file."""
    return LAYOUTS_DIR / layout_cls.CSS_FILE
