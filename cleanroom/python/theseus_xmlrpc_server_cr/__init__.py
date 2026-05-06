"""Clean-room implementation of xmlrpc.server behavioral surface.

This module provides a minimal stand-in for the standard library's
xmlrpc.server module, sufficient to satisfy the Theseus invariants
without importing the original implementation.
"""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_dotted(obj, name):
    """Resolve a dotted attribute path on ``obj``.

    Mirrors the behaviour of the standard library's ``resolve_dotted_attribute``
    while disallowing access to private attributes (those beginning with an
    underscore) for safety.
    """
    parts = name.split(".")
    for part in parts:
        if part.startswith("_"):
            raise AttributeError(
                "attempt to access private attribute %r" % (part,)
            )
        obj = getattr(obj, part)
    return obj


def _list_public_methods(obj):
    """Return a list of public callable attribute names on ``obj``."""
    return [
        attr
        for attr in dir(obj)
        if not attr.startswith("_") and callable(getattr(obj, attr))
    ]


# ---------------------------------------------------------------------------
# Fault — the canonical XML-RPC error object
# ---------------------------------------------------------------------------


class Fault(Exception):
    """A simple XML-RPC fault representation."""

    def __init__(self, faultCode, faultString, **extra):
        Exception.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString
        self.extra = extra

    def __repr__(self):
        return "<Fault %s: %r>" % (self.faultCode, self.faultString)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class SimpleXMLRPCDispatcher(object):
    """Mimics the public API of ``xmlrpc.server.SimpleXMLRPCDispatcher``."""

    def __init__(self, allow_none=False, encoding=None,
                 use_builtin_types=False):
        self.funcs = {}
        self.instance = None
        self.allow_none = allow_none
        self.encoding = encoding or "utf-8"
        self.use_builtin_types = use_builtin_types

    # -- registration ------------------------------------------------------

    def register_instance(self, instance, allow_dotted_names=False):
        self.instance = instance
        self.allow_dotted_names = allow_dotted_names

    def register_function(self, function=None, name=None):
        # Allow use as a decorator with keyword arguments.
        if function is None:
            def decorator(func):
                self.register_function(func, name=name)
                return func
            return decorator
        if name is None:
            name = function.__name__
        self.funcs[name] = function
        return function

    def register_introspection_functions(self):
        self.funcs.update({
            "system.listMethods": self.system_listMethods,
            "system.methodSignature": self.system_methodSignature,
            "system.methodHelp": self.system_methodHelp,
        })

    def register_multicall_functions(self):
        self.funcs["system.multicall"] = self.system_multicall

    # -- introspection -----------------------------------------------------

    def system_listMethods(self):
        methods = set(self.funcs)
        if self.instance is not None:
            if hasattr(self.instance, "_listMethods"):
                methods.update(self.instance._listMethods())
            else:
                methods.update(_list_public_methods(self.instance))
        return sorted(methods)

    def system_methodSignature(self, method_name):
        return "signatures not supported"

    def system_methodHelp(self, method_name):
        method = None
        if method_name in self.funcs:
            method = self.funcs[method_name]
        elif self.instance is not None:
            if hasattr(self.instance, "_methodHelp"):
                return self.instance._methodHelp(method_name)
            try:
                method = _resolve_dotted(self.instance, method_name)
            except AttributeError:
                method = None
        if method is None:
            return ""
        return getattr(method, "__doc__", "") or ""

    def system_multicall(self, call_list):
        results = []
        for call in call_list:
            method_name = call.get("methodName")
            params = call.get("params", ())
            try:
                results.append([self._dispatch(method_name, params)])
            except Fault as fault:
                results.append({
                    "faultCode": fault.faultCode,
                    "faultString": fault.faultString,
                })
            except Exception as exc:  # pragma: no cover - defensive
                results.append({
                    "faultCode": 1,
                    "faultString": "%s:%s" % (type(exc).__name__, exc),
                })
        return results

    # -- dispatch ----------------------------------------------------------

    def _dispatch(self, method, params):
        func = self.funcs.get(method)
        if func is not None:
            return func(*params)
        if self.instance is not None:
            dispatch = getattr(self.instance, "_dispatch", None)
            if dispatch is not None:
                return dispatch(method, params)
            try:
                attr = _resolve_dotted(self.instance, method)
            except AttributeError:
                raise Exception("method %r is not supported" % (method,))
            return attr(*params)
        raise Exception("method %r is not supported" % (method,))

    def dispatch(self, method, params):
        """Public entry point for invoking a registered method."""
        return self._dispatch(method, params)


# ---------------------------------------------------------------------------
# Server stubs (clean-room placeholders, no socket binding)
# ---------------------------------------------------------------------------


class SimpleXMLRPCRequestHandler(object):
    """Lightweight placeholder for the request-handler class."""

    rpc_paths = ("/", "/RPC2")
    encode_threshold = 1400
    aepattern = None

    def __init__(self, *args, **kwargs):
        # Real handlers wire themselves into BaseHTTPRequestHandler; the
        # clean-room version just accepts arbitrary positional/keyword args
        # so that callers can instantiate it.
        self.args = args
        self.kwargs = kwargs


class SimpleXMLRPCServer(SimpleXMLRPCDispatcher):
    """Clean-room replacement for ``xmlrpc.server.SimpleXMLRPCServer``."""

    allow_reuse_address = True

    def __init__(self, addr=None, requestHandler=SimpleXMLRPCRequestHandler,
                 logRequests=True, allow_none=False, encoding=None,
                 bind_and_activate=True, use_builtin_types=False):
        SimpleXMLRPCDispatcher.__init__(
            self,
            allow_none=allow_none,
            encoding=encoding,
            use_builtin_types=use_builtin_types,
        )
        self.server_address = addr
        self.requestHandler = requestHandler
        self.logRequests = logRequests
        self.bind_and_activate = bind_and_activate


class CGIXMLRPCRequestHandler(SimpleXMLRPCDispatcher):
    """Clean-room placeholder for the CGI request handler."""

    def __init__(self, allow_none=False, encoding=None,
                 use_builtin_types=False):
        SimpleXMLRPCDispatcher.__init__(
            self,
            allow_none=allow_none,
            encoding=encoding,
            use_builtin_types=use_builtin_types,
        )


class MultiPathXMLRPCServer(SimpleXMLRPCServer):
    """Mimics the multi-path server class."""

    def __init__(self, addr=None, requestHandler=SimpleXMLRPCRequestHandler,
                 logRequests=True, allow_none=False, encoding=None,
                 bind_and_activate=True, use_builtin_types=False):
        SimpleXMLRPCServer.__init__(
            self,
            addr=addr,
            requestHandler=requestHandler,
            logRequests=logRequests,
            allow_none=allow_none,
            encoding=encoding,
            bind_and_activate=bind_and_activate,
            use_builtin_types=use_builtin_types,
        )
        self.dispatchers = {}

    def add_dispatcher(self, path, dispatcher):
        self.dispatchers[path] = dispatcher
        return dispatcher

    def get_dispatcher(self, path):
        return self.dispatchers[path]


class DocXMLRPCServer(SimpleXMLRPCServer):
    """Documentation-flavoured placeholder."""


class DocCGIXMLRPCRequestHandler(CGIXMLRPCRequestHandler):
    """Documentation-flavoured CGI placeholder."""


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


def xmlrpcserver2_classes():
    """The expected XML-RPC server classes are present and instantiable."""
    expected = (
        SimpleXMLRPCDispatcher,
        SimpleXMLRPCServer,
        SimpleXMLRPCRequestHandler,
        CGIXMLRPCRequestHandler,
        MultiPathXMLRPCServer,
        DocXMLRPCServer,
        DocCGIXMLRPCRequestHandler,
    )
    for cls in expected:
        if not isinstance(cls, type):
            return False
    # Spot-check that the dispatcher hierarchy is intact.
    if not issubclass(SimpleXMLRPCServer, SimpleXMLRPCDispatcher):
        return False
    if not issubclass(MultiPathXMLRPCServer, SimpleXMLRPCServer):
        return False
    return True


def xmlrpcserver2_dispatcher():
    """A dispatcher can be created and methods registered on it."""
    dispatcher = SimpleXMLRPCDispatcher()

    def add(a, b):
        return a + b

    dispatcher.register_function(add)
    dispatcher.register_function(lambda x: x * 2, name="double")

    if "add" not in dispatcher.funcs:
        return False
    if "double" not in dispatcher.funcs:
        return False

    dispatcher.register_introspection_functions()
    listed = dispatcher.system_listMethods()
    for required in ("add", "double", "system.listMethods"):
        if required not in listed:
            return False
    return True


def xmlrpcserver2_dispatch():
    """Dispatch should invoke registered functions and instance methods."""
    dispatcher = SimpleXMLRPCDispatcher()
    dispatcher.register_function(lambda a, b: a + b, name="sum")

    if dispatcher.dispatch("sum", (2, 3)) != 5:
        return False

    class Service(object):
        def echo(self, value):
            return value

        def square(self, value):
            return value * value

    dispatcher.register_instance(Service())

    if dispatcher.dispatch("echo", ("hello",)) != "hello":
        return False
    if dispatcher.dispatch("square", (4,)) != 16:
        return False

    # Multicall should aggregate dispatch results and faults.
    dispatcher.register_multicall_functions()
    results = dispatcher.dispatch("system.multicall", ([
        {"methodName": "sum", "params": [1, 2]},
        {"methodName": "square", "params": [3]},
        {"methodName": "no_such_method", "params": []},
    ],))
    if results[0] != [3]:
        return False
    if results[1] != [9]:
        return False
    if not isinstance(results[2], dict) or "faultCode" not in results[2]:
        return False
    return True


__all__ = [
    "Fault",
    "SimpleXMLRPCDispatcher",
    "SimpleXMLRPCRequestHandler",
    "SimpleXMLRPCServer",
    "CGIXMLRPCRequestHandler",
    "MultiPathXMLRPCServer",
    "DocXMLRPCServer",
    "DocCGIXMLRPCRequestHandler",
    "xmlrpcserver2_classes",
    "xmlrpcserver2_dispatcher",
    "xmlrpcserver2_dispatch",
]