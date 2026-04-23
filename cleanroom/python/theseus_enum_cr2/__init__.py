"""
theseus_enum_cr2 - Clean-room implementation of extended enum utilities.
Do NOT import enum or any third-party library.
"""

# ─────────────────────────────────────────────────────────────────────────────
# auto() sentinel
# ─────────────────────────────────────────────────────────────────────────────

class auto:
    """Sentinel for automatic value assignment in enum definitions."""
    _counter = 0

    def __init__(self):
        # The actual value is assigned by the metaclass
        self._assigned_value = None

    def __repr__(self):
        return f"auto()"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: resolve auto() values in a namespace dict
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_auto(members):
    """
    Given an ordered list of (name, value) pairs, replace auto() instances
    with sequential integers starting at 1.
    Returns a list of (name, resolved_value).
    """
    counter = 1
    resolved = []
    for name, value in members:
        if isinstance(value, auto):
            resolved.append((name, counter))
            counter += 1
        else:
            # If it's an int, advance counter past it
            if isinstance(value, int):
                counter = value + 1
            resolved.append((name, value))
    return resolved


# ─────────────────────────────────────────────────────────────────────────────
# Enum namespace collector (preserves insertion order)
# ─────────────────────────────────────────────────────────────────────────────

class _EnumNamespace(dict):
    """A dict subclass that records member definitions in order."""

    def __init__(self):
        super().__init__()
        self._member_names = []  # ordered list of (name, value)

    def __setitem__(self, key, value):
        # Skip dunder and private names from member tracking
        if not key.startswith('_') and not callable(value):
            self._member_names.append((key, value))
        elif not key.startswith('_') and callable(value) and isinstance(value, auto):
            self._member_names.append((key, value))
        super().__setitem__(key, value)


# ─────────────────────────────────────────────────────────────────────────────
# Base EnumMember class
# ─────────────────────────────────────────────────────────────────────────────

class EnumMember:
    """Represents a single enum member."""

    def __init__(self, name, value, enum_class):
        self._name = name
        self._value = value
        self._enum_class = enum_class

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return f"<{self._enum_class.__name__}.{self._name}: {self._value!r}>"

    def __str__(self):
        return f"{self._enum_class.__name__}.{self._name}"

    def __eq__(self, other):
        if isinstance(other, EnumMember):
            return self._value == other._value and self._enum_class is other._enum_class
        return NotImplemented

    def __hash__(self):
        return hash((self._enum_class, self._name, self._value))


# ─────────────────────────────────────────────────────────────────────────────
# IntEnumMember: also behaves as an int
# ─────────────────────────────────────────────────────────────────────────────

class IntEnumMember(int):
    """An enum member that is also an int."""

    # These will be set after creation
    _name = None
    _value = None
    _enum_class = None

    def __new__(cls, value):
        obj = int.__new__(cls, value)
        obj._value = value
        return obj

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return f"<{self._enum_class.__name__}.{self._name}: {self._value!r}>"

    def __str__(self):
        return f"{self._enum_class.__name__}.{self._name}"

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == int(other)
        return NotImplemented

    def __hash__(self):
        return int.__hash__(self)


# ─────────────────────────────────────────────────────────────────────────────
# FlagMember: supports bitwise operations
# ─────────────────────────────────────────────────────────────────────────────

class FlagMember:
    """An enum member that supports bitwise operations."""

    def __init__(self, name, value, enum_class):
        self._name = name
        self._value = value
        self._enum_class = enum_class

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __or__(self, other):
        if isinstance(other, FlagMember) and other._enum_class is self._enum_class:
            combined_value = self._value | other._value
            # Create a combined pseudo-member
            result = FlagMember(_combined_name(self, other), combined_value, self._enum_class)
            return result
        return NotImplemented

    def __and__(self, other):
        if isinstance(other, FlagMember) and other._enum_class is self._enum_class:
            combined_value = self._value & other._value
            result = FlagMember(_combined_name(self, other, op='&'), combined_value, self._enum_class)
            return result
        return NotImplemented

    def __xor__(self, other):
        if isinstance(other, FlagMember) and other._enum_class is self._enum_class:
            combined_value = self._value ^ other._value
            result = FlagMember(_combined_name(self, other, op='^'), combined_value, self._enum_class)
            return result
        return NotImplemented

    def __invert__(self):
        result = FlagMember(f"~{self._name}", ~self._value, self._enum_class)
        return result

    def __contains__(self, other):
        if isinstance(other, FlagMember):
            return (self._value & other._value) == other._value
        return NotImplemented

    def __bool__(self):
        return bool(self._value)

    def __int__(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, FlagMember):
            return self._value == other._value and self._enum_class is other._enum_class
        if isinstance(other, int):
            return self._value == other
        return NotImplemented

    def __hash__(self):
        return hash((self._enum_class, self._value))

    def __repr__(self):
        return f"<{self._enum_class.__name__}.{self._name}: {self._value!r}>"

    def __str__(self):
        return f"{self._enum_class.__name__}.{self._name}"


def _combined_name(a, b, op='|'):
    return f"{a._name}{op}{b._name}"


# ─────────────────────────────────────────────────────────────────────────────
# IntFlagMember: int + flag
# ─────────────────────────────────────────────────────────────────────────────

class IntFlagMember(int):
    """An enum member that is both an int and supports bitwise operations."""

    _name = None
    _value = None
    _enum_class = None

    def __new__(cls, value):
        obj = int.__new__(cls, value)
        obj._value = value
        return obj

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __or__(self, other):
        if isinstance(other, IntFlagMember) and other._enum_class is self._enum_class:
            combined_value = int(self) | int(other)
            result = IntFlagMember.__new__(IntFlagMember, combined_value)
            result._name = _combined_name(self, other)
            result._value = combined_value
            result._enum_class = self._enum_class
            return result
        return NotImplemented

    def __and__(self, other):
        if isinstance(other, IntFlagMember) and other._enum_class is self._enum_class:
            combined_value = int(self) & int(other)
            result = IntFlagMember.__new__(IntFlagMember, combined_value)
            result._name = _combined_name(self, other, '&')
            result._value = combined_value
            result._enum_class = self._enum_class
            return result
        return NotImplemented

    def __xor__(self, other):
        if isinstance(other, IntFlagMember) and other._enum_class is self._enum_class:
            combined_value = int(self) ^ int(other)
            result = IntFlagMember.__new__(IntFlagMember, combined_value)
            result._name = _combined_name(self, other, '^')
            result._value = combined_value
            result._enum_class = self._enum_class
            return result
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == int(other)
        return NotImplemented

    def __hash__(self):
        return int.__hash__(self)

    def __repr__(self):
        return f"<{self._enum_class.__name__}.{self._name}: {self._value!r}>"

    def __str__(self):
        return f"{self._enum_class.__name__}.{self._name}"


# ─────────────────────────────────────────────────────────────────────────────
# Metaclass for IntEnum
# ─────────────────────────────────────────────────────────────────────────────

class _IntEnumMeta(type):

    @classmethod
    def __prepare__(mcs, name, bases):
        return _EnumNamespace()

    def __new__(mcs, name, bases, namespace):
        # Collect raw member definitions
        raw_members = list(namespace._member_names)

        # Resolve auto() values
        resolved = _resolve_auto(raw_members)

        # Build the class dict (clean)
        cls_dict = {}
        for key, val in namespace.items():
            if key.startswith('_') or key in [m[0] for m in raw_members]:
                if key.startswith('_'):
                    cls_dict[key] = val
            # methods
            elif callable(val) and not isinstance(val, auto):
                cls_dict[key] = val

        cls = super().__new__(mcs, name, bases, cls_dict)

        # Create member instances
        cls._members_ = {}
        for mname, mvalue in resolved:
            member = IntEnumMember.__new__(IntEnumMember, mvalue)
            member._name = mname
            member._value = mvalue
            member._enum_class = cls
            cls._members_[mname] = member
            setattr(cls, mname, member)

        return cls

    def __iter__(cls):
        return iter(cls._members_.values())

    def __getitem__(cls, name):
        return cls._members_[name]

    def __call__(cls, value):
        for member in cls._members_.values():
            if int(member) == value:
                return member
        raise ValueError(f"{value!r} is not a valid {cls.__name__}")

    def __repr__(cls):
        return f"<IntEnum '{cls.__name__}'>"


# ─────────────────────────────────────────────────────────────────────────────
# Metaclass for Flag
# ─────────────────────────────────────────────────────────────────────────────

class _FlagMeta(type):

    @classmethod
    def __prepare__(mcs, name, bases):
        return _EnumNamespace()

    def __new__(mcs, name, bases, namespace):
        raw_members = list(namespace._member_names)
        resolved = _resolve_auto(raw_members)

        cls_dict = {}
        for key, val in namespace.items():
            if key.startswith('_'):
                cls_dict[key] = val
            elif callable(val) and not isinstance(val, auto) and key not in [m[0] for m in raw_members]:
                cls_dict[key] = val

        cls = super().__new__(mcs, name, bases, cls_dict)

        cls._members_ = {}
        for mname, mvalue in resolved:
            member = FlagMember(mname, mvalue, cls)
            cls._members_[mname] = member
            setattr(cls, mname, member)

        return cls

    def __iter__(cls):
        return iter(cls._members_.values())

    def __getitem__(cls, name):
        return cls._members_[name]

    def __call__(cls, value):
        for member in cls._members_.values():
            if member._value == value:
                return member
        raise ValueError(f"{value!r} is not a valid {cls.__name__}")

    def __repr__(cls):
        return f"<Flag '{cls.__name__}'>"


# ─────────────────────────────────────────────────────────────────────────────
# Metaclass for IntFlag
# ─────────────────────────────────────────────────────────────────────────────

class _IntFlagMeta(type):

    @classmethod
    def __prepare__(mcs, name, bases):
        return _EnumNamespace()

    def __new__(mcs, name, bases, namespace):
        raw_members = list(namespace._member_names)
        resolved = _resolve_auto(raw_members)

        cls_dict = {}
        for key, val in namespace.items():
            if key.startswith('_'):
                cls_dict[key] = val
            elif callable(val) and not isinstance(val, auto) and key not in [m[0] for m in raw_members]:
                cls_dict[key] = val

        cls = super().__new__(mcs, name, bases, cls_dict)

        cls._members_ = {}
        for mname, mvalue in resolved:
            member = IntFlagMember.__new__(IntFlagMember, mvalue)
            member._name = mname
            member._value = mvalue
            member._enum_class = cls
            cls._members_[mname] = member
            setattr(cls, mname, member)

        return cls

    def __iter__(cls):
        return iter(cls._members_.values())

    def __getitem__(cls, name):
        return cls._members_[name]

    def __call__(cls, value):
        for member in cls._members_.values():
            if int(member) == value:
                return member
        raise ValueError(f"{value!r} is not a valid {cls.__name__}")

    def __repr__(cls):
        return f"<IntFlag '{cls.__name__}'>"


# ─────────────────────────────────────────────────────────────────────────────
# Public base classes
# ─────────────────────────────────────────────────────────────────────────────

class IntEnum(metaclass=_IntEnumMeta):
    """Base class for integer enumerations."""
    pass


class Flag(metaclass=_FlagMeta):
    """Base class for flag enumerations."""
    pass


class IntFlag(metaclass=_IntFlagMeta):
    """Base class for integer flag enumerations."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Test / invariant functions
# ─────────────────────────────────────────────────────────────────────────────

def enum2_int_enum():
    """
    Demonstrates that IntEnum members compare equal to their int values.
    Returns True if the invariant holds.
    """
    class Color(IntEnum):
        RED = 1
        GREEN = 2
        BLUE = 3

    return (
        Color.RED == 1 and
        Color.GREEN == 2 and
        Color.BLUE == 3 and
        int(Color.RED) == 1 and
        Color.RED == Color.RED
    )


def enum2_flag_combine():
    """
    Demonstrates that Flag members support bitwise OR combination.
    Returns True if the invariant holds.
    """
    class Permission(Flag):
        READ = 1
        WRITE = 2
        EXECUTE = 4

    combined = Permission.READ | Permission.WRITE
    return (
        combined.value == 3 and
        (Permission.READ | Permission.WRITE).value == (1 | 2) and
        (Permission.READ | Permission.WRITE | Permission.EXECUTE).value == 7
    )


def enum2_auto_values():
    """
    Demonstrates that auto() assigns sequential integers starting at 1.
    Returns [1, 2, 3].
    """
    class Direction(IntEnum):
        NORTH = auto()
        SOUTH = auto()
        EAST = auto()

    return [int(Direction.NORTH), int(Direction.SOUTH), int(Direction.EAST)]


# ─────────────────────────────────────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    'IntEnum',
    'Flag',
    'IntFlag',
    'auto',
    'enum2_int_enum',
    'enum2_flag_combine',
    'enum2_auto_values',
]