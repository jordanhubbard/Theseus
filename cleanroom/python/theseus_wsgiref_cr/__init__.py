"""
theseus_wsgiref_cr — clean-room reimplementation of wsgiref.

Provides minimal Headers, environ helpers, and a validator, all built
from scratch using only the Python standard library (no wsgiref import).
"""

import sys
import io


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

class Headers(object):
    """A case-insensitive multi-valued mapping of HTTP response headers."""

    def __init__(self, headers=None):
        if headers is None:
            headers = []
        if not isinstance(headers, list):
            raise TypeError("Headers must be initialized with a list")
        for item in headers:
            if not (isinstance(item, tuple) and len(item) == 2):
                raise TypeError("Each header must be a (name, value) tuple")
        self._headers = list(headers)

    def _lower(self, name):
        return name.lower()

    def __len__(self):
        return len(self._headers)

    def __setitem__(self, name, value):
        del self[name]
        self._headers.append((name, value))

    def __delitem__(self, name):
        ln = self._lower(name)
        self._headers[:] = [
            (k, v) for k, v in self._headers if k.lower() != ln
        ]

    def __getitem__(self, name):
        return self.get(name)

    def __contains__(self, name):
        return self.get(name) is not None

    def has_key(self, name):
        return self.get(name) is not None

    def get(self, name, default=None):
        ln = self._lower(name)
        for k, v in self._headers:
            if k.lower() == ln:
                return v
        return default

    def get_all(self, name):
        ln = self._lower(name)
        return [v for k, v in self._headers if k.lower() == ln]

    def keys(self):
        return [k for k, _ in self._headers]

    def values(self):
        return [v for _, v in self._headers]

    def items(self):
        return list(self._headers)

    def __iter__(self):
        return iter(self.keys())

    def setdefault(self, name, value):
        existing = self.get(name)
        if existing is not None:
            return existing
        self._headers.append((name, value))
        return value

    def add_header(self, _name, _value, **_params):
        parts = []
        if _value is not None:
            parts.append(_value)
        for k, v in _params.items():
            k = k.replace('_', '-')
            if v is None:
                parts.append(k)
            else:
                parts.append('%s="%s"' % (k, str(v).replace('"', '\\"')))
        self._headers.append((_name, "; ".join(parts)))

    def __str__(self):
        lines = []
        for k, v in self._headers:
            lines.append("%s: %s" % (k, v))
        lines.append("")
        lines.append("")
        return "\r\n".join(lines)

    def __bytes__(self):
        return str(self).encode("latin-1")


def wsgiref2_headers():
    """Invariant: Headers class works as expected."""
    h = Headers([("Content-Type", "text/plain")])
    if h["content-type"] != "text/plain":
        return False
    if h.get("Missing", "x") != "x":
        return False
    h["X-Test"] = "v1"
    if h["x-test"] != "v1":
        return False
    h.add_header("Set-Cookie", "a=b")
    h.add_header("Set-Cookie", "c=d")
    if h.get_all("set-cookie") != ["a=b", "c=d"]:
        return False
    if "X-Test" not in h:
        return False
    del h["x-test"]
    if "X-Test" in h:
        return False
    if len(h) != 3:
        return False
    rendered = str(h)
    if not rendered.endswith("\r\n\r\n"):
        return False
    return True


# ---------------------------------------------------------------------------
# Environ helpers
# ---------------------------------------------------------------------------

def _guess_scheme(environ):
    if environ.get("HTTPS") in ("on", "ON", "1", "yes"):
        return "https"
    return "http"


def setup_testing_defaults(environ):
    """Populate a CGI/WSGI environ dict with reasonable defaults for testing."""
    environ.setdefault("SERVER_NAME", "127.0.0.1")
    environ.setdefault("SERVER_PORT", "80")
    environ.setdefault("HTTP_HOST", "127.0.0.1")
    environ.setdefault("REMOTE_ADDR", "127.0.0.1")
    environ.setdefault("REQUEST_METHOD", "GET")
    environ.setdefault("SCRIPT_NAME", "")
    environ.setdefault("PATH_INFO", "/")
    environ.setdefault("SERVER_PROTOCOL", "HTTP/1.0")
    environ.setdefault("SERVER_SOFTWARE", "theseus_wsgiref_cr/1.0")

    environ.setdefault("wsgi.version", (1, 0))
    environ.setdefault("wsgi.url_scheme", _guess_scheme(environ))
    environ.setdefault("wsgi.input", io.BytesIO(b""))
    environ.setdefault("wsgi.errors", sys.stderr)
    environ.setdefault("wsgi.multithread", False)
    environ.setdefault("wsgi.multiprocess", True)
    environ.setdefault("wsgi.run_once", False)


def request_uri(environ, include_query=True):
    """Reconstruct the request URI from the WSGI environ."""
    url = environ["wsgi.url_scheme"] + "://"
    if environ.get("HTTP_HOST"):
        url += environ["HTTP_HOST"]
    else:
        url += environ["SERVER_NAME"]
        scheme = environ["wsgi.url_scheme"]
        port = environ.get("SERVER_PORT", "")
        if (scheme == "https" and port != "443") or \
           (scheme == "http" and port != "80"):
            if port:
                url += ":" + port
    url += _quote_path(environ.get("SCRIPT_NAME", ""))
    url += _quote_path(environ.get("PATH_INFO", ""))
    if include_query and environ.get("QUERY_STRING"):
        url += "?" + environ["QUERY_STRING"]
    return url


def application_uri(environ):
    """Return the WSGI application's base URI."""
    url = environ["wsgi.url_scheme"] + "://"
    if environ.get("HTTP_HOST"):
        url += environ["HTTP_HOST"]
    else:
        url += environ["SERVER_NAME"]
        scheme = environ["wsgi.url_scheme"]
        port = environ.get("SERVER_PORT", "")
        if (scheme == "https" and port != "443") or \
           (scheme == "http" and port != "80"):
            if port:
                url += ":" + port
    url += _quote_path(environ.get("SCRIPT_NAME", "")) or "/"
    return url


_SAFE_PATH_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "/-_.~!$&'()*+,;=:@"
)


def _quote_path(s):
    out = []
    for ch in s:
        if ch in _SAFE_PATH_CHARS:
            out.append(ch)
        else:
            for byte in ch.encode("utf-8"):
                out.append("%%%02X" % byte)
    return "".join(out)


def shift_path_info(environ):
    """Shift a single name from PATH_INFO to SCRIPT_NAME."""
    path_info = environ.get("PATH_INFO", "")
    if not path_info:
        return None
    path_parts = path_info.split("/")
    path_parts = [p for p in path_parts[1:] if p != ""]
    if not path_parts:
        environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + path_info
        environ["PATH_INFO"] = ""
        return ""
    name = path_parts[0]
    rest = path_parts[1:]
    script_name = environ.get("SCRIPT_NAME", "") + "/" + name
    environ["SCRIPT_NAME"] = script_name
    if rest:
        environ["PATH_INFO"] = "/" + "/".join(rest)
        if path_info.endswith("/"):
            environ["PATH_INFO"] += "/"
    elif path_info.endswith("/" + name + "/"):
        environ["PATH_INFO"] = "/"
    else:
        environ["PATH_INFO"] = ""
    return name


def wsgiref2_environ():
    """Invariant: environ helpers work as expected."""
    environ = {}
    setup_testing_defaults(environ)
    if environ["wsgi.version"] != (1, 0):
        return False
    if environ["wsgi.url_scheme"] != "http":
        return False
    if environ["REQUEST_METHOD"] != "GET":
        return False
    if environ["PATH_INFO"] != "/":
        return False

    e2 = {"HTTPS": "on"}
    setup_testing_defaults(e2)
    if e2["wsgi.url_scheme"] != "https":
        return False

    e3 = {
        "wsgi.url_scheme": "http",
        "HTTP_HOST": "example.com",
        "SCRIPT_NAME": "/app",
        "PATH_INFO": "/foo/bar",
        "QUERY_STRING": "x=1",
        "SERVER_NAME": "example.com",
        "SERVER_PORT": "80",
    }
    if request_uri(e3) != "http://example.com/app/foo/bar?x=1":
        return False
    if request_uri(e3, include_query=False) != "http://example.com/app/foo/bar":
        return False
    if application_uri(e3) != "http://example.com/app":
        return False

    e4 = {"PATH_INFO": "/a/b/c", "SCRIPT_NAME": ""}
    name = shift_path_info(e4)
    if name != "a":
        return False
    if e4["SCRIPT_NAME"] != "/a":
        return False
    if e4["PATH_INFO"] != "/b/c":
        return False
    return True


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class WSGIWarning(Warning):
    """Warning emitted by the validator when a WSGI app misbehaves."""


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _check_environ(environ):
    _assert(isinstance(environ, dict),
            "environ must be a dict, got %r" % type(environ))
    required = [
        "REQUEST_METHOD",
        "SERVER_NAME",
        "SERVER_PORT",
        "wsgi.version",
        "wsgi.input",
        "wsgi.errors",
        "wsgi.url_scheme",
    ]
    for key in required:
        _assert(key in environ, "environ missing required key %r" % key)
    _assert(environ["wsgi.url_scheme"] in ("http", "https"),
            "wsgi.url_scheme must be 'http' or 'https'")
    _assert(isinstance(environ["wsgi.version"], tuple) and
            len(environ["wsgi.version"]) == 2,
            "wsgi.version must be a 2-tuple")


def _check_status(status):
    _assert(isinstance(status, str), "Status must be a str, got %r" % type(status))
    _assert(len(status) >= 4, "Status must be at least 4 chars: %r" % status)
    code = status[:3]
    _assert(code.isdigit(), "Status code must be 3 digits: %r" % status)
    _assert(status[3] == " ", "Status must have a space after the code: %r" % status)
    _assert(int(code) >= 100, "Status code must be >= 100: %r" % status)


def _check_headers(headers):
    _assert(isinstance(headers, list),
            "Headers must be a list, got %r" % type(headers))
    for item in headers:
        _assert(isinstance(item, tuple) and len(item) == 2,
                "Each header must be a (name, value) tuple")
        name, value = item
        _assert(isinstance(name, str), "Header name must be str: %r" % name)
        _assert(isinstance(value, str), "Header value must be str: %r" % value)
        _assert(":" not in name and "\n" not in name,
                "Header name has illegal char: %r" % name)
        forbidden = {
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers",
            "transfer-encoding", "upgrade",
        }
        _assert(name.lower() not in forbidden,
                "Hop-by-hop header not allowed: %r" % name)


class _IteratorWrapper(object):
    def __init__(self, iterable, start_response_called):
        self._iterable = iter(iterable)
        self._original = iterable
        self._start_called = start_response_called
        self._closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed:
            raise AssertionError("Iterating over a closed body")
        if not self._start_called[0]:
            raise AssertionError(
                "The application returned data before start_response was called"
            )
        item = next(self._iterable)
        _assert(isinstance(item, (bytes, bytearray)),
                "Application yielded non-bytes value: %r" % type(item))
        return bytes(item)

    next = __next__  # legacy

    def close(self):
        self._closed = True
        closer = getattr(self._original, "close", None)
        if closer is not None:
            closer()


def validator(application):
    """Wrap a WSGI application with a strict validator."""

    def validating_app(environ, start_response):
        _check_environ(environ)
        _assert(callable(start_response),
                "start_response must be callable")

        start_called = [False]

        def checked_start_response(status, headers, exc_info=None):
            _check_status(status)
            _check_headers(headers)
            if exc_info is not None:
                _assert(isinstance(exc_info, tuple) and len(exc_info) == 3,
                        "exc_info must be a 3-tuple")
            start_called[0] = True
            # Forward to the actual start_response so the caller's side
            # effects (and the returned write callable) are preserved.
            real_write = start_response(status, headers, exc_info)

            def write(data):
                _assert(isinstance(data, (bytes, bytearray)),
                        "write() requires bytes, got %r" % type(data))
                if real_write is not None:
                    real_write(bytes(data))
            return write

        result = application(environ, checked_start_response)
        _assert(result is not None,
                "Application returned None instead of an iterable")
        try:
            iter(result)
        except TypeError:
            raise AssertionError("Application return value is not iterable")
        return _IteratorWrapper(result, start_called)

    return validating_app


def wsgiref2_validate():
    """Invariant: validator wraps and checks a WSGI app correctly."""

    def good_app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"hello"]

    environ = {}
    setup_testing_defaults(environ)
    captured = {}

    def sr(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = headers

    wrapped = validator(good_app)
    body = list(wrapped(environ, sr))
    if body != [b"hello"]:
        return False
    if captured.get("status") != "200 OK":
        return False

    def bad_status(environ, start_response):
        start_response(200, [("Content-Type", "text/plain")])
        return [b""]

    try:
        list(validator(bad_status)(dict(environ), sr))
    except AssertionError:
        pass
    else:
        return False

    def bad_header(environ, start_response):
        start_response("200 OK", [("Content-Type", 123)])
        return [b""]

    try:
        list(validator(bad_header)(dict(environ), sr))
    except AssertionError:
        pass
    else:
        return False

    def bad_yield(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return ["not bytes"]

    try:
        list(validator(bad_yield)(dict(environ), sr))
    except AssertionError:
        pass
    else:
        return False

    def env_app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b""]

    try:
        validator(env_app)({}, sr)
    except AssertionError:
        pass
    else:
        return False

    def hop_app(environ, start_response):
        start_response("200 OK", [("Connection", "close")])
        return [b""]

    try:
        list(validator(hop_app)(dict(environ), sr))
    except AssertionError:
        pass
    else:
        return False

    return True


__all__ = [
    "Headers",
    "setup_testing_defaults",
    "request_uri",
    "application_uri",
    "shift_path_info",
    "validator",
    "WSGIWarning",
    "wsgiref2_headers",
    "wsgiref2_environ",
    "wsgiref2_validate",
]