from enum import Enum


class HTTPStatus(Enum):
    # 1xx Informational
    CONTINUE = (100, 'Continue')
    SWITCHING_PROTOCOLS = (101, 'Switching Protocols')
    PROCESSING = (102, 'Processing')
    EARLY_HINTS = (103, 'Early Hints')

    # 2xx Success
    OK = (200, 'OK')
    CREATED = (201, 'Created')
    ACCEPTED = (202, 'Accepted')
    NON_AUTHORITATIVE_INFORMATION = (203, 'Non-Authoritative Information')
    NO_CONTENT = (204, 'No Content')
    RESET_CONTENT = (205, 'Reset Content')
    PARTIAL_CONTENT = (206, 'Partial Content')
    MULTI_STATUS = (207, 'Multi-Status')
    ALREADY_REPORTED = (208, 'Already Reported')
    IM_USED = (226, 'IM Used')

    # 3xx Redirection
    MULTIPLE_CHOICES = (300, 'Multiple Choices')
    MOVED_PERMANENTLY = (301, 'Moved Permanently')
    FOUND = (302, 'Found')
    SEE_OTHER = (303, 'See Other')
    NOT_MODIFIED = (304, 'Not Modified')
    USE_PROXY = (305, 'Use Proxy')
    TEMPORARY_REDIRECT = (307, 'Temporary Redirect')
    PERMANENT_REDIRECT = (308, 'Permanent Redirect')

    # 4xx Client Errors
    BAD_REQUEST = (400, 'Bad Request')
    UNAUTHORIZED = (401, 'Unauthorized')
    PAYMENT_REQUIRED = (402, 'Payment Required')
    FORBIDDEN = (403, 'Forbidden')
    NOT_FOUND = (404, 'Not Found')
    METHOD_NOT_ALLOWED = (405, 'Method Not Allowed')
    NOT_ACCEPTABLE = (406, 'Not Acceptable')
    PROXY_AUTHENTICATION_REQUIRED = (407, 'Proxy Authentication Required')
    REQUEST_TIMEOUT = (408, 'Request Timeout')
    CONFLICT = (409, 'Conflict')
    GONE = (410, 'Gone')
    LENGTH_REQUIRED = (411, 'Length Required')
    PRECONDITION_FAILED = (412, 'Precondition Failed')
    REQUEST_ENTITY_TOO_LARGE = (413, 'Request Entity Too Large')
    REQUEST_URI_TOO_LONG = (414, 'Request-URI Too Long')
    UNSUPPORTED_MEDIA_TYPE = (415, 'Unsupported Media Type')
    REQUESTED_RANGE_NOT_SATISFIABLE = (416, 'Requested Range Not Satisfiable')
    EXPECTATION_FAILED = (417, 'Expectation Failed')
    IM_A_TEAPOT = (418, "I'm a Teapot")
    MISDIRECTED_REQUEST = (421, 'Misdirected Request')
    UNPROCESSABLE_ENTITY = (422, 'Unprocessable Entity')
    LOCKED = (423, 'Locked')
    FAILED_DEPENDENCY = (424, 'Failed Dependency')
    TOO_EARLY = (425, 'Too Early')
    UPGRADE_REQUIRED = (426, 'Upgrade Required')
    PRECONDITION_REQUIRED = (428, 'Precondition Required')
    TOO_MANY_REQUESTS = (429, 'Too Many Requests')
    REQUEST_HEADER_FIELDS_TOO_LARGE = (431, 'Request Header Fields Too Large')
    UNAVAILABLE_FOR_LEGAL_REASONS = (451, 'Unavailable For Legal Reasons')

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = (500, 'Internal Server Error')
    NOT_IMPLEMENTED = (501, 'Not Implemented')
    BAD_GATEWAY = (502, 'Bad Gateway')
    SERVICE_UNAVAILABLE = (503, 'Service Unavailable')
    GATEWAY_TIMEOUT = (504, 'Gateway Timeout')
    HTTP_VERSION_NOT_SUPPORTED = (505, 'HTTP Version Not Supported')
    VARIANT_ALSO_NEGOTIATES = (506, 'Variant Also Negotiates')
    INSUFFICIENT_STORAGE = (507, 'Insufficient Storage')
    LOOP_DETECTED = (508, 'Loop Detected')
    NOT_EXTENDED = (510, 'Not Extended')
    NETWORK_AUTHENTICATION_REQUIRED = (511, 'Network Authentication Required')

    def __new__(cls, value, phrase):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.phrase = phrase
        return obj

    @property
    def value(self):
        return self._value_

    def __int__(self):
        return self._value_

    def __str__(self):
        return f'{self._value_} {self.phrase}'


def http_client_ok_value() -> int:
    """Return the integer value of HTTPStatus.OK (200)."""
    return HTTPStatus.OK.value


def http_client_not_found_phrase() -> str:
    """Return the phrase for HTTPStatus.NOT_FOUND ('Not Found')."""
    return HTTPStatus.NOT_FOUND.phrase


def http_client_is_success() -> bool:
    """Return True if HTTPStatus.OK is a success status (200-299)."""
    return 200 <= HTTPStatus.OK.value < 300


# Integer status code constants
OK = 200
CREATED = 201
NO_CONTENT = 204
MOVED_PERMANENTLY = 301
FOUND = 302
NOT_MODIFIED = 304
BAD_REQUEST = 400
UNAUTHORIZED = 401
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
INTERNAL_SERVER_ERROR = 500
NOT_IMPLEMENTED = 501
BAD_GATEWAY = 502
SERVICE_UNAVAILABLE = 503

responses = {s.value: s.phrase for s in HTTPStatus}

HTTP_PORT = 80
HTTPS_PORT = 443
HTTP_11 = 'HTTP/1.1'
HTTP_10 = 'HTTP/1.0'


class HTTPException(Exception):
    pass


class NotConnected(HTTPException):
    pass


class InvalidURL(HTTPException):
    pass


class RemoteDisconnected(HTTPException):
    pass


class CannotSendRequest(HTTPException):
    pass


class CannotSendHeader(HTTPException):
    pass


class ResponseNotReady(HTTPException):
    pass


class BadStatusLine(HTTPException):
    pass


class ImproperConnectionState(HTTPException):
    pass


class IncompleteRead(HTTPException):
    def __init__(self, partial, expected=None):
        self.partial = partial
        self.expected = expected
        super().__init__(f"IncompleteRead ({len(partial)} bytes read)")


import socket as _socket
import io as _io


class HTTPMessage:
    def __init__(self, headers=None):
        self._headers = headers or {}

    def get(self, name, default=None):
        return self._headers.get(name.lower(), default)

    def __getitem__(self, name):
        return self._headers[name.lower()]

    def __contains__(self, name):
        return name.lower() in self._headers

    def items(self):
        return self._headers.items()


class HTTPResponse:
    def __init__(self, sock, debuglevel=0, method=None, url=None):
        self.fp = sock.makefile('rb')
        self.debuglevel = debuglevel
        self._method = method
        self.status = None
        self.reason = None
        self.version = None
        self.headers = None
        self.will_close = True
        self.chunked = False
        self.chunk_left = None
        self.length = None

    def begin(self):
        line = self.fp.readline(65536).decode('iso-8859-1')
        line = line.rstrip('\r\n')
        try:
            version, status, reason = line.split(None, 2)
        except ValueError:
            try:
                version, status = line.split(None, 1)
                reason = ''
            except ValueError:
                raise BadStatusLine(line)
        try:
            self.status = int(status)
        except ValueError:
            raise BadStatusLine(line)
        self.reason = reason.strip()
        if version in ('HTTP/1.0', 'HTTP/0.9'):
            self.version = 10
        elif version.startswith('HTTP/1.'):
            self.version = 11
        else:
            self.version = 10
        self.headers = self._parse_headers()

    def _parse_headers(self):
        headers = {}
        while True:
            line = self.fp.readline(65536).decode('iso-8859-1').rstrip('\r\n')
            if not line:
                break
            if ':' in line:
                key, _, value = line.partition(':')
                headers[key.lower().strip()] = value.strip()
        return HTTPMessage(headers)

    def read(self, amt=None):
        if self.fp is None:
            return b''
        if amt is not None:
            return self.fp.read(amt)
        return self.fp.read()

    def readinto(self, b):
        return self.fp.readinto(b)

    def getheader(self, name, default=None):
        if self.headers is None:
            raise ResponseNotReady()
        return self.headers.get(name, default)

    def getheaders(self):
        if self.headers is None:
            return []
        return list(self.headers.items())

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    def isclosed(self):
        return self.fp is None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class HTTPConnection:
    default_port = HTTP_PORT
    response_class = HTTPResponse
    http_vsn = 11
    http_vsn_str = 'HTTP/1.1'

    def __init__(self, host, port=None, timeout=_socket._GLOBAL_DEFAULT_TIMEOUT,
                 source_address=None, blocksize=8192):
        if port is None:
            port = self.default_port
            if ':' in host:
                host, _, port_str = host.rpartition(':')
                try:
                    port = int(port_str)
                except ValueError:
                    pass
        self.host = host
        self.port = port
        self.timeout = timeout
        self.source_address = source_address
        self.blocksize = blocksize
        self.sock = None
        self._buffer = []
        self._response = None
        self._HTTPConnection__state = 'idle'

    def set_debuglevel(self, level):
        self.debuglevel = level

    def connect(self):
        self.sock = _socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address
        )

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, data):
        if not self.sock:
            self.connect()
        if isinstance(data, str):
            data = data.encode('latin-1')
        self.sock.sendall(data)

    def _send_request(self, method, url, body, headers):
        request = f'{method} {url} {self.http_vsn_str}\r\n'
        for k, v in headers.items():
            request += f'{k}: {v}\r\n'
        request += '\r\n'
        if body:
            if isinstance(body, str):
                body = body.encode('latin-1')
            self.send(request.encode('latin-1') + body)
        else:
            self.send(request.encode('latin-1'))

    def request(self, method, url, body=None, headers=None):
        if headers is None:
            headers = {}
        if 'Host' not in headers and 'host' not in headers:
            headers['Host'] = self.host
        if 'Accept-Encoding' not in headers:
            headers['Accept-Encoding'] = 'identity'
        if body is not None and 'Content-Length' not in headers:
            if isinstance(body, (bytes, bytearray)):
                headers['Content-Length'] = str(len(body))
            elif isinstance(body, str):
                body_bytes = body.encode('latin-1')
                headers['Content-Length'] = str(len(body_bytes))
                body = body_bytes
        self._send_request(method, url, body, headers)

    def getresponse(self):
        if not self.sock:
            raise NotConnected()
        response = self.response_class(self.sock)
        response.begin()
        return response

    def set_tunnel(self, host, port=None, headers=None):
        self._tunnel_host = host
        self._tunnel_port = port
        self._tunnel_headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# New invariant functions matching the cleanroom spec
# ---------------------------------------------------------------------------

def httpclient2_constants():
    """HTTP status constants exist (OK=200, NOT_FOUND=404); returns True."""
    return OK == 200 and NOT_FOUND == 404 and INTERNAL_SERVER_ERROR == 500


def httpclient2_responses():
    """responses dict maps status codes to descriptions; returns True."""
    return (isinstance(responses, dict) and
            responses.get(200) == 'OK' and
            responses.get(404) == 'Not Found')


def httpclient2_classes():
    """HTTPConnection and HTTPResponse classes exist; returns True."""
    return (isinstance(HTTPConnection, type) and
            isinstance(HTTPResponse, type) and
            HTTPConnection.__name__ == 'HTTPConnection')