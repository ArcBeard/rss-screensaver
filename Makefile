PREFIX ?= $(HOME)/.local
BINDIR = $(PREFIX)/bin
CONFIGDIR = $(HOME)/.config/rss-screensaver

.PHONY: install uninstall

install:
	install -Dm755 rss_screensaver.py $(BINDIR)/rss-screensaver
	install -Dm755 rss-screensaver-launch $(BINDIR)/rss-screensaver-launch
	install -Dm644 config/config.toml $(CONFIGDIR)/config.toml
	install -Dm644 config/style.css $(CONFIGDIR)/style.css

uninstall:
	rm -f $(BINDIR)/rss-screensaver
	rm -f $(BINDIR)/rss-screensaver-launch
	@echo "Config left in $(CONFIGDIR) — remove manually if desired"
