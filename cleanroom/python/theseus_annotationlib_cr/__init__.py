"""
theseus_annotationlib_cr — Clean-room annotationlib module.
No import of the standard `annotationlib` module.
Provides annotation utilities (Python 3.14+).
"""

import enum as _enum
import sys as _sys
import types as _types
import typing as _typing


class Format(_enum.IntEnum):
    """Format for retrieving annotations."""
    VALUE = 1
    VALUE_WITH_FAKE_GLOBALS = 2
    FORWARDREF = 3
    STRING = 4


class ForwardRef:
    """A forward reference to a type annotation."""

    __slots__ = (
        '__arg__', '__forward_evaluated__', '__forward_value__',
        '__forward_is_argument__', '__forward_is_class__',
        '__forward_module__', '__code__', '__cell__', '__ast_node__',
        '__extra_names__',
    )

    def __init__(self, arg, *, is_argument=True, module=None, is_class=False):
        if not isinstance(arg, str):
            raise TypeError(f"Forward reference must be a string -- got {arg!r}")
        self.__arg__ = arg
        self.__forward_evaluated__ = False
        self.__forward_value__ = None
        self.__forward_is_argument__ = is_argument
        self.__forward_is_class__ = is_class
        self.__forward_module__ = module
        try:
            self.__code__ = compile(arg, '<string>', 'eval')
        except SyntaxError:
            self.__code__ = None
        self.__cell__ = None
        self.__ast_node__ = None
        self.__extra_names__ = None

    def _evaluate(self, globalns, localns, type_params, *, recursive_guard):
        if self.__forward_evaluated__ and localns is None:
            return self.__forward_value__
        if globalns is None:
            globalns = {}
        if localns is None:
            localns = {}
        try:
            val = eval(self.__code__, globalns, localns)
            self.__forward_evaluated__ = True
            self.__forward_value__ = val
            return val
        except NameError:
            return self

    def __repr__(self):
        return f'ForwardRef({self.__arg__!r})'

    def __hash__(self):
        return hash(self.__arg__)

    def __eq__(self, other):
        if not isinstance(other, ForwardRef):
            return NotImplemented
        return self.__arg__ == other.__arg__

    def __class_getitem__(cls, item):
        return cls


def get_annotations(obj, *, globals=None, locals=None,
                    eval_str=False, format=Format.VALUE):
    """Compute the annotations dict for an object."""
    if isinstance(format, int):
        format = Format(format)

    if isinstance(obj, type):
        # Class
        hints = {}
        for base in reversed(obj.__mro__):
            base_annotations = base.__dict__.get('__annotations__', {})
            if isinstance(base_annotations, dict):
                hints.update(base_annotations)
        ann = hints
    elif callable(obj):
        ann = getattr(obj, '__annotations__', {})
    elif hasattr(obj, '__annotations__'):
        ann = obj.__annotations__
    else:
        ann = {}

    if not ann:
        return {}

    result = {}
    for key, value in ann.items():
        if eval_str and isinstance(value, str):
            try:
                g = globals or getattr(obj, '__globals__', {})
                l = locals or {}
                value = eval(compile(value, '<string>', 'eval'), g, l)
            except Exception:
                pass
        elif format == Format.STRING and not isinstance(value, str):
            value = type_repr(value)
        elif format == Format.FORWARDREF and isinstance(value, str):
            value = ForwardRef(value)
        result[key] = value

    return result


def type_repr(obj):
    """Return a string representation of a type annotation."""
    if isinstance(obj, type):
        if obj.__module__ == 'builtins':
            return obj.__qualname__
        return f'{obj.__module__}.{obj.__qualname__}'
    if isinstance(obj, str):
        return obj
    return repr(obj)


def call_annotate_function(annotate, format, *, owner=None):
    """Call an __annotate__ function with the given format."""
    if callable(annotate):
        try:
            return annotate(format)
        except NotImplementedError:
            return {}
    return {}


def call_evaluate_function(evaluate, format, *, owner=None):
    """Call an __evaluate__ function."""
    if callable(evaluate):
        try:
            return evaluate()
        except Exception:
            return None
    return None


def get_annotate_from_class_namespace(ns):
    """Get the __annotate__ function from a class namespace."""
    return ns.get('__annotate__')


def annotations_to_string(annotations):
    """Convert an annotations dict to a string representation."""
    if not annotations:
        return '{}'
    parts = []
    for k, v in annotations.items():
        parts.append(f'{k}: {type_repr(v)}')
    return '{' + ', '.join(parts) + '}'


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def annotlib2_get_annotations():
    """get_annotations() retrieves annotations from a function; returns True."""
    def f(x: int, y: str) -> bool:
        pass
    ann = get_annotations(f)
    return (isinstance(ann, dict) and
            ann.get('x') is int and
            ann.get('y') is str)


def annotlib2_forward_ref():
    """ForwardRef class can be instantiated; returns True."""
    ref = ForwardRef('MyClass')
    return (ref.__arg__ == 'MyClass' and
            repr(ref) == "ForwardRef('MyClass')")


def annotlib2_format():
    """Format enum has VALUE and STRING members; returns True."""
    return (Format.VALUE == 1 and
            Format.STRING == 4 and
            Format.FORWARDREF == 3)


__all__ = [
    'Format', 'ForwardRef', 'get_annotations',
    'call_annotate_function', 'call_evaluate_function',
    'get_annotate_from_class_namespace', 'annotations_to_string',
    'type_repr',
    'annotlib2_get_annotations', 'annotlib2_forward_ref', 'annotlib2_format',
]
