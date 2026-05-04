"""Clean-room xmlrpc.server subset for Theseus invariants."""


def resolve_dotted_attribute(obj, attr, allow_dotted_names=True):
    target = obj
    for part in attr.split("."):
        if part.startswith("_"):
            raise AttributeError(part)
        target = getattr(target, part)
    return target


def list_public_methods(obj):
    return [name for name in dir(obj) if not name.startswith("_") and callable(getattr(obj, name))]


class SimpleXMLRPCDispatcher:
    def __init__(self, allow_none=False, encoding=None, use_builtin_types=False):
        self.funcs = {}
        self.instance = None

    def register_function(self, function=None, name=None):
        if function is None:
            def decorator(fn):
                self.register_function(fn, name)
                return fn
            return decorator
        self.funcs[name or function.__name__] = function
        return function

    def register_instance(self, instance, allow_dotted_names=False):
        self.instance = instance

    def _dispatch(self, method, params):
        if method in self.funcs:
            return self.funcs[method](*params)
        if self.instance is not None:
            return resolve_dotted_attribute(self.instance, method)(*params)
        raise Exception("method %r is not supported" % method)


class SimpleXMLRPCRequestHandler:
    pass


class SimpleXMLRPCServer(SimpleXMLRPCDispatcher):
    pass


class MultiPathXMLRPCServer(SimpleXMLRPCServer):
    pass


class CGIXMLRPCRequestHandler(SimpleXMLRPCDispatcher):
    pass


def xmlrpcserver2_classes():
    return isinstance(SimpleXMLRPCServer, type) and isinstance(MultiPathXMLRPCServer, type) and issubclass(MultiPathXMLRPCServer, SimpleXMLRPCServer)


def xmlrpcserver2_dispatcher():
    d = SimpleXMLRPCDispatcher()
    d.register_function(lambda x: x * 2, "double")
    return "double" in d.funcs and callable(d.funcs["double"])


def xmlrpcserver2_dispatch():
    d = SimpleXMLRPCDispatcher()
    d.register_function(lambda x, y: x + y, "add")
    return d._dispatch("add", (3, 4)) == 7


__all__ = [
    "SimpleXMLRPCDispatcher", "SimpleXMLRPCRequestHandler",
    "SimpleXMLRPCServer", "MultiPathXMLRPCServer", "CGIXMLRPCRequestHandler",
    "resolve_dotted_attribute", "list_public_methods",
    "xmlrpcserver2_classes", "xmlrpcserver2_dispatcher", "xmlrpcserver2_dispatch",
]
