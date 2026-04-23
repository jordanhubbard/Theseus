"""
theseus_warnings_cr - Clean-room warning registry implementation.
Do NOT import the original `warnings` module.
"""

# Internal registry of recorded warnings
_registry = []

# Filter list: each entry is a dict with keys: action, message, category, module, lineno
_filters = []


def warn(msg, category=None, stacklevel=1):
    """
    Record a warning in the registry, unless a filter suppresses it.
    
    :param msg: Warning message (str) or Warning instance.
    :param category: Warning category class (default: UserWarning).
    :param stacklevel: Stack level (ignored in this implementation).
    """
    if category is None:
        category = UserWarning

    # Check filters
    for f in reversed(_filters):
        action = f.get('action', 'default')
        fcat = f.get('category', Warning)
        fmsg = f.get('message', '')

        # Check category match
        try:
            cat_match = issubclass(category, fcat)
        except TypeError:
            cat_match = False

        # Check message match
        if fmsg:
            import re
            msg_str = str(msg)
            try:
                msg_match = bool(re.search(fmsg, msg_str))
            except Exception:
                msg_match = False
        else:
            msg_match = True

        if cat_match and msg_match:
            if action == 'ignore':
                return
            elif action in ('always', 'default', 'all', 'error'):
                if action == 'error':
                    raise category(msg)
                break
            break

    # Record the warning
    _registry.append({'message': msg, 'category': category})


def filterwarnings(action, message='', category=Warning, module='', lineno=0, append=False):
    """
    Add a filter to the warning filter list.
    
    :param action: One of 'ignore', 'always', 'default', 'error', 'module', 'once'.
    :param message: Regex pattern to match warning messages.
    :param category: Warning category class to match.
    :param module: Regex pattern to match module names (unused in this impl).
    :param lineno: Line number to match (unused in this impl).
    :param append: If True, append to end; otherwise insert at beginning.
    """
    f = {
        'action': action,
        'message': message,
        'category': category,
        'module': module,
        'lineno': lineno,
    }
    if append:
        _filters.append(f)
    else:
        _filters.insert(0, f)


def simplefilter(action, category=Warning, lineno=0, append=False):
    """
    Add a simple filter (no message or module pattern).
    
    :param action: Filter action string.
    :param category: Warning category class.
    :param lineno: Line number (unused).
    :param append: If True, append; otherwise insert at front.
    """
    filterwarnings(action, message='', category=category, module='', lineno=lineno, append=append)


class catch_warnings:
    """
    Context manager that saves and restores the filter state (and registry state).
    """

    def __init__(self, record=False):
        self._record = record
        self._saved_filters = None
        self._saved_registry = None

    def __enter__(self):
        global _filters, _registry
        # Save current state (deep copy of filters list)
        self._saved_filters = [dict(f) for f in _filters]
        self._saved_registry = list(_registry)
        if self._record:
            # Clear registry so caller can inspect new warnings
            _registry.clear()
        return _registry if self._record else None

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _filters, _registry
        # Restore previous state
        _filters.clear()
        _filters.extend(self._saved_filters)
        _registry.clear()
        _registry.extend(self._saved_registry)
        return False  # Do not suppress exceptions


# ---------------------------------------------------------------------------
# Invariant test helpers (used by the test harness)
# ---------------------------------------------------------------------------

def warnings_warn_records():
    """
    Test: warn('test') is recorded in the registry list.
    Returns True if the warning was recorded.
    """
    global _registry
    before = len(_registry)
    warn('test', UserWarning)
    after = len(_registry)
    # Clean up the test entry
    if after > before:
        _registry.pop()
    return after > before


def warnings_filter_ignore():
    """
    Test: filter 'ignore' suppresses warnings.
    Returns True if an ignored warning is NOT recorded.
    """
    global _registry
    with catch_warnings():
        simplefilter('ignore')
        before = len(_registry)
        warn('ignored warning', UserWarning)
        after = len(_registry)
    return after == before


def warnings_catch_restores():
    """
    Test: catch_warnings restores previous filter state.
    Returns True if filters are restored after the context manager exits.
    """
    global _filters
    # Record original filter state
    original_filters = [dict(f) for f in _filters]

    with catch_warnings():
        simplefilter('ignore')
        simplefilter('always')
        # Filters are modified inside

    # After exiting, filters should be restored
    restored = [dict(f) for f in _filters]
    return restored == original_filters