"""
theseus_warnings_cr2 — Clean-room warnings utilities.
No import of the standard `warnings` module.
"""

import re

# Module-level filter list: each entry is a tuple
# (action, message_pattern, category, module_pattern, lineno)
_filters = []

# Module-level list of issued warnings (for tracking)
_issued = []


def resetwarnings():
    """Clear all warning filters."""
    global _filters
    _filters = []


def filterwarnings(action, message='', category=Warning, module='', lineno=0, append=False):
    """
    Add a warning filter.

    Parameters
    ----------
    action  : str  — one of 'default', 'ignore', 'always', 'error', 'once', 'module'
    message : str  — regex pattern matched against the warning message
    category: type — Warning subclass
    module  : str  — regex pattern matched against the module name
    lineno  : int  — line number (0 = any)
    append  : bool — if True, append; otherwise prepend
    """
    if not (isinstance(lineno, int) and lineno >= 0):
        raise ValueError("Lineno must be a non-negative integer")
    if not (isinstance(category, type) and issubclass(category, Warning)):
        raise TypeError("category must be a Warning subclass")

    # Compile patterns to validate them (but store as strings)
    try:
        re.compile(message)
    except re.error as e:
        raise ValueError(f"Invalid message pattern: {e}") from e
    try:
        re.compile(module)
    except re.error as e:
        raise ValueError(f"Invalid module pattern: {e}") from e

    entry = (action, message, category, module, lineno)
    if append:
        _filters.append(entry)
    else:
        _filters.insert(0, entry)


def simplefilter(action, category=Warning, lineno=0, append=False):
    """
    Simplified filter — matches any message and any module.
    """
    filterwarnings(action, message='', category=category, module='', lineno=lineno, append=append)


def warn(msg, cat=UserWarning):
    """
    Issue a warning.  Applies the current filter list to decide what to do.
    """
    if not (isinstance(cat, type) and issubclass(cat, Warning)):
        raise TypeError("category must be a Warning subclass")

    action = _get_action(str(msg), cat, '', 0)

    if action == 'error':
        raise cat(msg)
    elif action == 'ignore':
        return
    elif action == 'always':
        _issued.append((msg, cat))
        _show_warning(msg, cat)
    elif action == 'once':
        key = (msg, cat)
        if key not in _issued:
            _issued.append(key)
            _show_warning(msg, cat)
    elif action == 'default':
        key = (msg, cat)
        if key not in _issued:
            _issued.append(key)
            _show_warning(msg, cat)
    elif action == 'module':
        _show_warning(msg, cat)
    else:
        # Unknown action — show anyway
        _show_warning(msg, cat)


def _get_action(message, category, module, lineno):
    """Walk the filter list and return the matching action, or 'default'."""
    for (action, msg_pat, cat, mod_pat, filt_lineno) in _filters:
        # Check category
        if not issubclass(category, cat):
            continue
        # Check message pattern
        if msg_pat and not re.search(msg_pat, message):
            continue
        # Check module pattern
        if mod_pat and not re.search(mod_pat, module):
            continue
        # Check lineno
        if filt_lineno and filt_lineno != lineno:
            continue
        return action
    return 'default'


def _show_warning(msg, cat):
    """Print a warning to stderr."""
    import sys
    print(f"{cat.__name__}: {msg}", file=sys.stderr)


class catch_warnings:
    """
    Context manager that saves and restores the warnings filter list.

    Usage:
        with catch_warnings():
            filterwarnings('ignore')
            ...
    """

    def __init__(self):
        self._saved_filters = None

    def __enter__(self):
        global _filters
        # Save a shallow copy of the current filter list
        self._saved_filters = list(_filters)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _filters
        # Restore the saved filter list
        _filters = self._saved_filters
        return False  # Do not suppress exceptions


# ---------------------------------------------------------------------------
# Zero-argument invariant helpers
# ---------------------------------------------------------------------------

def warnings2_catch():
    """Verify that catch_warnings works as a context manager. Returns True."""
    with catch_warnings():
        pass
    return True


def warnings2_filter():
    """Verify that filterwarnings('ignore') does not raise. Returns True."""
    with catch_warnings():
        filterwarnings('ignore')
    return True


def warnings2_simplefilter():
    """Verify that simplefilter('always') does not raise. Returns True."""
    with catch_warnings():
        simplefilter('always')
    return True


__all__ = [
    'warn',
    'filterwarnings',
    'simplefilter',
    'catch_warnings',
    'resetwarnings',
    'warnings2_catch',
    'warnings2_filter',
    'warnings2_simplefilter',
]