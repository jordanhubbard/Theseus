"""Clean-room implementation of Python's abc module.

Provides ABCMeta metaclass, abstractmethod decorator, and ABC convenience
base class. No imports from the standard abc module.
"""


def abstractmethod(funcobj):
    """Mark a method as abstract.

    Classes whose metaclass is ABCMeta cannot be instantiated unless all
    of their abstract methods are overridden.
    """
    funcobj.__isabstractmethod__ = True
    return funcobj


class ABCMeta(type):
    """Metaclass for defining Abstract Base Classes.

    Use this metaclass to create an ABC. An ABC can be subclassed
    directly, and then acts as a mix-in class. Concrete subclasses must
    override every abstractmethod or instantiation will raise TypeError.
    """

    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        # Collect abstract methods declared directly on this class.
        abstracts = set()
        for key, value in namespace.items():
            if getattr(value, "__isabstractmethod__", False):
                abstracts.add(key)

        # Inherit unfulfilled abstracts from bases.
        for base in bases:
            for inherited in getattr(base, "__abstractmethods__", set()):
                value = getattr(cls, inherited, None)
                if getattr(value, "__isabstractmethod__", False):
                    abstracts.add(inherited)

        cls.__abstractmethods__ = frozenset(abstracts)
        # Per-class virtual subclass registry.
        cls._abc_registry = set()
        return cls

    def __call__(cls, *args, **kwargs):
        # Block instantiation of any class that still has abstract methods.
        abstracts = getattr(cls, "__abstractmethods__", frozenset())
        if abstracts:
            joined = ", ".join(sorted(abstracts))
            raise TypeError(
                "Can't instantiate abstract class "
                + cls.__name__
                + " with abstract method"
                + ("s " if len(abstracts) != 1 else " ")
                + joined
            )
        return super().__call__(*args, **kwargs)

    def register(cls, subclass):
        """Register a virtual subclass of an ABC."""
        if not isinstance(subclass, type):
            raise TypeError("Can only register classes")
        if issubclass(cls, subclass):
            raise RuntimeError(
                "Refusing to create an inheritance cycle"
            )
        cls._abc_registry.add(subclass)
        return subclass

    def __instancecheck__(cls, instance):
        # Real subclass relationship first.
        if type.__instancecheck__(cls, instance):
            return True
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        if not isinstance(subclass, type):
            return False
        # Real subclass relationship.
        if type.__subclasscheck__(cls, subclass):
            return True
        # Direct virtual registration.
        if subclass in getattr(cls, "_abc_registry", set()):
            return True
        # Transitive via registered virtual subclasses.
        for registered in getattr(cls, "_abc_registry", set()):
            if isinstance(registered, type) and issubclass(subclass, registered):
                return True
        # Walk the MRO of subclass to see if any of its real bases are
        # registered virtual subclasses of cls.
        for base in subclass.__mro__[1:]:
            if base in getattr(cls, "_abc_registry", set()):
                return True
        return False


class ABC(metaclass=ABCMeta):
    """Helper class that provides a standard way to create an ABC using
    inheritance instead of specifying ``metaclass=ABCMeta`` directly.
    """
    __slots__ = ()


# ---------------------------------------------------------------------------
# Invariant verification functions.
# ---------------------------------------------------------------------------


def abc2_abstract():
    """A class with an abstract method cannot be instantiated."""

    class Shape(ABC):
        @abstractmethod
        def area(self):
            ...

    try:
        Shape()
    except TypeError:
        # Verify the abstract methods are tracked.
        return "area" in Shape.__abstractmethods__
    return False


def abc2_concrete():
    """A concrete subclass that overrides all abstract methods is usable."""

    class Shape(ABC):
        @abstractmethod
        def area(self):
            ...

    class Square(Shape):
        def __init__(self, side):
            self.side = side

        def area(self):
            return self.side * self.side

    sq = Square(4)
    return (
        sq.area() == 16
        and Square.__abstractmethods__ == frozenset()
    )


def abc2_isinstance():
    """isinstance / issubclass work for both real and virtual subclasses."""

    class Animal(ABC):
        @abstractmethod
        def speak(self):
            ...

    class Dog(Animal):
        def speak(self):
            return "woof"

    d = Dog()
    real_ok = (
        isinstance(d, Dog)
        and isinstance(d, Animal)
        and isinstance(d, ABC)
        and issubclass(Dog, Animal)
    )

    # Virtual subclass registration.
    class Robot:
        def speak(self):
            return "beep"

    Animal.register(Robot)
    r = Robot()
    virtual_ok = (
        isinstance(r, Animal)
        and issubclass(Robot, Animal)
        and not isinstance(r, Dog)
    )

    return real_ok and virtual_ok


__all__ = [
    "ABC",
    "ABCMeta",
    "abstractmethod",
    "abc2_abstract",
    "abc2_concrete",
    "abc2_isinstance",
]