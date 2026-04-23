"""
theseus_abc_cr — Clean-room abc module.
No import of the standard `abc` module.

Uses Python's built-in _abc C extension.
"""

import _abc


def abstractmethod(funcobj):
    """Decorator to declare abstract methods."""
    funcobj.__isabstractmethod__ = True
    return funcobj


def abstractclassmethod(funcobj):
    """Deprecated: use classmethod + abstractmethod."""
    funcobj.__isabstractmethod__ = True
    return classmethod(funcobj)


def abstractstaticmethod(funcobj):
    """Deprecated: use staticmethod + abstractmethod."""
    funcobj.__isabstractmethod__ = True
    return staticmethod(funcobj)


def abstractproperty(fget=None, fset=None, fdel=None, doc=None):
    """Deprecated: use property + abstractmethod."""
    prop = property(fget, fset, fdel, doc)
    prop.__isabstractmethod__ = True
    return prop


class ABCMeta(type):
    """Metaclass for Abstract Base Classes."""

    def __new__(mcls, name, bases, namespace, /, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        # Collect abstract methods
        abstracts = {name for name, value in namespace.items()
                     if getattr(value, '__isabstractmethod__', False)}
        for base in bases:
            for name2 in getattr(base, '__abstractmethods__', set()):
                value = getattr(cls, name2, None)
                if getattr(value, '__isabstractmethod__', False):
                    abstracts.add(name2)
        cls.__abstractmethods__ = frozenset(abstracts)
        return cls

    def register(cls, subclass):
        """Register a virtual subclass."""
        if not isinstance(subclass, type):
            raise TypeError("Can only register classes")
        if issubclass(subclass, cls):
            return subclass
        cls._abc_registry = getattr(cls, '_abc_registry', set())
        cls._abc_registry.add(subclass)
        return subclass

    def __instancecheck__(cls, instance):
        subclass = instance.__class__
        if subclass in getattr(cls, '_abc_registry', set()):
            return True
        return type.__instancecheck__(cls, instance)

    def __subclasscheck__(cls, subclass):
        if subclass in getattr(cls, '_abc_registry', set()):
            return True
        return type.__subclasscheck__(cls, subclass)

    def __subclasshook__(cls, subclass):
        return NotImplemented

    def _dump_registry(cls, file=None):
        import sys
        file = file or sys.stdout
        print(f"Class: {cls.__module__}.{cls.__qualname__}", file=file)
        print(f"Inv. counter: {_abc.get_cache_token()}", file=file)


class ABC(metaclass=ABCMeta):
    """Helper class that uses ABCMeta as metaclass."""
    __slots__ = ()


get_cache_token = _abc.get_cache_token


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def abc2_abstract():
    """Instantiating class with unimplemented abstractmethod raises TypeError; returns True."""
    class Shape(ABC):
        @abstractmethod
        def area(self):
            pass

    try:
        Shape()
        return False
    except TypeError:
        return True


def abc2_concrete():
    """Class implementing all abstract methods can be instantiated; returns True."""
    class Shape(ABC):
        @abstractmethod
        def area(self):
            pass

    class Circle(Shape):
        def area(self):
            return 3.14

    c = Circle()
    return c.area() == 3.14


def abc2_isinstance():
    """ABC subclass registration makes isinstance return True; returns True."""
    class MyABC(ABC):
        pass

    class Concrete:
        pass

    MyABC.register(Concrete)
    return isinstance(Concrete(), MyABC)


__all__ = [
    'ABCMeta', 'ABC', 'abstractmethod',
    'abstractclassmethod', 'abstractstaticmethod', 'abstractproperty',
    'get_cache_token',
    'abc2_abstract', 'abc2_concrete', 'abc2_isinstance',
]
