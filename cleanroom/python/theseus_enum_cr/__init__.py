"""
theseus_enum_cr — Clean-room enum module.
No import of the standard `enum` module.
"""


class _EnumDict(dict):
    def __init__(self):
        super().__init__()
        self._member_names = []
        self._last_value = 0

    def __setitem__(self, key, value):
        if key.startswith('_') or callable(value) or isinstance(value, (classmethod, staticmethod, property)):
            super().__setitem__(key, value)
            return
        if not isinstance(value, auto):
            self._last_value = value
        else:
            self._last_value += 1
            value = self._last_value
        self._member_names.append(key)
        super().__setitem__(key, value)


class auto:
    """Automatic value for enum members."""
    pass


class EnumMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return _EnumDict()

    def __new__(mcs, name, bases, namespace):
        if not bases:
            return super().__new__(mcs, name, bases, dict(namespace))

        member_names = namespace._member_names
        members = {k: namespace[k] for k in member_names}

        cls_dict = {k: v for k, v in namespace.items() if k not in member_names}
        cls_dict['_member_names_'] = member_names
        cls_dict['_value2member_map_'] = {}
        cls_dict['_member_map_'] = {}

        cls = super().__new__(mcs, name, bases, cls_dict)

        for m_name, m_value in members.items():
            if isinstance(m_value, auto):
                raise ValueError("auto() not resolved")
            member = object.__new__(cls)
            member._name_ = m_name
            member._value_ = m_value
            cls._member_map_[m_name] = member
            cls._value2member_map_[m_value] = member
            setattr(cls, m_name, member)

        return cls

    def __call__(cls, value):
        try:
            return cls._value2member_map_[value]
        except KeyError:
            raise ValueError(f"{value!r} is not a valid {cls.__name__}")

    def __iter__(cls):
        return (cls._member_map_[name] for name in cls._member_names_)

    def __len__(cls):
        return len(cls._member_names_)

    def __repr__(cls):
        return f"<enum {cls.__name__!r}>"

    def __getitem__(cls, name):
        return cls._member_map_[name]


class Enum(metaclass=EnumMeta):
    """Base class for enumerations."""

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_

    def __repr__(self):
        return f'<{self.__class__.__name__}.{self._name_}: {self._value_!r}>'

    def __str__(self):
        return f'{self.__class__.__name__}.{self._name_}'

    def __hash__(self):
        return hash(self._name_)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._value_ == other._value_
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self._value_ < other._value_
        return NotImplemented


class IntEnum(int, Enum):
    """Enum with integer values."""

    def __new__(cls, value):
        # This gets called during member creation
        return int.__new__(cls, value)


class Flag(Enum):
    """Enum supporting bitwise operations."""

    def __or__(self, other):
        if isinstance(other, self.__class__):
            return self._value_ | other._value_
        return NotImplemented

    def __and__(self, other):
        if isinstance(other, self.__class__):
            return self._value_ & other._value_
        return NotImplemented

    def __xor__(self, other):
        if isinstance(other, self.__class__):
            return self._value_ ^ other._value_
        return NotImplemented

    def __invert__(self):
        return ~self._value_


class IntFlag(int, Flag):
    """Integer Flag enum."""
    pass


def unique(enumeration):
    """Class decorator for enumerations with no duplicate values."""
    seen_values = {}
    for member in enumeration:
        if member.value in seen_values:
            raise ValueError(
                f"duplicate values found in {enumeration!r}: "
                f"{member.name!r} -> {seen_values[member.value]!r}"
            )
        seen_values[member.value] = member.name
    return enumeration


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def enum2_name_value():
    """Color.RED.name == 'RED' and Color.RED.value == 1; returns True."""
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    return Color.RED.name == 'RED' and Color.RED.value == 1


def enum2_lookup():
    """Color(1) returns Color.RED; returns True."""
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    return Color(1) is Color.RED


def enum2_iteration():
    """list(Color) returns all 3 members; returns 3."""
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    return len(list(Color))


__all__ = [
    'Enum', 'IntEnum', 'Flag', 'IntFlag', 'EnumMeta',
    'auto', 'unique',
    'enum2_name_value', 'enum2_lookup', 'enum2_iteration',
]
