"""
theseus_xmlrpc_server_cr — Clean-room xmlrpc.server module.
No import of the standard `xmlrpc.server` module.
"""

import socketserver as _socketserver
import http.server as _http_server
import xmlrpc.client as _xmlrpc_client
import sys as _sys
import traceback as _traceback
import inspect as _inspect
import re as _re


def resolve_dotted_attribute(obj, attr, allow_dotted_names=True):
    """Resolves a dotted attribute name to an object."""
    if allow_dotted_names:
        attrs = attr.split('.')
    else:
        attrs = [attr]
    for i in attrs:
        if i.startswith('_'):
            raise AttributeError("attempt to access private attribute '%s'" % i)
        obj = getattr(obj, i)
    return obj


def list_public_methods(obj):
    """Returns a list of attribute strings, found in the specified object, which do not begin with an underscore character."""
    return [member for member in dir(obj) if not member.startswith('_')]


class SimpleXMLRPCDispatcher:
    """Mix-in class that dispatches XML-RPC requests."""

    def __init__(self, allow_none=False, encoding=None, use_builtin_types=False):
        self.funcs = {}
        self.instance = None
        self.allow_none = allow_none
        self.encoding = encoding or 'utf-8'
        self.use_builtin_types = use_builtin_types

    def register_instance(self, instance, allow_dotted_names=False):
        """Register an instance to respond to XML-RPC requests."""
        self.instance = instance
        self.allow_dotted_names = allow_dotted_names

    def register_function(self, function=None, name=None):
        """Register a function that responds to XML-RPC requests."""
        if function is None:
            return lambda func: self.register_function(func, name)
        if name is None:
            name = function.__name__
        self.funcs[name] = function
        return function

    def register_introspection_functions(self):
        """Register XML-RPC introspection functions."""
        self.funcs['system.listMethods'] = self.system_listMethods
        self.funcs['system.methodSignature'] = self.system_methodSignature
        self.funcs['system.methodHelp'] = self.system_methodHelp

    def register_multicall_functions(self):
        """Register XML-RPC multicall function."""
        self.funcs['system.multicall'] = self.system_multicall

    def _marshaled_dispatch(self, data, dispatch_handler=None, path=None):
        """Dispatches an XML-RPC method from marshalled (pickled) data."""
        try:
            params, method = _xmlrpc_client.loads(data, use_builtin_types=self.use_builtin_types)
            if dispatch_handler:
                response = dispatch_handler(method, params)
            else:
                response = self._dispatch(method, params)
            if not isinstance(response, tuple):
                response = (response,)
        except _xmlrpc_client.Fault as fault:
            response = _xmlrpc_client.dumps(fault, allow_none=self.allow_none,
                                             encoding=self.encoding)
        except BaseException:
            exc_type, exc_value, exc_tb = _sys.exc_info()
            try:
                response = _xmlrpc_client.dumps(
                    _xmlrpc_client.Fault(1, '%s:%s' % (exc_type, exc_value)),
                    encoding=self.encoding, allow_none=self.allow_none
                )
            finally:
                exc_type = exc_value = exc_tb = None
        else:
            response = _xmlrpc_client.dumps(response, methodresponse=True,
                                             allow_none=self.allow_none,
                                             encoding=self.encoding)
        return response.encode(self.encoding, 'xmlcharrefreplace')

    def system_listMethods(self):
        """Return a list of the methods supported by the server."""
        methods = set(self.funcs.keys())
        if self.instance is not None:
            if hasattr(self.instance, '_listMethods'):
                methods |= set(self.instance._listMethods())
            elif not hasattr(self.instance, '_dispatch'):
                methods |= set(list_public_methods(self.instance))
        return sorted(methods)

    def system_methodSignature(self, method_name):
        """Return a description of the argument format for the given method."""
        return 'signatures not supported'

    def system_methodHelp(self, method_name):
        """Return a help string describing the use of the given method."""
        method = None
        if method_name in self.funcs:
            method = self.funcs[method_name]
        elif self.instance is not None:
            try:
                method = resolve_dotted_attribute(self.instance, method_name,
                                                  getattr(self, 'allow_dotted_names', False))
            except AttributeError:
                pass
        if method is None:
            return ''
        return _inspect.getdoc(method) or ''

    def system_multicall(self, call_list):
        """Process a list of calls and return a list of results."""
        results = []
        for call in call_list:
            method_name = call['methodName']
            params = call['params']
            try:
                results.append([self._dispatch(method_name, params)])
            except _xmlrpc_client.Fault as fault:
                results.append({'faultCode': fault.faultCode,
                                 'faultString': fault.faultString})
            except BaseException:
                exc_type, exc_value, exc_tb = _sys.exc_info()
                results.append({'faultCode': 1,
                                 'faultString': '%s:%s' % (exc_type, exc_value)})
        return results

    def _dispatch(self, method, params):
        """Dispatches the XML-RPC method."""
        try:
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                try:
                    func = resolve_dotted_attribute(self.instance, method,
                                                    getattr(self, 'allow_dotted_names', False))
                except AttributeError:
                    raise Exception('method "%s" is not supported' % method)
            else:
                raise Exception('method "%s" is not supported' % method)
        return func(*params)


class SimpleXMLRPCRequestHandler(_http_server.BaseHTTPRequestHandler):
    """Simple XML-RPC request handler class."""

    rpc_paths = ('/', '/RPC2')
    encode_threshold = None
    wbufsize = -1
    disable_nagle_algorithm = False

    def is_rpc_path_valid(self):
        if self.rpc_paths:
            return self.path in self.rpc_paths
        return True

    def do_POST(self):
        if not self.is_rpc_path_valid():
            self.report_404()
            return
        try:
            max_chunk_size = 10 * 1024 * 1024
            size_remaining = int(self.headers.get('content-length', 0))
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                chunk = self.rfile.read(chunk_size)
                if not chunk:
                    break
                L.append(chunk)
                size_remaining -= len(L[-1])
            data = b''.join(L)

            data = self.decode_request_content(data)
            if data is None:
                return

            response = self.server._marshaled_dispatch(
                data, getattr(self, '_dispatch', None), self.path
            )
        except Exception as e:
            self.send_response(500)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/xml')
            self.send_header('Content-length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    def decode_request_content(self, data):
        encoding = self.headers.get('content-encoding', 'identity').lower()
        if encoding in ('identity',):
            return data
        elif encoding == 'gzip':
            import gzip as _gzip
            return _gzip.decompress(data)
        else:
            self.send_response(501, 'encoding %r not supported' % encoding)
            self.send_header('Content-length', '0')
            self.end_headers()
            return None

    def report_404(self):
        self.send_response(404)
        response = b'No such page'
        self.send_header('Content-type', 'text/plain')
        self.send_header('Content-length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_request(self, code='-', size='-'):
        pass


class SimpleXMLRPCServer(_socketserver.TCPServer, SimpleXMLRPCDispatcher):
    """Simple XML-RPC server."""

    allow_reuse_address = True
    _send_traceback_header = False
    timeout = None

    def __init__(self, addr, requestHandler=SimpleXMLRPCRequestHandler,
                 logRequests=True, allow_none=False, encoding=None,
                 bind_and_activate=True, use_builtin_types=False):
        self.logRequests = logRequests
        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding, use_builtin_types)
        _socketserver.TCPServer.__init__(self, addr, requestHandler,
                                          bind_and_activate)

    def server_bind(self):
        import socket as _socket
        self.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        _socketserver.TCPServer.server_bind(self)


class MultiPathXMLRPCServer(SimpleXMLRPCServer):
    """Multipath XML-RPC server."""

    def __init__(self, addr, requestHandler=SimpleXMLRPCRequestHandler,
                 logRequests=True, allow_none=False, encoding=None,
                 bind_and_activate=True, use_builtin_types=False):
        SimpleXMLRPCServer.__init__(self, addr, requestHandler, logRequests,
                                     allow_none, encoding, bind_and_activate,
                                     use_builtin_types)
        self.dispatchers = {}
        self.allow_none = allow_none
        self.encoding = encoding or 'utf-8'

    def add_dispatcher(self, path, dispatcher):
        self.dispatchers[path] = dispatcher
        return dispatcher

    def get_dispatcher(self, path):
        return self.dispatchers[path]

    def _marshaled_dispatch(self, data, dispatch_handler=None, path=None):
        if path in self.dispatchers:
            return self.dispatchers[path]._marshaled_dispatch(data, dispatch_handler, path)
        return SimpleXMLRPCDispatcher._marshaled_dispatch(self, data, dispatch_handler, path)


class CGIXMLRPCRequestHandler(SimpleXMLRPCDispatcher):
    """Simple handler for XML-RPC data passed through CGI."""

    def __init__(self, allow_none=False, encoding=None, use_builtin_types=False):
        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding, use_builtin_types)

    def handle_xmlrpc(self, request_text):
        """Handle a single XML-RPC request."""
        response = self._marshaled_dispatch(request_text.encode('utf-8') if isinstance(request_text, str) else request_text)
        return response

    def handle_get(self):
        """Handle HTTP GET request. Unimplemented."""
        response = b'Not Supported'
        return response

    def handle_request(self, request_text=None):
        """Handle a single XML-RPC request passed through a CGI post method."""
        import os as _os
        if request_text is None:
            import sys as _sys
            request_text = _sys.stdin.buffer.read()
        self.handle_xmlrpc(request_text)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xmlrpcserver2_classes():
    """SimpleXMLRPCServer and MultiPathXMLRPCServer classes exist; returns True."""
    return (isinstance(SimpleXMLRPCServer, type) and
            isinstance(MultiPathXMLRPCServer, type) and
            issubclass(MultiPathXMLRPCServer, SimpleXMLRPCServer))


def xmlrpcserver2_dispatcher():
    """SimpleXMLRPCDispatcher can be created and methods registered; returns True."""
    d = SimpleXMLRPCDispatcher()
    d.register_function(lambda x: x * 2, 'double')
    return 'double' in d.funcs and callable(d.funcs['double'])


def xmlrpcserver2_dispatch():
    """_dispatch() resolves and calls a registered method; returns True."""
    d = SimpleXMLRPCDispatcher()
    d.register_function(lambda x, y: x + y, 'add')
    result = d._dispatch('add', (3, 4))
    return result == 7


__all__ = [
    'SimpleXMLRPCDispatcher', 'SimpleXMLRPCRequestHandler',
    'SimpleXMLRPCServer', 'MultiPathXMLRPCServer', 'CGIXMLRPCRequestHandler',
    'resolve_dotted_attribute', 'list_public_methods',
    'xmlrpcserver2_classes', 'xmlrpcserver2_dispatcher', 'xmlrpcserver2_dispatch',
]
