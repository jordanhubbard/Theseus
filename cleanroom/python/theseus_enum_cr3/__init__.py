"""
theseus_enum_cr3 - Clean-room extended enum utilities.
Implements StrEnum, IntFlag, and auto() from scratch without importing enum.
"""


class AutoValue:
    """Sentinel object returned by auto() to signal automatic value assignment."""
    pass


def auto():
    """Return an AutoValue sentinel for automatic value assignment."""
    return AutoValue()


class EnumMeta(type):
    """Metaclass for basic Enum functionality."""

    def __new__(mcs, name, bases, namespace):
        # Check if this is a base class definition (Enum, StrEnum, IntFlag themselves)
        # by checking if any base already has _member_map_
        is_base = not any(hasattr(b, '_member_map_') for b in bases)

        if is_base:
            cls = super().__new__(mcs, name, bases, namespace)
            cls._member_map_ = {}
            cls._members_ = []
            return cls

        # Separate member definitions from non-member items
        member_items = []
        new_namespace = {}

        for key, value in namespace.items():
            if key.startswith('_'):
                new_namespace[key] = value
            elif callable(value) and not isinstance(value, AutoValue):
                new_namespace[key] = value
            elif isinstance(value, (classmethod, staticmethod, property)):
                new_namespace[key] = value
            else:
                member_items.append((key, value))

        # Create the class without members
        cls = super().__new__(mcs, name, bases, new_namespace)
        cls._member_map_ = {}
        cls._members_ = []

        # Resolve auto values
        auto_counter = [0]
        # Pre-scan for max non-auto int value
        for key, value in member_items:
            if not isinstance(value, AutoValue) and isinstance(value, int):
                if value > auto_counter[0]:
                    auto_counter[0] = value

        # Reset counter for sequential auto
        auto_counter[0] = 0
        # Re-scan to find starting point based on order
        # auto() increments from last value
        last_value = [0]

        resolved_members = []
        for key, value in member_items:
            if isinstance(value, AutoValue):
                last_value[0] += 1
                resolved_members.append((key, last_value[0]))
            else:
                if isinstance(value, int):
                    last_value[0] = value
                resolved_members.append((key, value))

        # Create member instances
        for member_name, member_value in resolved_members:
            member = cls._create_member_(member_name, member_value)
            cls._member_map_[member_name] = member
            cls._members_.append(member)
            setattr(cls, member_name, member)

        return cls

    def _create_member_(cls, name, value):
        """Create a member instance. Override in subclasses."""
        instance = object.__new__(cls)
        instance._name_ = name
        instance._value_ = value
        return instance

    def __iter__(cls):
        return iter(cls._members_)

    def __contains__(cls, item):
        return item in cls._member_map_.values()

    def __getitem__(cls, name):
        return cls._member_map_[name]

    def __repr__(cls):
        return f"<enum {cls.__name__!r}>"


class Enum(metaclass=EnumMeta):
    """Base Enum class."""

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
        if isinstance(other, Enum):
            return self._value_ == other._value_ and type(self) is type(other)
        return NotImplemented

    def __hash__(self):
        return hash(self._value_)


class StrEnumMeta(EnumMeta):
    """Metaclass for StrEnum."""

    def _create_member_(cls, name, value):
        """Create a string member instance."""
        instance = str.__new__(cls, value)
        instance._name_ = name
        instance._value_ = value
        return instance


class StrEnum(str, metaclass=StrEnumMeta):
    """Enum where members are strings and behave as strings."""

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name_}: {self._value_!r}>"

    def __str__(self):
        return self._value_

    def __eq__(self, other):
        if isinstance(other, str):
            return str.__eq__(self, other)
        return NotImplemented

    def __hash__(self):
        return hash(str(self))

    def __new__(cls, value=''):
        return str.__new__(cls, value)


class IntFlagMeta(EnumMeta):
    """Metaclass for IntFlag."""

    def _create_member_(cls, name, value):
        """Create an integer flag member instance."""
        instance = int.__new__(cls, value)
        instance._name_ = name
        instance._value_ = value
        return instance

    def _create_pseudo_member_(cls, value):
        """Create a pseudo-member for combined flag values."""
        # Check if it's an existing member
        for member in cls._members_:
            if member._value_ == value:
                return member
        instance = int.__new__(cls, value)
        instance._name_ = _flag_name(cls, value)
        instance._value_ = value
        return instance


def _flag_name(cls, value):
    """Generate a name for a combined flag value."""
    if value == 0:
        return '0'
    members = []
    for member in cls._members_:
        if member._value_ != 0 and (value & member._value_) == member._value_:
            members.append(member._name_)
    if members:
        return '|'.join(members)
    return str(value)


class IntFlag(int, metaclass=IntFlagMeta):
    """Enum supporting bitwise operations."""

    def __new__(cls, value=0):
        return int.__new__(cls, value)

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name_}: {self._value_}>"

    def __str__(self):
        return f"{type(self).__name__}.{self._name_}"

    def __or__(self, other):
        if isinstance(other, int):
            result_value = int(self) | int(other)
        else:
            result_value = int(self) | other
        return type(self)._create_pseudo_member_(result_value)

    def __and__(self, other):
        if isinstance(other, int):
            result_value = int(self) & int(other)
        else:
            result_value = int(self) & other
        return type(self)._create_pseudo_member_(result_value)

    def __xor__(self, other):
        if isinstance(other, int):
            result_value = int(self) ^ int(other)
        else:
            result_value = int(self) ^ other
        return type(self)._create_pseudo_member_(result_value)

    def __invert__(self):
        all_bits = 0
        for member in type(self)._members_:
            all_bits |= member._value_
        result_value = all_bits & ~int(self)
        return type(self)._create_pseudo_member_(result_value)

    def __ror__(self, other):
        return self.__or__(other)

    def __rand__(self, other):
        return self.__and__(other)

    def __rxor__(self, other):
        return self.__xor__(other)

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == int(other)
        return NotImplemented

    def __hash__(self):
        return hash(int(self))


# Test functions as specified in invariants

def enum3_strenum():
    """Test StrEnum: Color.RED == 'red' should return True."""
    class Color(StrEnum):
        RED = 'red'
        GREEN = 'green'
        BLUE = 'blue'

    return Color.RED == 'red'


def enum3_intflag():
    """Test IntFlag: (Perm.R | Perm.W).value == 6."""
    class Perm(IntFlag):
        R = 4
        W = 2
        X = 1

    return (Perm.R | Perm.W).value


def enum3_auto():
    """Test auto(): Dir.SOUTH.value == 2."""
    class Dir(Enum):
        NORTH = auto()
        SOUTH = auto()
        EAST = auto()
        WEST = auto()

    return Dir.SOUTH.value


__all__ = ['StrEnum', 'IntFlag', 'auto', 'Enum', 'enum3_strenum', 'enum3_intflag', 'enum3_auto']