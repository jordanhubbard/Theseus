"""
theseus_typing_utils - Clean-room typing utilities for runtime type checking.
No imports from the `typing` module or any third-party libraries.
"""


def typed_namedtuple(name, fields):
    """
    Create a namedtuple-like class with named fields.
    
    Parameters
    ----------
    name : str
        The name of the new class.
    fields : list of str
        The field names for the new class.
    
    Returns
    -------
    A new class with the given name and fields accessible as attributes.
    """
    fields = list(fields)
    
    # Validate field names
    for field in fields:
        if not isinstance(field, str):
            raise TypeError(f"Field names must be strings, got {type(field)}")
        if not field.isidentifier():
            raise ValueError(f"Field name {field!r} is not a valid identifier")
    
    num_fields = len(fields)
    fields_tuple = tuple(fields)
    
    def __init__(self, *args, **kwargs):
        if len(args) > num_fields:
            raise TypeError(
                f"{name}() takes {num_fields} positional arguments but {len(args)} were given"
            )
        
        # Start with positional args
        values = list(args)
        
        # Fill in keyword args
        for i in range(len(args), num_fields):
            field = fields_tuple[i]
            if field in kwargs:
                values.append(kwargs.pop(field))
            else:
                raise TypeError(f"{name}() missing required argument: '{field}'")
        
        if kwargs:
            extra = next(iter(kwargs))
            raise TypeError(f"{name}() got an unexpected keyword argument '{extra}'")
        
        for field, value in zip(fields_tuple, values):
            object.__setattr__(self, field, value)
    
    def __setattr__(self, key, value):
        raise AttributeError("can't set attribute")
    
    def __repr__(self):
        parts = ", ".join(f"{f}={getattr(self, f)!r}" for f in fields_tuple)
        return f"{name}({parts})"
    
    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        return all(getattr(self, f) == getattr(other, f) for f in fields_tuple)
    
    def __hash__(self):
        return hash(tuple(getattr(self, f) for f in fields_tuple))
    
    def __iter__(self):
        for f in fields_tuple:
            yield getattr(self, f)
    
    def __len__(self):
        return num_fields
    
    def __getitem__(self, index):
        return tuple(getattr(self, f) for f in fields_tuple)[index]
    
    def _asdict(self):
        return {f: getattr(self, f) for f in fields_tuple}
    
    def _replace(self, **kwargs):
        current = {f: getattr(self, f) for f in fields_tuple}
        current.update(kwargs)
        return type(self)(**current)
    
    # Build the class namespace
    namespace = {
        '__init__': __init__,
        '__setattr__': __setattr__,
        '__repr__': __repr__,
        '__eq__': __eq__,
        '__hash__': __hash__,
        '__iter__': __iter__,
        '__len__': __len__,
        '__getitem__': __getitem__,
        '_asdict': _asdict,
        '_replace': _replace,
        '_fields': fields_tuple,
        '__slots__': fields_tuple,
    }
    
    # Create the class dynamically
    cls = type(name, (), namespace)
    return cls


def get_annotations(cls):
    """
    Get the annotations dictionary for a class, similar to typing.get_type_hints
    but without resolving forward references.
    
    Parameters
    ----------
    cls : type
        The class to introspect.
    
    Returns
    -------
    dict
        A dictionary mapping attribute names to their annotated types.
    """
    if not isinstance(cls, type):
        raise TypeError(f"Expected a class, got {type(cls)}")
    
    # Get annotations directly from the class's __dict__ to avoid inheriting
    # parent class annotations
    annotations = {}
    
    # Walk the MRO in reverse to get inherited annotations first,
    # then override with the class's own annotations
    for base in reversed(cls.__mro__):
        if base is object:
            continue
        base_annotations = getattr(base, '__annotations__', {}) or {}
        annotations.update(base_annotations)
    
    return annotations


def typing_get_annotations():
    class _C:
        x: int
        y: str
    return bool(get_annotations(_C))


def typing_namedtuple_fields():
    Point = typed_namedtuple('Point', ['x', 'y'])
    return list(Point._fields)


def typing_namedtuple_x():
    Point = typed_namedtuple('Point', ['x', 'y'])
    p = Point(1, 2)
    return p.x


def is_optional(tp):
    """
    Returns True if tp is Optional[X] (i.e., Union[X, None]).
    
    Since we cannot import typing, we check the internal structure
    of the type hint object.
    
    Parameters
    ----------
    tp : any
        The type hint to check.
    
    Returns
    -------
    bool
    """
    # Optional[X] is represented as Union[X, None]
    # In Python's typing module internals, Union types have __origin__ == Union
    # and __args__ containing the types
    origin = getattr(tp, '__origin__', None)
    if origin is None:
        return False
    
    # Check if origin is Union - we need to check without importing typing
    # The string representation of Union's origin
    origin_name = getattr(origin, '__name__', None) or str(origin)
    
    # In Python 3.7+, Union.__origin__ is typing.Union
    # We check by looking at the string representation
    if 'Union' not in str(origin) and origin_name != 'Union':
        return False
    
    args = getattr(tp, '__args__', None)
    if args is None:
        return False
    
    # Optional[X] has exactly 2 args, one of which is NoneType
    return type(None) in args


__all__ = [
    'typed_namedtuple',
    'get_annotations',
    'typing_get_annotations',
    'typing_namedtuple_fields',
    'typing_namedtuple_x',
    'is_optional',
]