"""
theseus_site_cr — Clean-room reimplementation of Python's site module.

Provides minimal site-package configuration: PREFIXES, user site directory,
and addsitedir() for processing .pth files. No imports from the original
`site` module; implemented entirely against the standard library.
"""

import os as _os
import sys as _sys


# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

# PREFIXES: list of installation prefixes searched for site-packages.
PREFIXES = []

# Tracks whether ENABLE_USER_SITE has been determined.
ENABLE_USER_SITE = None

# User site-packages directory (computed lazily).
USER_SITE = None

# User base directory (computed lazily).
USER_BASE = None


def _is_64bit():
    return _sys.maxsize > 2 ** 32


def _init_prefixes():
    """Initialize PREFIXES from sys.prefix and sys.exec_prefix."""
    global PREFIXES
    prefixes = [_sys.prefix, _sys.exec_prefix]
    seen = set()
    result = []
    for p in prefixes:
        if not p:
            continue
        if p in seen:
            continue
        seen.add(p)
        result.append(p)
    PREFIXES = result
    return PREFIXES


def getsitepackages(prefixes=None):
    """Return a list of site-packages directories for the given prefixes.

    If `prefixes` is None, use the module-level PREFIXES list.
    """
    sitepackages = []
    seen = set()

    if prefixes is None:
        prefixes = PREFIXES

    for prefix in prefixes:
        if not prefix or prefix in seen:
            continue
        seen.add(prefix)

        if _os.sep == "/":
            # Posix layout: <prefix>/lib/pythonX.Y/site-packages
            libdirs = ["lib"]
            if _is_64bit() and "lib64" not in libdirs:
                # Some distros use lib64
                pass
            for libdir in libdirs:
                path = _os.path.join(
                    prefix,
                    libdir,
                    "python%d.%d" % _sys.version_info[:2],
                    "site-packages",
                )
                sitepackages.append(path)
        else:
            # Windows-style layout
            sitepackages.append(prefix)
            sitepackages.append(_os.path.join(prefix, "Lib", "site-packages"))

    return sitepackages


# ---------------------------------------------------------------------------
# User site-packages
# ---------------------------------------------------------------------------

def _getuserbase():
    """Compute the user base directory (PYTHONUSERBASE or platform default)."""
    env_base = _os.environ.get("PYTHONUSERBASE")
    if env_base:
        return _os.path.abspath(env_base)

    def joinuser(*args):
        return _os.path.expanduser(_os.path.join(*args))

    if _os.name == "nt":
        appdata = _os.environ.get("APPDATA") or "~"
        return joinuser(appdata, "Python")
    if _sys.platform == "darwin" and _sys._framework if hasattr(_sys, "_framework") else False:
        return joinuser("~", "Library", "Python", "%d.%d" % _sys.version_info[:2])
    return joinuser("~", ".local")


def getuserbase():
    """Return the user base directory, computing it once and caching."""
    global USER_BASE
    if USER_BASE is not None:
        return USER_BASE
    USER_BASE = _getuserbase()
    return USER_BASE


def _get_user_site_path(user_base):
    """Compute the user site-packages path under the given user_base."""
    if _os.name == "nt":
        return _os.path.join(
            user_base,
            "Python%d%d" % _sys.version_info[:2],
            "site-packages",
        )
    return _os.path.join(
        user_base,
        "lib",
        "python%d.%d" % _sys.version_info[:2],
        "site-packages",
    )


def getusersitepackages():
    """Return the user site-packages directory."""
    global USER_SITE
    user_base = getuserbase()
    if USER_SITE is not None:
        return USER_SITE
    USER_SITE = _get_user_site_path(user_base)
    return USER_SITE


def check_enableusersite():
    """Decide whether the user site-packages directory should be enabled.

    Returns:
        True  — enabled
        False — explicitly disabled
        None  — disabled because of a security mismatch (e.g. setuid)
    """
    if _sys.flags.no_user_site:
        return False

    # If running as setuid/setgid, refuse to enable the user site.
    if hasattr(_os, "getuid") and hasattr(_os, "geteuid"):
        if _os.geteuid() != _os.getuid():
            return None
    if hasattr(_os, "getgid") and hasattr(_os, "getegid"):
        if _os.getegid() != _os.getgid():
            return None

    return True


# ---------------------------------------------------------------------------
# .pth file processing and addsitedir
# ---------------------------------------------------------------------------

def _make_path_absolute(path, base):
    """Return path made absolute relative to base (if not already absolute)."""
    if _os.path.isabs(path):
        return path
    return _os.path.abspath(_os.path.join(base, path))


def addpackage(sitedir, name, known_paths):
    """Process a .pth file `name` inside `sitedir`.

    Each non-empty, non-comment line is either:
      * a directive starting with "import " or "import\\t" — executed via exec
      * a path (absolute or relative to sitedir) — added to sys.path if it
        exists and is not already present

    Returns the (possibly mutated) known_paths set, or None if reset.
    """
    if known_paths is None:
        reset = True
        known_paths = set()
    else:
        reset = False

    fullname = _os.path.join(sitedir, name)
    try:
        f = open(fullname, "r", encoding="utf-8", errors="replace")
    except OSError:
        return known_paths

    try:
        for n, line in enumerate(f):
            if line.startswith("#"):
                continue
            line = line.rstrip()
            if not line:
                continue
            try:
                if line.startswith(("import ", "import\t")):
                    exec(line)
                    continue
                # Otherwise treat as path
                line_abs = _make_path_absolute(line, sitedir)
                if line_abs not in known_paths and _os.path.exists(line_abs):
                    _sys.path.append(line_abs)
                    known_paths.add(line_abs)
            except Exception:
                # Mirror site.py behaviour: report and continue.
                print(
                    "Error processing line {:d} of {}".format(n + 1, fullname),
                    file=_sys.stderr,
                )
                continue
    finally:
        f.close()

    if reset:
        known_paths = None
    return known_paths


def _init_pathinfo():
    """Build a set of canonical paths already in sys.path."""
    d = set()
    for item in _sys.path:
        try:
            if item and _os.path.exists(item):
                d.add(_os.path.abspath(item))
        except (TypeError, AttributeError):
            continue
    return d


def addsitedir(sitedir, known_paths=None):
    """Add `sitedir` to sys.path and process every *.pth file inside it.

    Returns the updated known_paths set.
    """
    if known_paths is None:
        known_paths = _init_pathinfo()
        reset = True
    else:
        reset = False

    sitedir_abs = _os.path.abspath(sitedir)

    if sitedir_abs not in known_paths:
        _sys.path.append(sitedir_abs)
        known_paths.add(sitedir_abs)

    try:
        names = _os.listdir(sitedir_abs)
    except OSError:
        return known_paths

    # Process .pth files in sorted order for deterministic behaviour.
    pth_files = sorted(n for n in names if n.endswith(".pth"))
    for pth in pth_files:
        addpackage(sitedir_abs, pth, known_paths)

    if reset:
        # Caller didn't pass known_paths in — return a fresh set so they can
        # observe what we added without poisoning a shared set.
        pass
    return known_paths


# ---------------------------------------------------------------------------
# Module-level initialization
# ---------------------------------------------------------------------------

_init_prefixes()


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def site2_prefixes():
    """Verify that PREFIXES is initialized with sys.prefix / sys.exec_prefix."""
    if not isinstance(PREFIXES, list):
        return False
    if len(PREFIXES) == 0:
        return False
    # PREFIXES should contain sys.prefix.
    if _sys.prefix and _sys.prefix not in PREFIXES:
        return False
    # PREFIXES should be deduplicated.
    if len(PREFIXES) != len(set(PREFIXES)):
        return False
    # getsitepackages() should produce non-empty results for non-empty PREFIXES.
    pkgs = getsitepackages()
    if not isinstance(pkgs, list):
        return False
    if len(pkgs) == 0:
        return False
    # Every entry must be a string path.
    for p in pkgs:
        if not isinstance(p, str) or not p:
            return False
    return True


def site2_user_site():
    """Verify user-site computation: getuserbase / getusersitepackages."""
    base = getuserbase()
    if not isinstance(base, str) or not base:
        return False
    # Should be cached on second call.
    if getuserbase() is not base and getuserbase() != base:
        return False

    user_site = getusersitepackages()
    if not isinstance(user_site, str) or not user_site:
        return False
    # User site must live under the user base.
    if not user_site.startswith(base):
        return False
    # Cached.
    if getusersitepackages() != user_site:
        return False

    # PYTHONUSERBASE override should be honoured.
    saved_env = _os.environ.get("PYTHONUSERBASE")
    saved_base = globals()["USER_BASE"]
    saved_site = globals()["USER_SITE"]
    try:
        globals()["USER_BASE"] = None
        globals()["USER_SITE"] = None
        test_dir = _os.path.abspath(_os.sep + "tmp" + _os.sep + "theseus_user_base_probe")
        _os.environ["PYTHONUSERBASE"] = test_dir
        if getuserbase() != test_dir:
            return False
        site_path = getusersitepackages()
        if not site_path.startswith(test_dir):
            return False
    finally:
        globals()["USER_BASE"] = saved_base
        globals()["USER_SITE"] = saved_site
        if saved_env is None:
            _os.environ.pop("PYTHONUSERBASE", None)
        else:
            _os.environ["PYTHONUSERBASE"] = saved_env

    # check_enableusersite should return True/False/None.
    enabled = check_enableusersite()
    if enabled not in (True, False, None):
        return False
    return True


def site2_addsitedir():
    """Verify addsitedir adds directories and processes .pth files."""
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp(prefix="theseus_site_cr_")
    saved_path = list(_sys.path)
    try:
        # Create a sub-directory we'll reference from a .pth file.
        sub = _os.path.join(tmp, "extra_pkg_dir")
        _os.mkdir(sub)

        # Write a .pth file with: a comment, blank line, a relative path,
        # an absolute path, and a non-existent path that must be ignored.
        pth_path = _os.path.join(tmp, "test.pth")
        with open(pth_path, "w", encoding="utf-8") as f:
            f.write("# a comment\n")
            f.write("\n")
            f.write("extra_pkg_dir\n")
            f.write(sub + "\n")
            f.write(_os.path.join(tmp, "definitely_does_not_exist") + "\n")

        known = addsitedir(tmp)

        if not isinstance(known, set):
            return False
        # The site directory itself should now be on sys.path.
        if _os.path.abspath(tmp) not in _sys.path:
            return False
        # The relative path from the .pth file (resolved against sitedir).
        if sub not in _sys.path:
            return False
        # The non-existent path must NOT be on sys.path.
        bogus = _os.path.join(tmp, "definitely_does_not_exist")
        if bogus in _sys.path:
            return False

        # addsitedir on the same dir should not duplicate sys.path entries.
        before = _sys.path.count(_os.path.abspath(tmp))
        addsitedir(tmp, known)
        after = _sys.path.count(_os.path.abspath(tmp))
        if after != before:
            return False
    except Exception:
        return False
    finally:
        _sys.path[:] = saved_path
        try:
            shutil.rmtree(tmp)
        except OSError:
            pass

    return True


__all__ = [
    "PREFIXES",
    "ENABLE_USER_SITE",
    "USER_SITE",
    "USER_BASE",
    "getsitepackages",
    "getuserbase",
    "getusersitepackages",
    "check_enableusersite",
    "addpackage",
    "addsitedir",
    "site2_prefixes",
    "site2_user_site",
    "site2_addsitedir",
]