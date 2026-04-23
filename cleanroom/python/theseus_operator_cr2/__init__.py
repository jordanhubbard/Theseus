def attrgetter(*attrs):
    if len(attrs) == 1:
        attr = attrs[0]
        def getter(obj):
            return getattr(obj, attr)
        return getter
    else:
        def getter(obj):
            return tuple(getattr(obj, attr) for attr in attrs)
        return getter


def itemgetter(*items):
    if len(items) == 1:
        item = items[0]
        def getter(obj):
            return obj[item]
        return getter
    else:
        def getter(obj):
            return tuple(obj[item] for item in items)
        return getter


def methodcaller(name, *args, **kwargs):
    def caller(obj):
        return getattr(obj, name)(*args, **kwargs)
    return caller


def operator2_attrgetter():
    from types import SimpleNamespace
    ns = SimpleNamespace(x=42)
    return attrgetter('x')(ns)


def operator2_itemgetter():
    return itemgetter(1)([10, 20, 30])


def operator2_methodcaller():
    return methodcaller('upper')('hello')