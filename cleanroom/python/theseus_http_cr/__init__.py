"""Clean-room reimplementation of a small subset of Python's http module.

Provides HTTP status codes, HTTP methods, and category classification
without importing the standard-library ``http`` package.
"""

# ---------------------------------------------------------------------------
# HTTP status codes
# ---------------------------------------------------------------------------

# (value, name, phrase, description)
_STATUS_TABLE = [
    # 1xx Informational
    (100, "CONTINUE", "Continue",
     "Request received, please continue"),
    (101, "SWITCHING_PROTOCOLS", "Switching Protocols",
     "Switching to new protocol; obey Upgrade header"),
    (102, "PROCESSING", "Processing", ""),
    (103, "EARLY_HINTS", "Early Hints", ""),

    # 2xx Success
    (200, "OK", "OK", "Request fulfilled, document follows"),
    (201, "CREATED", "Created", "Document created, URL follows"),
    (202, "ACCEPTED", "Accepted",
     "Request accepted, processing continues off-line"),
    (203, "NON_AUTHORITATIVE_INFORMATION", "Non-Authoritative Information",
     "Request fulfilled from cache"),
    (204, "NO_CONTENT", "No Content", "Request fulfilled, nothing follows"),
    (205, "RESET_CONTENT", "Reset Content", "Clear input form for further input"),
    (206, "PARTIAL_CONTENT", "Partial Content", "Partial content follows"),
    (207, "MULTI_STATUS", "Multi-Status", ""),
    (208, "ALREADY_REPORTED", "Already Reported", ""),
    (226, "IM_USED", "IM Used", ""),

    # 3xx Redirection
    (300, "MULTIPLE_CHOICES", "Multiple Choices",
     "Object has several resources -- see URI list"),
    (301, "MOVED_PERMANENTLY", "Moved Permanently",
     "Object moved permanently -- see URI list"),
    (302, "FOUND", "Found", "Object moved temporarily -- see URI list"),
    (303, "SEE_OTHER", "See Other", "Object moved -- see Method and URL list"),
    (304, "NOT_MODIFIED", "Not Modified",
     "Document has not changed since given time"),
    (305, "USE_PROXY", "Use Proxy",
     "You must use proxy specified in Location to access this resource"),
    (307, "TEMPORARY_REDIRECT", "Temporary Redirect",
     "Object moved temporarily -- see URI list"),
    (308, "PERMANENT_REDIRECT", "Permanent Redirect",
     "Object moved permanently -- see URI list"),

    # 4xx Client Error
    (400, "BAD_REQUEST", "Bad Request",
     "Bad request syntax or unsupported method"),
    (401, "UNAUTHORIZED", "Unauthorized",
     "No permission -- see authorization schemes"),
    (402, "PAYMENT_REQUIRED", "Payment Required",
     "No payment -- see charging schemes"),
    (403, "FORBIDDEN", "Forbidden",
     "Request forbidden -- authorization will not help"),
    (404, "NOT_FOUND", "Not Found", "Nothing matches the given URI"),
    (405, "METHOD_NOT_ALLOWED", "Method Not Allowed",
     "Specified method is invalid for this resource"),
    (406, "NOT_ACCEPTABLE", "Not Acceptable",
     "URI not available in preferred format"),
    (407, "PROXY_AUTHENTICATION_REQUIRED", "Proxy Authentication Required",
     "You must authenticate with this proxy before proceeding"),
    (408, "REQUEST_TIMEOUT", "Request Timeout",
     "Request timed out; try again later"),
    (409, "CONFLICT", "Conflict", "Request conflict"),
    (410, "GONE", "Gone",
     "URI no longer exists and has been permanently removed"),
    (411, "LENGTH_REQUIRED", "Length Required",
     "Client must specify Content-Length"),
    (412, "PRECONDITION_FAILED", "Precondition Failed",
     "Precondition in headers is false"),
    (413, "REQUEST_ENTITY_TOO_LARGE", "Request Entity Too Large",
     "Entity is too large"),
    (414, "REQUEST_URI_TOO_LONG", "Request-URI Too Long",
     "URI is too long"),
    (415, "UNSUPPORTED_MEDIA_TYPE", "Unsupported Media Type",
     "Entity body in unsupported format"),
    (416, "REQUESTED_RANGE_NOT_SATISFIABLE",
     "Requested Range Not Satisfiable",
     "Cannot satisfy request range"),
    (417, "EXPECTATION_FAILED", "Expectation Failed",
     "Expect condition could not be satisfied"),
    (418, "IM_A_TEAPOT", "I'm a Teapot",
     "Server refuses to brew coffee because it is a teapot."),
    (421, "MISDIRECTED_REQUEST", "Misdirected Request",
     "Server is not able to produce a response"),
    (422, "UNPROCESSABLE_ENTITY", "Unprocessable Entity", ""),
    (423, "LOCKED", "Locked", ""),
    (424, "FAILED_DEPENDENCY", "Failed Dependency", ""),
    (425, "TOO_EARLY", "Too Early", ""),
    (426, "UPGRADE_REQUIRED", "Upgrade Required", ""),
    (428, "PRECONDITION_REQUIRED", "Precondition Required",
     "The origin server requires the request to be conditional"),
    (429, "TOO_MANY_REQUESTS", "Too Many Requests",
     "The user has sent too many requests in a given amount of time"),
    (431, "REQUEST_HEADER_FIELDS_TOO_LARGE",
     "Request Header Fields Too Large",
     "The server is unwilling to process the request because its header "
     "fields are too large"),
    (451, "UNAVAILABLE_FOR_LEGAL_REASONS", "Unavailable For Legal Reasons",
     "The server is denying access to the resource as a consequence of a "
     "legal demand"),

    # 5xx Server Error
    (500, "INTERNAL_SERVER_ERROR", "Internal Server Error",
     "Server got itself in trouble"),
    (501, "NOT_IMPLEMENTED", "Not Implemented",
     "Server does not support this operation"),
    (502, "BAD_GATEWAY", "Bad Gateway",
     "Invalid responses from another server/proxy"),
    (503, "SERVICE_UNAVAILABLE", "Service Unavailable",
     "The server cannot process the request due to a high load"),
    (504, "GATEWAY_TIMEOUT", "Gateway Timeout",
     "The gateway server did not receive a timely response"),
    (505, "HTTP_VERSION_NOT_SUPPORTED", "HTTP Version Not Supported",
     "Cannot fulfill request"),
    (506, "VARIANT_ALSO_NEGOTIATES", "Variant Also Negotiates", ""),
    (507, "INSUFFICIENT_STORAGE", "Insufficient Storage", ""),
    (508, "LOOP_DETECTED", "Loop Detected", ""),
    (510, "NOT_EXTENDED", "Not Extended", ""),
    (511, "NETWORK_AUTHENTICATION_REQUIRED",
     "Network Authentication Required",
     "The client needs to authenticate to gain network access"),
]


class _HTTPStatusMember(int):
    """Single HTTP status code, behaves like an int."""

    # Note: ``int`` does not allow non-empty ``__slots__`` on subclasses,
    # so we rely on the default per-instance ``__dict__``.

    def __new__(cls, value, name, phrase, description):
        obj = int.__new__(cls, value)
        obj._name_ = name
        obj.phrase = phrase
        obj.description = description
        return obj

    @property
    def value(self):
        return int(self)

    @property
    def name(self):
        return self._name_

    @property
    def is_informational(self):
        return 100 <= int(self) < 200

    @property
    def is_success(self):
        return 200 <= int(self) < 300

    @property
    def is_redirection(self):
        return 300 <= int(self) < 400

    @property
    def is_client_error(self):
        return 400 <= int(self) < 500

    @property
    def is_server_error(self):
        return 500 <= int(self) < 600

    def __repr__(self):
        return "<HTTPStatus.%s: %d>" % (self._name_, int(self))

    def __str__(self):
        return "HTTPStatus.%s" % (self._name_,)


class _HTTPStatusMeta(type):
    """Metaclass that lets HTTPStatus(value) act like an enum lookup."""

    def __call__(cls, value):
        # Lookup by integer value.
        if isinstance(value, _HTTPStatusMember):
            return value
        member = cls._value2member_.get(int(value))
        if member is None:
            raise ValueError("%d is not a valid HTTPStatus" % int(value))
        return member

    def __iter__(cls):
        return iter(cls._members_)

    def __len__(cls):
        return len(cls._members_)

    def __contains__(cls, item):
        if isinstance(item, _HTTPStatusMember):
            return item in cls._members_
        try:
            return int(item) in cls._value2member_
        except (TypeError, ValueError):
            return False

    def __getitem__(cls, name):
        try:
            return cls._name2member_[name]
        except KeyError:
            raise KeyError(name)


class HTTPStatus(metaclass=_HTTPStatusMeta):
    """HTTP status codes, modelled on http.HTTPStatus."""

    _members_ = []
    _value2member_ = {}
    _name2member_ = {}


def _build_status_members():
    for value, name, phrase, description in _STATUS_TABLE:
        member = _HTTPStatusMember(value, name, phrase, description)
        HTTPStatus._members_.append(member)
        HTTPStatus._value2member_[value] = member
        HTTPStatus._name2member_[name] = member
        setattr(HTTPStatus, name, member)


_build_status_members()


# ---------------------------------------------------------------------------
# HTTP methods
# ---------------------------------------------------------------------------

_METHOD_TABLE = [
    ("CONNECT", "Establish a tunnel to the server"),
    ("DELETE", "Remove the target resource"),
    ("GET", "Retrieve the target"),
    ("HEAD", "Same as GET, but only transfer the status line and header"),
    ("OPTIONS", "Describe the communication options for the target resource"),
    ("PATCH", "Apply partial modifications to a resource"),
    ("POST",
     "Perform resource-specific processing on the request payload"),
    ("PUT", "Replace the target resource with the request payload"),
    ("TRACE", "Perform a message loop-back test along the path to the target"),
]


class _HTTPMethodMember(str):
    """Single HTTP method, behaves like a str."""

    # Note: ``str`` likewise does not allow non-empty ``__slots__`` on
    # subclasses, so we rely on the default per-instance ``__dict__``.

    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._name_ = value
        obj.description = description
        return obj

    @property
    def value(self):
        return str.__str__(self)

    @property
    def name(self):
        return self._name_

    def __repr__(self):
        return "<HTTPMethod.%s>" % (self._name_,)


class _HTTPMethodMeta(type):

    def __call__(cls, value):
        if isinstance(value, _HTTPMethodMember):
            return value
        member = cls._value2member_.get(value)
        if member is None:
            raise ValueError("%r is not a valid HTTPMethod" % (value,))
        return member

    def __iter__(cls):
        return iter(cls._members_)

    def __len__(cls):
        return len(cls._members_)

    def __contains__(cls, item):
        if isinstance(item, _HTTPMethodMember):
            return item in cls._members_
        return item in cls._value2member_

    def __getitem__(cls, name):
        return cls._name2member_[name]


class HTTPMethod(metaclass=_HTTPMethodMeta):
    """HTTP methods, modelled on http.HTTPMethod."""

    _members_ = []
    _value2member_ = {}
    _name2member_ = {}


def _build_method_members():
    for name, description in _METHOD_TABLE:
        member = _HTTPMethodMember(name, description)
        HTTPMethod._members_.append(member)
        HTTPMethod._value2member_[name] = member
        HTTPMethod._name2member_[name] = member
        setattr(HTTPMethod, name, member)


_build_method_members()


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def status_category(code):
    """Return the textual category of an HTTP status code."""
    code = int(code)
    if 100 <= code < 200:
        return "informational"
    if 200 <= code < 300:
        return "success"
    if 300 <= code < 400:
        return "redirection"
    if 400 <= code < 500:
        return "client_error"
    if 500 <= code < 600:
        return "server_error"
    raise ValueError("%d is not a valid HTTP status code" % code)


# ---------------------------------------------------------------------------
# Required invariant functions
# ---------------------------------------------------------------------------

def http2_status():
    """Verify the HTTPStatus implementation."""
    # Common codes are present and have the correct value.
    expected = {
        "OK": 200,
        "CREATED": 201,
        "NO_CONTENT": 204,
        "MOVED_PERMANENTLY": 301,
        "FOUND": 302,
        "NOT_MODIFIED": 304,
        "BAD_REQUEST": 400,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "IM_A_TEAPOT": 418,
        "INTERNAL_SERVER_ERROR": 500,
        "NOT_IMPLEMENTED": 501,
        "BAD_GATEWAY": 502,
        "SERVICE_UNAVAILABLE": 503,
    }
    for name, value in expected.items():
        member = getattr(HTTPStatus, name, None)
        if member is None:
            return False
        if int(member) != value:
            return False
        if member.name != name:
            return False
        if member.value != value:
            return False
        if not member.phrase:
            # Phrase should be a non-empty human-readable string.
            return False

    # Lookup by value.
    if HTTPStatus(200) is not HTTPStatus.OK:
        return False
    if HTTPStatus(404).name != "NOT_FOUND":
        return False

    # Lookup by name (subscript).
    if HTTPStatus["OK"] is not HTTPStatus.OK:
        return False

    # Containment.
    if 200 not in HTTPStatus:
        return False
    if 999 in HTTPStatus:
        return False
    if HTTPStatus.OK not in HTTPStatus:
        return False

    # Iteration yields the registered members.
    members = list(HTTPStatus)
    if len(members) != len(_STATUS_TABLE):
        return False
    if HTTPStatus.OK not in members:
        return False

    # Invalid lookup raises.
    try:
        HTTPStatus(999)
    except ValueError:
        pass
    else:
        return False

    return True


def http2_method():
    """Verify the HTTPMethod implementation."""
    expected = [
        "CONNECT", "DELETE", "GET", "HEAD",
        "OPTIONS", "PATCH", "POST", "PUT", "TRACE",
    ]
    for name in expected:
        member = getattr(HTTPMethod, name, None)
        if member is None:
            return False
        if str(member) != name:
            return False
        if member.name != name:
            return False
        if member.value != name:
            return False

    # Lookup by value.
    if HTTPMethod("GET") is not HTTPMethod.GET:
        return False
    if HTTPMethod["POST"] is not HTTPMethod.POST:
        return False

    # Containment.
    if "GET" not in HTTPMethod:
        return False
    if "FROBNICATE" in HTTPMethod:
        return False
    if HTTPMethod.GET not in HTTPMethod:
        return False

    # Iteration.
    members = list(HTTPMethod)
    if len(members) != len(expected):
        return False

    # Invalid lookup raises.
    try:
        HTTPMethod("FROBNICATE")
    except ValueError:
        pass
    else:
        return False

    return True


def http2_categories():
    """Verify category classification of HTTP status codes."""
    # Spot-check the boolean ``is_*`` properties.
    checks = [
        (HTTPStatus.CONTINUE,
         (True, False, False, False, False)),
        (HTTPStatus.OK,
         (False, True, False, False, False)),
        (HTTPStatus.CREATED,
         (False, True, False, False, False)),
        (HTTPStatus.MOVED_PERMANENTLY,
         (False, False, True, False, False)),
        (HTTPStatus.NOT_FOUND,
         (False, False, False, True, False)),
        (HTTPStatus.IM_A_TEAPOT,
         (False, False, False, True, False)),
        (HTTPStatus.INTERNAL_SERVER_ERROR,
         (False, False, False, False, True)),
        (HTTPStatus.SERVICE_UNAVAILABLE,
         (False, False, False, False, True)),
    ]
    for member, expected in checks:
        actual = (
            member.is_informational,
            member.is_success,
            member.is_redirection,
            member.is_client_error,
            member.is_server_error,
        )
        if actual != expected:
            return False

    # Exactly one category must be true for any valid code.
    for member in HTTPStatus:
        flags = [
            member.is_informational,
            member.is_success,
            member.is_redirection,
            member.is_client_error,
            member.is_server_error,
        ]
        if sum(1 for f in flags if f) != 1:
            return False

    # The textual helper agrees with the boolean properties.
    category_checks = [
        (100, "informational"),
        (200, "success"),
        (301, "redirection"),
        (404, "client_error"),
        (500, "server_error"),
    ]
    for code, expected in category_checks:
        if status_category(code) != expected:
            return False

    # Out-of-range codes are rejected.
    try:
        status_category(999)
    except ValueError:
        pass
    else:
        return False

    return True


__all__ = [
    "HTTPStatus",
    "HTTPMethod",
    "status_category",
    "http2_status",
    "http2_method",
    "http2_categories",
]