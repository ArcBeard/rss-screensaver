PREFIX ?= $(HOME)/.local
BINDIR = $(PREFIX)/bin
LIBDIR = $(PREFIX)/share/rss-screensaver
CONFIGDIR = $(HOME)/.config/rss-screensaver

.PHONY: install uninstall

install:
	install -Dm755 rss_screensaver.py $(LIBDIR)/rss_screensaver.py
	install -Dm644 layouts/__init__.py $(LIBDIR)/layouts/__init__.py
	install -Dm644 layouts/cards.py $(LIBDIR)/layouts/cards.py
	install -Dm644 layouts/cards.css $(LIBDIR)/layouts/cards.css
	install -Dm644 layouts/newspaper.py $(LIBDIR)/layouts/newspaper.py
	install -Dm644 layouts/newspaper.css $(LIBDIR)/layouts/newspaper.css
	install -Dm755 rss-screensaver-launch $(BINDIR)/rss-screensaver-launch
	@printf '#!/bin/bash\ncd $(LIBDIR) && exec python3 rss_screensaver.py "$$@"\n' > $(BINDIR)/rss-screensaver
	@chmod 755 $(BINDIR)/rss-screensaver
	install -Dm644 config/config.toml $(CONFIGDIR)/config.toml
	install -Dm644 config/style.css $(CONFIGDIR)/style.css

uninstall:
	rm -f $(BINDIR)/rss-screensaver
	rm -f $(BINDIR)/rss-screensaver-launch
	rm -rf $(LIBDIR)
	@echo "Config left in $(CONFIGDIR) — remove manually if desired"
