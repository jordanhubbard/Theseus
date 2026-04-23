"""
theseus_enum_utils - Clean-room Enum implementation.
Do NOT import the standard `enum` module.
"""


class EnumMeta(type):
    """Metaclass for Enum that handles member creation and lookup."""

    def __new__(mcs, name, bases, namespace):
        # Collect members: items that don't start with '_' and aren't functions/descriptors
        members = {}
        member_names = []

        # Find existing members from base Enum classes
        existing_members = {}
        for base in bases:
            if hasattr(base, '_member_map_'):
                existing_members.update(base._member_map_)

        # Build the new class namespace without the member values
        # (we'll replace them with member instances after class creation)
        clean_namespace = {}
        raw_members = {}

        for key, value in namespace.items():
            if key.startswith('_') or callable(value) or isinstance(value, (classmethod, staticmethod, property)):
                clean_namespace[key] = value
            else:
                raw_members[key] = value
                member_names.append(key)

        # Create the class
        cls = super().__new__(mcs, name, bases, clean_namespace)

        # Initialize member storage
        cls._member_map_ = {}
        cls._value_map_ = {}
        cls._member_names_ = []

        # Copy existing members from bases
        for mname, member in existing_members.items():
            cls._member_map_[mname] = member
            cls._value_map_[member.value] = member

        # Create member instances
        for mname in member_names:
            value = raw_members[mname]
            # Create a new instance of the class for this member
            member = cls._create_member_(mname, value)
            cls._member_map_[mname] = member
            cls._value_map_[value] = member
            cls._member_names_.append(mname)
            setattr(cls, mname, member)

        return cls

    def _create_member_(cls, name, value):
        """Create a single enum member."""
        # We need to create an instance without triggering __new__ member logic
        member = object.__new__(cls)
        member._name_ = name
        member._value_ = value
        return member

    def __getitem__(cls, name):
        """Allow Color['RED'] lookup."""
        try:
            return cls._member_map_[name]
        except KeyError:
            raise KeyError(name)

    def __call__(cls, value):
        """Allow Color(1) lookup by value."""
        try:
            return cls._value_map_[value]
        except KeyError:
            raise ValueError(f"{value!r} is not a valid {cls.__name__}")

    def __iter__(cls):
        """Iterate over enum members in definition order."""
        for name in cls._member_names_:
            yield cls._member_map_[name]

    def __len__(cls):
        return len(cls._member_names_)

    def __repr__(cls):
        return f"<enum {cls.__name__!r}>"

    def __contains__(cls, member):
        if isinstance(member, cls):
            return member._name_ in cls._member_map_
        return False


class Enum(metaclass=EnumMeta):
    """Base class for enumerations."""

    def __new__(cls, value=None):
        # When called as Color(1), the metaclass __call__ handles it.
        # This __new__ is for internal member creation only.
        return object.__new__(cls)

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name_}: {self._value_!r}>"

    def __str__(self):
        return f"{type(self).__name__}.{self._name_}"

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return hash(self._name_)

    def __reduce_ex__(self, proto):
        return type(self), (self._value_,)


class IntEnumMeta(EnumMeta):
    """Metaclass for IntEnum."""

    def _create_member_(cls, name, value):
        """Create an IntEnum member that also behaves as an int."""
        member = int.__new__(cls, value)
        member._name_ = name
        member._value_ = value
        return member

    def __call__(cls, value):
        """Allow IntColor(1) lookup by value."""
        try:
            return cls._value_map_[value]
        except KeyError:
            raise ValueError(f"{value!r} is not a valid {cls.__name__}")


class IntEnum(int, Enum, metaclass=IntEnumMeta):
    """Enum where members are also integers."""

    def __new__(cls, value=None):
        if value is None:
            return int.__new__(cls)
        return int.__new__(cls, value)

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == int(other)
        return self is other

    def __hash__(self):
        return int.__hash__(self)


# ---------------------------------------------------------------------------
# Invariant helper functions
# ---------------------------------------------------------------------------

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


def enum_member_value():
    """Return the value of Color.RED (should be 1)."""
    return Color.RED.value


def enum_member_by_name():
    """Return True if Color['RED'] == Color.RED."""
    return Color['RED'] == Color.RED


def enum_member_by_value():
    """Return True if Color(1) == Color.RED."""
    return Color(1) == Color.RED


__all__ = [
    'Enum',
    'IntEnum',
    'enum_member_value',
    'enum_member_by_name',
    'enum_member_by_value',
]