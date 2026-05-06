"""Clean-room implementation of a Python tab-completion helper.

Provides a Completer class similar to the standard library's rlcompleter,
implemented from scratch using only Python built-ins.
"""

import builtins
import keyword
import re


def _get_class_members(klass):
    """Recursively collect attribute names for a class and its bases."""
    members = list(dir(klass))
    bases = getattr(klass, '__bases__', ())
    for base in bases:
        members = members + _get_class_members(base)
    return members


class Completer:
    """Tab-completion provider for global names and attribute access."""

    def __init__(self, namespace=None):
        if namespace is not None and not isinstance(namespace, dict):
            raise TypeError('namespace must be a dictionary')
        if namespace is None:
            self.use_main_ns = True
            self.namespace = {}
        else:
            self.use_main_ns = False
            self.namespace = namespace
        self.matches = []

    def complete(self, text, state):
        """Return the `state`-th completion for `text`, or None when exhausted."""
        if self.use_main_ns:
            try:
                import __main__
                self.namespace = __main__.__dict__
            except Exception:
                self.namespace = {}

        if state == 0:
            stripped = text.strip() if text is not None else ''
            if not stripped:
                self.matches = ['\t']
            elif '.' in text:
                self.matches = self.attr_matches(text)
            else:
                self.matches = self.global_matches(text)

        if 0 <= state < len(self.matches):
            return self.matches[state]
        return None

    def _callable_postfix(self, val, word):
        if callable(val):
            return word + '('
        return word

    def global_matches(self, text):
        """Match keywords, namespace names, and builtins by prefix."""
        matches = []
        seen = set()
        n = len(text)

        # Keywords
        for word in keyword.kwlist:
            if word[:n] == text and word not in seen:
                seen.add(word)
                if word in ('finally', 'try'):
                    matches.append(word + ':')
                elif word in ('False', 'None', 'True', 'break',
                              'continue', 'pass', 'else'):
                    matches.append(word)
                else:
                    matches.append(word + ' ')

        # User namespace then builtins
        for nspace in (self.namespace, vars(builtins)):
            for word, val in nspace.items():
                if not isinstance(word, str):
                    continue
                if word[:n] == text and word not in seen:
                    seen.add(word)
                    matches.append(self._callable_postfix(val, word))

        return matches

    def attr_matches(self, text):
        """Match attribute names of an object identified by a dotted expression."""
        m = re.match(r"(\w+(\.\w+)*)\.(\w*)", text)
        if not m:
            return []
        expr = m.group(1)
        attr = m.group(3)

        try:
            thisobject = eval(expr, self.namespace)
        except Exception:
            return []

        words = set(dir(thisobject))
        klass = getattr(thisobject, '__class__', None)
        if klass is not None:
            words.add('__class__')
            words.update(_get_class_members(klass))

        matches = []
        n = len(attr)
        for word in words:
            if not isinstance(word, str):
                continue
            if word[:n] == attr and (word != '__builtins__' or attr):
                full = '%s.%s' % (expr, word)
                try:
                    val = getattr(thisobject, word)
                    matches.append(self._callable_postfix(val, full))
                except Exception:
                    matches.append(full)
        matches.sort()
        return matches


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def rlcompleter2_create():
    """Construct a Completer with several namespace forms."""
    try:
        c1 = Completer()
        if c1 is None:
            return False
        c2 = Completer({})
        if c2 is None:
            return False
        ns = {'foo': 1, 'bar': 'x'}
        c3 = Completer(ns)
        if c3 is None or c3.namespace is not ns:
            return False
        # Reject non-dict namespaces
        try:
            Completer([])
        except TypeError:
            pass
        else:
            return False
        return True
    except Exception:
        return False


def rlcompleter2_complete_builtin():
    """Completion of a builtin prefix should return a name starting with that prefix."""
    try:
        c = Completer({})
        first = c.complete('pri', 0)
        if not isinstance(first, str):
            return False
        # Strip trailing '(' added for callables
        bare = first[:-1] if first.endswith('(') else first
        if not bare.startswith('pri'):
            return False
        if 'print' not in {(m[:-1] if m.endswith('(') else m) for m in c.matches}:
            return False

        # An obviously absent prefix should yield no completions on state 0.
        c2 = Completer({})
        none_result = c2.complete('zzzzzznotaname', 0)
        if none_result is not None:
            return False
        return True
    except Exception:
        return False


def rlcompleter2_complete_none():
    """complete() should return None when the requested state is out of range."""
    try:
        c = Completer({})
        # No matches at all -> None
        if c.complete('zzzzz_no_such_name_zzzzz', 0) is not None:
            return False

        # Exhaust matches for a known prefix and verify None is returned.
        c2 = Completer({})
        idx = 0
        while True:
            r = c2.complete('pri', idx)
            if r is None:
                break
            idx += 1
            if idx > 10000:
                return False
        if idx == 0:
            return False  # expected at least one match for 'pri'

        # Empty text returns a tab on state 0 and None thereafter.
        c3 = Completer({})
        if c3.complete('', 0) != '\t':
            return False
        if c3.complete('', 1) is not None:
            return False

        # Negative or large state returns None.
        c4 = Completer({})
        if c4.complete('pri', 99999) is not None:
            return False
        return True
    except Exception:
        return False