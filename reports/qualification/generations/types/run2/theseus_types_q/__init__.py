# generation B namespace class

class _Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


SimpleNamespace = _Namespace

__all__ = ["SimpleNamespace"]
