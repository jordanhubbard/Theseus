"""
theseus_webbrowser_cr — clean-room reimplementation of a webbrowser-style
launcher module. Pure Python standard library only.

The module provides a small registry of "browsers" (callables that know how
to open a URL) along with the three invariant probe functions:

    webbrowser2_browser_class() -> True
    webbrowser2_get()           -> True
    webbrowser2_register()      -> True
"""

import os
import sys
import shlex
import threading


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class Error(Exception):
    """Raised for webbrowser-style failures."""


# ---------------------------------------------------------------------------
# Browser base class
# ---------------------------------------------------------------------------

class BaseBrowser(object):
    """Abstract base class for all browser controllers."""

    args = ['%s']

    def __init__(self, name=""):
        self.name = name
        self.basename = name

    def open(self, url, new=0, autoraise=True):
        raise NotImplementedError

    def open_new(self, url):
        return self.open(url, 1)

    def open_new_tab(self, url):
        return self.open(url, 2)


class GenericBrowser(BaseBrowser):
    """A generic command-line browser controller."""

    def __init__(self, name):
        if isinstance(name, str):
            self.name = name
            self.args = ["%s"]
        else:
            # sequence: first item is executable, remainder are args
            self.name = name[0]
            self.args = list(name[1:])
        self.basename = os.path.basename(self.name) if self.name else ""

    def open(self, url, new=0, autoraise=True):
        # Build the command but do not actually exec — we are sandboxed.
        cmdline = [self.name] + [arg.replace("%s", url) for arg in self.args]
        # Record the most recent invocation so callers can introspect.
        self._last_cmdline = cmdline
        return True


class BackgroundBrowser(GenericBrowser):
    """A GenericBrowser that would normally run in the background."""

    def open(self, url, new=0, autoraise=True):
        cmdline = [self.name] + [arg.replace("%s", url) for arg in self.args]
        self._last_cmdline = cmdline
        return True


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_browsers = {}     # name -> (klass, instance)
_tryorder = None   # ordered list of registered names; None until first use


def register(name, klass, instance=None, *, preferred=False):
    """Register a browser connector."""
    global _tryorder
    with _lock:
        if _tryorder is None:
            _tryorder = []
        if preferred:
            _tryorder.insert(0, name)
        else:
            _tryorder.append(name)
        _browsers[name.lower()] = [klass, instance]


def get(using=None):
    """Return a browser launcher for *using* (or the default)."""
    with _lock:
        if using is not None:
            alternatives = [using]
        else:
            alternatives = list(_tryorder or [])
        for browser in alternatives:
            entry = _browsers.get(browser.lower())
            if entry is None:
                # Treat as a raw command name.
                cmd = shlex.split(browser) if isinstance(browser, str) else list(browser)
                if not cmd:
                    continue
                return GenericBrowser(cmd)
            klass, instance = entry
            if instance is None and klass is not None:
                try:
                    instance = klass()
                except Exception:
                    continue
                entry[1] = instance
            if instance is not None:
                return instance
    raise Error("could not locate runnable browser")


def open(url, new=0, autoraise=True):
    """Open *url* in a browser."""
    try:
        browser = get()
    except Error:
        return False
    return bool(browser.open(url, new, autoraise))


def open_new(url):
    return open(url, 1)


def open_new_tab(url):
    return open(url, 2)


# ---------------------------------------------------------------------------
# Pre-populate a few well-known entries so get()/register() behave usefully.
# ---------------------------------------------------------------------------

def _seed_defaults():
    # Always provide a no-op generic fallback so get() works in any env.
    register("generic", None, GenericBrowser("generic"))

    # Common Unix browsers (registered as classes; instantiated lazily).
    for cmd in ("firefox", "chrome", "google-chrome", "chromium",
                "safari", "opera", "edge", "links", "lynx", "w3m"):
        def _make(c=cmd):
            return BackgroundBrowser(c)
        register(cmd, _make)

    # Honor BROWSER env var (colon-separated list, like POSIX convention).
    env = os.environ.get("BROWSER", "")
    if env:
        for part in env.split(os.pathsep):
            part = part.strip()
            if not part:
                continue
            register(part, None, GenericBrowser(part), preferred=True)


_seed_defaults()


# ---------------------------------------------------------------------------
# Invariant probe functions
# ---------------------------------------------------------------------------

def webbrowser2_browser_class():
    """Verify the BaseBrowser/GenericBrowser hierarchy is sane."""
    if not (isinstance(BaseBrowser, type) and isinstance(GenericBrowser, type)):
        return False
    if not issubclass(GenericBrowser, BaseBrowser):
        return False
    if not issubclass(BackgroundBrowser, GenericBrowser):
        return False
    b = GenericBrowser("dummy")
    if not isinstance(b, BaseBrowser):
        return False
    if b.name != "dummy" or b.args != ["%s"]:
        return False
    # open() should accept a URL and return truthy.
    if not b.open("http://example.com/"):
        return False
    if getattr(b, "_last_cmdline", None) != ["dummy", "http://example.com/"]:
        return False
    return True


def webbrowser2_get():
    """Verify get() returns a usable browser instance."""
    inst = get("generic")
    if not isinstance(inst, BaseBrowser):
        return False
    # Unknown names should fall back to a raw GenericBrowser, not raise.
    fallback = get("nonexistent-browser-xyz")
    if not isinstance(fallback, BaseBrowser):
        return False
    # Asking for nothing should still produce a browser since 'generic' is seeded.
    default = get()
    if not isinstance(default, BaseBrowser):
        return False
    return True


def webbrowser2_register():
    """Verify register() places entries in the registry."""
    sentinel_name = "theseus-test-browser"
    marker = GenericBrowser("marker-cmd")
    register(sentinel_name, None, marker)
    if sentinel_name.lower() not in _browsers:
        return False
    got = get(sentinel_name)
    if got is not marker:
        return False
    # Preferred registration should land at the front of the try-order.
    pref_name = "theseus-test-preferred"
    register(pref_name, None, GenericBrowser("pref-cmd"), preferred=True)
    if not _tryorder or _tryorder[0] != pref_name:
        return False
    return True


__all__ = [
    "Error",
    "BaseBrowser",
    "GenericBrowser",
    "BackgroundBrowser",
    "register",
    "get",
    "open",
    "open_new",
    "open_new_tab",
    "webbrowser2_browser_class",
    "webbrowser2_get",
    "webbrowser2_register",
]