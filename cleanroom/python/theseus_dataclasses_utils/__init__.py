"""
theseus_dataclasses_utils - Clean-room implementation of dataclass utilities.
"""

import inspect

_MISSING = object()


class Field:
    """Represents a field in a dataclass."""
    
    def __init__(self, default=_MISSING, default_factory=_MISSING, name=None, type=None):
        if default is not _MISSING and default_factory is not _MISSING:
            raise ValueError("cannot specify both default and default_factory")
        self.default = default
        self.default_factory = default_factory
        self.name = name
        self.type = type
    
    def has_default(self):
        return self.default is not _MISSING or self.default_factory is not _MISSING
    
    def get_default(self):
        if self.default_factory is not _MISSING:
            return self.default_factory()
        if self.default is not _MISSING:
            return self.default
        raise ValueError(f"Field '{self.name}' has no default value")


def field(default=_MISSING, default_factory=_MISSING):
    """Create a field descriptor with optional default or default_factory."""
    return Field(default=default, default_factory=default_factory)


def _get_fields(cls):
    """Extract fields from class annotations and defaults."""
    annotations = {}
    # Collect annotations from MRO (excluding object)
    for base in reversed(cls.__mro__):
        if base is object:
            continue
        if hasattr(base, '__annotations__'):
            annotations.update(base.__annotations__)
    
    fields = []
    for name, type_ in annotations.items():
        # Check if there's a default value set on the class
        class_val = getattr(cls, name, _MISSING)
        
        if isinstance(class_val, Field):
            f = Field(default=class_val.default, default_factory=class_val.default_factory)
        elif class_val is not _MISSING:
            f = Field(default=class_val)
        else:
            f = Field()
        
        f.name = name
        f.type = type_
        fields.append(f)
    
    return fields


def _make_init(fields):
    """Generate __init__ method for the dataclass."""
    def __init__(self, *args, **kwargs):
        # Match positional args to fields
        if len(args) > len(fields):
            raise TypeError(
                f"__init__() takes {len(fields)} positional arguments but {len(args)} were given"
            )
        
        for i, f in enumerate(fields):
            if i < len(args):
                # Positional argument
                if f.name in kwargs:
                    raise TypeError(f"__init__() got multiple values for argument '{f.name}'")
                setattr(self, f.name, args[i])
            elif f.name in kwargs:
                setattr(self, f.name, kwargs.pop(f.name))
            elif f.has_default():
                setattr(self, f.name, f.get_default())
            else:
                raise TypeError(f"__init__() missing required argument: '{f.name}'")
        
        if kwargs:
            extra = next(iter(kwargs))
            raise TypeError(f"__init__() got an unexpected keyword argument '{extra}'")
    
    return __init__


def _make_repr(fields):
    """Generate __repr__ method for the dataclass."""
    def __repr__(self):
        cls_name = type(self).__name__
        parts = []
        for f in fields:
            val = getattr(self, f.name)
            parts.append(f"{f.name}={val!r}")
        return f"{cls_name}({', '.join(parts)})"
    
    return __repr__


def _make_eq(fields):
    """Generate __eq__ method for the dataclass."""
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        for f in fields:
            if getattr(self, f.name) != getattr(other, f.name):
                return False
        return True
    
    return __eq__


def dataclass(cls=None):
    """
    Decorator that generates __init__, __repr__, and __eq__ from class annotations.
    Can be used as @dataclass or @dataclass().
    """
    def wrap(cls):
        fields = _get_fields(cls)
        
        # Remove Field descriptors from class namespace to avoid confusion
        for f in fields:
            if isinstance(getattr(cls, f.name, None), Field):
                try:
                    delattr(cls, f.name)
                except AttributeError:
                    pass
        
        # Only add methods if not already defined by the user
        if '__init__' not in cls.__dict__:
            cls.__init__ = _make_init(fields)
        
        if '__repr__' not in cls.__dict__:
            cls.__repr__ = _make_repr(fields)
        
        if '__eq__' not in cls.__dict__:
            cls.__eq__ = _make_eq(fields)
        
        # Store fields metadata on the class
        cls.__dataclass_fields__ = {f.name: f for f in fields}
        
        return cls
    
    if cls is None:
        # Called as @dataclass()
        return wrap
    
    # Called as @dataclass (without parentheses)
    return wrap(cls)


def asdict(obj):
    """
    Recursively convert a dataclass instance to a dictionary.
    """
    if not hasattr(obj, '__dataclass_fields__'):
        raise TypeError(f"asdict() should be called on dataclass instances, not {type(obj)}")
    
    result = {}
    for name, f in obj.__dataclass_fields__.items():
        val = getattr(obj, name)
        result[name] = _asdict_inner(val)
    
    return result


def _asdict_inner(val):
    """Helper to recursively convert values."""
    if hasattr(val, '__dataclass_fields__'):
        return asdict(val)
    elif isinstance(val, dict):
        return {k: _asdict_inner(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        converted = [_asdict_inner(item) for item in val]
        return type(val)(converted)
    else:
        return val


# --- Functions required by invariants ---

def dataclass_init():
    """Test that dataclass generates __init__ correctly. Returns Point(1,2).x == 1."""
    @dataclass
    class Point:
        x: int
        y: int
    
    p = Point(1, 2)
    return p.x


def dataclass_repr():
    """Test that repr contains class name and field values."""
    @dataclass
    class Point:
        x: int
        y: int
    
    return repr(Point(1, 2))


def dataclass_repr_has_name():
    """Test that repr contains 'Point' and field values."""
    r = dataclass_repr()
    return 'Point' in r and '1' in r and '2' in r


def dataclass_eq():
    """Test equality of dataclass instances."""
    @dataclass
    class Point:
        x: int
        y: int
    
    return Point(1, 2) == Point(1, 2) and Point(1, 2) != Point(3, 4)