"""
theseus_dataclasses_cr2 - Clean-room extended dataclass utilities.

Implements asdict, astuple, and replace without importing the dataclasses module.
"""


def _is_dataclass_instance(obj):
    """Check if obj is an instance of a dataclass (not the class itself)."""
    cls = type(obj)
    return hasattr(cls, '__dataclass_fields__') and isinstance(obj, cls)


def _get_fields(obj):
    """
    Return an ordered list of (field_name, field_value) pairs for a dataclass instance.
    Uses __dataclass_fields__ to get field names in definition order.
    """
    cls = type(obj)
    fields_dict = cls.__dataclass_fields__
    result = []
    for name in fields_dict:
        value = getattr(obj, name)
        result.append((name, value))
    return result


def _asdict_inner(obj):
    """Recursively convert a value to a dict-friendly form."""
    if _is_dataclass_instance(obj):
        return {name: _asdict_inner(value) for name, value in _get_fields(obj)}
    elif isinstance(obj, dict):
        return {_asdict_inner(k): _asdict_inner(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        converted = [_asdict_inner(item) for item in obj]
        return type(obj)(converted)
    else:
        return obj


def asdict(instance):
    """
    Recursively convert a dataclass instance to a dictionary.
    
    Each dataclass field becomes a key in the resulting dict.
    Nested dataclasses, lists, tuples, and dicts are recursively converted.
    
    Example:
        asdict(Point(x=1, y=2)) == {'x': 1, 'y': 2}
    """
    if not _is_dataclass_instance(instance):
        raise TypeError(f"asdict() should be called on dataclass instances, not {type(instance)!r}")
    return _asdict_inner(instance)


def _astuple_inner(obj):
    """Recursively convert a value to a list-friendly form."""
    if _is_dataclass_instance(obj):
        return [_astuple_inner(value) for _, value in _get_fields(obj)]
    elif isinstance(obj, dict):
        return {_astuple_inner(k): _astuple_inner(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        converted = [_astuple_inner(item) for item in obj]
        return type(obj)(converted)
    else:
        return obj


def astuple(instance):
    """
    Recursively convert a dataclass instance to a list.
    
    Each dataclass field becomes an element in the resulting list.
    Nested dataclasses, lists, tuples, and dicts are recursively converted.
    
    Example:
        astuple(Point(x=1, y=2)) == [1, 2]
    """
    if not _is_dataclass_instance(instance):
        raise TypeError(f"astuple() should be called on dataclass instances, not {type(instance)!r}")
    return _astuple_inner(instance)


def replace(instance, **changes):
    """
    Create a new dataclass instance with some fields replaced.
    
    Returns a new instance of the same dataclass type with the specified
    fields replaced by the provided values. Fields not mentioned in
    `changes` retain their original values.
    
    Example:
        replace(Point(1, 2), y=99).y == 99
    """
    if not _is_dataclass_instance(instance):
        raise TypeError(f"replace() should be called on dataclass instances, not {type(instance)!r}")
    
    cls = type(instance)
    fields_dict = cls.__dataclass_fields__
    
    # Validate that all change keys are valid field names
    for key in changes:
        if key not in fields_dict:
            raise TypeError(f"replace() got an unexpected keyword argument '{key}'")
    
    # Build kwargs for the new instance: current values overridden by changes
    kwargs = {}
    for name in fields_dict:
        if name in changes:
            kwargs[name] = changes[name]
        else:
            kwargs[name] = getattr(instance, name)
    
    return cls(**kwargs)


# --- Test helpers referenced in the invariants ---

def dataclasses2_asdict():
    """
    Demonstration: asdict(Point(x=1, y=2)) == {'x': 1, 'y': 2}
    Returns the result for testing.
    """
    Point = _make_simple_dataclass('Point', ['x', 'y'])
    instance = Point(x=1, y=2)
    return asdict(instance)


def dataclasses2_astuple():
    """
    Demonstration: astuple(Point(x=1, y=2)) == [1, 2]
    Returns the result for testing.
    """
    Point = _make_simple_dataclass('Point', ['x', 'y'])
    instance = Point(x=1, y=2)
    return astuple(instance)


def dataclasses2_replace():
    """
    Demonstration: replace(Point(1, 2), y=99).y == 99
    Returns the .y value for testing.
    """
    Point = _make_simple_dataclass('Point', ['x', 'y'])
    instance = Point(x=1, y=2)
    new_instance = replace(instance, y=99)
    return new_instance.y


def _make_simple_dataclass(name, field_names):
    """
    Create a minimal dataclass-compatible class with the given field names.
    This is used internally for demonstration/testing purposes.
    The resulting class has __dataclass_fields__ and an __init__ that accepts
    keyword arguments for each field.
    """
    class _Field:
        def __init__(self, fname):
            self.name = fname
            self.default = _MISSING
            self.default_factory = _MISSING
    
    fields = {fname: _Field(fname) for fname in field_names}
    
    def __init__(self, **kwargs):
        for fname in field_names:
            if fname in kwargs:
                object.__setattr__(self, fname, kwargs[fname])
            else:
                raise TypeError(f"__init__() missing required argument: '{fname}'")
    
    def __repr__(self):
        parts = ', '.join(f"{fname}={getattr(self, fname)!r}" for fname in field_names)
        return f"{name}({parts})"
    
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return all(getattr(self, f) == getattr(other, f) for f in field_names)
    
    cls = type(name, (), {
        '__init__': __init__,
        '__repr__': __repr__,
        '__eq__': __eq__,
        '__dataclass_fields__': fields,
    })
    return cls


class _MISSING_TYPE:
    """Sentinel for missing default values."""
    def __repr__(self):
        return 'MISSING'

_MISSING = _MISSING_TYPE()


__all__ = ['asdict', 'astuple', 'replace', 'dataclasses2_asdict', 'dataclasses2_astuple', 'dataclasses2_replace']