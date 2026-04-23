"""
theseus_pprint_cr — Clean-room pprint module.
No import of the standard `pprint` module.
"""

import sys as _sys
import re as _re
import io as _io
import types as _types
import collections as _collections


def pformat(object, indent=1, width=80, depth=None, *, compact=False, sort_dicts=True, underscore_numbers=False):
    """Format a Python object into a pretty-printed representation."""
    return PrettyPrinter(indent=indent, width=width, depth=depth, compact=compact,
                         sort_dicts=sort_dicts).pformat(object)


def pprint(object, stream=None, indent=1, width=80, depth=None, *, compact=False, sort_dicts=True, underscore_numbers=False):
    """Pretty-print a Python object to a stream."""
    printer = PrettyPrinter(stream=stream, indent=indent, width=width, depth=depth,
                            compact=compact, sort_dicts=sort_dicts)
    printer.pprint(object)


def isreadable(object):
    """Returns True if object is readable (repr can be eval'd)."""
    return PrettyPrinter().isreadable(object)


def isrecursive(object):
    """Returns True if object is self-referential."""
    return PrettyPrinter().isrecursive(object)


def saferepr(object):
    """Same as repr(object), but protects against recursive data structures."""
    return PrettyPrinter().pformat(object)


def pp(object, *args, sort_dicts=False, **kwargs):
    """Prettily-print a Python object."""
    pprint(object, *args, sort_dicts=sort_dicts, **kwargs)


def _safe_tuple(t):
    return _SafeKey(t[0]), t[1]


class _SafeKey:
    __slots__ = ['obj']

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        try:
            return self.obj < other.obj
        except TypeError:
            return (str(type(self.obj)), id(self.obj)) < (str(type(other.obj)), id(other.obj))


class PrettyPrinter:
    """Pretty-print Python objects."""

    def __init__(self, indent=1, width=80, depth=None, stream=None, *,
                 compact=False, sort_dicts=True, underscore_numbers=False):
        indent = int(indent)
        width = int(width)
        if indent < 0:
            raise ValueError('indent must be >= 0')
        if depth is not None and depth <= 0:
            raise ValueError('depth must be > 0')
        if width <= 0:
            raise ValueError('width must be > 0')
        self._depth = depth
        self._indent_per_level = indent
        self._width = width
        if stream is not None:
            self._stream = stream
        else:
            self._stream = _sys.stdout
        self._compact = compact
        self._sort_dicts = sort_dicts
        self._underscore_numbers = underscore_numbers

    def pprint(self, object):
        self._stream.write(self.pformat(object) + '\n')

    def pformat(self, object, indent=0, allowance=0, context=None, level=1):
        if context is None:
            context = {}
        sio = _io.StringIO()
        self._format(object, sio, indent, allowance, context, level)
        return sio.getvalue()

    def isrecursive(self, object):
        return self.format(object, {}, 0, 0)[2]

    def isreadable(self, object):
        s, readable, recursive = self.format(object, {}, 0, 0)
        return readable and not recursive

    def format(self, object, context, maxlevels, level):
        return _safe_repr(object, context, maxlevels, level, self._sort_dicts)

    def _format(self, object, stream, indent, allowance, context, level):
        obj_id = id(object)
        if obj_id in context:
            stream.write(_recursion(object))
            return
        max_depth = self._depth
        if max_depth is not None and level > max_depth:
            stream.write('...')
            return

        rep = self._repr(object, context, level)

        max_width = self._width - indent - allowance
        if len(rep) <= max_width:
            stream.write(rep)
            return

        # For compound types, try to format multi-line
        if isinstance(object, dict):
            self._format_dict(object, stream, indent, allowance, context, level)
        elif isinstance(object, (list, tuple)):
            self._format_sequence(object, stream, indent, allowance, context, level)
        elif isinstance(object, (set, frozenset)):
            self._format_set(object, stream, indent, allowance, context, level)
        else:
            stream.write(rep)

    def _repr(self, object, context, level):
        repr_fn, readable, recursive = _safe_repr(object, context, self._depth, level, self._sort_dicts)
        return repr_fn

    def _format_dict(self, obj, stream, indent, allowance, context, level):
        if not obj:
            stream.write('{}')
            return
        context[id(obj)] = 1
        stream.write('{\n')
        if self._sort_dicts:
            items = sorted(obj.items(), key=lambda item: _SafeKey(item[0]))
        else:
            items = obj.items()
        indent_str = ' ' * (indent + self._indent_per_level)
        for i, (key, value) in enumerate(items):
            stream.write(indent_str)
            self._format(key, stream, indent + self._indent_per_level, 1, context, level + 1)
            stream.write(': ')
            self._format(value, stream, indent + self._indent_per_level, 1, context, level + 1)
            if i < len(obj) - 1:
                stream.write(',')
            stream.write('\n')
        stream.write(' ' * indent + '}')
        del context[id(obj)]

    def _format_sequence(self, obj, stream, indent, allowance, context, level):
        if isinstance(obj, list):
            open_b, close_b = '[', ']'
        elif isinstance(obj, tuple):
            if len(obj) == 1:
                open_b, close_b = '(', ',)'
            else:
                open_b, close_b = '(', ')'
        else:
            open_b, close_b = '[', ']'
        if not obj:
            stream.write(open_b + close_b)
            return
        context[id(obj)] = 1
        stream.write(open_b + '\n')
        indent_str = ' ' * (indent + self._indent_per_level)
        for i, item in enumerate(obj):
            stream.write(indent_str)
            self._format(item, stream, indent + self._indent_per_level, 1, context, level + 1)
            if i < len(obj) - 1:
                stream.write(',')
            stream.write('\n')
        stream.write(' ' * indent + close_b)
        del context[id(obj)]

    def _format_set(self, obj, stream, indent, allowance, context, level):
        if isinstance(obj, frozenset):
            open_b, close_b = 'frozenset({', '})'
        else:
            open_b, close_b = '{', '}'
        if not obj:
            if isinstance(obj, frozenset):
                stream.write('frozenset()')
            else:
                stream.write('set()')
            return
        context[id(obj)] = 1
        stream.write(open_b + '\n')
        indent_str = ' ' * (indent + self._indent_per_level)
        items = sorted(obj, key=_SafeKey)
        for i, item in enumerate(items):
            stream.write(indent_str)
            self._format(item, stream, indent + self._indent_per_level, 1, context, level + 1)
            if i < len(obj) - 1:
                stream.write(',')
            stream.write('\n')
        stream.write(' ' * indent + close_b)
        del context[id(obj)]


def _safe_repr(object, context, maxlevels, level, sort_dicts):
    typ = type(object)
    if typ in _builtin_scalars:
        return repr(object), True, False

    r = getattr(typ, '__repr__', None)

    if isinstance(object, int) and r is int.__repr__:
        return repr(object), True, False

    if isinstance(object, dict):
        if not object:
            return '{}', True, False
        obj_id = id(object)
        if maxlevels and level >= maxlevels:
            return '{...}', False, obj_id in context
        if obj_id in context:
            return _recursion(object), False, True
        context[obj_id] = 1
        readable = True
        recursive = False
        components = []
        if sort_dicts:
            items = sorted(object.items(), key=lambda t: _SafeKey(t[0]))
        else:
            items = object.items()
        for k, v in items:
            krepr, kreadable, krecur = _safe_repr(k, context, maxlevels, level + 1, sort_dicts)
            vrepr, vreadable, vrecur = _safe_repr(v, context, maxlevels, level + 1, sort_dicts)
            components.append('%s: %s' % (krepr, vrepr))
            readable = readable and kreadable and vreadable
            if krecur or vrecur:
                recursive = True
        del context[obj_id]
        return '{%s}' % ', '.join(components), readable, recursive

    if isinstance(object, (list, tuple)):
        if isinstance(object, list):
            if not object:
                return '[]', True, False
            format = '[%s]'
        elif len(object) == 1:
            format = '(%s,)'
        else:
            if not object:
                return '()', True, False
            format = '(%s)'
        obj_id = id(object)
        if maxlevels and level >= maxlevels:
            return format % '...', False, obj_id in context
        if obj_id in context:
            return _recursion(object), False, True
        context[obj_id] = 1
        readable = True
        recursive = False
        components = []
        for o in object:
            orepr, oreadable, orecur = _safe_repr(o, context, maxlevels, level + 1, sort_dicts)
            components.append(orepr)
            if not oreadable:
                readable = False
            if orecur:
                recursive = True
        del context[obj_id]
        return format % ', '.join(components), readable, recursive

    if isinstance(object, (set, frozenset)):
        if not object:
            if isinstance(object, frozenset):
                return 'frozenset()', True, False
            return 'set()', True, False
        format = 'frozenset({%s})' if isinstance(object, frozenset) else '{%s}'
        obj_id = id(object)
        if maxlevels and level >= maxlevels:
            return format % '...', False, obj_id in context
        if obj_id in context:
            return _recursion(object), False, True
        context[obj_id] = 1
        readable = True
        recursive = False
        components = []
        for o in sorted(object, key=_SafeKey):
            orepr, oreadable, orecur = _safe_repr(o, context, maxlevels, level + 1, sort_dicts)
            components.append(orepr)
            if not oreadable:
                readable = False
            if orecur:
                recursive = True
        del context[obj_id]
        return format % ', '.join(components), readable, recursive

    rep = repr(object)
    return rep, (rep and not rep.startswith('<')), False


_builtin_scalars = frozenset({str, bytes, bytearray, float, complex,
                               bool, type(None)})


def _recursion(object):
    return ('<Recursion on %s with id=%s>' % (type(object).__name__, id(object)))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pprint2_pformat():
    """pformat of a simple dict returns a string; returns True."""
    result = pformat({'a': 1, 'b': 2})
    return isinstance(result, str) and len(result) > 0


def pprint2_nested():
    """pformat of nested list returns a string; returns True."""
    result = pformat([1, [2, [3]]])
    return isinstance(result, str) and '1' in result and '3' in result


def pprint2_isreadable():
    """isreadable returns True for simple objects; returns True."""
    return isreadable([1, 2, 3]) and isreadable({'a': 1})


__all__ = [
    'pformat', 'pprint', 'isreadable', 'isrecursive', 'saferepr', 'pp',
    'PrettyPrinter',
    'pprint2_pformat', 'pprint2_nested', 'pprint2_isreadable',
]
