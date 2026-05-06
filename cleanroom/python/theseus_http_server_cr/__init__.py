"""Clean-room implementation of a minimal http.server-like module.

This module provides:
  - HTTP status code/phrase mappings (responses)
  - A BaseHTTPRequestHandler class
  - Request line parsing

Implemented from scratch using only the Python standard library.
"""

import socket
import sys
import io


# --- HTTP status codes and reason phrases -----------------------------------

responses = {
    100: ("Continue", "Request received, please continue"),
    101: ("Switching Protocols",
          "Switching to new protocol; obey Upgrade header"),

    200: ("OK", "Request fulfilled, document follows"),
    201: ("Created", "Document created, URL follows"),
    202: ("Accepted", "Request accepted, processing continues off-line"),
    203: ("Non-Authoritative Information", "Request fulfilled from cache"),
    204: ("No Content", "Request fulfilled, nothing follows"),
    205: ("Reset Content", "Clear input form for further input."),
    206: ("Partial Content", "Partial content follows."),

    300: ("Multiple Choices", "Object has several resources -- see URI list"),
    301: ("Moved Permanently", "Object moved permanently -- see URI list"),
    302: ("Found", "Object moved temporarily -- see URI list"),
    303: ("See Other", "Object moved -- see Method and URL list"),
    304: ("Not Modified", "Document has not changed since given time"),
    305: ("Use Proxy",
          "You must use proxy specified in Location to access this resource."),
    307: ("Temporary Redirect",
          "Object moved temporarily -- see URI list"),

    400: ("Bad Request", "Bad request syntax or unsupported method"),
    401: ("Unauthorized",
          "No permission -- see authorization schemes"),
    402: ("Payment Required",
          "No payment -- see charging schemes"),
    403: ("Forbidden",
          "Request forbidden -- authorization will not help"),
    404: ("Not Found", "Nothing matches the given URI"),
    405: ("Method Not Allowed",
          "Specified method is invalid for this resource."),
    406: ("Not Acceptable", "URI not available in preferred format."),
    407: ("Proxy Authentication Required", "You must authenticate with "
          "this proxy before proceeding."),
    408: ("Request Timeout", "Request timed out; try again later."),
    409: ("Conflict", "Request conflict."),
    410: ("Gone",
          "URI no longer exists and has been permanently removed."),
    411: ("Length Required", "Client must specify Content-Length."),
    412: ("Precondition Failed", "Precondition in headers is false."),
    413: ("Request Entity Too Large", "Entity is too large."),
    414: ("Request-URI Too Long", "URI is too long."),
    415: ("Unsupported Media Type", "Entity body in unsupported format."),
    416: ("Requested Range Not Satisfiable",
          "Cannot satisfy request range."),
    417: ("Expectation Failed",
          "Expect condition could not be satisfied."),

    500: ("Internal Server Error", "Server got itself in trouble"),
    501: ("Not Implemented",
          "Server does not support this operation"),
    502: ("Bad Gateway", "Invalid responses from another server/proxy."),
    503: ("Service Unavailable",
          "The server cannot process the request due to a high load"),
    504: ("Gateway Timeout",
          "The gateway server did not receive a timely response"),
    505: ("HTTP Version Not Supported", "Cannot fulfill request."),
}


# --- Request handler --------------------------------------------------------

class HTTPError(Exception):
    """Base error for HTTP handling problems."""
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or responses.get(code, ("Error",))[0]
        super().__init__("%d %s" % (self.code, self.message))


def _parse_request_line(line):
    """Parse a single HTTP request line.

    Returns (method, path, version) tuple on success, or raises ValueError.
    """
    if isinstance(line, bytes):
        line = line.decode("iso-8859-1")
    line = line.rstrip("\r\n")
    parts = line.split()
    if len(parts) == 3:
        method, path, version = parts
    elif len(parts) == 2:
        method, path = parts
        version = "HTTP/0.9"
    else:
        raise ValueError("Bad request syntax: %r" % line)
    if not version.startswith("HTTP/"):
        raise ValueError("Bad HTTP version: %r" % version)
    return method, path, version


class BaseHTTPRequestHandler(object):
    """Minimal HTTP request handler skeleton.

    Subclasses implement do_GET, do_POST, etc.
    """

    server_version = "TheseusHTTP/0.1"
    sys_version = "Python/%d.%d" % (sys.version_info[0], sys.version_info[1])
    protocol_version = "HTTP/1.0"
    default_request_version = "HTTP/0.9"

    # MessageClass = SimpleNamespace would be the equivalent of email.message
    # but we provide a tiny header dict instead.

    def __init__(self, request=None, client_address=None, server=None):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.command = None
        self.path = None
        self.request_version = None
        self.headers = {}
        self.rfile = None
        self.wfile = None
        self.close_connection = True
        self.requestline = ""

    # -- Parsing -----------------------------------------------------------

    def parse_request(self):
        """Parse the request line and headers from self.rfile.

        Sets self.command, self.path, self.request_version, self.headers.
        Returns True on success, False on failure (after sending an error).
        """
        self.command = None
        self.request_version = version = self.default_request_version
        self.close_connection = True
        requestline = self.rfile.readline(65537)
        if len(requestline) > 65536:
            self.send_error(414)
            return False
        if not requestline:
            return False
        if isinstance(requestline, bytes):
            requestline = requestline.decode("iso-8859-1")
        requestline = requestline.rstrip("\r\n")
        self.requestline = requestline

        try:
            method, path, version = _parse_request_line(requestline)
        except ValueError:
            self.send_error(400, "Bad request syntax (%r)" % requestline)
            return False

        # Extract major/minor version
        try:
            base_version_number = version.split("/", 1)[1]
            version_number = base_version_number.split(".")
            if len(version_number) != 2:
                raise ValueError
            version_number = int(version_number[0]), int(version_number[1])
        except (ValueError, IndexError):
            self.send_error(400, "Bad request version (%r)" % version)
            return False

        if version_number >= (1, 1):
            self.close_connection = False
        if version_number >= (2, 0):
            self.send_error(505,
                            "Invalid HTTP version (%s)" % base_version_number)
            return False

        self.command, self.path, self.request_version = method, path, version

        # Parse headers
        headers = {}
        while True:
            line = self.rfile.readline(65537)
            if len(line) > 65536:
                self.send_error(431)
                return False
            if not line:
                break
            if isinstance(line, bytes):
                line = line.decode("iso-8859-1")
            line = line.rstrip("\r\n")
            if line == "":
                break
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip().lower()] = value.strip()
            else:
                # Continuation lines or malformed: ignore for simplicity
                pass
        self.headers = headers

        conntype = headers.get("connection", "").lower()
        if conntype == "close":
            self.close_connection = True
        elif conntype == "keep-alive" and version_number >= (1, 1):
            self.close_connection = False
        return True

    # -- Response helpers --------------------------------------------------

    def send_response(self, code, message=None):
        if message is None:
            if code in responses:
                message = responses[code][0]
            else:
                message = ""
        line = "%s %d %s\r\n" % (self.protocol_version, code, message)
        self.wfile.write(line.encode("iso-8859-1"))
        self.send_header("Server", self.version_string())

    def send_header(self, keyword, value):
        line = "%s: %s\r\n" % (keyword, value)
        self.wfile.write(line.encode("iso-8859-1"))

    def end_headers(self):
        self.wfile.write(b"\r\n")

    def send_error(self, code, message=None):
        try:
            short, longmsg = responses.get(code, ("???", "???"))
        except Exception:
            short, longmsg = "???", "???"
        if message is None:
            message = short
        body = ("Error %d: %s\r\n%s\r\n" % (code, message, longmsg)).encode(
            "utf-8")
        if self.wfile is not None:
            self.send_response(code, message)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

    def version_string(self):
        return "%s %s" % (self.server_version, self.sys_version)

    # -- Dispatcher --------------------------------------------------------

    def handle_one_request(self):
        if not self.parse_request():
            return
        mname = "do_" + (self.command or "")
        if not hasattr(self, mname):
            self.send_error(501, "Unsupported method (%r)" % self.command)
            return
        method = getattr(self, mname)
        method()

    def handle(self):
        self.close_connection = False
        while not self.close_connection:
            self.handle_one_request()


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """A trivial echo handler used for testing."""

    def do_GET(self):
        body = ("Hello from %s\r\nPath: %s\r\n" %
                (self.server_version, self.path)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# --- Tiny server (single-threaded, used only for completeness) --------------

class HTTPServer(object):
    def __init__(self, server_address, RequestHandlerClass):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def server_bind(self):
        self.socket.bind(self.server_address)

    def server_activate(self, backlog=5):
        self.socket.listen(backlog)

    def serve_forever(self):
        while True:
            conn, addr = self.socket.accept()
            try:
                rfile = conn.makefile("rb", buffering=0)
                wfile = conn.makefile("wb", buffering=0)
                handler = self.RequestHandlerClass()
                handler.rfile = rfile
                handler.wfile = wfile
                handler.client_address = addr
                handler.server = self
                handler.handle()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass


# --- Invariant-required predicate functions ---------------------------------

def http_server2_responses():
    """True iff the responses table is well-formed.

    Checks that common HTTP status codes are present, that values are
    (short, long) tuples of strings, and that 200 maps to "OK".
    """
    if not isinstance(responses, dict):
        return False
    required_codes = (200, 301, 400, 403, 404, 500)
    for code in required_codes:
        if code not in responses:
            return False
        entry = responses[code]
        if not (isinstance(entry, tuple) and len(entry) == 2):
            return False
        short, longmsg = entry
        if not (isinstance(short, str) and isinstance(longmsg, str)):
            return False
        if not short:
            return False
    if responses[200][0] != "OK":
        return False
    if responses[404][0] != "Not Found":
        return False
    return True


def http_server2_handler_exists():
    """True iff BaseHTTPRequestHandler is defined and usable."""
    if not isinstance(BaseHTTPRequestHandler, type):
        return False
    # Must have the standard method names
    required = ("parse_request", "send_response", "send_header",
                "end_headers", "send_error", "handle_one_request",
                "version_string")
    for name in required:
        if not hasattr(BaseHTTPRequestHandler, name):
            return False
        if not callable(getattr(BaseHTTPRequestHandler, name)):
            return False
    # Verify we can construct an instance
    try:
        h = BaseHTTPRequestHandler()
    except Exception:
        return False
    if not isinstance(h, BaseHTTPRequestHandler):
        return False
    return True


def http_server2_parse_request():
    """True iff parse_request correctly extracts method/path/version.

    Exercises the parser with a synthetic request stream and checks that
    fields are populated as expected.
    """
    request_bytes = (
        b"GET /index.html HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"User-Agent: theseus-test/1.0\r\n"
        b"Connection: close\r\n"
        b"\r\n"
    )
    handler = BaseHTTPRequestHandler()
    handler.rfile = io.BytesIO(request_bytes)
    handler.wfile = io.BytesIO()
    ok = handler.parse_request()
    if not ok:
        return False
    if handler.command != "GET":
        return False
    if handler.path != "/index.html":
        return False
    if handler.request_version != "HTTP/1.1":
        return False
    if handler.headers.get("host") != "example.com":
        return False
    if handler.headers.get("connection") != "close":
        return False
    if handler.close_connection is not True:
        return False

    # Also exercise the standalone parser
    try:
        m, p, v = _parse_request_line("POST /submit HTTP/1.0\r\n")
    except Exception:
        return False
    if (m, p, v) != ("POST", "/submit", "HTTP/1.0"):
        return False

    # Bad request line should raise
    try:
        _parse_request_line("nonsense")
        return False
    except ValueError:
        pass

    return True


__all__ = [
    "responses",
    "BaseHTTPRequestHandler",
    "SimpleHTTPRequestHandler",
    "HTTPServer",
    "HTTPError",
    "http_server2_responses",
    "http_server2_handler_exists",
    "http_server2_parse_request",
]