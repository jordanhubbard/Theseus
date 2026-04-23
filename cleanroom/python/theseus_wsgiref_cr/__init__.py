"""
theseus_wsgiref_cr — Clean-room wsgiref module.
No import of the standard `wsgiref` module.
"""

import os as _os
import sys as _sys


# Hop-by-hop header names (RFC 2616 Section 13.5.1)
_HOP_BY_HOP = frozenset({
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
})


def is_hop_by_hop(header_name):
    """Return True if header_name is a hop-by-hop header."""
    return header_name.lower() in _HOP_BY_HOP


class Headers:
    """Manage a collection of HTTP response headers."""

    def __init__(self, headers=None):
        if headers is None:
            headers = []
        self._headers = list(headers)

    def __len__(self):
        return len(self._headers)

    def __setitem__(self, name, val):
        del self[name]
        self._headers.append((name, val))

    def __delitem__(self, name):
        name = name.lower()
        self._headers[:] = [h for h in self._headers if h[0].lower() != name]

    def __getitem__(self, name):
        return self.get(name)

    def __contains__(self, name):
        return self.get(name) is not None

    def get(self, name, default=None):
        name = name.lower()
        for k, v in self._headers:
            if k.lower() == name:
                return v
        return default

    def get_all(self, name):
        name = name.lower()
        return [v for k, v in self._headers if k.lower() == name]

    def add_header(self, _name, _value, **_params):
        parts = [_value]
        for k, v in _params.items():
            k = k.replace('_', '-')
            if v is None:
                parts.append(k)
            else:
                parts.append(f'{k}="{v}"')
        self._headers.append((_name, '; '.join(parts)))

    def keys(self):
        return [k for k, v in self._headers]

    def values(self):
        return [v for k, v in self._headers]

    def items(self):
        return list(self._headers)

    def __str__(self):
        lines = [f'{k}: {v}' for k, v in self._headers]
        lines.append('')
        lines.append('')
        return '\r\n'.join(lines)

    def __bytes__(self):
        return str(self).encode('iso-8859-1')


def make_server(host, port, app, server_class=None, handler_class=None):
    """Create and return a WSGI server."""
    raise NotImplementedError("make_server requires a running HTTP server")


def read_environ():
    """Read environment variables for WSGI environ."""
    environ = {}
    environ['SERVER_NAME'] = _os.environ.get('SERVER_NAME', 'localhost')
    environ['GATEWAY_INTERFACE'] = 'CGI/1.1'
    environ['SERVER_PORT'] = _os.environ.get('SERVER_PORT', '80')
    environ['REMOTE_HOST'] = ''
    environ['CONTENT_LENGTH'] = ''
    environ['SCRIPT_NAME'] = ''
    return environ


def make_environ():
    """Create a minimal valid WSGI environ dict."""
    environ = {
        'REQUEST_METHOD': 'GET',
        'SCRIPT_NAME': '',
        'PATH_INFO': '/',
        'QUERY_STRING': '',
        'CONTENT_TYPE': 'text/plain',
        'CONTENT_LENGTH': '',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8080',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': _sys.stdin.buffer if hasattr(_sys.stdin, 'buffer') else _sys.stdin,
        'wsgi.errors': _sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    return environ


def application_uri(environ):
    """Return the application's base URI from a WSGI environ dict."""
    url = environ['wsgi.url_scheme'] + '://'
    from urllib.parse import quote
    host = environ.get('HTTP_HOST')
    if not host:
        host = environ['SERVER_NAME']
        port = environ.get('SERVER_PORT', '80')
        if environ['wsgi.url_scheme'] == 'https':
            if port != '443':
                host += ':' + port
        else:
            if port != '80':
                host += ':' + port
    url += host
    url += quote(environ.get('SCRIPT_NAME') or '/')
    return url


def request_uri(environ, include_query=True):
    """Return the full request URI from a WSGI environ dict."""
    url = application_uri(environ)
    from urllib.parse import quote
    path_info = quote(environ.get('PATH_INFO', ''), safe='/;=,')
    if not environ.get('SCRIPT_NAME'):
        url += path_info[1:]
    else:
        url += path_info
    if include_query and environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']
    return url


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def wsgiref2_headers():
    """Headers class can store and retrieve headers; returns True."""
    h = Headers()
    h['Content-Type'] = 'text/html'
    h['X-Custom'] = 'value'
    return (h['Content-Type'] == 'text/html' and
            h['X-Custom'] == 'value' and
            len(h) == 2)


def wsgiref2_environ():
    """make_environ() returns a valid WSGI environ dict; returns True."""
    env = make_environ()
    return (isinstance(env, dict) and
            'REQUEST_METHOD' in env and
            'wsgi.version' in env and
            env['wsgi.version'] == (1, 0))


def wsgiref2_validate():
    """is_hop_by_hop() identifies hop-by-hop headers; returns True."""
    return (is_hop_by_hop('connection') is True and
            is_hop_by_hop('transfer-encoding') is True and
            is_hop_by_hop('content-type') is False)


__all__ = [
    'Headers', 'make_environ', 'make_server', 'read_environ',
    'application_uri', 'request_uri', 'is_hop_by_hop',
    'wsgiref2_headers', 'wsgiref2_environ', 'wsgiref2_validate',
]
