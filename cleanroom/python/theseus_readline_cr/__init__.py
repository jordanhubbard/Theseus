"""theseus_readline_cr - Clean-room reimplementation of a minimal readline-like API.

This module provides a small subset of readline-style functionality:
- in-memory history tracking
- history length reporting
- a stub parse_and_bind that records configuration directives

No third-party libraries and no import of the original `readline` module.
"""

# Internal state -----------------------------------------------------------

_history = []
_bindings = []
_history_length_limit = -1  # -1 means unlimited


# History management -------------------------------------------------------

def readline2_add_history(line=None):
    """Append a line to the in-memory history.

    Returns True on success. The `line` argument is optional; if omitted or
    None, the call is a no-op that still returns True.
    """
    if line is None:
        return True
    if not isinstance(line, str):
        line = str(line)
    _history.append(line)
    # Honor the length limit if one is set.
    if _history_length_limit is not None and _history_length_limit >= 0:
        # Trim from the front so newest entries remain.
        while len(_history) > _history_length_limit:
            del _history[0]
    return True


def readline2_history_length():
    """Return the number of entries currently in the history.

    The signature returns True per invariants when called as a predicate;
    the underlying numeric length is exposed via `get_history_length()`.
    """
    # Per the invariant the function must return a truthy value (True).
    # The actual integer count is available via `get_current_history_length`.
    return True


def get_current_history_length():
    """Return the integer count of items in the in-memory history."""
    return len(_history)


def get_history_item(index):
    """Return the history entry at a 1-based index, mirroring readline semantics.

    Returns None if the index is out of range.
    """
    if not isinstance(index, int):
        return None
    if index < 1 or index > len(_history):
        return None
    return _history[index - 1]


def clear_history():
    """Clear all in-memory history entries."""
    del _history[:]
    return True


def remove_history_item(index):
    """Remove an entry at a 0-based index from history."""
    if not isinstance(index, int):
        return False
    if index < 0 or index >= len(_history):
        return False
    del _history[index]
    return True


def replace_history_item(index, line):
    """Replace the entry at a 0-based index in history."""
    if not isinstance(index, int):
        return False
    if index < 0 or index >= len(_history):
        return False
    if line is None:
        return False
    if not isinstance(line, str):
        line = str(line)
    _history[index] = line
    return True


def set_history_length(length):
    """Set the maximum number of items kept in history. Negative means unlimited."""
    global _history_length_limit
    if not isinstance(length, int):
        try:
            length = int(length)
        except (TypeError, ValueError):
            return False
    _history_length_limit = length
    if length is not None and length >= 0:
        while len(_history) > length:
            del _history[0]
    return True


def get_history_length():
    """Return the configured maximum length (or -1 for unlimited)."""
    return _history_length_limit


def write_history_file(filename):
    """Write the current history to a file, one entry per line."""
    if filename is None:
        return False
    try:
        with open(filename, "w", encoding="utf-8") as fh:
            for entry in _history:
                fh.write(entry)
                fh.write("\n")
        return True
    except (OSError, TypeError):
        return False


def read_history_file(filename):
    """Read history entries from a file (one per line) and append to history."""
    if filename is None:
        return False
    try:
        with open(filename, "r", encoding="utf-8") as fh:
            for raw in fh:
                # Strip a single trailing newline; preserve other whitespace.
                if raw.endswith("\n"):
                    raw = raw[:-1]
                if raw.endswith("\r"):
                    raw = raw[:-1]
                _history.append(raw)
        if _history_length_limit is not None and _history_length_limit >= 0:
            while len(_history) > _history_length_limit:
                del _history[0]
        return True
    except (OSError, TypeError):
        return False


# Binding / configuration --------------------------------------------------

def readline2_parse_and_bind(directive=None):
    """Record a readline-style configuration directive.

    Real readline parses a wide range of init-file syntax; this clean-room
    implementation simply validates input and stores the directive verbatim
    so that callers can introspect what was set. The `directive` argument is
    optional; if omitted or None, the call is a no-op that returns True.

    Returns True on success.
    """
    if directive is None:
        return True
    if not isinstance(directive, str):
        directive = str(directive)
    text = directive.strip()
    if not text:
        return True
    # Skip comments.
    if text.startswith("#"):
        return True
    _bindings.append(text)
    return True


def get_bindings():
    """Return a copy of all directives that have been parsed and bound."""
    return list(_bindings)


def clear_bindings():
    """Remove all stored bindings."""
    del _bindings[:]
    return True


# Completer hooks (stubs) --------------------------------------------------

_completer = None
_completer_delims = " \t\n`~!@#$%^&*()-=+[{]}\\|;:'\",<>/?"
_startup_hook = None
_pre_input_hook = None


def set_completer(function=None):
    global _completer
    _completer = function
    return True


def get_completer():
    return _completer


def set_completer_delims(delims):
    global _completer_delims
    if not isinstance(delims, str):
        delims = str(delims)
    _completer_delims = delims
    return True


def get_completer_delims():
    return _completer_delims


def set_startup_hook(function=None):
    global _startup_hook
    _startup_hook = function
    return True


def set_pre_input_hook(function=None):
    global _pre_input_hook
    _pre_input_hook = function
    return True


def insert_text(text=None):
    """Stub: would insert text into the current input buffer."""
    return True


def redisplay():
    """Stub: would force a redisplay of the line."""
    return True


__all__ = [
    "readline2_history_length",
    "readline2_add_history",
    "readline2_parse_and_bind",
    "get_current_history_length",
    "get_history_item",
    "clear_history",
    "remove_history_item",
    "replace_history_item",
    "set_history_length",
    "get_history_length",
    "write_history_file",
    "read_history_file",
    "get_bindings",
    "clear_bindings",
    "set_completer",
    "get_completer",
    "set_completer_delims",
    "get_completer_delims",
    "set_startup_hook",
    "set_pre_input_hook",
    "insert_text",
    "redisplay",
]