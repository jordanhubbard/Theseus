"""
theseus_webbrowser_cr — Clean-room webbrowser module.
No import of the standard `webbrowser` module.
"""

import os as _os
import subprocess as _subprocess
import sys as _sys


Error = OSError

_browsers = {}
_tryorder = None


class BaseBrowser:
    args = ['%s']

    def __init__(self, name=''):
        self.name = name
        self.basename = name

    def open(self, url, new=0, autoraise=True):
        raise NotImplementedError

    def open_new(self, url):
        return self.open(url, 1)

    def open_new_tab(self, url):
        return self.open(url, 2)


class GenericBrowser(BaseBrowser):
    def __init__(self, name):
        if isinstance(name, str):
            self.name = name
            self.args = ['%s']
        else:
            self.name = name[0]
            self.args = name[1:]
        self.basename = _os.path.basename(self.name)

    def open(self, url, new=0, autoraise=True):
        cmdline = [self.name] + [arg.replace('%s', url) for arg in self.args]
        try:
            p = _subprocess.Popen(cmdline, close_fds=True,
                                  stdout=_subprocess.DEVNULL,
                                  stderr=_subprocess.DEVNULL)
            return not p.wait()
        except OSError:
            return False


class BackgroundBrowser(GenericBrowser):
    def open(self, url, new=0, autoraise=True):
        cmdline = [self.name] + [arg.replace('%s', url) for arg in self.args]
        try:
            p = _subprocess.Popen(cmdline, close_fds=True,
                                  stdout=_subprocess.DEVNULL,
                                  stderr=_subprocess.DEVNULL,
                                  start_new_session=True)
            return True
        except OSError:
            return False


class Konqueror(BaseBrowser):
    def open(self, url, new=0, autoraise=True):
        try:
            p = _subprocess.Popen(['kfmclient', 'openURL', url],
                                  close_fds=True,
                                  stdout=_subprocess.DEVNULL,
                                  stderr=_subprocess.DEVNULL)
            p.wait()
            return True
        except OSError:
            return False


class MacOSX(BaseBrowser):
    def __init__(self, name):
        self.name = name

    def open(self, url, new=0, autoraise=True):
        try:
            script = 'open location "%s"' % url.replace('"', '%22')
            _subprocess.run(['osascript', '-e', script],
                            stdout=_subprocess.DEVNULL,
                            stderr=_subprocess.DEVNULL)
            return True
        except OSError:
            return False


class MacOSXOSAScript(BaseBrowser):
    def __init__(self, name):
        self.name = name

    def open(self, url, new=0, autoraise=True):
        try:
            if self.name == 'default':
                script = 'open location "%s"' % url.replace('"', '%22')
            else:
                script = ('tell application "%s"\n'
                          '    activate\n'
                          '    open location "%s"\n'
                          'end tell\n') % (self.name, url.replace('"', '%22'))
            _subprocess.run(['osascript', '-e', script],
                            stdout=_subprocess.DEVNULL,
                            stderr=_subprocess.DEVNULL)
            return True
        except OSError:
            return False


def register(name, klass, instance=None, *, preferred=False):
    """Register a browser type."""
    _browsers[name.lower()] = [klass, instance]
    global _tryorder
    if _tryorder is None:
        _tryorder = []
    if preferred:
        _tryorder.insert(0, name)
    elif name not in _tryorder:
        _tryorder.append(name)


def get(using=None):
    """Return a browser controller."""
    if using is not None:
        if using in _browsers:
            entry = _browsers[using]
            if entry[1] is None and entry[0] is not None:
                entry[1] = entry[0](using)
            return entry[1]
        # Try as a command
        return GenericBrowser(using)
    # Try to find the best available browser
    if _sys.platform == 'darwin':
        return MacOSXOSAScript('default')
    env_browser = _os.environ.get('BROWSER')
    if env_browser:
        return GenericBrowser(env_browser)
    return None


def open(url, new=0, autoraise=True):
    """Open url in a web browser."""
    browser = get()
    if browser is None:
        return False
    return browser.open(url, new, autoraise)


def open_new(url):
    return open(url, 1)


def open_new_tab(url):
    return open(url, 2)


# Register platform browsers
if _sys.platform == 'darwin':
    register('safari', None, MacOSXOSAScript('safari'))
    register('firefox', None, MacOSXOSAScript('firefox'))
    register('default', None, MacOSXOSAScript('default'))
elif _sys.platform.startswith('linux'):
    for cmd in ['xdg-open', 'gnome-open', 'sensible-browser', 'firefox']:
        register(cmd, None, BackgroundBrowser(cmd))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def webbrowser2_browser_class():
    """BaseBrowser class exists; returns True."""
    b = BaseBrowser('test')
    return (isinstance(BaseBrowser, type) and
            isinstance(b, BaseBrowser) and
            hasattr(b, 'open') and
            hasattr(b, 'open_new'))


def webbrowser2_get():
    """get() returns a browser-like object or None; returns True."""
    result = get()
    return result is None or hasattr(result, 'open')


def webbrowser2_register():
    """register() works without error; returns True."""
    register('test-browser', GenericBrowser)
    return 'test-browser' in _browsers


__all__ = [
    'Error', 'BaseBrowser', 'GenericBrowser', 'BackgroundBrowser',
    'MacOSX', 'MacOSXOSAScript', 'Konqueror',
    'register', 'get', 'open', 'open_new', 'open_new_tab',
    'webbrowser2_browser_class', 'webbrowser2_get', 'webbrowser2_register',
]
