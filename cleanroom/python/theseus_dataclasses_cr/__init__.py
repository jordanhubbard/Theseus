"""
theseus_dataclasses_cr — Clean-room dataclasses module.
No import of the standard `dataclasses` module.
"""

import inspect as _inspect

_MISSING = object()
_HAS_DEFAULT_FACTORY = object()


class Field:
    __slots__ = ('name', 'type', 'default', 'default_factory', 'repr', 'hash',
                 'init', 'compare', 'metadata', 'kw_only', '_field_type')

    def __init__(self, default, default_factory, init, repr, hash, compare, metadata, kw_only):
        self.name = None
        self.type = None
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.hash = hash
        self.init = init
        self.compare = compare
        self.metadata = metadata
        self.kw_only = kw_only

    def __repr__(self):
        return (f'Field(name={self.name!r}, type={self.type!r}, '
                f'default={self.default!r}, init={self.init!r})')


def field(*, default=_MISSING, default_factory=_MISSING, init=True,
          repr=True, hash=None, compare=True, metadata=None, kw_only=False):
    if default is not _MISSING and default_factory is not _MISSING:
        raise TypeError("cannot specify both default and default_factory")
    return Field(default, default_factory, init, repr, hash, compare, metadata, kw_only)


def _get_fields(cls):
    fields = []
    annotations = {}
    for base in reversed(cls.__mro__):
        annotations.update(getattr(base, '__annotations__', {}))
    for name, typ in annotations.items():
        default = getattr(cls, name, _MISSING)
        if isinstance(default, Field):
            f = default
        else:
            f = Field(default, _MISSING, True, True, None, True, None, False)
        f.name = name
        f.type = typ
        fields.append(f)
    return fields


def _make_init(fields):
    params = []
    body = []
    for f in fields:
        if not f.init:
            continue
        if f.default is not _MISSING:
            params.append(f'{f.name}=__dflt_{f.name}')
        elif f.default_factory is not _MISSING:
            params.append(f'{f.name}=_MISSING')
        else:
            params.append(f.name)
        if f.default_factory is not _MISSING:
            body.append(
                f'  if {f.name} is _MISSING:\n'
                f'    self.{f.name} = __factory_{f.name}()\n'
                f'  else:\n'
                f'    self.{f.name} = {f.name}'
            )
        else:
            body.append(f'  self.{f.name} = {f.name}')
    init_src = f'def __init__(self, {", ".join(params)}):\n'
    if body:
        init_src += '\n'.join(body) + '\n'
    else:
        init_src += '  pass\n'
    return init_src


def dataclass(cls=None, *, init=True, repr=True, eq=True, order=False,
              unsafe_hash=False, frozen=False, match_args=True,
              kw_only=False, slots=False):
    def wrap(cls):
        flds = _get_fields(cls)
        cls.__dataclass_fields__ = {f.name: f for f in flds}

        if init:
            globs = {'_MISSING': _MISSING}
            for f in flds:
                if f.default is not _MISSING and not isinstance(f.default, Field):
                    globs[f'__dflt_{f.name}'] = f.default
                if f.default_factory is not _MISSING:
                    globs[f'__factory_{f.name}'] = f.default_factory
            init_src = _make_init(flds)
            exec(init_src, globs)
            cls.__init__ = globs['__init__']

        if repr:
            field_reprs = ', '.join(
                f'{f.name}={{self.{f.name}!r}}'
                for f in flds if f.repr
            )
            cls_name = cls.__name__
            cls.__repr__ = eval(
                f'lambda self: f"{cls_name}({field_reprs})"'
            )

        if eq:
            compare_fields = [f for f in flds if f.compare]
            if compare_fields:
                key_expr = '(' + ', '.join(f'self.{f.name}' for f in compare_fields) + ',)'
                other_key = '(' + ', '.join(f'other.{f.name}' for f in compare_fields) + ',)'
                cls.__eq__ = eval(
                    f'lambda self, other: {key_expr} == {other_key} '
                    f'if type(other) is type(self) else NotImplemented'
                )

        return cls

    if cls is None:
        return wrap
    return wrap(cls)


def fields(class_or_instance):
    """Return tuple of Field objects for a dataclass."""
    try:
        flds = class_or_instance.__dataclass_fields__
    except AttributeError:
        raise TypeError("has no dataclass fields")
    return tuple(flds.values())


def asdict(obj, *, dict_factory=dict):
    """Convert dataclass to dict recursively."""
    if not hasattr(obj, '__dataclass_fields__'):
        raise TypeError("asdict() should be called on dataclass instances")
    return _asdict_inner(obj, dict_factory)


def _asdict_inner(obj, dict_factory):
    if hasattr(obj, '__dataclass_fields__'):
        result = []
        for f in fields(obj):
            result.append((f.name, _asdict_inner(getattr(obj, f.name), dict_factory)))
        return dict_factory(result)
    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
                         for k, v in obj.items())
    return obj


def astuple(obj, *, tuple_factory=tuple):
    """Convert dataclass to tuple recursively."""
    if not hasattr(obj, '__dataclass_fields__'):
        raise TypeError("astuple() should be called on dataclass instances")
    return _astuple_inner(obj, tuple_factory)


def _astuple_inner(obj, tuple_factory):
    if hasattr(obj, '__dataclass_fields__'):
        return tuple_factory([_astuple_inner(getattr(obj, f.name), tuple_factory)
                               for f in fields(obj)])
    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[_astuple_inner(v, tuple_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_astuple_inner(v, tuple_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_astuple_inner(k, tuple_factory), _astuple_inner(v, tuple_factory))
                         for k, v in obj.items())
    return obj


def is_dataclass(obj):
    """Return True if obj is a dataclass or dataclass instance."""
    cls = obj if isinstance(obj, type) else type(obj)
    return hasattr(cls, '__dataclass_fields__')


def make_dataclass(cls_name, fields_list, *, bases=(object,), namespace=None,
                   init=True, repr=True, eq=True, order=False,
                   unsafe_hash=False, frozen=False):
    if namespace is None:
        namespace = {}
    anns = {}
    for item in fields_list:
        if isinstance(item, str):
            name = item
            tp = 'typing.Any'
        elif len(item) == 2:
            name, tp = item
        else:
            name, tp, spec = item
            namespace[name] = spec
        anns[name] = tp
    namespace['__annotations__'] = anns
    cls = type(cls_name, bases, namespace)
    return dataclass(cls, init=init, repr=repr, eq=eq, order=order,
                     unsafe_hash=unsafe_hash, frozen=frozen)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def dataclasses2_init():
    """dataclass auto-generates __init__ from fields; returns True."""
    @dataclass
    class Point:
        x: float
        y: float

    p = Point(1.0, 2.0)
    return p.x == 1.0 and p.y == 2.0


def dataclasses2_repr():
    """dataclass auto-generates __repr__; returns True."""
    @dataclass
    class Point:
        x: float
        y: float

    p = Point(1.0, 2.0)
    return 'Point' in repr(p) and '1.0' in repr(p)


def dataclasses2_eq():
    """dataclass auto-generates __eq__ based on fields; returns True."""
    @dataclass
    class Point:
        x: float
        y: float

    return Point(1.0, 2.0) == Point(1.0, 2.0) and Point(1.0, 2.0) != Point(3.0, 4.0)


__all__ = [
    'dataclass', 'field', 'Field', 'fields', 'asdict', 'astuple',
    'is_dataclass', 'make_dataclass',
    'dataclasses2_init', 'dataclasses2_repr', 'dataclasses2_eq',
]
