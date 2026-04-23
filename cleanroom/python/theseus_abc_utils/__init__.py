"""
theseus_abc_utils — clean-room abstract base class support.
No import of `abc` or any third-party library.
"""


def abstractmethod(func):
    """
    Decorator that marks a method as abstract.

    Sets ``func.__isabstractmethod__ = True`` so that ABCMeta can detect it.
    """
    func.__isabstractmethod__ = True
    return func


class ABCMeta(type):
    """
    Metaclass for abstract base classes.

    Collects all names whose underlying callable has
    ``__isabstractmethod__ == True`` into ``__abstractmethods__``
    (a frozenset).  Python's ``object.__new__`` raises ``TypeError``
    when it finds a non-empty ``__abstractmethods__`` on the class
    being instantiated, so we get the enforcement for free.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Collect abstract method names from this class and all bases.
        abstracts = set()

        # Walk the MRO (skip the class itself — we'll handle namespace directly)
        for base in bases:
            for attr_name in getattr(base, '__abstractmethods__', set()):
                # Only keep it abstract if the subclass hasn't overridden it
                # with a concrete implementation.
                value = namespace.get(attr_name, None)
                if value is None:
                    # Not overridden in this class — still abstract
                    abstracts.add(attr_name)
                else:
                    # Overridden — only abstract if the override is itself abstract
                    if getattr(value, '__isabstractmethod__', False):
                        abstracts.add(attr_name)

        # Also pick up any new abstract methods defined directly in this class.
        for attr_name, value in namespace.items():
            if getattr(value, '__isabstractmethod__', False):
                abstracts.add(attr_name)
            # If a previously-abstract name is overridden with a concrete
            # method, make sure it's removed (already handled above, but
            # handle the case where it was only in namespace).

        cls.__abstractmethods__ = frozenset(abstracts)
        return cls


class ABC(metaclass=ABCMeta):
    """
    Convenience base class for abstract base classes.

    Equivalent to::

        class MyABC(metaclass=ABCMeta):
            ...
    """
    __slots__ = ()


# ---------------------------------------------------------------------------
# Invariant test helpers
# ---------------------------------------------------------------------------

def abc_cannot_instantiate():
    """
    Returns True if instantiating a class with unimplemented abstract methods
    raises TypeError.
    """
    class MyABC(ABC):
        @abstractmethod
        def do_something(self):
            pass

    try:
        MyABC()
        return False  # Should have raised
    except TypeError:
        return True


def abc_concrete_ok():
    """
    Returns True if a concrete subclass that implements all abstract methods
    can be instantiated without error.
    """
    class MyABC(ABC):
        @abstractmethod
        def do_something(self):
            pass

    class Concrete(MyABC):
        def do_something(self):
            return 42

    try:
        obj = Concrete()
        return obj.do_something() == 42
    except TypeError:
        return False


def abc_is_abstract():
    """
    Returns True if the abstract method name is detectable via
    ``__isabstractmethod__`` and via ``__abstractmethods__`` on the class.
    """
    class MyABC(ABC):
        @abstractmethod
        def do_something(self):
            pass

    # The decorator must set __isabstractmethod__
    method_is_marked = getattr(MyABC.do_something, '__isabstractmethod__', False)

    # The metaclass must collect it into __abstractmethods__
    in_set = 'do_something' in getattr(MyABC, '__abstractmethods__', frozenset())

    return bool(method_is_marked) and in_set