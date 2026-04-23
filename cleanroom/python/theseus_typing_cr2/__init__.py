# theseus_typing_cr2 - Clean-room extended typing utilities
# No import of 'typing' or any third-party library allowed.


class TypeVar:
    """A type variable for use in generic type annotations."""
    
    def __init__(self, name, *constraints, bound=None):
        self.__name__ = name
        self.name = name
        self.__constraints__ = constraints
        self.__bound__ = bound
    
    def __repr__(self):
        return f"~{self.name}"


class _GenericMeta(type):
    """Metaclass for Generic to support Generic[T] syntax."""
    
    def __getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params,)
        # Return a _GenericAlias representing the parameterized generic
        return _GenericAlias(cls, params)


class Generic(metaclass=_GenericMeta):
    """Base class for generic types."""
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)


class _GenericAlias:
    """Represents a parameterized generic type like Generic[T]."""
    
    def __init__(self, origin, args):
        self.__origin__ = origin
        self.__args__ = args
    
    def __repr__(self):
        args_repr = ", ".join(repr(a) for a in self.__args__)
        return f"{self.__origin__.__name__}[{args_repr}]"


class _ProtocolMeta(_GenericMeta):
    """Metaclass for Protocol."""
    
    def __instancecheck__(cls, instance):
        # Basic structural check: verify instance has all protocol methods/attrs
        for attr in cls.__protocol_attrs__:
            if not hasattr(instance, attr):
                return False
        return True


class Protocol(metaclass=_ProtocolMeta):
    """Base class for structural subtyping (runtime_checkable)."""
    
    __protocol_attrs__ = []
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Collect protocol attributes (non-dunder methods defined in the class)
        attrs = []
        for name, value in cls.__dict__.items():
            if not name.startswith('__') and callable(value):
                attrs.append(name)
        cls.__protocol_attrs__ = attrs


class _LiteralMeta(type):
    """Metaclass for Literal to support Literal[...] syntax."""
    
    def __getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params,)
        instance = cls.__new__(cls)
        instance.__args__ = params
        return instance


class Literal(metaclass=_LiteralMeta):
    """Type that accepts specific literal values."""
    
    def __init__(self):
        pass
    
    def __repr__(self):
        args_repr = ", ".join(repr(a) for a in self.__args__)
        return f"Literal[{args_repr}]"


class _FinalMeta(type):
    """Metaclass for Final."""
    
    def __getitem__(cls, param):
        return _FinalAlias(param)
    
    def __call__(cls, func_or_class=None):
        if func_or_class is not None:
            # Used as a decorator
            func_or_class.__final__ = True
            return func_or_class
        return super().__call__()


class _FinalAlias:
    """Represents Final[T] annotation."""
    
    def __init__(self, arg):
        self.__arg__ = arg
    
    def __repr__(self):
        return f"Final[{self.__arg__!r}]"


class Final(metaclass=_FinalMeta):
    """Decorator/annotation to mark as final (no override)."""
    pass


# ── Invariant test functions ──────────────────────────────────────────────────

def typing2_typevar_name():
    """TypeVar('T').name == 'T'"""
    return TypeVar('T').name


def typing2_typevar_constrained():
    """TypeVar('AnyStr', str, bytes).__constraints__ == (str, bytes)"""
    tv = TypeVar('AnyStr', str, bytes)
    return tv.__constraints__ == (str, bytes)


def typing2_literal_args():
    """Literal[1, 2, 3].__args__ == (1, 2, 3)"""
    lit = Literal[1, 2, 3]
    return lit.__args__ == (1, 2, 3)