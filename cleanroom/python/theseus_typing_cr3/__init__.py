class _GenericAlias:
    def __init__(self, origin, args):
        self.__origin__ = origin
        self.__args__ = args

    def __repr__(self):
        if self.__origin__ is Union:
            return f"Union[{', '.join(repr(arg) for arg in self.__args__)}]"
        elif self.__origin__ is Optional:
            return f"Optional[{repr(self.__args__[0])}]"
        else:
            origin_name = getattr(self.__origin__, '__name__', repr(self.__origin__))
            return f"{origin_name}[{', '.join(repr(arg) for arg in self.__args__)}]"

    def __eq__(self, other):
        return (isinstance(other, _GenericAlias) and
                self.__origin__ is other.__origin__ and
                self.__args__ == other.__args__)

    def __hash__(self):
        return hash((self.__origin__, self.__args__))


class _UnionMeta(type):
    def __getitem__(cls, args):
        if not isinstance(args, tuple):
            args = (args,)
        return _GenericAlias(cls, args)


class Union(metaclass=_UnionMeta):
    pass


class _OptionalMeta(type):
    def __getitem__(cls, arg):
        return _GenericAlias(cls, (arg, type(None)))


class Optional(metaclass=_OptionalMeta):
    pass


def get_args(tp):
    if hasattr(tp, '__args__'):
        return tp.__args__
    else:
        raise TypeError(f"{tp} is not a generic alias")


def get_origin(tp):
    if hasattr(tp, '__origin__'):
        return tp.__origin__
    else:
        raise TypeError(f"{tp} is not a generic alias")


class Any:
    def __repr__(self):
        return "Any"


class _ListMeta(type):
    def __getitem__(cls, arg):
        return _GenericAlias(cls, (arg,))


class List(metaclass=_ListMeta):
    pass


class _DictMeta(type):
    def __getitem__(cls, args):
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("Dict requires exactly two type arguments")
        return _GenericAlias(cls, args)


class Dict(metaclass=_DictMeta):
    pass


class _TupleMeta(type):
    def __getitem__(cls, args):
        if not isinstance(args, tuple):
            args = (args,)
        return _GenericAlias(cls, args)


class Tuple(metaclass=_TupleMeta):
    pass


class _SetMeta(type):
    def __getitem__(cls, arg):
        return _GenericAlias(cls, (arg,))


class Set(metaclass=_SetMeta):
    pass


class _CallableMeta(type):
    def __getitem__(cls, args):
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("Callable requires [arg_types, return_type]")
        arg_types, return_type = args
        if not isinstance(arg_types, (list, tuple)):
            raise TypeError("Callable argument types must be a list or tuple")
        return _GenericAlias(cls, (tuple(arg_types), return_type))


class Callable(metaclass=_CallableMeta):
    pass


def typing3_union():
    return Union[int, str].__args__ == (int, str)


def typing3_optional():
    return Optional[int].__args__ == (int, type(None))


def typing3_get_args():
    return get_args(Optional[int]) == (int, type(None))