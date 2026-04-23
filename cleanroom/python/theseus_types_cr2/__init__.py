"""
theseus_types_cr2 - Clean-room implementation of extended types utilities.
Do NOT import the `types` module.
"""


class SimpleNamespace:
    """
    A simple object that stores kwargs as instance attributes accessible via dot notation.
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)

    def __repr__(self):
        attrs = vars(self)
        items = ", ".join(f"{k}={v!r}" for k, v in sorted(attrs.items()))
        return f"namespace({items})"

    def __eq__(self, other):
        if isinstance(other, SimpleNamespace):
            return vars(self) == vars(other)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


class MappingProxyType:
    """
    A read-only proxy of a dictionary.
    """
    def __init__(self, mapping):
        if not isinstance(mapping, dict):
            raise TypeError("MappingProxyType requires a dict")
        # Store a copy to prevent external mutation affecting the proxy
        object.__setattr__(self, '_mapping', dict(mapping))

    def __getitem__(self, key):
        return object.__getattribute__(self, '_mapping')[key]

    def __setitem__(self, key, value):
        raise TypeError("'mappingproxy' object does not support item assignment")

    def __delitem__(self, key):
        raise TypeError("'mappingproxy' object does not support item deletion")

    def __contains__(self, key):
        return key in object.__getattribute__(self, '_mapping')

    def __iter__(self):
        return iter(object.__getattribute__(self, '_mapping'))

    def __len__(self):
        return len(object.__getattribute__(self, '_mapping'))

    def __repr__(self):
        mapping = object.__getattribute__(self, '_mapping')
        return f"mappingproxy({mapping!r})"

    def keys(self):
        return object.__getattribute__(self, '_mapping').keys()

    def values(self):
        return object.__getattribute__(self, '_mapping').values()

    def items(self):
        return object.__getattribute__(self, '_mapping').items()

    def get(self, key, default=None):
        return object.__getattribute__(self, '_mapping').get(key, default)

    def __setattr__(self, name, value):
        raise AttributeError("'mappingproxy' object attribute is read-only")

    def copy(self):
        return dict(object.__getattribute__(self, '_mapping'))


def types2_namespace():
    """
    Returns SimpleNamespace(x=1).x == 1, i.e., returns 1.
    """
    ns = SimpleNamespace(x=1)
    return ns.x


def types2_mapping_proxy():
    """
    Returns MappingProxyType({'a': 1})['a'] == 1, i.e., returns 1.
    """
    proxy = MappingProxyType({'a': 1})
    return proxy['a']


def types2_namespace_repr():
    """
    Returns True if 'x=1' is in repr(SimpleNamespace(x=1)).
    """
    ns = SimpleNamespace(x=1)
    return 'x=1' in repr(ns)