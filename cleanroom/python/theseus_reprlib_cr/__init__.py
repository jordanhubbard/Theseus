"""
theseus_reprlib_cr - Clean-room truncating repr utility.
Do NOT import reprlib or any third-party library.
"""

# Save built-in repr before we shadow it
_builtin_repr = repr


class Repr:
    """
    Configurable repr with truncation for long sequences and strings.
    """

    def __init__(self):
        self.maxlevel = 6
        self.maxdict = 4
        self.maxlist = 6
        self.maxtuple = 6
        self.maxset = 6
        self.maxfrozenset = 6
        self.maxdeque = 6
        self.maxarray = 5
        self.maxlong = 40
        self.maxstring = 30
        self.maxother = 30
        self.fillvalue = '...'
        self.maxint = 40

    def repr(self, obj):
        return self.repr1(obj, self.maxlevel)

    def repr1(self, obj, level):
        typename = type(obj).__name__
        # Try to find a specific method
        method_name = 'repr_' + typename
        method = getattr(self, method_name, None)
        if method is not None:
            return method(obj, level)
        else:
            return self.repr_instance(obj, level)

    def _repr_iterable(self, obj, level, left, right, maxitems, trail=''):
        n = len(obj)
        if n == 0:
            return left + right
        if level <= 0:
            return left + self.fillvalue + right
        items = list(obj)
        if n <= maxitems:
            pieces = [self.repr1(item, level - 1) for item in items]
            s = ', '.join(pieces)
        else:
            pieces = [self.repr1(item, level - 1) for item in items[:maxitems]]
            pieces.append(self.fillvalue)
            s = ', '.join(pieces)
        return left + s + trail + right

    def repr_list(self, obj, level):
        return self._repr_iterable(obj, level, '[', ']', self.maxlist)

    def repr_tuple(self, obj, level):
        trail = ',' if len(obj) == 1 else ''
        return self._repr_iterable(obj, level, '(', ')', self.maxtuple, trail)

    def repr_set(self, obj, level):
        if not obj:
            return 'set()'
        return self._repr_iterable(sorted(obj, key=_builtin_repr), level, '{', '}', self.maxset)

    def repr_frozenset(self, obj, level):
        if not obj:
            return 'frozenset()'
        inner = self._repr_iterable(sorted(obj, key=_builtin_repr), level, '{', '}', self.maxfrozenset)
        return 'frozenset(' + inner + ')'

    def repr_dict(self, obj, level):
        n = len(obj)
        if n == 0:
            return '{}'
        if level <= 0:
            return '{' + self.fillvalue + '}'
        items = list(obj.items())
        if n <= self.maxdict:
            pieces = [self.repr1(k, level - 1) + ': ' + self.repr1(v, level - 1)
                      for k, v in items]
        else:
            pieces = [self.repr1(k, level - 1) + ': ' + self.repr1(v, level - 1)
                      for k, v in items[:self.maxdict]]
            pieces.append(self.fillvalue)
        return '{' + ', '.join(pieces) + '}'

    def repr_str(self, obj, level):
        s = _builtin_repr(obj)
        if len(obj) > self.maxstring:
            i = max(0, self.maxstring)
            truncated = obj[:i]
            r = _builtin_repr(truncated)
            # Remove closing quote, add ellipsis, re-add closing quote
            quote_char = r[0]
            r = r[:-1] + self.fillvalue + quote_char
            return r
        return s

    def repr_int(self, obj, level):
        s = _builtin_repr(obj)
        if len(s) > self.maxlong:
            i = max(0, self.maxlong)
            s = s[:i] + self.fillvalue
        return s

    def repr_float(self, obj, level):
        return _builtin_repr(obj)

    def repr_bool(self, obj, level):
        return _builtin_repr(obj)

    def repr_NoneType(self, obj, level):
        return _builtin_repr(obj)

    def repr_bytes(self, obj, level):
        s = _builtin_repr(obj)
        if len(obj) > self.maxstring:
            truncated = obj[:self.maxstring]
            r = _builtin_repr(truncated)
            # r ends with b'...' style; remove last quote, add fillvalue, re-add
            quote_char = r[-1]
            r = r[:-1] + self.fillvalue + quote_char
            return r
        return s

    def repr_instance(self, obj, level):
        try:
            s = _builtin_repr(obj)
        except Exception:
            s = '<' + type(obj).__name__ + ' instance>'
        if len(s) > self.maxother:
            i = max(0, self.maxother)
            s = s[:i] + self.fillvalue
        return s


# Module-level default Repr instance
_default_repr = Repr()


def repr(obj):
    """Return an abbreviated string representation of obj."""
    return _default_repr.repr(obj)


# Test helper functions referenced in invariants

def reprlib_repr_long_list():
    """repr(list(range(100))) is truncated (contains '...')."""
    result = repr(list(range(100)))
    return '...' in result


def reprlib_repr_short_list():
    """repr([1,2,3]) == '[1, 2, 3]'."""
    return repr([1, 2, 3])


def reprlib_repr_long_str():
    """repr('x'*1000) is truncated."""
    result = repr('x' * 1000)
    return '...' in result