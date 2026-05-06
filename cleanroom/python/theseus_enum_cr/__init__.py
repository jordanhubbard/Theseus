"""Clean-room enum module for Theseus (theseus_enum_cr).

Implements Enum, IntEnum, Flag, and auto() without importing the stdlib
`enum` package. Built from scratch using only Python built-ins.
"""


class _AutoValue:
    """Sentinel marker for auto-assigned values."""
    __slots__ = ()

    def __repr__(self):
        return "auto()"


_AUTO_SENTINEL = _AutoValue()


def auto():
    """Return a sentinel signalling automatic value assignment."""
    return _AutoValue()


def _is_auto(value):
    return isinstance(value, _AutoValue)


def _is_dunder(name):
    return (
        len(name) > 4
        and name.startswith("__")
        and name.endswith("__")
        and name[2] != "_"
        and name[-3] != "_"
    )


def _is_sunder(name):
    return (
        len(name) > 2
        and name.startswith("_")
        and name.endswith("_")
        and name[1:2] != "_"
        and name[-2:-1] != "_"
    )


class _EnumDict(dict):
    """Captures member definition order for class body evaluation."""

    def __init__(self):
        super().__init__()
        self._member_names = []

    def __setitem__(self, key, value):
        if (
            not _is_dunder(key)
            and not _is_sunder(key)
            and not callable(value)
            and not isinstance(value, (classmethod, staticmethod, property))
        ):
            if key in self._member_names:
                raise TypeError("Attempted to reuse key: %r" % key)
            self._member_names.append(key)
        super().__setitem__(key, value)


class EnumMeta(type):
    """Metaclass for Enum types — builds member instances from class body."""

    @classmethod
    def __prepare__(mcs, name, bases):
        return _EnumDict()

    def __new__(mcs, cls_name, bases, classdict):
        member_names = getattr(classdict, "_member_names", [])

        # Find the Enum base (the first non-Enum base is the data-type base, if any)
        enum_base = None
        for base in bases:
            if isinstance(base, EnumMeta):
                if enum_base is None:
                    enum_base = base

        # Determine value-mixin type (e.g. int for IntEnum)
        member_type = object
        for base in bases:
            if base is object:
                continue
            if isinstance(base, EnumMeta):
                # Use the same member_type as the Enum base
                mt = getattr(base, "_member_type_", None)
                if mt is not None and mt is not object:
                    member_type = mt
            else:
                # First non-Enum, non-object base is the data type (e.g. int)
                if member_type is object:
                    member_type = base

        # Strip member assignments from classdict — they'll become instances.
        member_values = {}
        for name in member_names:
            member_values[name] = classdict[name]
            del classdict[name]

        # Compute auto values
        resolved_values = {}
        last_int = 0
        for name in member_names:
            raw = member_values[name]
            if _is_auto(raw):
                last_int += 1
                resolved_values[name] = last_int
            else:
                resolved_values[name] = raw
                if isinstance(raw, int) and not isinstance(raw, bool):
                    last_int = raw

        # Create the class itself
        new_cls = super().__new__(mcs, cls_name, bases, dict(classdict))
        new_cls._member_type_ = member_type
        new_cls._member_names_ = []
        new_cls._member_map_ = {}
        new_cls._value2member_map_ = {}

        # Create member instances
        for name in member_names:
            value = resolved_values[name]
            if member_type is object:
                member = object.__new__(new_cls)
            else:
                # Construct using the data type (e.g. int(value))
                if isinstance(value, tuple):
                    member = member_type.__new__(new_cls, *value)
                else:
                    member = member_type.__new__(new_cls, value)
            member._name_ = name
            member._value_ = value
            # Reuse existing member if same value already registered (alias)
            if value in new_cls._value2member_map_:
                canonical = new_cls._value2member_map_[value]
                new_cls._member_map_[name] = canonical
                setattr(new_cls, name, canonical)
            else:
                new_cls._member_names_.append(name)
                new_cls._member_map_[name] = member
                new_cls._value2member_map_[value] = member
                setattr(new_cls, name, member)

        return new_cls

    def __call__(cls, value=None, *args, **kwargs):
        # Lookup by value: MyEnum(1) -> the member with value 1
        if args or kwargs:
            raise TypeError("Enum lookup takes a single value")
        if value in cls._value2member_map_:
            return cls._value2member_map_[value]
        # For Flag, attempt bitwise composition
        if issubclass(cls, Flag) and isinstance(value, int):
            return cls._missing_flag_(value)
        raise ValueError("%r is not a valid %s" % (value, cls.__name__))

    def __iter__(cls):
        return (cls._member_map_[name] for name in cls._member_names_)

    def __len__(cls):
        return len(cls._member_names_)

    def __contains__(cls, item):
        if isinstance(item, cls):
            return True
        try:
            return item in cls._value2member_map_
        except TypeError:
            return False

    def __getitem__(cls, name):
        return cls._member_map_[name]

    def __repr__(cls):
        return "<enum %r>" % cls.__name__


class Enum(metaclass=EnumMeta):
    """Base enumeration class."""

    def __repr__(self):
        return "<%s.%s: %r>" % (
            self.__class__.__name__,
            self._name_,
            self._value_,
        )

    def __str__(self):
        return "%s.%s" % (self.__class__.__name__, self._name_)

    def __hash__(self):
        return hash(self._name_)

    def __eq__(self, other):
        if isinstance(other, Enum):
            return self is other
        return NotImplemented

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_


class IntEnum(int, Enum):
    """Enum whose members are also (and are) ints."""

    def __str__(self):
        return "%s.%s" % (self.__class__.__name__, self._name_)

    def __repr__(self):
        return "<%s.%s: %r>" % (
            self.__class__.__name__,
            self._name_,
            self._value_,
        )


class Flag(Enum):
    """Enum supporting bitwise operations (|, &, ^, ~)."""

    @classmethod
    def _missing_flag_(cls, value):
        # Build a pseudo-member representing the bit combination.
        if value == 0:
            # Look for a zero-valued member
            if 0 in cls._value2member_map_:
                return cls._value2member_map_[0]
            pseudo = object.__new__(cls)
            pseudo._name_ = None
            pseudo._value_ = 0
            return pseudo
        # Validate that value is composed of known bits only
        all_bits = 0
        for m in cls._value2member_map_.values():
            if isinstance(m._value_, int):
                all_bits |= m._value_
        if value & ~all_bits:
            raise ValueError("%r is not a valid %s" % (value, cls.__name__))

        if value in cls._value2member_map_:
            return cls._value2member_map_[value]

        # Compose name from individual bits
        names = []
        remaining = value
        # Iterate in declaration order for stable naming
        for name in cls._member_names_:
            m = cls._member_map_[name]
            v = m._value_
            if v and (v & value) == v:
                names.append(name)
                remaining &= ~v
        pseudo = object.__new__(cls)
        pseudo._name_ = "|".join(names) if names else None
        pseudo._value_ = value
        # Cache it
        cls._value2member_map_[value] = pseudo
        return pseudo

    def __or__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__(self._value_ | other._value_)
        if isinstance(other, int):
            return self.__class__(self._value_ | other)
        return NotImplemented

    def __and__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__(self._value_ & other._value_)
        if isinstance(other, int):
            return self.__class__(self._value_ & other)
        return NotImplemented

    def __xor__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__(self._value_ ^ other._value_)
        if isinstance(other, int):
            return self.__class__(self._value_ ^ other)
        return NotImplemented

    def __invert__(self):
        all_bits = 0
        for m in self.__class__._value2member_map_.values():
            if isinstance(m._value_, int):
                all_bits |= m._value_
        return self.__class__(all_bits & ~self._value_)

    def __contains__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return (self._value_ & other._value_) == other._value_

    def __bool__(self):
        return bool(self._value_)


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def _make_color_enum():
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3
    return Color


def enum2_name_value():
    """Verify .name and .value attributes work correctly."""
    Color = _make_color_enum()
    if Color.RED.name != "RED":
        return False
    if Color.RED.value != 1:
        return False
    if Color.GREEN.name != "GREEN":
        return False
    if Color.GREEN.value != 2:
        return False
    if Color.BLUE.name != "BLUE":
        return False
    if Color.BLUE.value != 3:
        return False
    return True


def enum2_lookup():
    """Verify lookup by value (Color(1)) and by name (Color['RED'])."""
    Color = _make_color_enum()
    if Color(1) is not Color.RED:
        return False
    if Color(2) is not Color.GREEN:
        return False
    if Color(3) is not Color.BLUE:
        return False
    if Color["RED"] is not Color.RED:
        return False
    if Color["BLUE"] is not Color.BLUE:
        return False
    # Invalid lookup must raise
    try:
        Color(99)
        return False
    except ValueError:
        pass
    return True


def enum2_iteration():
    """Return the count of members yielded by iteration over the enum."""
    Color = _make_color_enum()
    return sum(1 for _ in Color)


__all__ = [
    "Enum",
    "IntEnum",
    "Flag",
    "auto",
    "EnumMeta",
    "enum2_name_value",
    "enum2_lookup",
    "enum2_iteration",
]