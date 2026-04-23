"""
Clean-room implementation of dataclasses utilities.
No import of the original `dataclasses` module.
"""

import inspect

# ── internal registry ──────────────────────────────────────────────────────────

_FIELDS_ATTR = "__dataclass_fields__"   # dict[name -> Field]
_PARAMS_ATTR = "__dataclass_params__"   # internal params marker


# ── Field ─────────────────────────────────────────────────────────────────────

_MISSING = object()          # sentinel for "no default"


class Field:
    """Represents a single field in a dataclass."""

    __slots__ = (
        "name", "type", "default", "default_factory",
        "repr", "hash", "init", "compare", "metadata",
    )

    def __init__(
        self,
        name,
        type_,
        default=_MISSING,
        default_factory=_MISSING,
        repr=True,
        hash=None,
        init=True,
        compare=True,
        metadata=None,
    ):
        self.name = name
        self.type = type_
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.hash = hash
        self.init = init
        self.compare = compare
        self.metadata = metadata or {}

    def __repr__(self):
        return (
            f"Field(name={self.name!r}, type={self.type!r}, "
            f"default={self.default!r})"
        )


def field(
    *,
    default=_MISSING,
    default_factory=_MISSING,
    repr=True,
    hash=None,
    init=True,
    compare=True,
    metadata=None,
):
    """Equivalent of dataclasses.field(...)."""
    if default is not _MISSING and default_factory is not _MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return _FieldSpec(
        default=default,
        default_factory=default_factory,
        repr=repr,
        hash=hash,
        init=init,
        compare=compare,
        metadata=metadata,
    )


class _FieldSpec:
    """Temporary holder returned by field(); consumed by @dataclass."""
    __slots__ = (
        "default", "default_factory", "repr", "hash",
        "init", "compare", "metadata",
    )

    def __init__(self, *, default, default_factory, repr, hash, init, compare, metadata):
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.hash = hash
        self.init = init
        self.compare = compare
        self.metadata = metadata


# ── @dataclass decorator ───────────────────────────────────────────────────────

def dataclass(cls=None, *, init=True, repr=True, eq=True, order=False, frozen=False):
    """Class decorator that turns a class into a dataclass."""

    def wrap(cls):
        return _process_class(cls, init=init, repr=repr, eq=eq, order=order, frozen=frozen)

    if cls is None:
        return wrap
    return wrap(cls)


def _process_class(cls, *, init, repr, eq, order, frozen):
    # Collect annotations from the class (not inherited ones for simplicity)
    annotations = {}
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        annotations.update(getattr(klass, "__annotations__", {}))

    fields_dict = {}
    for name, type_ in annotations.items():
        # Check if there's a class-level default / _FieldSpec
        raw = cls.__dict__.get(name, _MISSING)
        if isinstance(raw, _FieldSpec):
            f = Field(
                name=name,
                type_=type_,
                default=raw.default,
                default_factory=raw.default_factory,
                repr=raw.repr,
                hash=raw.hash,
                init=raw.init,
                compare=raw.compare,
                metadata=raw.metadata,
            )
            # Remove the _FieldSpec from the class namespace
            try:
                delattr(cls, name)
            except AttributeError:
                pass
        elif raw is _MISSING:
            f = Field(name=name, type_=type_)
        else:
            # plain default value
            f = Field(name=name, type_=type_, default=raw)
            try:
                delattr(cls, name)
            except AttributeError:
                pass
        fields_dict[name] = f

    setattr(cls, _FIELDS_ATTR, fields_dict)

    if init:
        _set_new_attribute(cls, "__init__", _make_init(fields_dict, frozen))

    if repr:
        _set_new_attribute(cls, "__repr__", _make_repr(fields_dict))

    if eq:
        _set_new_attribute(cls, "__eq__", _make_eq(fields_dict))

    if frozen:
        _set_new_attribute(cls, "__setattr__", _frozen_setattr)
        _set_new_attribute(cls, "__delattr__", _frozen_delattr)

    return cls


def _set_new_attribute(cls, name, value):
    if name not in cls.__dict__:
        setattr(cls, name, value)


def _make_init(fields_dict, frozen):
    init_fields = [f for f in fields_dict.values() if f.init]

    def __init__(self, *args, **kwargs):
        # bind positional and keyword args
        bound = {}
        positional = list(init_fields)
        for i, val in enumerate(args):
            if i >= len(positional):
                raise TypeError("Too many positional arguments")
            bound[positional[i].name] = val
        for k, v in kwargs.items():
            if k in bound:
                raise TypeError(f"Duplicate argument: {k!r}")
            bound[k] = v

        for f in init_fields:
            if f.name in bound:
                val = bound[f.name]
            elif f.default is not _MISSING:
                val = f.default
            elif f.default_factory is not _MISSING:
                val = f.default_factory()
            else:
                raise TypeError(f"Missing required argument: {f.name!r}")
            if frozen:
                object.__setattr__(self, f.name, val)
            else:
                setattr(self, f.name, val)

        # non-init fields with defaults
        for f in fields_dict.values():
            if not f.init:
                if f.default is not _MISSING:
                    val = f.default
                elif f.default_factory is not _MISSING:
                    val = f.default_factory()
                else:
                    val = _MISSING
                if val is not _MISSING:
                    if frozen:
                        object.__setattr__(self, f.name, val)
                    else:
                        setattr(self, f.name, val)

        if hasattr(self.__class__, "__post_init__"):
            self.__post_init__()

    return __init__


def _make_repr(fields_dict):
    def __repr__(self):
        parts = []
        for f in fields_dict.values():
            if f.repr:
                parts.append(f"{f.name}={getattr(self, f.name)!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"
    return __repr__


def _make_eq(fields_dict):
    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented
        return all(
            getattr(self, f.name) == getattr(other, f.name)
            for f in fields_dict.values()
            if f.compare
        )
    return __eq__


def _frozen_setattr(self, name, value):
    raise TypeError(f"Cannot assign to field {name!r} of frozen dataclass")


def _frozen_delattr(self, name):
    raise TypeError(f"Cannot delete field {name!r} of frozen dataclass")


# ── Public API ─────────────────────────────────────────────────────────────────

def fields(cls_or_instance):
    """Return a tuple of Field objects for the given dataclass or instance."""
    cls = cls_or_instance if isinstance(cls_or_instance, type) else type(cls_or_instance)
    try:
        fields_dict = cls.__dict__[_FIELDS_ATTR]
    except KeyError:
        # walk MRO
        for klass in cls.__mro__:
            if _FIELDS_ATTR in klass.__dict__:
                fields_dict = klass.__dict__[_FIELDS_ATTR]
                break
        else:
            raise TypeError(f"{cls!r} is not a dataclass")
    return tuple(fields_dict.values())


def _is_dataclass_instance(obj):
    return hasattr(type(obj), _FIELDS_ATTR)


def asdict(obj):
    """Recursively convert a dataclass instance to a dict."""
    if not _is_dataclass_instance(obj):
        raise TypeError(f"asdict() should be called on dataclass instances, not {type(obj)!r}")
    return _asdict_inner(obj)


def _asdict_inner(obj):
    if _is_dataclass_instance(obj):
        result = {}
        for f in fields(obj):
            result[f.name] = _asdict_inner(getattr(obj, f.name))
        return result
    elif isinstance(obj, (list, tuple)):
        converted = [_asdict_inner(v) for v in obj]
        return type(obj)(converted) if isinstance(obj, tuple) else converted
    elif isinstance(obj, dict):
        return {_asdict_inner(k): _asdict_inner(v) for k, v in obj.items()}
    else:
        return obj


def astuple(obj):
    """Recursively convert a dataclass instance to a tuple."""
    if not _is_dataclass_instance(obj):
        raise TypeError(f"astuple() should be called on dataclass instances, not {type(obj)!r}")
    return _astuple_inner(obj)


def _astuple_inner(obj):
    if _is_dataclass_instance(obj):
        return tuple(_astuple_inner(getattr(obj, f.name)) for f in fields(obj))
    elif isinstance(obj, (list, tuple)):
        converted = [_astuple_inner(v) for v in obj]
        return type(obj)(converted) if isinstance(obj, tuple) else converted
    elif isinstance(obj, dict):
        return {_astuple_inner(k): _astuple_inner(v) for k, v in obj.items()}
    else:
        return obj


# ── Invariant helpers ──────────────────────────────────────────────────────────

@dataclass
class _Point:
    x: int
    y: int


def dataclasses3_fields():
    """Return the number of fields in the Point dataclass."""
    return len(fields(_Point))


def dataclasses3_asdict():
    """Return asdict(Point(1, 2))."""
    return asdict(_Point(1, 2))


def dataclasses3_astuple():
    """Return list(astuple(Point(1, 2)))."""
    return list(astuple(_Point(1, 2)))


# ── __all__ ────────────────────────────────────────────────────────────────────

__all__ = [
    "dataclass",
    "field",
    "fields",
    "asdict",
    "astuple",
    "dataclasses3_fields",
    "dataclasses3_asdict",
    "dataclasses3_astuple",
]