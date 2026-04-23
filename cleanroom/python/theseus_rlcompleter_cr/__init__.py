"""
theseus_rlcompleter_cr — Clean-room rlcompleter module.
No import of the standard `rlcompleter` module.
"""

import keyword as _keyword
import builtins as _builtins


class Completer:
    def __init__(self, namespace=None):
        if namespace is None:
            self.use_main_ns = True
            self.namespace = {}
        else:
            self.use_main_ns = False
            self.namespace = namespace
        self.matches = []

    def complete(self, text, state):
        if state == 0:
            if self.use_main_ns:
                import __main__
                self.namespace = __main__.__dict__

            if '.' in text:
                self.matches = self.attr_matches(text)
            else:
                self.matches = self.global_matches(text)

        try:
            return self.matches[state]
        except IndexError:
            return None

    def global_matches(self, text):
        matches = []
        seen = set()

        for word in _keyword.kwlist:
            if word.startswith(text) and word not in seen:
                seen.add(word)
                matches.append(word)

        for word in dir(_builtins):
            if word.startswith(text) and word not in seen:
                seen.add(word)
                matches.append(word)

        for word in self.namespace:
            if word.startswith(text) and word not in seen:
                seen.add(word)
                matches.append(word)

        return matches

    def attr_matches(self, text):
        import re
        m = re.match(r'(\w+(\.\w+)*)\.(\w*)', text)
        if not m:
            return []
        expr, attr = m.group(1), m.group(3)
        try:
            thisobject = eval(expr, self.namespace)
        except Exception:
            return []
        words = set(dir(thisobject))
        if hasattr(thisobject, '__class__'):
            words |= set(dir(thisobject.__class__))
        matches = []
        for word in words:
            if word.startswith(attr) and not word.startswith('__'):
                matches.append('%s.%s' % (expr, word))
        if not matches and attr.startswith('__'):
            for word in words:
                if word.startswith(attr):
                    matches.append('%s.%s' % (expr, word))
        return matches


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def rlcompleter2_create():
    """Completer() can be created; returns True."""
    c = Completer()
    return callable(c.complete)


def rlcompleter2_complete_builtin():
    """complete() returns builtins for 'pr'; returns True."""
    c = Completer({'x': 1})
    first = c.complete('pr', 0)
    return first is not None and first.startswith('pr')


def rlcompleter2_complete_none():
    """complete() returns None when no more completions; returns True."""
    c = Completer({'xyz_unique_var': 1})
    match0 = c.complete('xyz_unique_var', 0)
    match1 = c.complete('xyz_unique_var', 1)
    return match0 == 'xyz_unique_var' and match1 is None


__all__ = [
    'Completer',
    'rlcompleter2_create', 'rlcompleter2_complete_builtin',
    'rlcompleter2_complete_none',
]
