"""Clean-room typing module for theseus_typing_cr.

Implements minimal type-aliasing and generic-type primitives without importing
the standard library's `typing` module. Only the required invariant functions
are exercised by the spec, but supporting building blocks are provided so the
module name is meaningful.
"""


# ---------------------------------------------------------------------------
# Sentinels / simple type aliases
# ---------------------------------------------------------------------------

class _AnyType:
    """Stand-in for typing.Any."""
    def __repr__(self):
        return "Any"

    def __call__(self, *args, **kwargs):
        return None


Any = _AnyType()


class _SpecialForm:
    """A lightweight stand-in for typing special forms (Optional, Union, ...)."""

    def __init__(self, name):
        self._name = name

    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _GenericAlias(self, params)

    def __repr__(self):
        return self._name


class _GenericAlias:
    """A parametrized generic, e.g. List[int] or Optional[str]."""

    def __init__(self, origin, args):
        self.__origin__ = origin
        self.__args__ = tuple(args)

    def __repr__(self):
        inner = ", ".join(repr(a) for a in self.__args__)
        return "{0}[{1}]".format(repr(self.__origin__), inner)

    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _GenericAlias(self.__origin__, params)


Optional = _SpecialForm("Optional")
Union = _SpecialForm("Union")
List = _SpecialForm("List")
Dict = _SpecialForm("Dict")
Tuple = _SpecialForm("Tuple")
Set = _SpecialForm("Set")
Callable = _SpecialForm("Callable")
ClassVar = _SpecialForm("ClassVar")
Final = _SpecialForm("Final")


# ---------------------------------------------------------------------------
# TypeVar / Generic / Protocol
# ---------------------------------------------------------------------------

class TypeVar:
    """Minimal TypeVar implementation."""

    def __init__(self, name, *constraints, bound=None, covariant=False, contravariant=False):
        self.__name__ = name
        self.__constraints__ = tuple(constraints)
        self.__bound__ = bound
        self.__covariant__ = bool(covariant)
        self.__contravariant__ = bool(contravariant)

    def __repr__(self):
        prefix = ""
        if self.__covariant__:
            prefix = "+"
        elif self.__contravariant__:
            prefix = "-"
        return "{0}{1}".format(prefix, self.__name__)


class Generic:
    """Marker base class for generic types."""

    def __class_getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _GenericAlias(cls, params)


class Protocol:
    """Marker base class for protocols (structural typing)."""

    def __class_getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params,)
        return _GenericAlias(cls, params)


# ---------------------------------------------------------------------------
# Helpers: cast, overload, get_type_hints
# ---------------------------------------------------------------------------

def cast(typ, value):
    """Return value unchanged; cast is a no-op at runtime."""
    return value


def overload(func):
    """Decorator marking a function as an overload variant."""
    def _overloaded_stub(*args, **kwargs):
        raise NotImplementedError(
            "Overloaded function {0} called directly".format(getattr(func, "__name__", "<anonymous>"))
        )
    _overloaded_stub.__wrapped__ = func
    _overloaded_stub.__name__ = getattr(func, "__name__", "_overloaded_stub")
    return _overloaded_stub


def get_type_hints(obj, globalns=None, localns=None):
    """Return the annotations of the given object as a dict.

    Supports modules, classes, and callables. Forward references provided as
    strings are resolved against the supplied (or inferred) global namespace.
    """
    hints = {}

    if isinstance(obj, type):
        # Walk the MRO so subclasses inherit base annotations.
        mro = list(obj.__mro__)
        mro.reverse()
        for klass in mro:
            ann = getattr(klass, "__annotations__", None)
            if ann:
                hints.update(ann)
        ns_globals = getattr(__import__(obj.__module__, fromlist=["*"]), "__dict__", {}) if hasattr(obj, "__module__") else {}
    else:
        ann = getattr(obj, "__annotations__", None)
        if ann:
            hints.update(ann)
        mod_name = getattr(obj, "__module__", None)
        ns_globals = {}
        if mod_name:
            try:
                ns_globals = getattr(__import__(mod_name, fromlist=["*"]), "__dict__", {})
            except Exception:
                ns_globals = {}

    if globalns is not None:
        ns_globals = globalns
    ns_locals = localns if localns is not None else {}

    resolved = {}
    for name, value in hints.items():
        if isinstance(value, str):
            try:
                value = eval(value, ns_globals, ns_locals)
            except Exception:
                pass
        resolved[name] = value
    return resolved


# ---------------------------------------------------------------------------
# Invariant functions required by the spec
# ---------------------------------------------------------------------------

def typing2_optional():
    """Return True to confirm Optional support is wired up."""
    _ = Optional[int]  # exercise __getitem__
    return True


def typing2_typevar():
    """Return the name of a TypeVar — demonstrates TypeVar construction."""
    T = TypeVar("T")
    return T.__name__


def typing2_cast():
    """Return cast(int, 42); cast is a runtime no-op."""
    return cast(int, 42)


__all__ = [
    "Any",
    "Optional",
    "Union",
    "List",
    "Dict",
    "Tuple",
    "Set",
    "Callable",
    "ClassVar",
    "Final",
    "TypeVar",
    "Generic",
    "Protocol",
    "cast",
    "overload",
    "get_type_hints",
    "typing2_optional",
    "typing2_typevar",
    "typing2_cast",
]