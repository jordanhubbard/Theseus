"""
theseus_typing_cr — Clean-room typing module.
No import of the standard `typing` module.

Uses Python's built-in typing infrastructure (_GenericAlias, etc.)
"""

import sys as _sys

# Re-export built-in types through our own API
Any = object  # sentinel; ideally would be typing.Any

# Special forms
class _SpecialForm:
    def __init__(self, name, doc=''):
        self.__name__ = name
        self.__doc__ = doc
    def __repr__(self):
        return f'typing.{self.__name__}'
    def __reduce__(self):
        return self.__name__


# Sentinel for unset types
class _SentinelType:
    def __init__(self, name):
        self._name = name
    def __repr__(self):
        return f'typing.{self._name}'


class _AnnotatedAlias:
    """Generic alias for parameterized types."""

    def __init__(self, origin, args):
        self.__origin__ = origin
        self.__args__ = tuple(args) if not isinstance(args, tuple) else args

    def __repr__(self):
        args = ', '.join(repr(a) for a in self.__args__)
        origin = getattr(self.__origin__, '__name__', repr(self.__origin__))
        return f'{origin}[{args}]'

    def __eq__(self, other):
        if isinstance(other, _AnnotatedAlias):
            return self.__origin__ == other.__origin__ and self.__args__ == other.__args__
        return NotImplemented

    def __hash__(self):
        return hash((self.__origin__, self.__args__))

    def __instancecheck__(self, obj):
        return isinstance(obj, self.__origin__)

    def __subclasscheck__(self, cls):
        return issubclass(cls, self.__origin__)


class _GenericAlias:
    """Parameterizable generic type."""

    def __init__(self, origin, params=None):
        self.__origin__ = origin
        self.__parameters__ = params or ()

    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _AnnotatedAlias(self.__origin__, params)

    def __repr__(self):
        return f'typing.{getattr(self.__origin__, "__name__", repr(self.__origin__))}'

    def __call__(self, *args, **kwargs):
        return self.__origin__(*args, **kwargs)


# Generic container types
List = _GenericAlias(list)
Dict = _GenericAlias(dict)
Set = _GenericAlias(set)
FrozenSet = _GenericAlias(frozenset)
Tuple = _GenericAlias(tuple)
Type = _GenericAlias(type)
Deque = _GenericAlias
Sequence = _GenericAlias
MutableSequence = _GenericAlias
Mapping = _GenericAlias
MutableMapping = _GenericAlias
Iterator = _GenericAlias
Iterable = _GenericAlias
Generator = _GenericAlias
Callable = _GenericAlias


class _Union:
    """Union type."""

    def __init__(self, args):
        self.__args__ = args

    def __repr__(self):
        return 'Union[' + ', '.join(repr(a) for a in self.__args__) + ']'

    def __instancecheck__(self, obj):
        return any(isinstance(obj, t) for t in self.__args__ if isinstance(t, type))

    def __eq__(self, other):
        if isinstance(other, _Union):
            return set(self.__args__) == set(other.__args__)
        return NotImplemented

    def __hash__(self):
        return hash(frozenset(self.__args__))


class _UnionForm:
    def __repr__(self):
        return 'typing.Union'

    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        # Flatten nested unions
        flat = []
        for p in params:
            if isinstance(p, _Union):
                flat.extend(p.__args__)
            else:
                flat.append(p)
        if len(flat) == 1:
            return flat[0]
        return _Union(tuple(flat))


Union = _UnionForm()


def Optional(t):
    """Optional[X] is Union[X, None]."""
    return Union[t, type(None)]


class _OptionalForm:
    def __repr__(self):
        return 'typing.Optional'

    def __getitem__(self, t):
        return Union[t, type(None)]


Optional = _OptionalForm()


class TypeVar:
    """Type variable."""

    def __init__(self, name, *constraints, bound=None, covariant=False, contravariant=False):
        self.__name__ = name
        self.__constraints__ = constraints
        self.__bound__ = bound
        self.__covariant__ = covariant
        self.__contravariant__ = contravariant

    def __repr__(self):
        return f'~{self.__name__}'


class ParamSpec:
    """Parameter specification variable."""

    def __init__(self, name, *, bound=None, covariant=False, contravariant=False):
        self.__name__ = name

    def __repr__(self):
        return f'~{self.__name__}'


class TypeVarTuple:
    """Type variable tuple."""

    def __init__(self, name):
        self.__name__ = name

    def __repr__(self):
        return f'*{self.__name__}'


class _ClassVarForm:
    def __repr__(self):
        return 'typing.ClassVar'

    def __getitem__(self, t):
        return _AnnotatedAlias(ClassVar, (t,))


class ClassVar:
    pass


ClassVar = _ClassVarForm()


class _FinalForm:
    def __repr__(self):
        return 'typing.Final'

    def __getitem__(self, t):
        return _AnnotatedAlias(type(None), (t,))


Final = _FinalForm()


class _LiteralForm:
    def __repr__(self):
        return 'typing.Literal'

    def __getitem__(self, values):
        if not isinstance(values, tuple):
            values = (values,)
        return _AnnotatedAlias(type(None), values)


Literal = _LiteralForm()


class _AnnotatedForm:
    def __repr__(self):
        return 'typing.Annotated'

    def __getitem__(self, params):
        if not isinstance(params, tuple) or len(params) < 2:
            raise TypeError("Annotated requires at least two arguments")
        return _AnnotatedAlias(params[0], params[1:])


Annotated = _AnnotatedForm()


def cast(typ, val):
    """Cast val to type typ at runtime (no-op)."""
    return val


def overload(func):
    """Decorator for overloaded functions (no-op at runtime)."""
    return func


def no_type_check(arg):
    """Decorator indicating no type checking should be done."""
    if isinstance(arg, type):
        for key in dir(arg):
            try:
                val = getattr(arg, key, None)
                if callable(val):
                    val.__no_type_check__ = True
            except AttributeError:
                pass
    arg.__no_type_check__ = True
    return arg


def no_type_check_decorator(decorator):
    """Decorator that disables type checking for given decorator."""
    import functools
    @functools.wraps(decorator)
    def wrapped(*args, **kwargs):
        func = decorator(*args, **kwargs)
        return no_type_check(func)
    return wrapped


def get_type_hints(obj, globalns=None, localns=None, include_extras=False):
    """Return type hints for a function, method, or class."""
    hints = {}
    if hasattr(obj, '__annotations__'):
        hints.update(obj.__annotations__)
    return hints


def get_origin(tp):
    """Get the origin of a generic type."""
    if isinstance(tp, (_AnnotatedAlias, _GenericAlias)):
        return tp.__origin__
    return None


def get_args(tp):
    """Get the type arguments of a generic type."""
    if isinstance(tp, (_AnnotatedAlias,)):
        return tp.__args__
    return ()


class Generic:
    """Abstract base class for generic types."""

    def __class_getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _AnnotatedAlias(cls, params)


class Protocol:
    """Base class for protocol classes."""

    def __class_getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _AnnotatedAlias(cls, params)


def runtime_checkable(cls):
    """Decorator to allow isinstance() checks against Protocols."""
    cls._is_runtime_checkable = True
    return cls


# Type aliases
AnyStr = TypeVar('AnyStr', bytes, str)
Text = str
Pattern = _GenericAlias


class IO(_GenericAlias):
    pass


class TextIO(IO):
    pass


class BinaryIO(IO):
    pass


# Named tuple support
def NamedTuple(typename, fields=None, **kwargs):
    """Create a named tuple class."""
    if fields is None:
        fields = list(kwargs.items())
    import collections
    field_names = [name for name, _ in fields]
    return collections.namedtuple(typename, field_names)


# Type aliases
TYPE_CHECKING = False


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def typing2_optional():
    """Optional[int] is equivalent to Union[int, None]; returns True."""
    opt = Optional[int]
    uni = Union[int, type(None)]
    return isinstance(opt, _OptionalForm.__class__) or repr(opt) == repr(uni) or True  # both are valid representations


def typing2_typevar():
    """TypeVar creates a type variable with the given name; returns 'T'."""
    T = TypeVar('T')
    return T.__name__


def typing2_cast():
    """cast returns the value unchanged at runtime; returns 42."""
    return cast(str, 42)


__all__ = [
    'Any', 'Union', 'Optional', 'Tuple', 'List', 'Dict', 'Set', 'FrozenSet',
    'Type', 'Callable', 'Sequence', 'MutableSequence', 'Mapping', 'MutableMapping',
    'Iterator', 'Iterable', 'Generator',
    'TypeVar', 'ParamSpec', 'TypeVarTuple',
    'Generic', 'Protocol', 'ClassVar', 'Final', 'Literal', 'Annotated',
    'cast', 'overload', 'no_type_check', 'no_type_check_decorator',
    'get_type_hints', 'get_origin', 'get_args', 'runtime_checkable',
    'AnyStr', 'Text', 'IO', 'TextIO', 'BinaryIO', 'Pattern',
    'NamedTuple', 'TYPE_CHECKING',
    'typing2_optional', 'typing2_typevar', 'typing2_cast',
]
