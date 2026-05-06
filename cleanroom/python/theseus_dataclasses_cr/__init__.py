"""Clean-room implementation of dataclasses (theseus_dataclasses_cr).

Implements: dataclass decorator, field(), fields(), asdict(), astuple().
"""


class _MissingType:
    def __repr__(self):
        return "MISSING"


MISSING = _MissingType()


class Field:
    __slots__ = ("name", "type", "default", "default_factory",
                 "init", "repr", "compare", "hash", "metadata")

    def __init__(self, default=MISSING, default_factory=MISSING,
                 init=True, repr=True, compare=True, hash=None,
                 metadata=None, name=None, type=None):
        self.name = name
        self.type = type
        self.default = default
        self.default_factory = default_factory
        self.init = init
        self.repr = repr
        self.compare = compare
        self.hash = hash
        self.metadata = metadata if metadata is not None else {}

    def __repr__(self):
        return (
            f"Field(name={self.name!r},type={self.type!r},"
            f"default={self.default!r},default_factory={self.default_factory!r},"
            f"init={self.init!r},repr={self.repr!r},compare={self.compare!r})"
        )


def field(*, default=MISSING, default_factory=MISSING,
          init=True, repr=True, compare=True, hash=None, metadata=None):
    """Return a Field descriptor used to customize dataclass field behavior."""
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return Field(
        default=default,
        default_factory=default_factory,
        init=init,
        repr=repr,
        compare=compare,
        hash=hash,
        metadata=metadata,
    )


def _collect_fields(cls):
    """Walk the MRO to gather annotated fields (base classes first)."""
    fields_map = {}
    # Iterate MRO in reverse (excluding object) so subclasses override
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        annotations = klass.__dict__.get("__annotations__", {})
        for name, type_ in annotations.items():
            default = klass.__dict__.get(name, MISSING)
            if isinstance(default, Field):
                f = default
                f.name = name
                f.type = type_
            else:
                f = Field(
                    default=default if default is not MISSING else MISSING,
                    name=name,
                    type=type_,
                )
            fields_map[name] = f
    return list(fields_map.values())


def _build_init(cls, fields_list):
    init_fields = [f for f in fields_list if f.init]

    # Validate: non-default fields cannot follow default fields
    seen_default = False
    for f in init_fields:
        has_default = f.default is not MISSING or f.default_factory is not MISSING
        if seen_default and not has_default:
            raise TypeError(
                f"non-default argument {f.name!r} follows default argument"
            )
        if has_default:
            seen_default = True

    def __init__(self, *args, **kwargs):
        if len(args) > len(init_fields):
            raise TypeError(
                f"__init__() takes at most {len(init_fields)} positional "
                f"arguments but {len(args)} were given"
            )
        bound = {}
        for i, value in enumerate(args):
            bound[init_fields[i].name] = value
        for k, v in kwargs.items():
            if k in bound:
                raise TypeError(f"got multiple values for argument {k!r}")
            bound[k] = v

        for f in init_fields:
            if f.name in bound:
                value = bound[f.name]
            elif f.default is not MISSING:
                value = f.default
            elif f.default_factory is not MISSING:
                value = f.default_factory()
            else:
                raise TypeError(
                    f"__init__() missing required argument: {f.name!r}"
                )
            setattr(self, f.name, value)

        # Set non-init fields from defaults
        for f in fields_list:
            if not f.init:
                if f.default is not MISSING:
                    setattr(self, f.name, f.default)
                elif f.default_factory is not MISSING:
                    setattr(self, f.name, f.default_factory())

        post_init = getattr(self, "__post_init__", None)
        if post_init is not None:
            post_init()

    return __init__


def _build_repr(fields_list):
    repr_fields = [f for f in fields_list if f.repr]

    def __repr__(self):
        parts = []
        for f in repr_fields:
            parts.append(f"{f.name}={getattr(self, f.name)!r}")
        return f"{type(self).__name__}({', '.join(parts)})"

    return __repr__


def _build_eq(fields_list):
    cmp_fields = [f for f in fields_list if f.compare]

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented
        a = tuple(getattr(self, f.name) for f in cmp_fields)
        b = tuple(getattr(other, f.name) for f in cmp_fields)
        return a == b

    return __eq__


def _process_class(cls, init=True, repr=True, eq=True):
    fields_list = _collect_fields(cls)

    # Remove plain class-level defaults (Field objects) from the namespace,
    # but leave simple value defaults so the class still has them as attrs.
    for f in fields_list:
        if f.name in cls.__dict__ and isinstance(cls.__dict__[f.name], Field):
            if f.default is MISSING:
                try:
                    delattr(cls, f.name)
                except AttributeError:
                    pass
            else:
                setattr(cls, f.name, f.default)

    cls.__dataclass_fields__ = {f.name: f for f in fields_list}

    if init:
        cls.__init__ = _build_init(cls, fields_list)
    if repr:
        cls.__repr__ = _build_repr(fields_list)
    if eq:
        cls.__eq__ = _build_eq(fields_list)
        # Make instances unhashable by default when eq is set (mirror std lib)
        cls.__hash__ = None

    return cls


def dataclass(cls=None, *, init=True, repr=True, eq=True):
    """Decorator: transform a class into a dataclass.

    Auto-generates __init__, __repr__, and __eq__ based on annotations.
    """
    def wrap(c):
        return _process_class(c, init=init, repr=repr, eq=eq)

    if cls is None:
        return wrap
    return wrap(cls)


def _is_dataclass_instance(obj):
    return hasattr(type(obj), "__dataclass_fields__")


def is_dataclass(obj):
    cls = obj if isinstance(obj, type) else type(obj)
    return hasattr(cls, "__dataclass_fields__")


def fields(class_or_instance):
    """Return a tuple of Field objects for a dataclass class or instance."""
    try:
        flds = getattr(class_or_instance, "__dataclass_fields__")
    except AttributeError:
        raise TypeError(
            "fields() should be called on dataclass instances or types"
        )
    return tuple(flds.values())


def _copy_value(value):
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_copy_value(v) for v in value]
    if isinstance(value, tuple):
        # Preserve namedtuple-ish types when possible
        if hasattr(value, "_fields"):
            return type(value)(*(_copy_value(v) for v in value))
        return tuple(_copy_value(v) for v in value)
    if isinstance(value, dict):
        return {_copy_value(k): _copy_value(v) for k, v in value.items()}
    return value


def asdict(obj):
    """Recursively convert a dataclass instance into a plain dict."""
    if not _is_dataclass_instance(obj):
        raise TypeError("asdict() should be called on dataclass instances")
    result = {}
    for f in fields(obj):
        result[f.name] = _copy_value(getattr(obj, f.name))
    return result


def _copy_value_tuple(value):
    if is_dataclass(value) and not isinstance(value, type):
        return astuple(value)
    if isinstance(value, list):
        return [_copy_value_tuple(v) for v in value]
    if isinstance(value, tuple):
        if hasattr(value, "_fields"):
            return type(value)(*(_copy_value_tuple(v) for v in value))
        return tuple(_copy_value_tuple(v) for v in value)
    if isinstance(value, dict):
        return {
            _copy_value_tuple(k): _copy_value_tuple(v)
            for k, v in value.items()
        }
    return value


def astuple(obj):
    """Recursively convert a dataclass instance into a plain tuple."""
    if not _is_dataclass_instance(obj):
        raise TypeError("astuple() should be called on dataclass instances")
    return tuple(_copy_value_tuple(getattr(obj, f.name)) for f in fields(obj))


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def dataclasses2_init():
    """Verify that @dataclass auto-generates a working __init__."""
    @dataclass
    class Point:
        x: int
        y: int = 0

    p = Point(1, 2)
    if p.x != 1 or p.y != 2:
        return False

    p2 = Point(5)
    if p2.x != 5 or p2.y != 0:
        return False

    p3 = Point(x=7, y=8)
    if p3.x != 7 or p3.y != 8:
        return False

    @dataclass
    class WithFactory:
        items: list = field(default_factory=list)

    a = WithFactory()
    b = WithFactory()
    if a.items != [] or b.items != []:
        return False
    a.items.append(1)
    if b.items != []:  # ensure factory produced independent instances
        return False

    flds = fields(Point)
    if len(flds) != 2 or flds[0].name != "x" or flds[1].name != "y":
        return False

    return True


def dataclasses2_repr():
    """Verify auto-generated __repr__ produces the expected format."""
    @dataclass
    class Point:
        x: int
        y: int

    p = Point(1, 2)
    if repr(p) != "Point(x=1, y=2)":
        return False

    @dataclass
    class Named:
        name: str
        age: int = 0

    n = Named("alice", 30)
    if repr(n) != "Named(name='alice', age=30)":
        return False

    n2 = Named("bob")
    if repr(n2) != "Named(name='bob', age=0)":
        return False

    return True


def dataclasses2_eq():
    """Verify auto-generated __eq__ compares by value."""
    @dataclass
    class Point:
        x: int
        y: int

    p1 = Point(1, 2)
    p2 = Point(1, 2)
    p3 = Point(1, 3)

    if not (p1 == p2):
        return False
    if p1 == p3:
        return False
    if p1 != p2:
        return False

    # Different types should not compare equal
    @dataclass
    class Other:
        x: int
        y: int

    o = Other(1, 2)
    if p1 == o:
        return False

    # asdict / astuple sanity
    if asdict(p1) != {"x": 1, "y": 2}:
        return False
    if astuple(p1) != (1, 2):
        return False

    return True


__all__ = [
    "dataclass",
    "field",
    "fields",
    "asdict",
    "astuple",
    "is_dataclass",
    "Field",
    "MISSING",
    "dataclasses2_init",
    "dataclasses2_repr",
    "dataclasses2_eq",
]