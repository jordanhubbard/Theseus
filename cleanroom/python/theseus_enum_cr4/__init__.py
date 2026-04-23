"""
theseus_enum_cr4 — Clean-room implementation of enum utilities.
No import of the standard `enum` module.
"""

# ---------------------------------------------------------------------------
# auto() helper
# ---------------------------------------------------------------------------

class auto:
    """Sentinel that EnumMeta replaces with an automatically chosen value."""

    def __repr__(self):
        return "auto()"


# ---------------------------------------------------------------------------
# EnumMeta — the metaclass that powers all Enum classes
# ---------------------------------------------------------------------------

class EnumMeta(type):
    """
    Metaclass for Enum.  Collects class-body assignments whose names don't
    start with '_' and are not callables/descriptors, turning them into
    enum members.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Determine if any base is a non-Enum type mixin (e.g. int)
        # We need to look through the full MRO of all bases
        member_type = object

        for b in bases:
            if b is object:
                continue
            # Walk the MRO of each base to find non-EnumMeta, non-object types
            for mro_cls in b.__mro__:
                if mro_cls is object:
                    continue
                if isinstance(mro_cls, EnumMeta):
                    continue
                if isinstance(mro_cls, type):
                    # This is a concrete mixin type (e.g. int)
                    member_type = mro_cls
                    break

        # Resolve member candidates from namespace
        member_names = []
        member_values = {}  # name -> resolved value

        new_namespace = {}

        for key, val in namespace.items():
            if key.startswith('_'):
                # dunders, sunders, private — not members
                new_namespace[key] = val
            elif isinstance(val, (classmethod, staticmethod, property)):
                new_namespace[key] = val
            elif callable(val) and not isinstance(val, auto):
                # method defined in body
                new_namespace[key] = val
            else:
                # It's a member candidate
                if isinstance(val, auto):
                    # Generate next value
                    if member_names:
                        prev_val = member_values[member_names[-1]]
                        if isinstance(prev_val, int):
                            val = prev_val + 1
                        else:
                            val = len(member_names) + 1
                    else:
                        val = 1
                member_names.append(key)
                member_values[key] = val

        # Build the class without member attributes first
        new_namespace['_member_names_'] = member_names
        new_namespace['_member_map_'] = {}
        new_namespace['_value2member_map_'] = {}
        new_namespace['_member_type_'] = member_type

        cls = super().__new__(mcs, name, bases, new_namespace)

        # Now create member instances and attach them
        for mname in member_names:
            mval = member_values[mname]
            member = mcs._create_member(cls, mname, mval, member_type)
            cls._member_map_[mname] = member
            cls._value2member_map_[mval] = member
            # Set as class attribute (bypass descriptor protocol)
            type.__setattr__(cls, mname, member)

        return cls

    @staticmethod
    def _create_member(cls, name, value, member_type):
        """Create a single enum member."""
        if member_type is not object and member_type is not None:
            # Use the mixin type's __new__ directly to avoid recursion
            try:
                member = member_type.__new__(cls, value)
            except Exception:
                member = object.__new__(cls)
        else:
            member = object.__new__(cls)

        # Set private attributes directly
        object.__setattr__(member, '_name_', name)
        object.__setattr__(member, '_value_', value)
        return member

    def __call__(cls, value):
        """Look up a member by value, or create a new instance if base class."""
        # Walk MRO for value map
        for klass in cls.__mro__:
            if '_value2member_map_' in klass.__dict__:
                if value in klass._value2member_map_:
                    return klass._value2member_map_[value]
        raise ValueError(f"{value!r} is not a valid {cls.__name__}")

    def __iter__(cls):
        return (cls._member_map_[n] for n in cls._member_names_)

    def __len__(cls):
        return len(cls._member_names_)

    def __repr__(cls):
        return f"<enum {cls.__name__!r}>"

    def __getitem__(cls, name):
        return cls._member_map_[name]

    def __contains__(cls, member):
        return isinstance(member, cls) and member._name_ in cls._member_map_


# ---------------------------------------------------------------------------
# Enum base class
# ---------------------------------------------------------------------------

class Enum(metaclass=EnumMeta):
    """Base class for all enumerations."""

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name_}: {self._value_!r}>"

    def __str__(self):
        return f"{type(self).__name__}.{self._name_}"

    def __hash__(self):
        return hash(self._name_)

    def __eq__(self, other):
        if isinstance(other, Enum):
            return self is other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_


# ---------------------------------------------------------------------------
# IntEnum — members are also int instances
# ---------------------------------------------------------------------------

class IntEnum(int, Enum):
    """Enum where members are also integers."""

    def __new__(cls, value):
        # This is called when doing IntEnum(value) lookup
        # The actual member creation goes through EnumMeta._create_member
        # which calls int.__new__(cls, value) directly
        return int.__new__(cls, value)

    def __eq__(self, other):
        return int.__eq__(self, other)

    def __ne__(self, other):
        return int.__ne__(self, other)

    def __lt__(self, other):
        return int.__lt__(self, other)

    def __le__(self, other):
        return int.__le__(self, other)

    def __gt__(self, other):
        return int.__gt__(self, other)

    def __ge__(self, other):
        return int.__ge__(self, other)

    def __hash__(self):
        return int.__hash__(self)

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name_}: {int(self)}>"

    def __str__(self):
        return f"{type(self).__name__}.{self._name_}"

    def __add__(self, other):
        return int.__add__(self, other)

    def __radd__(self, other):
        return int.__radd__(self, other)

    def __sub__(self, other):
        return int.__sub__(self, other)

    def __rsub__(self, other):
        return int.__rsub__(self, other)

    def __mul__(self, other):
        return int.__mul__(self, other)

    def __rmul__(self, other):
        return int.__rmul__(self, other)

    def __int__(self):
        return int.__int__(self)


# ---------------------------------------------------------------------------
# Flag — enum with bitwise operations
# ---------------------------------------------------------------------------

class Flag(Enum):
    """Enum with support for bitwise operations."""

    def __or__(self, other):
        if isinstance(other, type(self)):
            val = self._value_ | other._value_
        else:
            val = self._value_ | other
        try:
            return type(self)(val)
        except ValueError:
            pseudo = object.__new__(type(self))
            object.__setattr__(pseudo, '_name_', '')
            object.__setattr__(pseudo, '_value_', val)
            return pseudo

    def __and__(self, other):
        if isinstance(other, type(self)):
            val = self._value_ & other._value_
        else:
            val = self._value_ & other
        try:
            return type(self)(val)
        except ValueError:
            pseudo = object.__new__(type(self))
            object.__setattr__(pseudo, '_name_', '')
            object.__setattr__(pseudo, '_value_', val)
            return pseudo

    def __xor__(self, other):
        if isinstance(other, type(self)):
            val = self._value_ ^ other._value_
        else:
            val = self._value_ ^ other
        try:
            return type(self)(val)
        except ValueError:
            pseudo = object.__new__(type(self))
            object.__setattr__(pseudo, '_name_', '')
            object.__setattr__(pseudo, '_value_', val)
            return pseudo

    def __invert__(self):
        all_bits = 0
        for m in type(self):
            all_bits |= m._value_
        val = all_bits & ~self._value_
        try:
            return type(self)(val)
        except ValueError:
            pseudo = object.__new__(type(self))
            object.__setattr__(pseudo, '_name_', '')
            object.__setattr__(pseudo, '_value_', val)
            return pseudo

    def __bool__(self):
        return bool(self._value_)

    def __contains__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"unsupported operand type(s)")
        return (self._value_ & other._value_) == other._value_


# ---------------------------------------------------------------------------
# IntFlag — Flag where members are also int instances
# ---------------------------------------------------------------------------

def _make_intflag_pseudo(cls, val):
    result = int.__new__(cls, val)
    object.__setattr__(result, '_name_', '')
    object.__setattr__(result, '_value_', val)
    return result


class IntFlag(int, Flag):
    """Flag enum where members are also integers."""

    def __new__(cls, value):
        return int.__new__(cls, value)

    def __or__(self, other):
        val = int.__or__(self, int(other))
        try:
            return type(self)(val)
        except ValueError:
            return _make_intflag_pseudo(type(self), val)

    def __and__(self, other):
        val = int.__and__(self, int(other))
        try:
            return type(self)(val)
        except ValueError:
            return _make_intflag_pseudo(type(self), val)

    def __xor__(self, other):
        val = int.__xor__(self, int(other))
        try:
            return type(self)(val)
        except ValueError:
            return _make_intflag_pseudo(type(self), val)

    def __invert__(self):
        val = int.__invert__(self)
        try:
            return type(self)(val)
        except ValueError:
            return _make_intflag_pseudo(type(self), val)

    def __eq__(self, other):
        return int.__eq__(self, other)

    def __hash__(self):
        return int.__hash__(self)

    def __int__(self):
        return int.__int__(self)

    def __bool__(self):
        return int.__bool__(self)


# ---------------------------------------------------------------------------
# unique decorator
# ---------------------------------------------------------------------------

def unique(cls):
    """
    Class decorator that ensures no two enum members share the same value.
    Raises ValueError if duplicates are found.
    """
    seen = {}
    for name in cls._member_names_:
        val = cls._member_map_[name]._value_
        if val in seen:
            raise ValueError(
                f"duplicate values found in {cls.__name__!r}: "
                f"{name!r} -> {val!r} already used by {seen[val]!r}"
            )
        seen[val] = name
    return cls


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def enum4_intenum() -> bool:
    """
    Create an IntEnum, verify member equality with int and isinstance check.
    """
    class Status(IntEnum):
        OK = 200
        NOT_FOUND = 404

    ok = Status.OK
    # Must equal the integer 200
    if ok != 200:
        return False
    # Must be an instance of int
    if not isinstance(ok, int):
        return False
    # Must be an instance of IntEnum
    if not isinstance(ok, IntEnum):
        return False
    # Value attribute
    if ok.value != 200:
        return False
    return True


def enum4_unique() -> bool:
    """
    Apply @unique to an enum with duplicate values; expect ValueError.
    Returns True if ValueError is raised (error caught).
    """
    try:
        @unique
        class Color(Enum):
            RED = 1
            CRIMSON = 1  # duplicate!
            BLUE = 2

        return False  # Should have raised
    except ValueError:
        return True


def enum4_intenum_compare() -> bool:
    """
    Verify that IntEnum members support integer comparison (> 0).
    """
    class Status(IntEnum):
        OK = 200
        ERROR = 500

    if not (Status.OK > 0):
        return False
    if not (Status.ERROR > Status.OK):
        return False
    if not (Status.OK >= 200):
        return False
    if not (Status.OK < Status.ERROR):
        return False
    return True


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    'Enum',
    'IntEnum',
    'Flag',
    'IntFlag',
    'auto',
    'unique',
    'EnumMeta',
    'enum4_intenum',
    'enum4_unique',
    'enum4_intenum_compare',
]